"""
Feature serving engine for real-time and batch feature retrieval
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import redis.asyncio as redis
from core.config import settings
from core.logging import log_feature_access
from models.feature_set import FeatureSet
from redis.asyncio import ConnectionPool

logger = logging.getLogger(__name__)


class ServingEngine:
    """High-performance feature serving engine"""

    def __init__(self, storage):
        self.storage = storage
        self.redis_pool: Optional[ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.cache_enabled = settings.SERVING_CACHE_ENABLED
        self.cache_ttl = settings.SERVING_CACHE_TTL

    async def start(self):
        """Initialize serving engine"""
        if self.cache_enabled and settings.ONLINE_STORE_ENABLED:
            try:
                # Create Redis connection pool
                self.redis_pool = ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    decode_responses=True,
                )
                self.redis_client = redis.Redis(connection_pool=self.redis_pool)

                # Test connection
                await self.redis_client.ping()
                logger.info("Feature serving engine initialized with Redis cache")

            except Exception as e:
                logger.warning(
                    f"Failed to connect to Redis: {e}. Running without cache."
                )
                self.cache_enabled = False
        else:
            logger.info("Feature serving engine initialized without cache")

    async def stop(self):
        """Cleanup serving engine resources"""
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()

    async def get_online_features(
        self,
        feature_sets: List[str],
        entities: Dict[str, List[str]],
        features: Optional[List[str]] = None,
    ) -> Dict[str, Dict[str, any]]:
        """
        Get features from online store for serving

        Args:
            feature_sets: List of feature set names
            entities: Entity type to entity IDs mapping
            features: Optional list of specific features

        Returns:
            Entity ID to features mapping
        """
        start_time = time.time()
        cache_hits = 0
        total_lookups = 0

        try:
            # Validate feature sets exist
            valid_feature_sets = await self._validate_feature_sets(feature_sets)

            # Get all features if not specified
            if not features:
                features = await self._get_all_features(valid_feature_sets)

            # Build result dictionary
            result = {}

            # Batch fetch features for all entities
            for entity_type, entity_ids in entities.items():
                for entity_id in entity_ids:
                    if entity_id not in result:
                        result[entity_id] = {}

                    # Try cache first
                    if self.cache_enabled:
                        cached_features = await self._get_cached_features(
                            entity_id, entity_type, features
                        )
                        if cached_features:
                            result[entity_id].update(cached_features)
                            cache_hits += len(cached_features)
                            total_lookups += len(features)
                            continue

                    # Fetch from storage
                    stored_features = await self._get_stored_features(
                        entity_id, entity_type, features, valid_feature_sets
                    )

                    if stored_features:
                        result[entity_id].update(stored_features)

                        # Update cache
                        if self.cache_enabled:
                            await self._cache_features(
                                entity_id, entity_type, stored_features
                            )

                    total_lookups += len(features)

            # Log access metrics
            latency_ms = (time.time() - start_time) * 1000
            cache_hit_rate = cache_hits / total_lookups if total_lookups > 0 else 0

            log_feature_access(
                feature_set=",".join(feature_sets),
                features=features,
                entity_ids=[id for ids in entities.values() for id in ids],
                latency_ms=latency_ms,
                cache_hit=cache_hit_rate > 0,
            )

            return result

        except Exception as e:
            logger.error(f"Error serving online features: {e}")
            raise

    async def get_historical_features(
        self,
        feature_sets: List[str],
        entity_df: pd.DataFrame,
        features: Optional[List[str]] = None,
        timestamp_column: str = "event_timestamp",
    ) -> pd.DataFrame:
        """
        Get point-in-time correct features for historical analysis

        Args:
            feature_sets: List of feature set names
            entity_df: DataFrame with entity IDs and timestamps
            features: Optional list of specific features
            timestamp_column: Name of timestamp column

        Returns:
            DataFrame with entity features at specified timestamps
        """
        start_time = time.time()

        try:
            # Validate inputs
            if timestamp_column not in entity_df.columns:
                raise ValueError(f"Timestamp column '{timestamp_column}' not found")

            # Validate feature sets
            valid_feature_sets = await self._validate_feature_sets(feature_sets)

            # Get all features if not specified
            if not features:
                features = await self._get_all_features(valid_feature_sets)

            # Initialize result dataframe
            result_df = entity_df.copy()

            # For each feature, get point-in-time values
            for feature_name in features:
                feature_values = []

                for idx, row in entity_df.iterrows():
                    # Get feature value at specified timestamp
                    value = await self._get_feature_at_timestamp(
                        entity_id=row.get("entity_id", row.get("id")),
                        feature_name=feature_name,
                        timestamp=row[timestamp_column],
                        feature_sets=valid_feature_sets,
                    )
                    feature_values.append(value)

                result_df[feature_name] = feature_values

            # Log metrics
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Retrieved {len(features)} historical features for "
                f"{len(entity_df)} entities in {latency_ms:.2f}ms"
            )

            return result_df

        except Exception as e:
            logger.error(f"Error retrieving historical features: {e}")
            raise

    async def _validate_feature_sets(self, feature_sets: List[str]) -> List[FeatureSet]:
        """Validate that feature sets exist and are active"""
        valid_sets = []

        for fs_name in feature_sets:
            feature_set = await self.storage.get_feature_set_by_name(fs_name)
            if not feature_set:
                raise ValueError(f"Feature set '{fs_name}' not found")
            if feature_set.status != "active":
                raise ValueError(f"Feature set '{fs_name}' is not active")
            valid_sets.append(feature_set)

        return valid_sets

    async def _get_all_features(self, feature_sets: List[FeatureSet]) -> List[str]:
        """Get all feature names from feature sets"""
        features = []
        for fs in feature_sets:
            features.extend(fs.get_feature_names())
        return list(set(features))  # Remove duplicates

    async def _get_cached_features(
        self, entity_id: str, entity_type: str, features: List[str]
    ) -> Optional[Dict[str, any]]:
        """Get features from Redis cache"""
        if not self.redis_client:
            return None

        try:
            # Build cache keys
            cache_keys = [
                f"feature:{entity_type}:{entity_id}:{feature}" for feature in features
            ]

            # Batch get from Redis
            values = await self.redis_client.mget(cache_keys)

            # Build result
            result = {}
            for feature, value in zip(features, values):
                if value is not None:
                    result[feature] = json.loads(value)

            return result if result else None

        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
            return None

    async def _cache_features(
        self, entity_id: str, entity_type: str, features: Dict[str, any]
    ):
        """Cache features in Redis"""
        if not self.redis_client:
            return

        try:
            # Prepare cache entries
            pipe = self.redis_client.pipeline()

            for feature_name, value in features.items():
                cache_key = f"feature:{entity_type}:{entity_id}:{feature_name}"
                pipe.setex(cache_key, self.cache_ttl, json.dumps(value))

            await pipe.execute()

        except Exception as e:
            logger.warning(f"Cache update error: {e}")

    async def _get_stored_features(
        self,
        entity_id: str,
        entity_type: str,
        features: List[str],
        feature_sets: List[FeatureSet],
    ) -> Dict[str, any]:
        """Get features from storage"""
        result = {}

        # Get features from each feature set
        for feature_set in feature_sets:
            fs_features = await self.storage.get_features_for_entity(
                feature_set_id=feature_set.id,
                entity_id=entity_id,
                entity_type=entity_type,
                feature_names=features,
            )

            for feature_name, value in fs_features.items():
                if feature_name in features:
                    result[feature_name] = value

        return result

    async def _get_feature_at_timestamp(
        self,
        entity_id: str,
        feature_name: str,
        timestamp: datetime,
        feature_sets: List[FeatureSet],
    ) -> any:
        """Get feature value at specific timestamp"""
        # Find feature in feature sets
        for feature_set in feature_sets:
            feature = await self.storage.get_feature_by_name(
                feature_set_id=feature_set.id, feature_name=feature_name
            )

            if feature:
                # Get historical value
                value = await self.storage.get_feature_value_at_timestamp(
                    feature_id=feature.id, entity_id=entity_id, timestamp=timestamp
                )

                if value is not None:
                    return value
                elif feature.default_value is not None:
                    return feature.default_value

        return None

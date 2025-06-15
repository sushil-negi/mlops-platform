"""
Feature storage layer for Feature Store
Handles offline and online storage of features
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from core.config import settings
from core.database import get_db
from models.feature import Feature
from models.feature_set import FeatureSet
from models.feature_value import FeatureValue
from sqlalchemy import and_, desc

logger = logging.getLogger(__name__)


class FeatureStorage:
    """Manages feature storage in offline and online stores"""

    def __init__(self):
        self.offline_store = None
        self.online_store = None
        self.s3_client = None
        self.duckdb_conn = None

    async def initialize(self):
        """Initialize storage backends"""
        # Initialize offline store (S3/MinIO)
        if settings.STORAGE_BACKEND == "s3":
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                use_ssl=settings.S3_USE_SSL,
            )

            # Create bucket if it doesn't exist
            try:
                self.s3_client.head_bucket(Bucket=settings.S3_BUCKET)
            except Exception:
                self.s3_client.create_bucket(Bucket=settings.S3_BUCKET)

            logger.info(f"Initialized S3 storage with bucket: {settings.S3_BUCKET}")

        # Initialize compute engine (DuckDB)
        if settings.COMPUTE_ENGINE == "duckdb":
            self.duckdb_conn = duckdb.connect(":memory:")
            # Install and load httpfs for S3 access
            self.duckdb_conn.execute("INSTALL httpfs;")
            self.duckdb_conn.execute("LOAD httpfs;")

            # Configure S3 credentials for DuckDB
            if settings.STORAGE_BACKEND == "s3":
                self.duckdb_conn.execute(
                    f"""
                    SET s3_endpoint='{
                        settings.S3_ENDPOINT.replace("http://", "")
                        .replace("https://", "")
                    }';
                    SET s3_access_key_id='{settings.S3_ACCESS_KEY}';
                    SET s3_secret_access_key='{settings.S3_SECRET_KEY}';
                    SET s3_use_ssl={str(settings.S3_USE_SSL).lower()};
                """
                )

            logger.info("Initialized DuckDB compute engine")

    async def close(self):
        """Close storage connections"""
        if self.duckdb_conn:
            self.duckdb_conn.close()

    async def write_feature_values(
        self,
        feature_set: FeatureSet,
        feature_values: pd.DataFrame,
        mode: str = "append",
    ) -> str:
        """
        Write feature values to offline store

        Args:
            feature_set: Feature set to write to
            feature_values: DataFrame with feature values
            mode: Write mode - append or overwrite

        Returns:
            Path to written data
        """
        try:
            # Generate storage path
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = f"feature_sets/{feature_set.name}/data/{timestamp}.parquet"

            if settings.STORAGE_BACKEND == "s3":
                # Convert to parquet and upload to S3
                table = pa.Table.from_pandas(feature_values)

                # Write to buffer
                import io

                buffer = io.BytesIO()
                pq.write_table(table, buffer)
                buffer.seek(0)

                # Upload to S3
                s3_key = path
                self.s3_client.put_object(
                    Bucket=settings.S3_BUCKET,
                    Key=s3_key,
                    Body=buffer.getvalue(),
                )

                full_path = f"s3://{settings.S3_BUCKET}/{s3_key}"

            else:
                # Local file storage
                local_path = f"{settings.STORAGE_PATH}/{path}"
                import os

                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                feature_values.to_parquet(local_path)
                full_path = local_path

            logger.info(f"Wrote {len(feature_values)} rows to {full_path}")

            # Update feature set metadata
            await self._update_feature_set_stats(feature_set, len(feature_values))

            return full_path

        except Exception as e:
            logger.error(f"Error writing feature values: {e}")
            raise

    async def read_feature_values(
        self,
        feature_set: FeatureSet,
        features: Optional[List[str]] = None,
        entity_ids: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Read feature values from offline store

        Args:
            feature_set: Feature set to read from
            features: Optional list of features to read
            entity_ids: Optional list of entity IDs to filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            DataFrame with feature values
        """
        try:
            # Get data files for feature set
            data_files = await self._list_feature_set_files(feature_set)

            if not data_files:
                return pd.DataFrame()

            # Build query
            if settings.COMPUTE_ENGINE == "duckdb":
                # Create view from parquet files
                if settings.STORAGE_BACKEND == "s3":
                    file_pattern = (
                        f"s3://{settings.S3_BUCKET}/feature_sets/"
                        f"{feature_set.name}/data/*.parquet"
                    )
                else:
                    file_pattern = (
                        f"{settings.STORAGE_PATH}/feature_sets/"
                        f"{feature_set.name}/data/*.parquet"
                    )

                query = f"SELECT * FROM read_parquet('{file_pattern}')"

                # Add filters
                filters = []
                if entity_ids:
                    entity_filter = " OR ".join(
                        [f"entity_id = '{eid}'" for eid in entity_ids]
                    )
                    filters.append(f"({entity_filter})")

                if start_date:
                    filters.append(f"event_timestamp >= '{start_date.isoformat()}'")

                if end_date:
                    filters.append(f"event_timestamp <= '{end_date.isoformat()}'")

                if filters:
                    query += " WHERE " + " AND ".join(filters)

                # Select specific features
                if features:
                    columns = ["entity_id", "event_timestamp"] + features
                    query = query.replace("SELECT *", f"SELECT {', '.join(columns)}")

                # Execute query
                result_df = self.duckdb_conn.execute(query).df()

                return result_df

        except Exception as e:
            logger.error(f"Error reading feature values: {e}")
            raise

    async def get_feature_set_by_name(self, name: str) -> Optional[FeatureSet]:
        """Get feature set by name"""
        db = next(get_db())
        try:
            feature_set = db.query(FeatureSet).filter(FeatureSet.name == name).first()
            return feature_set
        finally:
            db.close()

    async def get_features_for_entity(
        self,
        feature_set_id: str,
        entity_id: str,
        entity_type: str,
        feature_names: List[str],
    ) -> Dict[str, any]:
        """Get latest feature values for an entity"""
        db = next(get_db())
        try:
            # Get features from database
            features = (
                db.query(Feature)
                .filter(
                    and_(
                        Feature.feature_set_id == feature_set_id,
                        Feature.name.in_(feature_names),
                    )
                )
                .all()
            )

            result = {}

            for feature in features:
                # Get latest value for this feature
                value_record = (
                    db.query(FeatureValue)
                    .filter(
                        and_(
                            FeatureValue.feature_id == feature.id,
                            FeatureValue.entity_id == entity_id,
                            FeatureValue.entity_type == entity_type,
                        )
                    )
                    .order_by(desc(FeatureValue.event_timestamp))
                    .first()
                )

                if value_record:
                    result[feature.name] = value_record.get_value()
                elif feature.default_value is not None:
                    result[feature.name] = feature.default_value

            return result

        finally:
            db.close()

    async def get_feature_by_name(
        self, feature_set_id: str, feature_name: str
    ) -> Optional[Feature]:
        """Get feature by name within a feature set"""
        db = next(get_db())
        try:
            feature = (
                db.query(Feature)
                .filter(
                    and_(
                        Feature.feature_set_id == feature_set_id,
                        Feature.name == feature_name,
                    )
                )
                .first()
            )
            return feature
        finally:
            db.close()

    async def get_feature_value_at_timestamp(
        self, feature_id: str, entity_id: str, timestamp: datetime
    ) -> any:
        """Get feature value at specific timestamp"""
        db = next(get_db())
        try:
            # Get the most recent value before or at the timestamp
            value_record = (
                db.query(FeatureValue)
                .filter(
                    and_(
                        FeatureValue.feature_id == feature_id,
                        FeatureValue.entity_id == entity_id,
                        FeatureValue.event_timestamp <= timestamp,
                    )
                )
                .order_by(desc(FeatureValue.event_timestamp))
                .first()
            )

            if value_record:
                return value_record.get_value()

            return None

        finally:
            db.close()

    async def materialize_features(
        self, feature_set: FeatureSet, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Materialize features for a date range

        Args:
            feature_set: Feature set to materialize
            start_date: Start date for materialization
            end_date: End date for materialization

        Returns:
            Materialization statistics
        """
        try:
            logger.info(
                f"Starting materialization for {feature_set.name} "
                f"from {start_date} to {end_date}"
            )

            # Get source data based on feature set configuration
            source_data = await self._get_source_data(feature_set, start_date, end_date)

            if source_data.empty:
                logger.warning(f"No source data found for {feature_set.name}")
                return {"rows_processed": 0, "status": "no_data"}

            # Apply transformations for each feature
            transformed_data = await self._apply_transformations(
                feature_set, source_data
            )

            # Write to offline store
            output_path = await self.write_feature_values(feature_set, transformed_data)

            # Update online store if enabled
            if settings.ONLINE_STORE_ENABLED and feature_set.online_enabled:
                await self._update_online_store(feature_set, transformed_data)

            # Update feature set metadata
            stats = {
                "rows_processed": len(transformed_data),
                "status": "success",
                "output_path": output_path,
                "duration_seconds": 0,  # Would be calculated
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }

            return stats

        except Exception as e:
            logger.error(f"Error materializing features: {e}")
            raise

    async def _list_feature_set_files(self, feature_set: FeatureSet) -> List[str]:
        """List all data files for a feature set"""
        files = []

        if settings.STORAGE_BACKEND == "s3":
            prefix = f"feature_sets/{feature_set.name}/data/"

            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=prefix)

            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        if obj["Key"].endswith(".parquet"):
                            files.append(f"s3://{settings.S3_BUCKET}/{obj['Key']}")

        else:
            # Local file system
            import os

            data_dir = (
                f"{settings.STORAGE_PATH}/feature_sets/" f"{feature_set.name}/data/"
            )
            if os.path.exists(data_dir):
                for file in os.listdir(data_dir):
                    if file.endswith(".parquet"):
                        files.append(os.path.join(data_dir, file))

        return files

    async def _update_feature_set_stats(self, feature_set: FeatureSet, row_count: int):
        """Update feature set statistics"""
        db = next(get_db())
        try:
            feature_set.last_materialization = datetime.utcnow()
            feature_set.row_count = (feature_set.row_count or 0) + row_count
            db.commit()
        finally:
            db.close()

    async def _get_source_data(
        self, feature_set: FeatureSet, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """Get source data for feature set"""
        # This would be implemented based on source_config
        # For now, return empty DataFrame
        return pd.DataFrame()

    async def _apply_transformations(
        self, feature_set: FeatureSet, source_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Apply feature transformations"""
        # This would apply SQL/Python transformations defined in features
        # For now, return source data as-is
        return source_data

    async def _update_online_store(self, feature_set: FeatureSet, data: pd.DataFrame):
        """Update online store with latest feature values"""
        # This would update Redis or other online store
        # Implementation depends on online store backend

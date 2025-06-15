"""
Entity model for Feature Store
"""

from datetime import datetime
from enum import Enum
from typing import Dict
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

from core.database import Base


class EntityType(str, Enum):
    """Entity types"""

    USER = "user"
    ITEM = "item"
    SESSION = "session"
    TRANSACTION = "transaction"
    DEVICE = "device"
    LOCATION = "location"
    MERCHANT = "merchant"
    CUSTOM = "custom"


class Entity(Base):
    """Entity definition model"""

    __tablename__ = "entities"

    # Primary key
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Entity identification
    name = Column(String(255), nullable=False, unique=True)
    entity_type = Column(SQLEnum(EntityType), nullable=False)

    # Metadata
    description = Column(Text)
    value_type = Column(String(50), nullable=False)  # string, int, uuid
    join_keys = Column(JSON, default=list)  # column names used for joining

    # Configuration
    properties = Column(JSON, default=dict)
    tags = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))

    # Indexes
    __table_args__ = (
        Index("idx_entity_name", "name"),
        Index("idx_entity_type", "entity_type"),
    )

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "id": str(self.id),
            "name": self.name,
            "entity_type": self.entity_type.value if self.entity_type else None,
            "description": self.description,
            "value_type": self.value_type,
            "join_keys": self.join_keys or [],
            "properties": self.properties or {},
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

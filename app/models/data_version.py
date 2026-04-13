from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class DataVersion(BaseModel):
    """
    Track versions of input data used for predictions.
    Allows answering: "What data did we have when we made this prediction?"
    """
    
    __tablename__ = "data_versions"
    
    version_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )  # SHA256 of input data
    
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # match, player, team
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    snapshot_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    
    __table_args__ = (
        Index("ix_data_versions_entity", "entity_type", "entity_id", "created_at"),
    )
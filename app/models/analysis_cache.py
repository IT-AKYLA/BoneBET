from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, JSON, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AnalysisCache(BaseModel):
    """
    Short-lived cache for AI predictions on upcoming/live matches.
    Prevents duplicate LLM calls within a short time window.
    Invalidated when match starts or player data updates.
    """
    
    __tablename__ = "analysis_cache"
    
    # Cache key
    match_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        default="pre_match",
    )  # pre_match, live
    
    # Snapshot reference (which data version was used)
    data_snapshot_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )  # Hash of input data, used for invalidation
    
    # AI Output
    prediction_team_a_win: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detailed_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_matchups: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    map_predictions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    llm_provider: Mapped[str] = mapped_column(String(50), default="openai")
    llm_model: Mapped[str] = mapped_column(String(100), default="gpt-4-turbo-preview")
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Expiry (short TTL)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.utcnow() + timedelta(hours=1),
    )
    
    __table_args__ = (
        Index("ix_analysis_cache_match_type", "match_id", "analysis_type"),
    )
    
    def __repr__(self) -> str:
        return f"<AnalysisCache(match_id={self.match_id}, type='{self.analysis_type}')>"
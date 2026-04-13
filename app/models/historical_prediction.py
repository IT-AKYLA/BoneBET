from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, JSON, Index, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class HistoricalPrediction(BaseModel):
    """
    Permanent archive of predictions vs actual results.
    Used for:
    - Model performance tracking
    - Training future models
    - Analytics dashboards
    """
    
    __tablename__ = "historical_predictions"
    
    # Match reference
    match_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Teams at time of prediction
    team_a_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    team_b_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    team_a_name: Mapped[str] = mapped_column(String(100), nullable=False)
    team_b_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Prediction
    predicted_winner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    predicted_team_a_win_prob: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Context (snapshot of data used)
    team_a_bone_score_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    team_b_bone_score_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    team_a_ranking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    team_b_ranking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Input data snapshot (full player stats used)
    input_data_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # AI metadata
    llm_provider: Mapped[str] = mapped_column(String(50), default="openai")
    llm_model: Mapped[str] = mapped_column(String(100), default="gpt-4-turbo-preview")
    prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    analysis_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Actual result (filled after match)
    actual_winner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_team_a_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_team_b_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    was_upset: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # Underdog won
    prediction_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # Timestamps
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    result_recorded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    match: Mapped["Match"] = relationship("Match")
    
    __table_args__ = (
        Index("ix_historical_predictions_match", "match_id"),
        Index("ix_historical_predictions_correct", "prediction_correct"),
        Index("ix_historical_predictions_predicted_at", "predicted_at"),
    )
    
    def __repr__(self) -> str:
        return f"<HistoricalPrediction(match_id={self.match_id}, correct={self.prediction_correct})>"
    
    @property
    def prediction_accuracy(self) -> Optional[float]:
        """How close was probability to actual outcome? Brier score component."""
        if self.actual_winner_id is None:
            return None
        actual = 1.0 if self.actual_winner_id == self.team_a_id else 0.0
        return 1.0 - (self.predicted_team_a_win_prob - actual) ** 2
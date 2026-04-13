from datetime import date
from typing import Optional

from sqlalchemy import String, Integer, Float, Date, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class MetricSnapshot(BaseModel):
    """Daily snapshot of player/team metrics for trend analysis."""
    
    __tablename__ = "metric_snapshots"
    
    # What this snapshot is for
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Foreign keys
    player_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=True,
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
    )
    
    # Core metrics at snapshot time
    bone_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    true_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    form_trend: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Player-specific snapshot metrics
    faceit_elo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    official_rating_20: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    official_rating_5: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adr_30d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    kd_30d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Team-specific snapshot metrics
    world_ranking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    team_synergy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    win_rate_30d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Raw data backup
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    player: Mapped[Optional["Player"]] = relationship("Player", back_populates="snapshots")
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="snapshots")
    
    __table_args__ = (
        Index("ix_metric_snapshots_entity_date", "entity_type", "entity_id", "snapshot_date"),
        Index("ix_metric_snapshots_player_date", "player_id", "snapshot_date"),
        Index("ix_metric_snapshots_team_date", "team_id", "snapshot_date"),
    )
    
    def __repr__(self) -> str:
        return f"<MetricSnapshot(entity='{self.entity_type}', id={self.entity_id}, date={self.snapshot_date})>"
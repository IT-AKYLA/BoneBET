from typing import List, Optional
from datetime import date

from sqlalchemy import String, Integer, Float, Date, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Player(BaseModel):
    """Player model - stores basic info and current stats from API."""
    
    __tablename__ = "players"
    
    # Basic info
    nickname: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    
    # Current team (from API)
    current_team_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    current_team_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # FACEIT stats (from API)
    faceit_elo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    faceit_skill_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    faceit_kd_30d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    faceit_adr_30d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    faceit_winrate_30d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    faceit_matches_30d: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    faceit_last_updated: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Official stats (from API)
    official_total_matches: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    official_avg_kd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    official_avg_adr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    official_avg_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    official_last_updated: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # BoneBET calculated metrics
    bone_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    true_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    form_trend: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # rising, falling, stable
    consistency_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_sync_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Relationships
    match_stats: Mapped[List["PlayerMatchStats"]] = relationship(
        "PlayerMatchStats",
        back_populates="player",
        cascade="all, delete-orphan",
    )
    snapshots: Mapped[List["MetricSnapshot"]] = relationship(
        "MetricSnapshot",
        back_populates="player",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_players_active_score", "is_active", "bone_score"),
        Index("ix_players_nickname_active", "nickname", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Player(nickname='{self.nickname}', bone_score={self.bone_score})>"
    
    @property
    def kd_ratio_combined(self) -> Optional[float]:
        """Get best available K/D ratio."""
        return self.official_avg_kd or self.faceit_kd_30d
    
    @property
    def rating_combined(self) -> Optional[float]:
        """Get best available rating."""
        return self.official_avg_rating
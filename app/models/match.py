from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import BaseModel


class MatchStatus(str, enum.Enum):
    """Match status enum."""
    UPCOMING = "upcoming"
    LIVE = "live"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class MatchFormat(str, enum.Enum):
    """Match format enum."""
    BO1 = "bo1"
    BO3 = "bo3"
    BO5 = "bo5"


class Match(BaseModel):
    """Match model - stores match info and results from API."""
    
    __tablename__ = "matches"
    
    # Match identification
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(20), default="bo3")  # faceit, bo3, hltv
    
    # Teams
    team_a_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_b_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_a_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    team_b_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    winner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Match info
    tournament_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tournament_tier: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # S, A, B, C
    format: Mapped[MatchFormat] = mapped_column(
        Enum(MatchFormat),
        default=MatchFormat.BO3,
    )
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus),
        default=MatchStatus.UPCOMING,
        index=True,
    )
    
    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Maps played
    maps_played: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Additional info
    vod_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    prize_pool: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    team_a: Mapped[Optional["Team"]] = relationship(
        "Team",
        foreign_keys=[team_a_id],
        back_populates="matches_as_team_a",
    )
    team_b: Mapped[Optional["Team"]] = relationship(
        "Team",
        foreign_keys=[team_b_id],
        back_populates="matches_as_team_b",
    )
    player_stats: Mapped[List["PlayerMatchStats"]] = relationship(
        "PlayerMatchStats",
        back_populates="match",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_matches_status_scheduled", "status", "scheduled_at"),
        Index("ix_matches_teams", "team_a_id", "team_b_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Match(team_a_id={self.team_a_id}, team_b_id={self.team_b_id}, status='{self.status}')>"
    
    @property
    def is_finished(self) -> bool:
        return self.status == MatchStatus.FINISHED
    
    @property
    def is_live(self) -> bool:
        return self.status == MatchStatus.LIVE
    
    @property
    def is_upcoming(self) -> bool:
        return self.status == MatchStatus.UPCOMING
    
    @property
    def winner_team_id(self) -> Optional[int]:
        """Determine winner based on scores."""
        if not self.is_finished:
            return None
        if self.team_a_score is None or self.team_b_score is None:
            return None
        if self.team_a_score > self.team_b_score:
            return self.team_a_id
        elif self.team_b_score > self.team_a_score:
            return self.team_b_id
        return None
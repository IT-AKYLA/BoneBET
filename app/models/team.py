from typing import List, Optional
import json

from sqlalchemy import String, Integer, Float, Boolean, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Team(BaseModel):
    """Team model - stores current team info from API."""
    
    __tablename__ = "teams"
    
    # Basic info
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    short_name: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  
    
    # Rankings (from API)
    world_ranking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    ranking_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ranking_change: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  
    peak_ranking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Team stats (from API)
    total_matches: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    win_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # BoneBET calculated metrics
    team_synergy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carry_dependency: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    momentum_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Current roster (JSON array of player nicknames from API)
    current_roster_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_sync_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    matches_as_team_a: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.team_a_id",
        back_populates="team_a",
    )
    matches_as_team_b: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.team_b_id",
        back_populates="team_b",
    )
    snapshots: Mapped[List["MetricSnapshot"]] = relationship(
        "MetricSnapshot",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index("ix_teams_active_ranking", "is_active", "world_ranking"),
        Index("ix_teams_name_active", "name", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Team(name='{self.name}', ranking={self.world_ranking})>"
    
    @property
    def ranking_trend(self) -> str:
        """Return ranking trend direction."""
        if self.ranking_change is None:
            return "unknown"
        if self.ranking_change > 0:
            return "up"
        elif self.ranking_change < 0:
            return "down"
        return "stable"
    
    @property
    def current_roster(self) -> List[str]:
        """Get current roster as list of nicknames."""
        if not self.current_roster_json:
            return []
        try:
            return json.loads(self.current_roster_json)
        except json.JSONDecodeError:
            return []
    
    def set_current_roster(self, roster: List[str]) -> None:
        """Set current roster from list of nicknames."""
        self.current_roster_json = json.dumps(roster)
    
    @property
    def roster_size(self) -> int:
        """Get number of players in current roster."""
        return len(self.current_roster)
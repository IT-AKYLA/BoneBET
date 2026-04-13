from typing import Optional

from sqlalchemy import String, Integer, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PlayerMatchStats(BaseModel):
    """Player statistics for a specific match from API."""
    
    __tablename__ = "player_match_stats"
    
    # Foreign keys
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Map info
    map_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    map_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Core stats
    kills: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    adr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    
    # Advanced stats (if available from API)
    kast: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    impact: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    headshot_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    utility_damage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    first_kills: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    first_deaths: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clutches_won: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="match_stats")
    match: Mapped["Match"] = relationship("Match", back_populates="player_stats")
    
    __table_args__ = (
        UniqueConstraint("player_id", "match_id", "map_name", name="uq_player_match_map"),
        Index("ix_player_match_stats_player_rating", "player_id", "rating"),
        Index("ix_player_match_stats_match_player", "match_id", "player_id"),
    )
    
    def __repr__(self) -> str:
        return f"<PlayerMatchStats(player_id={self.player_id}, match_id={self.match_id}, rating={self.rating})>"
    
    @property
    def kd_ratio(self) -> float:
        """Calculate K/D ratio."""
        if self.deaths == 0:
            return float(self.kills)
        return round(self.kills / self.deaths, 2)
    
    @property
    def kpr(self) -> float:
        """Kills per round (estimate)."""
        return round(self.kills / 30.0, 2)
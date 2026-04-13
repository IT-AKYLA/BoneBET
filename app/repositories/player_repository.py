from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player


class PlayerRepository:
    """Repository for Player model."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_nickname(self, nickname: str) -> Optional[Player]:
        """Get player by nickname."""
        result = await self.session.execute(
            select(Player).where(Player.nickname == nickname)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, player_id: int) -> Optional[Player]:
        """Get player by ID."""
        result = await self.session.execute(
            select(Player).where(Player.id == player_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_active(self, limit: int = 100) -> List[Player]:
        """Get all active players."""
        result = await self.session.execute(
            select(Player)
            .where(Player.is_active == True)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, player: Player) -> Player:
        """Create new player."""
        self.session.add(player)
        await self.session.flush()
        return player
    
    async def update(self, player: Player) -> Player:
        """Update existing player."""
        await self.session.merge(player)
        await self.session.flush()
        return player
    
    async def create_or_update(self, player: Player) -> Player:
        """Create or update player based on nickname."""
        existing = await self.get_by_nickname(player.nickname)
        if existing:
            # Update existing
            existing.current_team_id = player.current_team_id
            existing.current_team_name = player.current_team_name
            existing.faceit_elo = player.faceit_elo
            existing.faceit_kd_30d = player.faceit_kd_30d
            existing.faceit_adr_30d = player.faceit_adr_30d
            existing.faceit_winrate_30d = player.faceit_winrate_30d
            existing.faceit_matches_30d = player.faceit_matches_30d
            existing.official_avg_rating = player.official_avg_rating
            existing.official_avg_kd = player.official_avg_kd
            existing.official_avg_adr = player.official_avg_adr
            existing.official_total_matches = player.official_total_matches
            existing.last_sync_at = player.last_sync_at
            return await self.update(existing)
        else:
            # Create new
            return await self.create(player)
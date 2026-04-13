from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import Team


class TeamRepository:
    """Repository for Team model."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_name(self, name: str) -> Optional[Team]:
        """Get team by name."""
        result = await self.session.execute(
            select(Team).where(Team.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, team_id: int) -> Optional[Team]:
        """Get team by ID."""
        result = await self.session.execute(
            select(Team).where(Team.id == team_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_active(self, limit: int = 50) -> List[Team]:
        """Get all active teams."""
        result = await self.session.execute(
            select(Team)
            .where(Team.is_active == True)
            .order_by(Team.world_ranking)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, team: Team) -> Team:
        """Create new team."""
        self.session.add(team)
        await self.session.flush()
        return team
    
    async def update(self, team: Team) -> Team:
        """Update existing team."""
        await self.session.merge(team)
        await self.session.flush()
        return team
    
    async def create_or_update(self, team: Team) -> Team:
        """Create or update team based on name."""
        existing = await self.get_by_name(team.name)
        if existing:
            # Update existing
            existing.short_name = team.short_name
            existing.logo_url = team.logo_url
            existing.country = team.country
            existing.region = team.region
            existing.world_ranking = team.world_ranking
            existing.ranking_points = team.ranking_points
            existing.ranking_change = team.ranking_change
            existing.total_matches = team.total_matches
            existing.win_rate = team.win_rate
            existing.avg_rating = team.avg_rating
            existing.current_roster_json = team.current_roster_json
            existing.last_sync_at = team.last_sync_at
            return await self.update(existing)
        else:
            # Create new
            return await self.create(team)
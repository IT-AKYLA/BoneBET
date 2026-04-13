from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.player_service import PlayerService
from app.services.team_service import TeamService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SyncService:
    """Orchestrates data synchronization from CS2 Analytics API."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.player_service = PlayerService(session)
        self.team_service = TeamService(session)
    
    async def sync_all(self, top_teams_limit: int = 30) -> dict:
        """
        Full synchronization: teams and their players.
        
        Returns:
            Dict with sync statistics
        """
        logger.info("Starting full sync...")
        
        stats = {
            "teams_synced": 0,
            "players_synced": 0,
            "errors": [],
        }
        
        try:
            # 1. Sync top teams
            teams = await self.team_service.sync_top_teams(limit=top_teams_limit)
            stats["teams_synced"] = len(teams)
            
            # 2. Sync players from each team
            for team in teams:
                try:
                    players = await self.player_service.sync_team_roster(
                        team_id=team.id,
                        team_name=team.name,
                    )
                    stats["players_synced"] += len(players)
                except Exception as e:
                    error_msg = f"Failed to sync roster for {team.name}: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            await self.session.commit()
            logger.info(f"Full sync completed: {stats}")
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Full sync failed: {e}")
            raise
        
        return stats
    
    async def sync_specific_players(self, nicknames: List[str]) -> List:
        """Sync specific players by nickname."""
        return await self.player_service.sync_players(nicknames)
    
    async def close(self):
        """Close all clients."""
        await self.player_service.close()
        await self.team_service.close()
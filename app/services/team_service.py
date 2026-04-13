from datetime import datetime
import json
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.cs2_analytics import CS2AnalyticsClient
from app.clients.exceptions import TeamNotFoundError
from app.models.team import Team
from app.repositories.team_repository import TeamRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TeamService:
    """Service for managing teams."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = TeamRepository(session)
        self.client = CS2AnalyticsClient()
    
    async def sync_team(self, team_id: int) -> Optional[Team]:
        """Fetch team from API and save to database."""
        try:
            logger.info(f"Fetching team: {team_id}")
            api_data = await self.client.get_team(team_id, wait_for_loading=True)
            
            team = self._map_api_to_model(api_data)
            saved_team = await self.repository.create_or_update(team)
            logger.info(f"Saved team: {saved_team.name} (ID: {saved_team.id})")
            
            return saved_team
            
        except TeamNotFoundError:
            logger.warning(f"Team not found: {team_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to sync team {team_id}: {e}")
            raise
    
    async def sync_top_teams(self, limit: int = 30) -> List[Team]:
        """Sync top teams from rankings."""
        try:
            logger.info(f"Fetching top {limit} teams")
            rankings = await self.client.get_team_rankings(limit=limit)
            
            teams = []
            for team_data in rankings:
                team_id = team_data.get("id")
                if team_id:
                    team = await self.sync_team(team_id)
                    if team:
                        teams.append(team)
            
            logger.info(f"Synced {len(teams)} teams")
            return teams
            
        except Exception as e:
            logger.error(f"Failed to sync top teams: {e}")
            return []
    
    def _map_api_to_model(self, api_data: dict) -> Team:
        """Map API response to Team model."""
        team = Team(
            name=api_data.get("name"),
            short_name=api_data.get("short_name"),
            logo_url=api_data.get("logo_url"),
            country=api_data.get("country"),
            region=api_data.get("region"),
            world_ranking=api_data.get("world_ranking"),
            ranking_points=api_data.get("ranking_points"),
            ranking_change=api_data.get("ranking_change"),
            total_matches=api_data.get("total_matches"),
            win_rate=api_data.get("win_rate"),
            avg_rating=api_data.get("avg_rating"),
            is_active=True,
            last_sync_at=datetime.utcnow().isoformat(),
        )
        
        # Roster
        players = api_data.get("players", [])
        if players:
            roster_nicknames = [p.get("nickname") for p in players if p.get("nickname")]
            team.current_roster_json = json.dumps(roster_nicknames)
        
        return team
    
    async def close(self):
        """Close API client."""
        await self.client.close()
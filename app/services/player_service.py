from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.cs2_analytics import CS2AnalyticsClient
from app.clients.exceptions import PlayerNotFoundError, DataLoadingError
from app.models.player import Player
from app.repositories.player_repository import PlayerRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlayerService:
    """Service for managing players."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PlayerRepository(session)
        self.client = CS2AnalyticsClient()
    
    async def sync_player(self, nickname: str) -> Optional[Player]:
        """
        Fetch player from API and save to database.
        
        Args:
            nickname: Player nickname
            
        Returns:
            Saved Player object or None if not found
        """
        try:
            # Fetch from API
            logger.info(f"Fetching player: {nickname}")
            api_data = await self.client.get_player(nickname, wait_for_loading=True)
            
            # Map API data to Player model
            player = self._map_api_to_model(api_data)
            
            # Save to DB
            saved_player = await self.repository.create_or_update(player)
            logger.info(f"Saved player: {nickname} (ID: {saved_player.id})")
            
            return saved_player
            
        except PlayerNotFoundError:
            logger.warning(f"Player not found: {nickname}")
            return None
        except DataLoadingError:
            logger.warning(f"Player data still loading: {nickname}")
            return None
        except Exception as e:
            logger.error(f"Failed to sync player {nickname}: {e}")
            raise
    
    async def sync_players(self, nicknames: list[str]) -> list[Player]:
        """Sync multiple players."""
        players = []
        for nickname in nicknames:
            player = await self.sync_player(nickname)
            if player:
                players.append(player)
        return players
    
    async def sync_team_roster(self, team_id: int, team_name: str) -> list[Player]:
        """Sync all players from a team."""
        try:
            # Get team data from API
            api_team = await self.client.get_team(team_id)
            
            # Extract player nicknames from roster
            roster = api_team.get("players", [])
            nicknames = [p.get("nickname") for p in roster if p.get("nickname")]
            
            logger.info(f"Syncing {len(nicknames)} players from {team_name}")
            
            players = []
            for nickname in nicknames:
                player = await self.sync_player(nickname)
                if player:
                    # Update team affiliation
                    player.current_team_id = team_id
                    player.current_team_name = team_name
                    await self.repository.update(player)
                    players.append(player)
            
            return players
            
        except Exception as e:
            logger.error(f"Failed to sync roster for team {team_name}: {e}")
            return []
    
    def _map_api_to_model(self, api_data: dict) -> Player:
        """Map API response to Player model."""
        player = Player(
            nickname=api_data.get("nickname"),
            first_name=api_data.get("first_name"),
            last_name=api_data.get("last_name"),
            country=api_data.get("country"),
            current_team_id=api_data.get("team_id"),
            is_active=True,
            last_sync_at=date.today(),
        )
        
        # FACEIT stats
        faceit = api_data.get("faceit_stats", {})
        if faceit:
            player.faceit_elo = faceit.get("elo")
            player.faceit_skill_level = faceit.get("skill_level")
            player.faceit_kd_30d = faceit.get("avg_kd_30d")
            player.faceit_adr_30d = faceit.get("avg_adr_30d")
            player.faceit_winrate_30d = faceit.get("win_rate_30d")
            player.faceit_matches_30d = faceit.get("matches_30d")
        
        # Official stats
        official = api_data.get("official_stats", {})
        if official:
            player.official_avg_rating = official.get("avg_rating")
            player.official_avg_kd = official.get("avg_kd")
            player.official_avg_adr = official.get("avg_adr")
            player.official_total_matches = official.get("total_matches")
        
        return player
    
    async def close(self):
        """Close API client."""
        await self.client.close()
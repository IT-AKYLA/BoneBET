"""CS2 Analytics API client."""

import asyncio
from typing import Optional, Dict, Any, List

from app.clients.base import BaseHTTPClient
from app.clients.exceptions import (
    PlayerNotFoundError,
    TeamNotFoundError,
    DataLoadingError,
    CS2APIError,
)
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CS2AnalyticsClient:
    """Client for CS2 Analytics API."""
    
    def __init__(self):
        settings = get_settings()
        self.http = BaseHTTPClient(
            base_url=settings.CS2_API_BASE_URL,
            timeout=settings.CS2_API_TIMEOUT,
            max_retries=settings.CS2_API_MAX_RETRIES,
        )
        self._loading_wait_time = 5  # Seconds to wait if data is loading
    
    async def close(self) -> None:
        """Close client."""
        await self.http.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return await self.http.get("/health")
    
    # ==================== PLAYERS ====================
    
    async def get_player(
        self,
        nickname: str,
        wait_for_loading: bool = True,
        max_wait_attempts: int = 12,  # 12 * 5s = 60s max wait
    ) -> Dict[str, Any]:
        """
        Get player by nickname.
        
        Args:
            nickname: Player nickname (e.g., "donk")
            wait_for_loading: If True, wait for background parsing to complete
            max_wait_attempts: Maximum number of wait attempts
        
        Returns:
            Player data including FACEIT and official stats
        """
        path = f"/api/v1/players/{nickname}"
        
        for attempt in range(max_wait_attempts if wait_for_loading else 1):
            try:
                data = await self.http.get(path)
            except Exception as e:
                # Check if 404 means player not found
                if "404" in str(e):
                    raise PlayerNotFoundError(f"Player '{nickname}' not found")
                raise
        
            loading_status = data.get("loading_status", "ready")
            
            if loading_status == "ready":
                return data
            
            if loading_status == "loading" and wait_for_loading:
                logger.info(
                    f"Player '{nickname}' data is loading, waiting... "
                    f"(attempt {attempt + 1}/{max_wait_attempts})"
                )
                await asyncio.sleep(self._loading_wait_time)
                continue
            
            # pending or loading but not waiting
            return data
        
        # Max attempts reached
        raise DataLoadingError("player", nickname)
    
    async def get_players(
        self,
        limit: int = 20,
        has_faceit: Optional[bool] = None,
        team_id: Optional[int] = None,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get list of players with filters."""
        params = {"limit": limit}
        if has_faceit is not None:
            params["has_faceit"] = str(has_faceit).lower()
        if team_id is not None:
            params["team_id"] = team_id
        if force_refresh:
            params["force_refresh"] = "true"
        
        return await self.http.get("/api/v1/players/", params=params)
    
    async def search_players(self, query: str) -> List[Dict[str, Any]]:
        """Search players by nickname."""
        return await self.http.get(f"/api/v1/players/search/{query}")
    
    async def get_player_matches(
        self,
        nickname: str,
        source: str = "all",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get player's match history."""
        params = {"source": source, "limit": limit}
        return await self.http.get(f"/api/v1/players/{nickname}/matches", params=params)
    
    async def get_team(
        self,
        team_id: int,
        wait_for_loading: bool = True,
    ) -> Dict[str, Any]:
        """Get team by ID."""
        path = f"/api/v1/teams/{team_id}"
        
        for attempt in range(12 if wait_for_loading else 1):
            try:
                data = await self.http.get(path)
            except Exception as e:
                if "404" in str(e):
                    raise TeamNotFoundError(f"Team with ID '{team_id}' not found")
                raise
            
            loading_status = data.get("loading_status", "ready")
            
            if loading_status == "ready":
                return data
            
            if loading_status == "loading" and wait_for_loading:
                logger.info(f"Team {team_id} data is loading, waiting...")
                await asyncio.sleep(self._loading_wait_time)
                continue
            
            return data
        
        raise DataLoadingError("team", str(team_id))
    
    async def get_teams(
        self,
        active_only: bool = True,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get list of teams."""
        params = {"active_only": str(active_only).lower(), "limit": limit}
        return await self.http.get("/api/v1/teams/", params=params)
    
    async def get_team_rankings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top teams with rankings."""
        params = {"limit": limit}
        return await self.http.get("/api/v1/teams/rankings", params=params)
    
    async def search_teams(self, query: str) -> List[Dict[str, Any]]:
        """Search teams by name."""
        return await self.http.get(f"/api/v1/teams/search/{query}")
    
    # ==================== MATCHES ====================
    
    async def get_live_matches(self) -> List[Dict[str, Any]]:
        """Get currently live matches."""
        return await self.http.get("/api/v1/matches/live")
    
    async def get_upcoming_matches(self) -> List[Dict[str, Any]]:
        """Get upcoming matches (from cache)."""
        return await self.http.get("/api/v1/matches/upcoming")
    
    async def get_team_matches(
        self,
        team_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get team's match history."""
        params = {"limit": limit}
        return await self.http.get(f"/api/v1/matches/team/{team_name}", params=params)
    
    async def load_team_matches(self, team_name: str) -> Dict[str, str]:
        """Trigger background loading of team matches."""
        return await self.http.post(f"/api/v1/matches/load/team/{team_name}")
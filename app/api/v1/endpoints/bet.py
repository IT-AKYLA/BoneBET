"""Bet endpoint with Redis caching."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.services.bet_service import BetService
from app.api.v1.schemas.bet import BetResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/")
async def get_bet_analysis(
    limit: int = Query(10, description="Maximum matches to analyze"),
    tier_filter: str = Query("all", description="Filter: all, tier1"),
    use_ai: bool = Query(True, description="Use AI for analysis"),
    force_refresh: bool = Query(False, description="Force refresh cache"),
):
    """
    Get betting analysis for live and upcoming matches.
    
    - Fetches matches from CS2 Analytics API
    - Filters by tier (tier1 = top-50 teams)
    - Caches results in Redis for 24 hours
    - Runs AI analysis for expert prediction
    - Returns complete analysis for each match
    """
    
    service = BetService()
    
    try:
        matches = await service.analyze_matches(
            limit=limit,
            tier_filter=tier_filter,
            use_ai=use_ai,
            force_refresh=force_refresh,
        )
        
        return BetResponse(
            total=len(matches),
            matches=matches,
            filters_applied={
                "limit": limit,
                "tier": tier_filter,
                "ai_enabled": use_ai,
                "cached": not force_refresh,
            }
        )
        
    except Exception as e:
        logger.error(f"Bet analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
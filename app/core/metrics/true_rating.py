from typing import Any, Dict, List, Optional

from app.core.metrics.base import BaseMetric


class TrueRatingMetric(BaseMetric):
    """Calculate True Rating weighted by opponent ranking."""
    
    name = "true_rating"
    description = "Rating weighted by opponent strength (HLTV ranking)"
    
    def __init__(self, top_50_teams: Dict[int, int]):
        """
        Args:
            top_50_teams: Dict of {team_id: ranking_position}
        """
        self.top_50_teams = top_50_teams
    
    def _get_opponent_coefficient(self, opponent_id: Optional[int]) -> float:
        """Calculate coefficient based on opponent's ranking."""
        if opponent_id is None:
            return 0.1  # Unknown opponent
        
        rank = self.top_50_teams.get(opponent_id)
        if rank is None:
            return 0.1  # Not in top-50
        
        # Coefficient = 1 / sqrt(rank)
        # #1 = 1.0, #10 = 0.32, #50 = 0.14
        return 1.0 / (rank ** 0.5)
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate True Rating from match history.
        
        Input format:
        {
            "matches": [
                {
                    "rating": 7.5,
                    "opponent_team_id": 10,
                    "map": "mirage",
                    "date": "2026-04-01"
                },
                ...
            ]
        }
        """
        matches = data.get("matches", [])
        if not matches:
            return {"true_rating": None, "matches_analyzed": 0}
        
        total_weight = 0.0
        weighted_rating = 0.0
        
        for match in matches:
            rating = match.get("rating")
            if rating is None:
                continue
            
            opponent_id = match.get("opponent_team_id")
            coeff = self._get_opponent_coefficient(opponent_id)
            
            weighted_rating += rating * coeff
            total_weight += coeff
        
        if total_weight == 0:
            return {"true_rating": None, "matches_analyzed": 0}
        
        true_rating = weighted_rating / total_weight
        
        return {
            "true_rating": round(true_rating, 2),
            "matches_analyzed": len(matches),
            "total_weight": round(total_weight, 2),
        }
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        return "matches" in data and isinstance(data["matches"], list)
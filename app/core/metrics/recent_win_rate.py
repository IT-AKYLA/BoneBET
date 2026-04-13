from typing import Any, Dict, List, Optional

from app.core.metrics.base import BaseMetric


class RecentWinRateMetric(BaseMetric):
    """Calculate recent win rate weighted by opponent ranking."""
    
    name = "recent_win_rate"
    description = "Win rate in recent matches weighted by opponent strength"
    
    def __init__(self, top_50_teams: Dict[int, int], matches_limit: int = 20):
        self.top_50_teams = top_50_teams
        self.matches_limit = matches_limit
    
    def _get_opponent_weight(self, opponent_id: Optional[int]) -> float:
        """Calculate weight based on opponent's ranking."""
        if opponent_id is None:
            return 0.1
        
        rank = self.top_50_teams.get(opponent_id)
        if rank is None:
            return 0.1
        
        return 1.0 / (rank ** 0.5)
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate recent win rate.
        
        Input format:
        {
            "matches": [
                {
                    "opponent_id": 1,
                    "opponent_rank": 31,
                    "result": "win",  # or "loss"
                    "date": "2026-03-29"
                },
                ...
            ],
            "team_name": "Vitality"
        }
        """
        matches = data.get("matches", [])
        if not matches:
            return {
                "recent_win_rate": None,
                "raw_win_rate": None,
                "matches_analyzed": 0,
            }
        
        # Берём последние N матчей
        recent_matches = matches[:self.matches_limit]
        
        total_weight = 0.0
        weighted_wins = 0.0
        wins = 0
        losses = 0
        
        for match in recent_matches:
            result = match.get("result", "")
            is_win = result.lower() == "win"
            
            if is_win:
                wins += 1
            else:
                losses += 1
            
            opponent_id = match.get("opponent_id")
            weight = self._get_opponent_weight(opponent_id)
            
            total_weight += weight
            if is_win:
                weighted_wins += weight
        
        raw_win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
        weighted_win_rate = weighted_wins / total_weight if total_weight > 0 else 0
        
        # Нормализуем в 0-100
        score = weighted_win_rate * 100
        
        return {
            "recent_win_rate": round(weighted_win_rate, 3),
            "raw_win_rate": round(raw_win_rate, 3),
            "score": round(score, 1),
            "wins": wins,
            "losses": losses,
            "matches_analyzed": len(recent_matches),
            "total_weight": round(total_weight, 2),
        }
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        return "matches" in data and isinstance(data["matches"], list)
from typing import Any, Dict, List

from app.core.metrics.base import BaseMetric


class H2HWinRateMetric(BaseMetric):
    """Calculate win rate against specific opponent."""
    
    name = "h2h_win_rate"
    description = "Win rate in head-to-head matches"
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate H2H win rate.
        
        Input format:
        {
            "matches": [
                {"opponent": "Vitality", "result": "loss"},
                {"opponent": "Vitality", "result": "loss"},
            ],
            "opponent_name": "Vitality"
        }
        """
        matches = data.get("matches", [])
        opponent_name = data.get("opponent_name", "").lower()
        
        if not matches or not opponent_name:
            return {
                "h2h_win_rate": None,
                "wins": 0,
                "losses": 0,
                "total_matches": 0,
            }
        
        h2h_matches = []
        for match in matches:
            opp = match.get("opponent", "").lower()
            if opponent_name in opp:
                h2h_matches.append(match)
        
        if not h2h_matches:
            return {
                "h2h_win_rate": None,
                "wins": 0,
                "losses": 0,
                "total_matches": 0,
            }
        
        wins = sum(1 for m in h2h_matches if m.get("result", "").lower() == "win")
        losses = len(h2h_matches) - wins
        
        win_rate = wins / len(h2h_matches) if h2h_matches else 0
        score = win_rate * 100
        
        return {
            "h2h_win_rate": round(win_rate, 3),
            "score": round(score, 1),
            "wins": wins,
            "losses": losses,
            "total_matches": len(h2h_matches),
        }
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        return "matches" in data and "opponent_name" in data
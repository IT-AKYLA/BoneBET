"""Map-specific statistics."""

from typing import Any, Dict, List, Optional

from app.core.metrics.base import BaseMetric


class MapStatsMetric(BaseMetric):
    """Calculate map-specific statistics for player or team."""
    
    name = "map_stats"
    description = "Performance statistics per map"
    
    def __init__(self, top_50_teams: Optional[Dict[int, int]] = None):
        self.top_50_teams = top_50_teams or {}
    
    def _get_opponent_coefficient(self, opponent_id: Optional[int]) -> float:
        """Calculate coefficient based on opponent's ranking."""
        if opponent_id is None:
            return 0.1
        rank = self.top_50_teams.get(opponent_id)
        if rank is None:
            return 0.1
        return 1.0 / (rank ** 0.5)
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate map statistics."""
        matches = data.get("matches", [])
        if not matches:
            return {"maps": {}, "best_map": None, "worst_map": None}
        
        map_data: Dict[str, Dict[str, Any]] = {}
        
        for match in matches:
            map_name = match.get("map")
            if not map_name or map_name == "Full match":
                continue
            
            rating = match.get("rating")
            result = match.get("result")
            opponent_id = match.get("opponent_team_id")
            
            if map_name not in map_data:
                map_data[map_name] = {
                    "ratings": [],
                    "wins": 0,
                    "losses": 0,
                    "weighted_ratings": [],
                }
            
            if rating is not None:
                map_data[map_name]["ratings"].append(rating)
                
                coeff = self._get_opponent_coefficient(opponent_id)
                map_data[map_name]["weighted_ratings"].append(rating * coeff)
            
            if result == "win":
                map_data[map_name]["wins"] += 1
            elif result == "loss":
                map_data[map_name]["losses"] += 1
        
        # Calculate aggregates per map
        result = {"maps": {}}
        best_map = None
        worst_map = None
        best_rating = -1
        worst_rating = 999
        
        for map_name, stats in map_data.items():
            ratings = stats["ratings"]
            weighted = stats["weighted_ratings"]
            total_games = stats["wins"] + stats["losses"]
            
            avg_rating = sum(ratings) / len(ratings) if ratings else None
            avg_weighted = sum(weighted) / len(weighted) if weighted else None
            win_rate = stats["wins"] / total_games if total_games > 0 else 0
            
            result["maps"][map_name] = {
                "games_played": total_games,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "win_rate": round(win_rate, 3),
                "avg_rating": round(avg_rating, 2) if avg_rating else None,
                "avg_weighted_rating": round(avg_weighted, 2) if avg_weighted else None,
            }
            
            # Track best/worst
            if avg_weighted and avg_weighted > best_rating:
                best_rating = avg_weighted
                best_map = map_name
            if avg_weighted and avg_weighted < worst_rating:
                worst_rating = avg_weighted
                worst_map = map_name
        
        result["best_map"] = best_map
        result["worst_map"] = worst_map
        result["best_rating"] = round(best_rating, 2) if best_rating > 0 else None
        result["worst_rating"] = round(worst_rating, 2) if worst_rating < 999 else None
        
        return result
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        return "matches" in data and isinstance(data["matches"], list)
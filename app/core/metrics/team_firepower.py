"""Team Firepower metrics."""

from typing import Any, Dict, List, Optional

from app.core.metrics.base import BaseMetric


class TeamFirepowerMetric(BaseMetric):
    """Calculate team's total firepower."""
    
    name = "team_firepower"
    description = "Team's total offensive power"
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate team firepower from player stats.
        
        Input format:
        {
            "players": [
                {
                    "nickname": "donk",
                    "true_rating": 7.8,
                    "faceit_elo": 5000,
                    "faceit_elo_score": 100
                },
                ...
            ]
        }
        """
        players = data.get("players", [])
        if not players:
            return {"team_firepower": None, "firepower_official": None, "firepower_faceit": None}
        
        # Official firepower (True Rating based)
        official_ratings = [p.get("true_rating") for p in players if p.get("true_rating")]
        firepower_official = sum(official_ratings) / len(official_ratings) if official_ratings else None
        
        # FACEIT firepower
        faceit_scores = [p.get("faceit_elo_score") for p in players if p.get("faceit_elo_score")]
        firepower_faceit = sum(faceit_scores) / len(faceit_scores) if faceit_scores else None
        
        # Combined (80% official, 20% FACEIT)
        if firepower_official and firepower_faceit:
            combined = firepower_official * 0.8 + firepower_faceit * 0.2
        elif firepower_official:
            combined = firepower_official
        elif firepower_faceit:
            combined = firepower_faceit
        else:
            combined = None
        
        # Carry index (max / average)
        if official_ratings:
            max_rating = max(official_ratings)
            avg_rating = sum(official_ratings) / len(official_ratings)
            carry_index = max_rating / avg_rating if avg_rating > 0 else 1.0
        else:
            carry_index = None
        
        return {
            "team_firepower": round(combined, 2) if combined else None,
            "firepower_official": round(firepower_official, 2) if firepower_official else None,
            "firepower_faceit": round(firepower_faceit, 2) if firepower_faceit else None,
            "carry_index": round(carry_index, 2) if carry_index else None,
            "players_analyzed": len(players),
        }
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        return "players" in data and isinstance(data["players"], list)
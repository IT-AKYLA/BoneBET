"""Consistency Index - how stable is the player."""

import math
from typing import Any, Dict, List

from app.core.metrics.base import BaseMetric


class ConsistencyMetric(BaseMetric):
    """Calculate player's consistency index."""
    
    name = "consistency"
    description = "How stable are the player's performances"
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate consistency from match ratings.
        
        Input format:
        {
            "ratings": [7.5, 6.8, 8.1, 5.2, ...]
        }
        """
        ratings = data.get("ratings", [])
        if not ratings or len(ratings) < 3:
            return {"consistency_index": None, "level": "unknown"}
        
        # Filter out None values
        valid_ratings = [r for r in ratings if r is not None]
        if len(valid_ratings) < 3:
            return {"consistency_index": None, "level": "unknown"}
        
        mean_rating = sum(valid_ratings) / len(valid_ratings)
        
        # Standard deviation
        variance = sum((r - mean_rating) ** 2 for r in valid_ratings) / len(valid_ratings)
        std_dev = math.sqrt(variance)
        
        # Consistency = 1 - (std / mean)
        if mean_rating > 0:
            consistency = 1.0 - (std_dev / mean_rating)
            consistency = max(0.0, min(1.0, consistency))
        else:
            consistency = 0.0
        
        # Level classification
        if consistency > 0.90:
            level = "very_stable"
        elif consistency > 0.80:
            level = "stable"
        elif consistency > 0.70:
            level = "average"
        else:
            level = "volatile"
        
        return {
            "consistency_index": round(consistency, 3),
            "level": level,
            "mean_rating": round(mean_rating, 2),
            "std_dev": round(std_dev, 2),
            "matches_analyzed": len(valid_ratings),
        }
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        return "ratings" in data and isinstance(data["ratings"], list)
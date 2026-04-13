"""Form Trend - with time decay."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.metrics.base import BaseMetric


class FormTrendMetric(BaseMetric):
    """Calculate form trend with time decay."""
    
    name = "form_trend"
    description = "Trend of player's form (rising/falling/stable)"
    
    def __init__(self, decay_factor: float = 0.9, window_days: int = 7):
        self.decay_factor = decay_factor
        self.window_days = window_days
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Safely parse date string."""
        if not date_str:
            return None
        try:
            # Handle ISO format with or without Z
            clean_date = date_str.replace("Z", "+00:00") if "Z" in date_str else date_str
            return datetime.fromisoformat(clean_date)
        except (ValueError, AttributeError):
            return None
    
    def _time_weight(self, match_date: datetime, reference_date: datetime) -> float:
        """Calculate time decay weight."""
        days_diff = (reference_date - match_date).days
        windows = max(0, days_diff) / self.window_days
        return self.decay_factor ** windows
    
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate form trend from match history."""
        matches = data.get("matches", [])
        if not matches:
            return {"form_trend": None, "trend_direction": "unknown"}
        
        # Filter matches with valid date and rating
        valid_matches = []
        for m in matches:
            rating = m.get("rating")
            date_str = m.get("date")
            if rating is None or date_str is None:
                continue
            
            parsed_date = self._parse_date(date_str)
            if parsed_date is None:
                continue
            
            valid_matches.append({
                "rating": rating,
                "date": parsed_date,
            })
        
        if len(valid_matches) < 3:
            return {"form_trend": None, "trend_direction": "unknown", "matches_analyzed": len(valid_matches)}
        
        # Sort by date (newest first)
        sorted_matches = sorted(valid_matches, key=lambda m: m["date"], reverse=True)
        reference_date = datetime.now()
        
        # Recent matches (first 5)
        recent_weighted = 0.0
        recent_weight_sum = 0.0
        
        for match in sorted_matches[:5]:
            weight = self._time_weight(match["date"], reference_date)
            recent_weighted += match["rating"] * weight
            recent_weight_sum += weight
        
        # Older matches (next 15)
        older_weighted = 0.0
        older_weight_sum = 0.0
        
        for match in sorted_matches[5:20]:
            weight = self._time_weight(match["date"], reference_date)
            older_weighted += match["rating"] * weight
            older_weight_sum += weight
        
        if recent_weight_sum == 0:
            return {"form_trend": None, "trend_direction": "unknown"}
        
        recent_avg = recent_weighted / recent_weight_sum
        older_avg = older_weighted / older_weight_sum if older_weight_sum > 0 else recent_avg
        
        trend_value = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
        
        if trend_value > 0.1:
            direction = "rising"
        elif trend_value < -0.1:
            direction = "falling"
        else:
            direction = "stable"
        
        return {
            "form_trend": round(trend_value, 3),
            "trend_direction": direction,
            "recent_avg": round(recent_avg, 2),
            "older_avg": round(older_avg, 2) if older_weight_sum > 0 else None,
            "matches_analyzed": len(valid_matches),
        }
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        return "matches" in data and isinstance(data["matches"], list)
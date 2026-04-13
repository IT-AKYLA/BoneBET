"""Normalize values to 0-100 scale."""

from typing import Optional


class Normalizer:
    """Normalize values to 0-100 scale."""
    
    DEFAULT_RANGES = {
        "rating": {"min": 3.0, "max": 8.0},
        "faceit_elo": {"min": 1500, "max": 5000},
        "kd": {"min": 0.5, "max": 1.5},
        "adr": {"min": 50.0, "max": 100.0},
    }
    
    @classmethod
    def normalize(
        cls,
        value: float,
        min_val: float,
        max_val: float,
        clip: bool = True,
    ) -> float:
        """Normalize value to 0-100."""
        if max_val == min_val:
            return 50.0
        
        normalized = ((value - min_val) / (max_val - min_val)) * 100
        
        if clip:
            normalized = max(0.0, min(100.0, normalized))
        
        return round(normalized, 2)
    
    @classmethod
    def normalize_rating(cls, rating: float) -> float:
        """Normalize HLTV rating to 0-100."""
        return cls.normalize(
            rating,
            cls.DEFAULT_RANGES["rating"]["min"],
            cls.DEFAULT_RANGES["rating"]["max"],
        )
    
    @classmethod
    def normalize_faceit_elo(cls, elo: int) -> float:
        """Normalize FACEIT ELO to 0-100."""
        return cls.normalize(
            float(elo),
            cls.DEFAULT_RANGES["faceit_elo"]["min"],
            cls.DEFAULT_RANGES["faceit_elo"]["max"],
        )
    
    @classmethod
    def normalize_kd(cls, kd: float) -> float:
        """Normalize K/D to 0-100."""
        return cls.normalize(
            kd,
            cls.DEFAULT_RANGES["kd"]["min"],
            cls.DEFAULT_RANGES["kd"]["max"],
        )
    
    @classmethod
    def normalize_adr(cls, adr: float) -> float:
        """Normalize ADR to 0-100."""
        return cls.normalize(
            adr,
            cls.DEFAULT_RANGES["adr"]["min"],
            cls.DEFAULT_RANGES["adr"]["max"],
        )
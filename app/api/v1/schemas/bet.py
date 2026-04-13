"""Schemas for /bet endpoint."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class PlayerAnalysisSchema(BaseModel):
    nickname: str
    official_rating: Optional[float] = None
    official_kd: Optional[float] = None
    official_adr: Optional[float] = None
    faceit_elo: Optional[int] = None


class TeamAnalysisSchema(BaseModel):
    id: int
    name: str
    ranking: Optional[int] = None
    firepower: Optional[float] = None
    players: List[PlayerAnalysisSchema] = []


class MatchPredictionSchema(BaseModel):
    winner: str
    team1_win_prob: float
    team2_win_prob: float
    confidence: str


class AIAnalysisSchema(BaseModel):
    text: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


class MatchAnalysisResponse(BaseModel):
    match_id: str
    team1: TeamAnalysisSchema
    team2: TeamAnalysisSchema
    tournament: Optional[str] = None
    scheduled_at: Optional[str] = None
    status: str
    prediction: MatchPredictionSchema
    ai_analysis: Optional[AIAnalysisSchema] = None


class BetResponse(BaseModel):
    total: int
    matches: List[MatchAnalysisResponse]
    filters_applied: Dict[str, Any]
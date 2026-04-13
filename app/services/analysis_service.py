"""Analysis service - combines all metrics for final prediction."""

from typing import Dict, Any, Optional, List
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MatchAnalyzer:
    """Combines all metrics for final match prediction."""
    
    # Веса для общей оценки
    WEIGHTS = {
        "firepower": 0.30,        # Командная огневая мощь
        "recent_win_rate": 0.30,  # Форма команды
        "h2h_win_rate": 0.15,     # История личных встреч
        "carry_penalty": 0.10,    # Штраф за зависимость от звезды
        "ranking": 0.15,          # Мировой рейтинг
    }
    
    def _normalize_ranking(self, ranking: Optional[int]) -> float:
        """Normalize ranking to 0-100 score (lower rank = higher score)."""
        if ranking is None:
            return 50.0
        
        # #1 = 100, #50 = 50, #100 = 0
        score = max(0, 100 - ranking)
        return float(score)
    
    def _normalize_carry(self, carry_index: Optional[float]) -> float:
        """Convert carry index to penalty score (lower carry = higher score)."""
        if carry_index is None:
            return 50.0
        
        # carry 1.0 = 100 (идеально), carry 1.5 = 0 (плохо)
        score = max(0, 100 - (carry_index - 1) * 100)
        return float(score)
    
    def _normalize_firepower(self, firepower: Optional[float]) -> float:
        """Normalize firepower to 0-100 score."""
        if firepower is None:
            return 50.0
        
        # 5.0 = 0, 6.0 = 50, 7.0 = 100
        score = (firepower - 5.0) * 50
        return max(0, min(100, score))
    
    def analyze(
        self,
        team1_data: Dict[str, Any],
        team2_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze match and return prediction.
        
        Args:
            team1_data: {
                "name": "Vitality",
                "ranking": 31,
                "firepower": 6.65,
                "carry_index": 1.11,
                "recent_win_rate": {"score": 85.0},
                "h2h_win_rate": {"score": 100.0},
                "players": [...]
            }
            team2_data: аналогично
        
        Returns:
            {
                "team1_score": 78.5,
                "team2_score": 62.3,
                "team1_win_prob": 55.8,
                "team2_win_prob": 44.2,
                "predicted_winner": "Vitality",
                "confidence": "medium",
                "breakdown": {...}
            }
        """
        
        # Извлекаем метрики
        def get_metrics(data: Dict) -> Dict[str, float]:
            firepower = data.get("firepower")
            firepower_score = self._normalize_firepower(firepower)
            
            recent_wr = data.get("recent_win_rate", {})
            recent_score = recent_wr.get("score", 50) if recent_wr else 50
            
            h2h_wr = data.get("h2h_win_rate", {})
            h2h_score = h2h_wr.get("score", 50) if h2h_wr else 50
            
            carry = data.get("carry_index")
            carry_score = self._normalize_carry(carry)
            
            ranking = data.get("ranking")
            ranking_score = self._normalize_ranking(ranking)
            
            return {
                "firepower": firepower_score,
                "recent_win_rate": recent_score,
                "h2h_win_rate": h2h_score,
                "carry_penalty": carry_score,
                "ranking": ranking_score,
            }
        
        metrics1 = get_metrics(team1_data)
        metrics2 = get_metrics(team2_data)
        
        # Считаем взвешенные суммы
        score1 = sum(metrics1[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        score2 = sum(metrics2[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        
        total = score1 + score2
        prob1 = (score1 / total) * 100 if total > 0 else 50
        prob2 = 100 - prob1
        
        # Определяем уверенность
        diff = abs(prob1 - 50)
        if diff > 15:
            confidence = "high"
        elif diff > 7:
            confidence = "medium"
        else:
            confidence = "low"
        
        predicted_winner = team1_data["name"] if prob1 > prob2 else team2_data["name"]
        
        logger.info(
            f"Match analysis: {team1_data['name']} vs {team2_data['name']}",
            winner=predicted_winner,
            prob1=round(prob1, 1),
            prob2=round(prob2, 1),
            confidence=confidence,
        )
        
        return {
            "team1_score": round(score1, 1),
            "team2_score": round(score2, 1),
            "team1_win_prob": round(prob1, 1),
            "team2_win_prob": round(prob2, 1),
            "predicted_winner": predicted_winner,
            "confidence": confidence,
            "breakdown": {
                "team1": {
                    "name": team1_data["name"],
                    "metrics": metrics1,
                },
                "team2": {
                    "name": team2_data["name"],
                    "metrics": metrics2,
                },
                "weights": self.WEIGHTS,
            }
        }


class AIAnalyzer:
    """AI-powered analysis using LLM."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def build_prompt(
        self,
        team1_data: Dict[str, Any],
        team2_data: Dict[str, Any],
        match_analyzer_result: Dict[str, Any],
        h2h_details: Optional[List[Dict]] = None,
    ) -> str:
        """Build prompt for LLM analysis."""
        
        prompt = f"""Ты — профессиональный аналитик CS2 с 10-летним опытом. Проанализируй предстоящий матч.

## Команда А: {team1_data['name']}
- Мировой рейтинг: #{team1_data.get('ranking', 'N/A')}
- Форма (True Win Rate): {team1_data.get('recent_win_rate', {}).get('score', 'N/A')}%
- Огневая мощь (Firepower): {team1_data.get('firepower', 'N/A')}
- Зависимость от звезды (Carry Index): {team1_data.get('carry_index', 'N/A')}

### Игроки:
"""
        for p in team1_data.get('players', [])[:5]:
            prompt += f"- {p['nickname']}: True Rating {p.get('true_rating', {}).get('true_rating', 'N/A')}, Форма: {p.get('form_trend', {}).get('trend_direction', 'N/A')}\n"
        
        prompt += f"""
## Команда Б: {team2_data['name']}
- Мировой рейтинг: #{team2_data.get('ranking', 'N/A')}
- Форма (True Win Rate): {team2_data.get('recent_win_rate', {}).get('score', 'N/A')}%
- Огневая мощь (Firepower): {team2_data.get('firepower', 'N/A')}
- Зависимость от звезды (Carry Index): {team2_data.get('carry_index', 'N/A')}

### Игроки:
"""
        for p in team2_data.get('players', [])[:5]:
            prompt += f"- {p['nickname']}: True Rating {p.get('true_rating', {}).get('true_rating', 'N/A')}, Форма: {p.get('form_trend', {}).get('trend_direction', 'N/A')}\n"
        
        # H2H
        h2h = team1_data.get('h2h_win_rate', {})
        if h2h.get('total_matches', 0) > 0:
            prompt += f"""
## История личных встреч:
- Всего матчей: {h2h['total_matches']}
- {team1_data['name']} побед: {h2h.get('wins', 0)}
- {team2_data['name']} побед: {h2h.get('losses', 0)}
"""
        
        prompt += f"""
## Статистический прогноз:
- {team1_data['name']}: {match_analyzer_result['team1_win_prob']}%
- {team2_data['name']}: {match_analyzer_result['team2_win_prob']}%
- Уверенность модели: {match_analyzer_result['confidence']}

## Задание:
1. Определи роли ключевых игроков (если знаешь)
2. Выдели слабые и сильные стороны каждой команды
3. Сравни команды по линиям (AWPer vs AWPer, Entry vs Entry)
4. Учитывая твои знания о текущей мете и форме команд, дай ФИНАЛЬНЫЙ ПРОГНОЗ:
   - Кто победит?
   - Примерный счёт (для BO3)
   - Ключевой игрок матча

Будь конкретен. Избегай общих фраз.
"""
        
        return prompt
    
    async def analyze(
        self,
        team1_data: Dict[str, Any],
        team2_data: Dict[str, Any],
        match_analyzer_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run AI analysis."""
        
        prompt = self.build_prompt(team1_data, team2_data, match_analyzer_result)
        
        if self.llm_client:
            # Здесь будет вызов LLM
            response = await self.llm_client.complete(prompt)
            return {
                "prompt": prompt,
                "response": response,
            }
        else:
            return {
                "prompt": prompt,
                "response": None,
                "error": "LLM client not configured",
            }
from typing import Dict, Any, List, Optional


class PromptTemplates:
    """Collection of prompt templates for different analysis types."""
    
    @staticmethod
    def player_analysis(
        nickname: str,
        team_name: str,
        official_rating: Optional[float],
        faceit_elo: Optional[int],
        recent_matches: List[Dict],
    ) -> str:
        """Prompt for individual player analysis."""
        
        matches_text = ""
        for m in recent_matches[:5]:
            matches_text += f"- vs {m['opponent']} (#{m['opponent_rank']}): {m['kills']}/{m['deaths']} (Rating: {m['rating']})\n"
        
        if not matches_text:
            matches_text = "Нет данных о последних матчах.\n"
        
        return f"""Ты — CS2 аналитик. Оцени игрока {nickname} из команды {team_name}.

## ДАННЫЕ ИГРОКА
- Official Rating: {official_rating if official_rating else 'N/A'}
- FACEIT ELO: {faceit_elo if faceit_elo else 'N/A'}

## ПОСЛЕДНИЕ 5 МАТЧЕЙ
{matches_text}

## ЗАДАНИЕ
1. Определи роль игрока (AWPer, Entry, IGL, Support, Lurker).
2. Оцени динамику формы: rising, falling, stable. Обоснуй.
3. Рассчитай True Rating (1-10) на основе ТОЛЬКО последних матчей с учётом силы соперников.
4. Если знаешь социальный контекст об игроке (конфликты, буст формы, замены) — укажи кратко.

## ФОРМАТ ОТВЕТА (строго)
```
Роль: [роль]
Динамика: [rising/falling/stable]
True Rating: [X.X]
Обоснование: [1 предложение]
Контекст: [опционально]
```"""
    
    @staticmethod
    def team_comparison(
        team1_name: str,
        team1_players: List[Dict],
        team2_name: str,
        team2_players: List[Dict],
        team1_win_rate: float,
        team2_win_rate: float,
    ) -> str:
        """Prompt for team comparison using pre-analyzed players."""
        
        t1_text = ""
        for p in team1_players:
            t1_text += f"- {p['nickname']}: {p.get('role', 'Unknown')}, {p.get('dynamic', 'stable')}, TR {p.get('true_rating', 5.0)}\n"
        
        t2_text = ""
        for p in team2_players:
            t2_text += f"- {p['nickname']}: {p.get('role', 'Unknown')}, {p.get('dynamic', 'stable')}, TR {p.get('true_rating', 5.0)}\n"
        
        return f"""Ты — CS2 аналитик. Сравни команды на основе предварительно оценённых игроков.

## {team1_name} (True Win Rate: {team1_win_rate*100:.1f}%)
{t1_text}

## {team2_name} (True Win Rate: {team2_win_rate*100:.1f}%)
{t2_text}

## ЗАДАНИЕ
1. Сравни команды по линиям (AWPer vs AWPer, Entry vs Entry, IGL vs IGL).
2. Оцени суммарную огневую мощь (средний True Rating).
3. Учти динамику формы — у кого больше игроков в rising/falling.
4. Учти True Win Rate команд.
5. Выдай финальный прогноз.

## ФОРМАТ ОТВЕТА
```
📊 Сравнение линий:
- AWPer: [кто сильнее и почему]
- Entry: [кто сильнее и почему]
- IGL: [кто сильнее и почему]

🔥 Огневая мощь: [средний TR команды 1] vs [средний TR команды 2] → [кто выше]

📈 Динамика формы: [у кого больше rising/falling]

✅ Прогноз: [победитель] с вероятностью [X]%
🎯 Ключевой фактор: [1 предложение]
```"""
    
    @staticmethod
    def match_analysis(
        team1_data: Dict[str, Any],
        team2_data: Dict[str, Any],
        stats_prediction: Dict[str, Any],
        team1_win_rate: float = 0.5,
        team2_win_rate: float = 0.5,
    ) -> str:
        """Legacy prompt for direct match analysis (kept for compatibility)."""
        
        t1_name = team1_data.get('name', 'Unknown')
        t2_name = team2_data.get('name', 'Unknown')
        t1_rank = team1_data.get('ranking', 'N/A')
        t2_rank = team2_data.get('ranking', 'N/A')
        t1_fp = team1_data.get('firepower', 'N/A')
        t2_fp = team2_data.get('firepower', 'N/A')
        t1_carry = team1_data.get('carry_index', 'N/A')
        t2_carry = team2_data.get('carry_index', 'N/A')
        
        prompt = f"""Ты — профессиональный CS2 аналитик. Дай экспертный прогноз.

## ДАННЫЕ BONEBET

### {t1_name} (HLTV #{t1_rank})
- True Win Rate: {team1_win_rate*100:.1f}%
- Firepower: {t1_fp}
- Carry Index: {t1_carry}

Ключевые игроки:
"""
        for p in team1_data.get('players', [])[:5]:
            prompt += f"- {p['nickname']}: Rating {p.get('official_rating', '—')}, K/D {p.get('official_kd', '—')}\n"
        
        prompt += f"""
### {t2_name} (HLTV #{t2_rank})
- True Win Rate: {team2_win_rate*100:.1f}%
- Firepower: {t2_fp}
- Carry Index: {t2_carry}

Ключевые игроки:
"""
        for p in team2_data.get('players', [])[:5]:
            prompt += f"- {p['nickname']}: Rating {p.get('official_rating', '—')}, K/D {p.get('official_kd', '—')}\n"
        
        prompt += f"""
## ПРОГНОЗ BONEBET
- {t1_name}: {stats_prediction.get('team1_win_prob', 50):.1f}%
- {t2_name}: {stats_prediction.get('team2_win_prob', 50):.1f}%

## ЗАДАНИЕ
1. Скорректируй прогноз с учётом силы соперников.
2. Сравни по линиям (AWPer, Entry, IGL).
3. Выдай финальный вердикт.

Формат ответа:
```
📊 BoneBET: {t1_name} {stats_prediction.get('team1_win_prob', 50):.1f}% / {t2_name} {stats_prediction.get('team2_win_prob', 50):.1f}%
🔄 Корректировки: [что и почему]
✅ Итог: {t1_name} X% — Y% {t2_name}
🎯 Победитель: [команда]
📋 Ключевой фактор: [1 предложение]
```"""
        return prompt
    
    @staticmethod
    def system_prompt() -> str:
        """Default system prompt for CS2 analyst."""
        return """Ты — профессиональный CS2 аналитик. Оценивай метрики в контексте оппозиции. Отвечай строго по формату."""

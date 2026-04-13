"""Prompt templates for AI analysis."""

from typing import Dict, Any


class PromptTemplates:
    """Collection of prompt templates for different analysis types."""
    
    @staticmethod
    def match_analysis(
        team1_data: Dict[str, Any],
        team2_data: Dict[str, Any],
        stats_prediction: Dict[str, Any],
        team1_win_rate: float = 0.5,
        team2_win_rate: float = 0.5,
    ) -> str:
        
        t1_name = team1_data.get('name', 'Unknown')
        t2_name = team2_data.get('name', 'Unknown')
        t1_rank = team1_data.get('ranking', 'N/A')
        t2_rank = team2_data.get('ranking', 'N/A')
        t1_fp = team1_data.get('firepower', 'N/A')
        t2_fp = team2_data.get('firepower', 'N/A')
        t1_carry = team1_data.get('carry_index', 'N/A')
        t2_carry = team2_data.get('carry_index', 'N/A')
        
        prompt = f"""Ты — профессиональный CS2 аналитик. Твоя задача — дать экспертный прогноз, жёстко привязанный к контексту силы соперников.

## ПРАВИЛА АНАЛИЗА

1. Каждая цифра должна оцениваться относительно оппозиции.
2. Явно применяй корректировки: "BoneBET даёт X%, я корректирую до Y% потому что..."
3. В ответе обязательно укажи исходный прогноз, корректировки и итоговый прогноз.

---

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
## ПРОГНОЗ BONEBET (исходный)
- {t1_name}: {stats_prediction.get('team1_win_prob', 50):.1f}%
- {t2_name}: {stats_prediction.get('team2_win_prob', 50):.1f}%

---

## ТВОЙ АНАЛИЗ

1. Оцени силу соперников для каждой команды.
2. Скорректируй метрики по правилам:
   - True WR >70% против слабых → понизить на 15-25%
   - True WR 50-60% против топ-20 → повысить на 10-20%
   - Carry Index >1.3 + звезда не в форме → штраф 10-15%
3. Сравни по линиям (AWPer, Entry, IGL).
4. Выдай финальный вердикт.

Формат ответа:
📊 BoneBET: {t1_name} {stats_prediction.get('team1_win_prob', 50):.1f}% / {t2_name} {stats_prediction.get('team2_win_prob', 50):.1f}%

🔄 Корректировки: [что и почему]

✅ Итог: {t1_name} X% — Y% {t2_name}
🎯 Победитель: [команда]
📋 Ключевой фактор: [1 предложение]

Отвечай на русском. Без воды.
"""
        return prompt
    
    @staticmethod
    def system_prompt() -> str:
        """Default system prompt for CS2 analyst."""
        return """Ты — профессиональный CS2 аналитик. Оценивай каждую метрику в контексте оппозиции. Явно указывай корректировки исходного прогноза BoneBET. Отвечай строго по формату."""
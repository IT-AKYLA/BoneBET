"""Prompt templates for AI analysis."""

from typing import Dict, Any, List, Optional


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

## ПРАВИЛА АНАЛИЗА (ОБЯЗАТЕЛЬНЫ К ИСПОЛНЕНИЮ)

1. **Каждая цифра должна оцениваться относительно оппозиции.**
   - True Win Rate 80% против команд #50+ ≠ True Win Rate 60% против топ-10.
   - Firepower 7.0 против тир-3 команд = завышенная оценка.

2. **Явно применяй корректировки.**
   - Напиши: "BoneBET даёт X%, я корректирую до Y% потому что..."

3. **В ответе обязательно укажи:**
   - Исходный прогноз BoneBET
   - Какие метрики ты скорректировал и почему
   - Итоговый прогноз

---

## ДАННЫЕ BONEBET

### {t1_name} (Рейтинг HLTV: #{t1_rank})
- True Win Rate: **{team1_win_rate*100:.1f}%** (вес: #1=1.0, #10=0.32, #50=0.14, #100+=0.1)
- Firepower: **{t1_fp}**
- Carry Index: **{t1_carry}** (>1.2 = зависимость от звезды)

Ключевые игроки:
"""
        for p in team1_data.get('players', [])[:5]:
            prompt += f"- {p['nickname']}: Rating {p.get('official_rating', '—')}, K/D {p.get('official_kd', '—')}\n"
        
        prompt += f"""
### {t2_name} (Рейтинг HLTV: #{t2_rank})
- True Win Rate: **{team2_win_rate*100:.1f}%**
- Firepower: **{t2_fp}**
- Carry Index: **{t2_carry}**

Ключевые игроки:
"""
        for p in team2_data.get('players', [])[:5]:
            prompt += f"- {p['nickname']}: Rating {p.get('official_rating', '—')}, K/D {p.get('official_kd', '—')}\n"
        
        prompt += f"""
## ПРОГНОЗ BONEBET (исходный)
- {t1_name}: **{stats_prediction.get('team1_win_prob', 50):.1f}%**
- {t2_name}: **{stats_prediction.get('team2_win_prob', 50):.1f}%**
- Уверенность модели: {stats_prediction.get('confidence', 'unknown')}

---

## ТВОЙ АНАЛИЗ

### 1. ОЦЕНКА СИЛЫ СОПЕРНИКОВ
Для каждой команды определи:
- Против кого набит True Win Rate? Топы или тир-3?
- Качество Firepower — против сильных или слабых команд?

### 2. КОРРЕКТИРОВКА МЕТРИК
Примени конкретные корректировки. Используй правила:

| Ситуация | Корректировка |
|----------|---------------|
| True WR >70% против слабых (#50+) | Понизить на 15-25% |
| True WR 50-60% против топ-20 | Повысить на 10-20% |
| Firepower >6.5 против тир-3 | Смотреть только на матчи против топ-30 |
| Carry Index >1.3 + звезда не в форме | Штраф 10-15% |
| IGL/Support с низким рейтингом | Не штрафовать команду |

**Напиши: "Исходный прогноз BoneBET: X% на {t1_name}. Я корректирую до Y% потому что..."**

### 3. СРАВНЕНИЕ ПО ЛИНИЯМ
- AWPer vs AWPer
- Entry vs Entry  
- IGL vs IGL

### 4. ФИНАЛЬНЫЙ ВЕРДИКТ

**Формат ответа (строго соблюдай):**
"""
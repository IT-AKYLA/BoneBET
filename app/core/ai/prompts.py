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
        h2h_details: Optional[List[Dict]] = None,
    ) -> str:
        """Generate comprehensive prompt for match analysis."""
        
        prompt = f"""Ты — профессиональный CS2 аналитик с доступом к базе данных интернета и знанием текущей меты.

## ТВОЯ ЗАДАЧА
Проанализируй матч **{team1_data.get('name', 'Unknown')} vs {team2_data.get('name', 'Unknown')}**, используя:
1. **Наши рассчитанные метрики** (ниже)
2. **Твои знания из интернета** (история команд, сила соперников, текущая форма, роли игроков)
3. **Сопоставь и скорректируй** наши метрики с реальным контекстом

---

## 🔵 КОМАНДА А: {team1_data.get('name', 'Unknown')}
### Базовые показатели
- Мировой рейтинг HLTV: #{team1_data.get('ranking', 'N/A')}
- **True Win Rate (взвешенный по силе соперников): {team1_win_rate * 100:.1f}%**
  *Этот показатель учитывает не просто победы, а КАЧЕСТВО соперников. #1 команда даёт вес 1.0, #50 — 0.14, #100+ — 0.1.*
- Огневая мощь (Firepower): **{team1_data.get('firepower', 'N/A')}** (средний True Rating игроков)

### Игроки (с нашими метриками)
"""
        for p in team1_data.get('players', [])[:5]:
            official_rating = p.get('official_rating', 'N/A')
            official_kd = p.get('official_kd', 'N/A')
            faceit_elo = p.get('faceit_elo', 'N/A')
            
            prompt += f"""
- **{p['nickname']}**
  - Official Rating: {official_rating}
  - K/D: {official_kd}
  - FACEIT ELO: {faceit_elo}
"""
        
        prompt += f"""
### 📊 Наша статистическая оценка команды
- **True Win Rate**: {team1_win_rate * 100:.1f}% (учти — это ВЗВЕШЕННЫЙ показатель, победы над слабыми дают мало веса)
- **Firepower**: {team1_data.get('firepower', 'N/A')}
- **Carry Index**: {team1_data.get('carry_index', 'N/A')} (чем выше, тем больше зависимость от звезды)

---

## 🔴 КОМАНДА Б: {team2_data.get('name', 'Unknown')}
### Базовые показатели
- Мировой рейтинг HLTV: #{team2_data.get('ranking', 'N/A')}
- **True Win Rate (взвешенный по силе соперников): {team2_win_rate * 100:.1f}%**
- Огневая мощь (Firepower): **{team2_data.get('firepower', 'N/A')}**

### Игроки (с нашими метриками)
"""
        for p in team2_data.get('players', [])[:5]:
            official_rating = p.get('official_rating', 'N/A')
            official_kd = p.get('official_kd', 'N/A')
            faceit_elo = p.get('faceit_elo', 'N/A')
            
            prompt += f"""
- **{p['nickname']}**
  - Official Rating: {official_rating}
  - K/D: {official_kd}
  - FACEIT ELO: {faceit_elo}
"""
        
        prompt += f"""
### 📊 Наша статистическая оценка команды
- **True Win Rate**: {team2_win_rate * 100:.1f}%
- **Firepower**: {team2_data.get('firepower', 'N/A')}
- **Carry Index**: {team2_data.get('carry_index', 'N/A')}

---

## 📈 НАШ СТАТИСТИЧЕСКИЙ ПРОГНОЗ
- {team1_data['name']}: **{stats_prediction.get('team1_win_prob', 50):.1f}%**
- {team2_data['name']}: **{stats_prediction.get('team2_win_prob', 50):.1f}%**
- Уверенность модели: {stats_prediction.get('confidence', 'unknown')}

---

## 🧠 ТВОЙ ЭКСПЕРТНЫЙ АНАЛИЗ

### 1. КОНТЕКСТ ИЗ ИНТЕРНЕТА (используй свои знания)
- **Роли игроков**: определи AWPer, IGL, Entry, Support для каждой команды
- **История встреч**: если знаешь H2H между командами — укажи
- **Сила соперников**: ОЦЕНИ — против кого команды набили свой True Win Rate? Учти, что высокий True Win Rate означает победы над СИЛЬНЫМИ соперниками.
- **Текущая мета**: какие карты сильны/слабы для этих команд?
- **Последние новости**: замены в составе, конфликты, буст формы

### 2. КОРРЕКТИРОВКА НАШИХ МЕТРИК
Сопоставь наши цифры с реальным контекстом:
- **Если True Win Rate высокий, но команда играла против слабых соперников — понизь оценку**
- Если у игрока низкий Official Rating, но он играет роль Support/IGL → его влияние выше, чем цифры
- Если Carry Index высокий, но звезда в плохой форме → риск для команды

### 3. СРАВНЕНИЕ ПО ЛИНИЯМ
- AWPer vs AWPer
- Entry vs Entry
- IGL vs IGL
- Суммарная огневая мощь рифлеров

### 4. СИЛЬНЫЕ И СЛАБЫЕ СТОРОНЫ
На основе ВСЕХ данных (наши метрики + твой контекст):
- Где каждая команда имеет преимущество?
- Где уязвима?

### 5. ФИНАЛЬНЫЙ ПРОГНОЗ (с учётом корректировок)
- **Победитель**: кто выиграет и почему?
- **Предполагаемый счёт** (BO3)
- **Ключевой игрок матча**
- **Уровень уверенности** (высокий/средний/низкий) — с обоснованием

---

## ⚠️ ВАЖНО
- **True Win Rate — ключевая метрика**. Высокий True Win Rate = команда побеждала СИЛЬНЫХ соперников.
- **Не игнорируй наши метрики** — они основаны на реальной статистике
- **Но и не принимай их слепо** — корректируй с учётом контекста из интернета
- Если данных недостаточно — честно скажи об этом
- Будь конкретен, избегай общих фраз
"""
        return prompt
    
    @staticmethod
    def system_prompt() -> str:
        """Default system prompt for CS2 analyst."""
        return """Ты — профессиональный аналитик CS2 с доступом к базе данных интернета.
Ты знаешь:
- Роли всех известных игроков (AWPer, IGL, Entry, Support, Lurker)
- Историю команд и их выступления на последних турнирах
- Текущую мету, сильные и слабые стороны карт
- Силу соперников (тир-1, тир-2, тир-3)

Твоя задача — взять наши рассчитанные метрики (True Win Rate, Firepower, Carry Index, рейтинги игроков) 
и дополнить их своим экспертным знанием из интернета. 

**Ключевая метрика — True Win Rate**. Она показывает не просто процент побед, а КАЧЕСТВО этих побед 
(вес зависит от рейтинга соперника: #1 = 1.0, #50 = 0.14, #100+ = 0.1).
Высокий True Win Rate = команда побеждала СИЛЬНЫХ соперников.

**Корректируй наши цифры, если контекст указывает на их неточность.**
Например:
- Высокий Win Rate против слабых команд ≠ сильная форма
- Низкий рейтинг у IGL/Support не означает слабого игрока
- Звезда в плохой форме = высокий Carry Index становится проблемой

Давай комплексный, объективный прогноз, объединяющий статистику и экспертизу."""
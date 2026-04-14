import asyncio
import json
import re
from typing import List, Dict, Any, Optional

from app.services.player_analysis_service import PlayerAnalysisService
from app.services.scraper.bo3_client import BO3Client
from app.services.scraper.match_scraper import MatchScraper
from app.services.scraper.team_rankings_scraper import TeamRankingsScraper
from app.services.scraper.team_scraper import TeamScraper
from app.services.scraper.team_matches_scraper import TeamMatchesScraper
from app.core.ai.prompts import PromptTemplates
from app.core.ai import get_ai_analyzer
from app.db.redis_client import RedisCache
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BetService:    
    def __init__(self):
        self.player_service = PlayerAnalysisService()
        self.cache = RedisCache(prefix="bonebet")
        self.cache_ttl = 300
        self.llm_semaphore = asyncio.Semaphore(1)
        self.ai_request_delay = 1

        client = BO3Client(headless=True)
        self.match_scraper = MatchScraper(client=client)
        self.team_scraper = TeamScraper(client=client)
        self.rankings_scraper = TeamRankingsScraper(client=client)
        self.matches_scraper = TeamMatchesScraper(client=client)

    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    async def analyze_matches(
        self,
        limit: int = 10,
        tier_filter: str = "all",
        use_ai: bool = True,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """Analyze live and upcoming matches with full AI player pipeline."""
        
        cache_key = f"matches_v3:{tier_filter}:{limit}:{use_ai}"
        
        if not force_refresh:
            if cached := await self._get_cached(cache_key):
                logger.info(f"Returning cached data for {cache_key}")
                return cached
        
        logger.info(f"Cache miss for {cache_key}, fetching fresh data...")
        
        # Fetch rankings
        rankings = await self._fetch_top_teams()
        top_50_names = {t["name"] for t in rankings}
        
        # Fetch matches
        matches = await self._fetch_all_matches()
        logger.info(f"Fetched {len(matches)} total matches")
        
        # Filter tier1
        if tier_filter == "tier1":
            matches = [m for m in matches if self._is_tier1_match(m, top_50_names)]
            logger.info(f"Filtered to {len(matches)} tier-1 matches")
        
        matches = matches[:limit]
        
        # Analyze sequentially to avoid overloading
        results = []
        for i, match in enumerate(matches, 1):
            try:
                logger.info(f"Analyzing match {i}/{len(matches)}")
                analysis = await self._analyze_match_v2(match, use_ai, force_refresh)
                if analysis:
                    results.append(analysis)
                if i < len(matches):
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Failed to analyze match {i}: {e}")
                continue
        
        if results:
            await self.cache.set(cache_key, json.dumps(results), ttl=self.cache_ttl)
            logger.info(f"Cached {len(results)} matches")
        
        return results
    
    async def invalidate_match_cache(self, tier_filter: str = "all") -> int:
        patterns = [f"matches_v3:{tier_filter}:*"]
        deleted = 0
        for pattern in patterns:
            deleted += await self.cache.delete_pattern(pattern)
        return deleted
    
    # ========================================================================
    # MATCH ANALYSIS
    # ========================================================================
    async def _fetch_all_matches_raw(self) -> List[Dict]:
        """Fetch all matches without filtering."""
        loop = asyncio.get_event_loop()
        with self.match_scraper as scraper:
            return await loop.run_in_executor(None, scraper.scrape_all_matches)
    
    async def _get_all_teams_cached(self) -> Dict[str, List[Dict]]:
        """Кэширует результат парсинга всех команд."""
        cache_key = "all_teams:top100"
        if cached := await self._get_cached(cache_key):
            return cached
        
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, self.team_scraper.scrape_all_teams, 5)
        
        await self.cache.set(cache_key, json.dumps(data), ttl=86400)  # 24 часа
        return data
    
    async def _get_team_win_rate_ai(self, team_name: str) -> float:
        """Get team's approximate win rate from AI."""
        cache_key = f"ai_win_rate:{team_name}"
        if cached := await self.cache.get(cache_key):
            try:
                return float(cached)
            except ValueError:
                pass
            
        try:
            ai = get_ai_analyzer(use_mock=False)
            prompt = f"""Ты эксперт по CS2. Назови ПРИМЕРНЫЙ процент побед команды "{team_name}" за последние 3 месяца.
    Ответ должен быть ТОЛЬКО числом от 0 до 100."""

            result = await ai.client.complete(
                prompt=prompt,
                system_prompt="Отвечай только числом от 0 до 100.",
                temperature=0.1,
                max_tokens=10,
            )
            await ai.close()

            import re
            numbers = re.findall(r'\d+', result['text'])
            wr = int(numbers[0]) / 100 if numbers else 0.5
            wr = max(0.1, min(0.9, wr))

            await self.cache.set(cache_key, str(wr), ttl=86400 * 7)
            return wr

        except Exception:
            return 0.5
    
    
    async def _analyze_match_v2(
        self,
        match: Dict[str, Any],
        use_ai: bool,
        force_refresh: bool,
    ) -> Optional[Dict[str, Any]]:
        """Analyze a single match."""
        
        t1_name = match.get('team1_name', 'Unknown')
        t2_name = match.get('team2_name', 'Unknown')
        
        if t1_name == 'Unknown' or t2_name == 'Unknown' or t1_name == 'TBD' or t2_name == 'TBD':
            return None
        
        logger.info(f"Analyzing: {t1_name} vs {t2_name}")
        
        # Get team data from scraper
        t1_data = await self._get_team_data_cached(t1_name)
        t2_data = await self._get_team_data_cached(t2_name)
        
        if not t1_data.get('players') or not t2_data.get('players'):
            logger.warning(f"No players for {t1_name} vs {t2_name}")
            return None
        
        # Win rates from scraper
        wr1 = await self._calculate_team_win_rate(t1_name)
        wr2 = await self._calculate_team_win_rate(t2_name)
        
        # Base prediction
        prediction = self._calculate_prediction(t1_data, t2_data, wr1, wr2)
        
        # AI enhancement
        ai_result = None
        if use_ai:
            ai_result = await self._run_ai_pipeline(t1_name, t2_name, wr1, wr2, force_refresh)
            if ai_result and ai_result.get('winner'):
                prediction = {
                    'winner': ai_result['winner'],
                    'team1_win_prob': ai_result.get('team1_prob', 50),
                    'team2_win_prob': ai_result.get('team2_prob', 50),
                    'confidence': ai_result.get('confidence', 'medium'),
                }
        
        return {
            "match_id": match.get('url', f"{t1_name}_vs_{t2_name}"),
            "team1": t1_data,
            "team2": t2_data,
            "tournament": match.get('event'),
            "scheduled_at": match.get('match_time'),
            "status": match.get('status', 'upcoming'),
            "prediction": prediction,
            "ai_analysis": ai_result,
        }
    
    async def _run_ai_pipeline(
        self,
        t1_name: str,
        t2_name: str,
        wr1: float,
        wr2: float,
        force_refresh: bool,
    ) -> Optional[Dict[str, Any]]:
        """Run AI: analyze players → compare teams."""
        try:
            t1_players = await self.player_service.analyze_team_players(t1_name, force_refresh)
            t2_players = await self.player_service.analyze_team_players(t2_name, force_refresh)
            
            if not t1_players or not t2_players:
                return None
            
            prompt = PromptTemplates.team_comparison(
                team1_name=t1_name, team1_players=t1_players,
                team2_name=t2_name, team2_players=t2_players,
                team1_win_rate=wr1, team2_win_rate=wr2,
            )
            
            async with self.llm_semaphore:
                await asyncio.sleep(self.ai_request_delay)
                
                ai = get_ai_analyzer(use_mock=False)
                result = await ai.client.complete(
                    prompt=prompt,
                    system_prompt="Ты — CS2 аналитик. Отвечай строго по формату.",
                    temperature=0.3,
                    max_tokens=500,
                )
                await ai.close()
            
            return self._parse_ai_response(result['text'], t1_name, t2_name, t1_players, t2_players)
            
        except Exception as e:
            logger.error(f"AI pipeline failed: {e}")
            return None
    
    def _parse_ai_response(
        self, text: str, t1_name: str, t2_name: str, t1_players: List, t2_players: List
    ) -> Dict[str, Any]:
        winner = t1_name if t1_name in text else t2_name if t2_name in text else t1_name
        prob_match = re.search(r'(\d+)%', text)
        prob = int(prob_match.group(1)) if prob_match else 50
        
        return {
            'text': text,
            'winner': winner,
            'team1_prob': prob if winner == t1_name else 100 - prob,
            'team2_prob': 100 - prob if winner == t1_name else prob,
            'confidence': 'medium',
            'players': {t1_name: t1_players, t2_name: t2_players},
        }
    
    # ========================================================================
    # DATA FETCHING (CACHED + SCRAPER)
    # ========================================================================
    
    async def invalidate_all_cache(self) -> int:
        """Сбросить ВЕСЬ кэш BoneBET."""
        patterns = [
            "matches_v3:*",           # Кэш матчей
            "top_teams:*",            # Рейтинг команд
            "team:*",                 # Составы команд
            "bonebet:player:*",       # Анализ игроков
            "true_win_rate:*",        # True Win Rate
            "ai_ranking:*",           # AI рейтинг команд
            "team_id:*",              # ID команд
        ]
        deleted = 0
        for pattern in patterns:
            count = await self.cache.delete_pattern(pattern)
            deleted += count
            logger.info(f"Deleted {count} keys for pattern {pattern}")
        return deleted
    
    async def _get_cached(self, key: str) -> Optional[Any]:
        if cached := await self.cache.get(key):
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        return None
    
    async def _fetch_all_matches(self) -> List[Dict]:
        """Fetch and filter matches to known teams only."""
        matches = await self._fetch_all_matches_raw()

        # Получаем список известных команд из кэша
        all_teams = await self._get_all_teams_cached()
        known_teams = set(all_teams.keys())

        filtered = []
        for m in matches:
            t1 = m.get('team1_name', '')
            t2 = m.get('team2_name', '')
            if t1 in known_teams or t2 in known_teams:
                filtered.append(m)

        logger.info(f"Filtered to {len(filtered)} known matches (from {len(matches)} total)")
        return filtered

    async def _fetch_top_teams(self) -> List[Dict]:
        cache_key = "top_teams:50"
        if cached := await self._get_cached(cache_key):
            return cached
        
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, self.rankings_scraper.scrape_rankings, 50)
        
        formatted = []
        for rank, team in enumerate(data, 1):
            formatted.append({
                "id": hash(team['name']) % 10_000_000,
                "name": team['name'],
                "world_ranking": rank,
            })
        
        await self.cache.set(cache_key, json.dumps(formatted), ttl=3600)
        return formatted
    
    async def _get_team_data_cached(self, team_name: str) -> Dict:
        key = f"team:{team_name}"
        if cached := await self._get_cached(key):
            return cached
        
        # Получаем ВСЕ команды из кэша (один запрос на 24 часа)
        all_teams = await self._get_all_teams_cached()
        players = all_teams.get(team_name, [])
        
        if not players:
            logger.warning(f"Team {team_name} not found, using placeholder")
            players = [{"nickname": f"{team_name}_player{i}"} for i in range(1, 6)]
        
        data = {
            "id": hash(team_name) % 10_000_000,
            "name": team_name,
            "ranking": None,
            "firepower": None,
            "players": [{"nickname": p['nickname']} for p in players[:5]],
        }
        
        await self.cache.set(key, json.dumps(data), ttl=86400)
        return data
    
    async def _calculate_team_win_rate(self, team_name: str) -> float:
        if team_name == "Unknown":
            return 0.5

        key = f"true_win_rate:{team_name}"
        if cached := await self.cache.get(key):
            try:
                return float(cached)
            except ValueError:
                pass
            
        # Пробуем спарсить
        loop = asyncio.get_event_loop()
        matches = await loop.run_in_executor(None, self.matches_scraper.scrape_team_matches, team_name, False)

        if matches:
            wins = sum(1 for m in matches if m.get('winner') == team_name)
            total = len(matches)
            wr = wins / total if total > 0 else 0.5
        else:
            # Fallback: запрашиваем у AI
            logger.warning(f"No matches for {team_name}, asking AI...")
            wr = await self._get_team_win_rate_ai(team_name)

        await self.cache.set(key, str(wr), ttl=21600)
        return wr
    
    def _calculate_prediction(self, t1: Dict, t2: Dict, wr1: float, wr2: float) -> Dict[str, Any]:
        fp1 = t1.get("firepower") or 5.0
        fp2 = t2.get("firepower") or 5.0
        
        score1 = wr1 * 70 + fp1 * 3.6
        score2 = wr2 * 70 + fp2 * 3.6
        
        total = score1 + score2
        prob1 = (score1 / total) * 100 if total > 0 else 50
        prob2 = 100 - prob1
        
        diff = abs(prob1 - 50)
        conf = "high" if diff > 15 else "medium" if diff > 7 else "low"
        
        return {
            "winner": t1["name"] if prob1 > prob2 else t2["name"],
            "team1_win_prob": round(prob1, 1),
            "team2_win_prob": round(prob2, 1),
            "confidence": conf,
        }
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _is_tier1_match(self, match: Dict, top_50_names: set) -> bool:
        t1 = match.get('team1_name', '')
        t2 = match.get('team2_name', '')
        return t1 in top_50_names and t2 in top_50_names
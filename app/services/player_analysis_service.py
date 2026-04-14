import json
import asyncio
import re
from typing import Dict, List, Optional

from app.services.scraper.bo3_client import BO3Client
from app.services.scraper.team_scraper import TeamScraper
from app.services.scraper.team_matches_scraper import TeamMatchesScraper
from app.core.ai import get_ai_analyzer
from app.db.redis_client import RedisCache
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlayerAnalysisService:
    """AI-powered player analysis with Redis caching."""
    
    def __init__(self):
        self.cache = RedisCache(prefix="bonebet:player")
        self.cache_ttl = 86400  # 24 часа
        self.ai_request_delay = 1.5
        self.llm_semaphore = asyncio.Semaphore(1)
        
        # Скраперы
        client = BO3Client(headless=True)
        self.team_scraper = TeamScraper(client=client)
        self.matches_scraper = TeamMatchesScraper(client=client)
        self.client = client
    
    async def analyze_player(
        self, 
        nickname: str, 
        team_name: str, 
        force_refresh: bool = False
    ) -> Dict:
        """Analyze player with AI, cache results for 24h."""
        
        cache_key = nickname
        
        if not force_refresh:
            if cached := await self._get_cached(cache_key):
                logger.info(f"Returning cached analysis for {nickname}")
                return cached
        
        logger.info(f"Analyzing player: {nickname}")
        
        # Получаем статистику игрока из скрапера
        recent_matches = await self._get_player_matches(nickname, team_name)
        
        # Fallback если нет данных
        if not recent_matches:
            logger.warning(f"No match data for {nickname}, using default")
            fallback = self._make_fallback(nickname, team_name, None, None)
            await self._set_cached(cache_key, fallback)
            return fallback
        
        # Build prompt
        from app.core.ai.prompts import PromptTemplates
        prompt = PromptTemplates.player_analysis(
            nickname=nickname,
            team_name=team_name,
            official_rating=None,
            faceit_elo=None,
            recent_matches=recent_matches,
        )
        
        # Call AI
        async with self.llm_semaphore:
            await asyncio.sleep(self.ai_request_delay)
            
            try:
                ai = get_ai_analyzer(use_mock=False)
                result = await ai.client.complete(
                    prompt=prompt,
                    system_prompt="Ты — CS2 аналитик. Отвечай строго по формату.",
                    temperature=0.3,
                    max_tokens=300,
                )
                await ai.close()
                
                analysis = self._parse_player_response(result['text'], None)
            except Exception as e:
                logger.error(f"AI call failed for {nickname}: {e}")
                analysis = self._make_fallback(nickname, team_name, None, None)
        
        analysis['nickname'] = nickname
        analysis['team'] = team_name
        
        await self._set_cached(cache_key, analysis)
        return analysis
    
    async def analyze_team_players(
        self, 
        team_name: str, 
        force_refresh: bool = False
    ) -> List[Dict]:
        """Analyze all players in a team (PARALLEL)."""

        # Получаем состав через скрапер
        loop = asyncio.get_event_loop()
        teams_data = await loop.run_in_executor(None, self.team_scraper.scrape_all_teams, 3)

        players_data = teams_data.get(team_name, [])

        if not players_data:
            logger.warning(f"No players found for {team_name}, using placeholder")
            players_data = [{"nickname": f"{team_name}_player{i}"} for i in range(1, 6)]

        # Параллельный анализ
        tasks = [
            self.analyze_player(p['nickname'], team_name, force_refresh) 
            for p in players_data[:5]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        analyzed = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                analyzed.append(result)
            else:
                nickname = players_data[i]['nickname'] if i < len(players_data) else f"{team_name}_player{i}"
                analyzed.append(self._make_fallback(nickname, team_name, None, None))

        return analyzed
    
    async def _get_cached(self, key: str) -> Optional[Dict]:
        if cached := await self.cache.get(key):
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        return None
    
    async def _set_cached(self, key: str, data: Dict) -> None:
        await self.cache.set(key, json.dumps(data), ttl=self.cache_ttl)
    
    def _make_fallback(
        self, 
        nickname: str, 
        team_name: str, 
        official_rating: Optional[float], 
        faceit_elo: Optional[int]
    ) -> Dict:
        return {
            'nickname': nickname,
            'team': team_name,
            'role': 'Unknown',
            'dynamic': 'stable',
            'true_rating': official_rating if official_rating else 5.0,
            'official_rating': official_rating,
            'faceit_elo': faceit_elo,
            'reasoning': 'No match data or AI unavailable',
            'context': '',
        }
    
    async def _get_player_matches(self, nickname: str, team_name: str) -> List[Dict]:
        """Get player's recent matches from scraper with full stats."""
        try:
            loop = asyncio.get_event_loop()

            # Собираем матчи команды с деталями
            matches = await loop.run_in_executor(
                None, 
                self.matches_scraper.scrape_team_matches, 
                team_name, 
                True  
            )

            player_matches = []
            for match in matches[:5]:  # Последние 5 матчей
                details = match.get('details', {})

                # Ищем игрока в статистике обеих команд
                for team_stats in [details.get('team1_stats'), details.get('team2_stats')]:
                    if not team_stats:
                        continue
                    
                    for p in team_stats.get('players', []):
                        if p.get('nickname', '').lower() == nickname.lower():
                            player_matches.append({
                                'opponent': self._get_opponent(match, team_name),
                                'opponent_rank': 100,  # TODO: получить реальный рейтинг
                                'kills': p.get('kills', 0),
                                'deaths': p.get('deaths', 0),
                                'rating': p.get('rating_bo3', 0),
                                'adr': p.get('adr', 0),
                                'map': details.get('metadata', {}).get('map', 'Unknown'),
                                'date': match.get('date'),
                            })
                            break
                        
            return player_matches

        except Exception as e:
            logger.warning(f"Failed to get matches for {nickname}: {e}")
            return []
        
    def _get_opponent(self, match: Dict, team_name: str) -> str:
        """Определяет соперника в матче."""
        if match.get('team1') == team_name:
            return match.get('team2', 'Unknown')
        return match.get('team1', 'Unknown')
    
    def _parse_player_response(self, text: str, official_rating: Optional[float]) -> Dict:
        result = {
            'role': 'Unknown',
            'dynamic': 'stable',
            'true_rating': official_rating if official_rating else 5.0,
            'reasoning': '',
            'context': '',
        }
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            lower = line.lower()
            
            if 'роль:' in lower or 'role:' in lower:
                role_text = line.split(':', 1)[1].strip().lower()
                if 'awp' in role_text:
                    result['role'] = 'AWPer'
                elif 'entry' in role_text:
                    result['role'] = 'Entry'
                elif 'igl' in role_text:
                    result['role'] = 'IGL'
                elif 'support' in role_text:
                    result['role'] = 'Support'
                elif 'lurker' in role_text:
                    result['role'] = 'Lurker'
                else:
                    result['role'] = role_text[:20]
            
            elif 'динамика:' in lower or 'dynamic:' in lower:
                dyn_text = line.split(':', 1)[1].strip().lower()
                if 'rising' in dyn_text:
                    result['dynamic'] = 'rising'
                elif 'falling' in dyn_text:
                    result['dynamic'] = 'falling'
                else:
                    result['dynamic'] = 'stable'
            
            elif 'true rating:' in lower:
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    result['true_rating'] = float(numbers[0])
            
            elif 'обоснование:' in lower or 'reasoning:' in lower:
                result['reasoning'] = line.split(':', 1)[1].strip()
            
            elif 'контекст:' in lower or 'context:' in lower:
                result['context'] = line.split(':', 1)[1].strip()
        
        return result
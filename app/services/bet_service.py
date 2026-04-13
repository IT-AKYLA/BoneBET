"""Service for /bet endpoint - orchestrates match analysis with Redis cache."""

import json
from typing import List, Dict, Any, Optional

from app.clients.cs2_analytics import CS2AnalyticsClient
from app.core.ai import get_ai_analyzer
from app.db.redis_client import RedisCache
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BetService:
    """Service for analyzing matches for betting with Redis cache."""
    
    def __init__(self):
        self.client = CS2AnalyticsClient()
        self.cache = RedisCache(prefix="bonebet")
        self.cache_ttl = 18000
        
    async def _get_team_ranking_ai(self, team_name: str) -> int:
        """Get team ranking from AI if not in top-50."""
        cache_key = f"ai_ranking:{team_name}"

        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return int(cached)
            except ValueError:
                pass
            
        try:
            ai_analyzer = get_ai_analyzer(use_mock=False)

            prompt = f"""Ты — эксперт по CS2. Назови ПРИМЕРНЫЙ текущий мировой рейтинг HLTV команды "{team_name}".

    Ответ должен быть ТОЛЬКО числом от 1 до 200. Если команда малоизвестная или тир-3 — укажи 100-150.
    Если команда неизвестна совсем — 200.
    Не пиши ничего кроме числа."""

            result = await ai_analyzer.client.complete(
                prompt=prompt,
                system_prompt="Ты — эксперт по CS2. Отвечай только числом.",
                temperature=0.1,
                max_tokens=10,
            )

            # Извлекаем число из ответа
            import re
            text = result.get("text", "100")
            numbers = re.findall(r'\d+', text)
            ranking = int(numbers[0]) if numbers else 100
            ranking = max(1, min(200, ranking))  # Ограничиваем 1-200

            await self.cache.set(cache_key, str(ranking), ttl=86400 * 7)  # Кэш на неделю
            await ai_analyzer.close()

            return ranking

        except Exception as e:
            logger.warning(f"Failed to get AI ranking for {team_name}: {e}")
            return 100  # По умолчанию — слабая команда
        
    async def analyze_matches(
        self,
        limit: int = 10,
        tier_filter: str = "all",
        use_ai: bool = True,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Analyze live and upcoming matches with caching.

        Cache key: bonebet:matches:{tier_filter}:{limit}:{use_ai}
        TTL: 24 hours
        """

        cache_key = f"matches:{tier_filter}:{limit}:{use_ai}"

        # Try to get from cache
        if not force_refresh:
            cached = await self.cache.get(cache_key)
            if cached:
                try:
                    data = json.loads(cached)
                    logger.info(f"Returning cached data for {cache_key}")
                    return data
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode cached data, refreshing...")

        logger.info(f"Cache miss for {cache_key}, fetching fresh data...")

        # Fetch fresh data
        results = await self._fetch_and_analyze(limit, tier_filter, use_ai)

        # Save to cache
        if results:
            await self.cache.set(cache_key, json.dumps(results), ttl=self.cache_ttl)
            logger.info(f"Cached {len(results)} matches with key {cache_key}")

        return results        
        
    async def _calculate_team_win_rate(
        self, 
        team_name: str,
        top_50_teams: Dict[int, int] = None
    ) -> float:
        """Calculate team's True Win Rate weighted by opponent strength (with AI fallback)."""
        cache_key = f"true_win_rate:{team_name}"
        
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return float(cached)
            except ValueError:
                pass
            
        try:
            matches = await self.client.get_team_matches(team_name, limit=20)
            if not matches:
                return 0.5
            
            total_weight = 0.0
            weighted_wins = 0.0
            
            for match in matches:
                team1 = match.get("team1", {})
                team2 = match.get("team2", {})
                team1_name_api = team1.get("name", "")
                team2_name_api = team2.get("name", "")
                score1 = match.get("team1_score", 0) or 0
                score2 = match.get("team2_score", 0) or 0
                
                # Определяем, за кого мы и кто соперник
                if team_name.lower() in team1_name_api.lower():
                    is_win = score1 > score2
                    opponent = team2
                elif team_name.lower() in team2_name_api.lower():
                    is_win = score2 > score1
                    opponent = team1
                else:
                    continue
                
                # Получаем рейтинг соперника
                opponent_id = opponent.get("id")
                opponent_name = opponent.get("name", "")
                
                # 1. Пробуем из топ-50
                if top_50_teams and opponent_id and opponent_id in top_50_teams:
                    opponent_rank = top_50_teams[opponent_id]
                else:
                    # 2. Пробуем из API (если есть)
                    api_rank = opponent.get("world_ranking")
                    if api_rank and api_rank > 0:
                        opponent_rank = api_rank
                    else:
                        # 3. Запрашиваем у AI
                        opponent_rank = await self._get_team_ranking_ai(opponent_name)
                
                # Вес соперника: #1 = 1.0, #10 = 0.32, #50 = 0.14, #100 = 0.1, #200 = 0.07
                weight = 1.0 / (opponent_rank ** 0.5) if opponent_rank > 0 else 0.1
                
                total_weight += weight
                if is_win:
                    weighted_wins += weight
            
            true_win_rate = weighted_wins / total_weight if total_weight > 0 else 0.5
            
            await self.cache.set(cache_key, str(true_win_rate), ttl=21600)
            logger.info(f"True Win Rate for {team_name}: {true_win_rate:.3f}")
            return true_win_rate
            
        except Exception as e:
            logger.warning(f"Failed to calculate true win rate for {team_name}: {e}")
            return 0.5
    
    async def _fetch_and_analyze(
        self,
        limit: int,
        tier_filter: str,
        use_ai: bool,
    ) -> List[Dict[str, Any]]:
        """Fetch and analyze matches (internal method)."""
        
        # 1. Get top-50 teams for tier filter
        rankings = await self._fetch_top_teams()
        top_50_ids = {t["id"] for t in rankings}
        
        # 2. Fetch matches
        live_matches = await self._fetch_live_matches()
        upcoming_matches = await self._fetch_upcoming_matches()
        
        all_matches = live_matches + upcoming_matches
        
        logger.info(f"Fetched {len(live_matches)} live, {len(upcoming_matches)} upcoming matches")
        
        # 3. Filter by tier
        if tier_filter == "tier1":
            all_matches = self._filter_tier1_matches(all_matches, top_50_ids)
            logger.info(f"Filtered to {len(all_matches)} tier-1 matches")
        
        # 4. Limit
        all_matches = all_matches[:limit]
        
        # 5. Analyze each match
        results = []
        
        # Initialize AI analyzer if needed
        ai_analyzer = None
        if use_ai:
            try:
                ai_analyzer = get_ai_analyzer(use_mock=False)
                logger.info("AI analyzer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize AI analyzer: {e}")
        
        for match in all_matches:
            try:
                analysis = await self._analyze_single_match(
                    match=match,
                    top_50_ids=top_50_ids,
                    ai_analyzer=ai_analyzer,
                )
                if analysis:
                    results.append(analysis)
            except Exception as e:
                match_id = match.get('id', 'unknown')
                logger.error(f"Failed to analyze match {match_id}: {e}")
                continue
        
        if ai_analyzer:
            await ai_analyzer.close()
        
        logger.info(f"Successfully analyzed {len(results)} matches")
        return results
    
    async def invalidate_cache(self, tier_filter: str = "all") -> None:
        """Invalidate cache for specific tier filter."""
        patterns = [
            f"matches:{tier_filter}:*",
            f"matches:{tier_filter}:*:*",
        ]
        for pattern in patterns:
            deleted = await self.cache.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted} cache entries for pattern {pattern}")
    
    # ========================================================================
    # PRIVATE FETCH METHODS (с кэшированием)
    # ========================================================================
    
    async def _fetch_top_teams(self) -> List[Dict]:
        """Fetch top-50 teams with caching."""
        cache_key = "top_teams:50"
        
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        
        try:
            data = await self.client.get_team_rankings(limit=50)
            await self.cache.set(cache_key, json.dumps(data), ttl=3600)  # 1 hour
            return data
        except Exception as e:
            logger.error(f"Failed to fetch top teams: {e}")
            return []
    
    async def _fetch_live_matches(self) -> List[Dict]:
        """Fetch live matches with short cache."""
        cache_key = "matches:live"
        
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        
        try:
            data = await self.client.get_live_matches()
            await self.cache.set(cache_key, json.dumps(data), ttl=300)  # 5 minutes
            return data
        except Exception as e:
            logger.error(f"Failed to fetch live matches: {e}")
            return []
    
    async def _fetch_upcoming_matches(self) -> List[Dict]:
        """Fetch upcoming matches with medium cache."""
        cache_key = "matches:upcoming"
        
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        
        try:
            data = await self.client.get_upcoming_matches()
            await self.cache.set(cache_key, json.dumps(data), ttl=3600)  # 1 hour
            return data
        except Exception as e:
            logger.error(f"Failed to fetch upcoming matches: {e}")
            return []
    
    async def _get_team_data_cached(self, team_id: Optional[int], team_name: str) -> Dict[str, Any]:
        """Get team data with caching."""
        cache_key = f"team:{team_id or team_name}"
        
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        
        data = await self._get_team_data_safe(team_id, team_name)
        
        if data.get("id") != 0:  # Cache only valid data
            await self.cache.set(cache_key, json.dumps(data), ttl=86400)  # 24 hours
        
        return data

    def _filter_tier1_matches(self, matches: List[Dict], top_50_ids: set) -> List[Dict]:
        """Filter matches to only include tier-1 teams."""
        filtered = []
        for m in matches:
            team1_id = self._extract_team_id(m, "team1")
            team2_id = self._extract_team_id(m, "team2")
            if team1_id in top_50_ids and team2_id in top_50_ids:
                filtered.append(m)
        return filtered
    
    async def _analyze_single_match(
        self,
        match: Dict[str, Any],
        top_50_ids: set,
        ai_analyzer: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Analyze a single match."""

        team1_name = self._extract_team_name(match, "team1")
        team2_name = self._extract_team_name(match, "team2")
        team1_id = self._extract_team_id(match, "team1")
        team2_id = self._extract_team_id(match, "team2")

        if not team1_name or not team2_name:
            logger.warning("Skipping match: missing team names")
            return None

        logger.info(f"Analyzing: {team1_name} vs {team2_name}")

        # Get team data with caching
        team1_data = await self._get_team_data_cached(team1_id, team1_name)
        team2_data = await self._get_team_data_cached(team2_id, team2_name)

        # Загружаем топ-50 команд с рейтингами
        top_teams = await self._fetch_top_teams()
        top_50_teams = {t["id"]: t["world_ranking"] for t in top_teams}

        # Calculate win rates
        team1_win_rate = await self._calculate_team_win_rate(team1_name, top_50_teams)
        team2_win_rate = await self._calculate_team_win_rate(team2_name, top_50_teams)

        # Calculate prediction with win rates
        prediction = self._calculate_prediction(
            team1_data, 
            team2_data,
            team1_win_rate,
            team2_win_rate,
        )
        
        # Run AI analysis if available
        ai_result = None
        if ai_analyzer:
            ai_result = await self._run_ai_analysis_safe(
                ai_analyzer=ai_analyzer,
                team1_data=team1_data,
                team2_data=team2_data,
                prediction=prediction,
            )
        
        return {
            "match_id": self._generate_match_id(match, team1_name, team2_name),
            "team1": team1_data,
            "team2": team2_data,
            "tournament": self._extract_tournament(match),
            "scheduled_at": self._extract_scheduled_time(match),
            "status": match.get("status", "upcoming"),
            "prediction": prediction,
            "ai_analysis": ai_result,
        }
    
    async def _get_team_data_safe(
        self,
        team_id: Optional[int],
        team_name: str,
    ) -> Dict[str, Any]:
        """Safely get team data with fallbacks."""
        
        if not team_id:
            team_id = await self._find_team_id_by_name(team_name)
        
        team = None
        if team_id:
            try:
                team = await self.client.get_team(team_id, wait_for_loading=True)
            except Exception as e:
                logger.warning(f"Failed to get team {team_name}: {e}")
        
        players = await self._get_players_stats_safe(team, team_name)
        
        ratings = [p.get("official_rating", 0) for p in players if p.get("official_rating")]
        firepower = sum(ratings) / len(ratings) if ratings else None
        
        return {
            "id": team_id or 0,
            "name": team.get("name", team_name) if team else team_name,
            "ranking": team.get("world_ranking") if team else None,
            "firepower": round(firepower, 2) if firepower else None,
            "players": players[:5],
        }
    
    async def _find_team_id_by_name(self, name: str) -> Optional[int]:
        """Find team ID by name with caching."""
        cache_key = f"team_id:{name}"
        
        cached = await self.cache.get(cache_key)
        if cached:
            return int(cached)
        
        try:
            teams = await self.client.search_teams(name)
            if teams:
                team_id = teams[0].get("id")
                if team_id:
                    await self.cache.set(cache_key, str(team_id), ttl=86400)
                    return team_id
        except Exception:
            pass
        return None
    
    async def _get_players_stats_safe(
        self,
        team: Optional[Dict],
        team_name: str,
    ) -> List[Dict]:
        """Safely get players stats with caching."""
        players = []
        
        players_data = team.get("players", []) if team else []
        unique_nicks = set()
        for p in players_data:
            nick = p.get("nickname")
            if nick:
                unique_nicks.add(nick)
        
        if not unique_nicks:
            logger.warning(f"No players found for {team_name}")
            return []
        
        for nickname in list(unique_nicks)[:5]:
            player_data = await self._get_player_cached(nickname)
            players.append(player_data)
        
        return players
    
    async def _get_player_cached(self, nickname: str) -> Dict:
        """Get player data with caching."""
        cache_key = f"player:{nickname}"
        
        cached = await self.cache.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass
        
        try:
            player = await self.client.get_player(nickname, wait_for_loading=False)
            official = player.get("official_stats", {})
            faceit = player.get("faceit_stats", {})
            
            data = {
                "nickname": nickname,
                "official_rating": official.get("avg_rating"),
                "official_kd": official.get("avg_kd"),
                "official_adr": official.get("avg_adr"),
                "faceit_elo": faceit.get("elo") if faceit else None,
            }
            
            await self.cache.set(cache_key, json.dumps(data), ttl=86400)
            return data
            
        except Exception as e:
            logger.warning(f"Failed to get player {nickname}: {e}")
            return {"nickname": nickname}
    
    def _calculate_prediction(
        self,
        team1_data: Dict,
        team2_data: Dict,
        team1_win_rate: float = 0.5,
        team2_win_rate: float = 0.5,
    ) -> Dict[str, Any]:
        """Calculate match prediction with True Win Rate."""
        
        fp1 = team1_data.get("firepower") or 5.0
        fp2 = team2_data.get("firepower") or 5.0
        
        # Win Rate — 70% веса (основной фактор)
        wr_score1 = team1_win_rate * 100
        wr_score2 = team2_win_rate * 100
        
        # Firepower — 30% веса (дополнительный фактор)
        fp_score1 = fp1 * 12  # 5.0 → 60, 7.0 → 84
        fp_score2 = fp2 * 12
        
        # Комбинированный счёт
        score1 = wr_score1 * 0.7 + fp_score1 * 0.3
        score2 = wr_score2 * 0.7 + fp_score2 * 0.3
        
        total = score1 + score2
        prob1 = (score1 / total) * 100 if total > 0 else 50
        prob2 = 100 - prob1
        
        diff = abs(prob1 - 50)
        if diff > 15:
            confidence = "high"
        elif diff > 7:
            confidence = "medium"
        else:
            confidence = "low"
        
        winner = team1_data["name"] if prob1 > prob2 else team2_data["name"]
        
        return {
            "winner": winner,
            "team1_win_prob": round(prob1, 1),
            "team2_win_prob": round(prob2, 1),
            "confidence": confidence,
        }
    
    async def _run_ai_analysis_safe(
        self,
        ai_analyzer: Any,
        team1_data: Dict,
        team2_data: Dict,
        prediction: Dict,
    ) -> Optional[Dict]:
        """Safely run AI analysis."""
        try:
            result = await ai_analyzer.analyze_match(
                team1_data=team1_data,
                team2_data=team2_data,
                stats_prediction=prediction,
            )
            
            return {
                "text": result.get("analysis"),
                "model": result.get("model"),
                "provider": result.get("provider"),
            }
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _extract_team_name(self, match: Dict, prefix: str) -> Optional[str]:
        name = match.get(f"{prefix}_name")
        if not name:
            team_obj = match.get(prefix, {})
            if isinstance(team_obj, dict):
                name = team_obj.get("name")
        return name or "Unknown"
    
    def _extract_team_id(self, match: Dict, prefix: str) -> Optional[int]:
        team_id = match.get(f"{prefix}_id")
        if team_id is None:
            team_obj = match.get(prefix, {})
            if isinstance(team_obj, dict):
                team_id = team_obj.get("id")
        return team_id
    
    def _extract_tournament(self, match: Dict) -> Optional[str]:
        return match.get("event") or match.get("tournament_name")
    
    def _extract_scheduled_time(self, match: Dict) -> Optional[str]:
        return match.get("match_time") or match.get("scheduled_at")
    
    def _generate_match_id(self, match: Dict, team1: str, team2: str) -> str:
        return str(match.get("id") or match.get("url", f"{team1}_vs_{team2}"))
"""Скрапер матчей с BO3.gg — live, upcoming, finished."""

import re
from typing import List, Dict, Any, Optional
from selectolax.parser import HTMLParser
from loguru import logger

from app.services.scraper.bo3_client import BO3Client


class MatchScraper:
    """Скрапер матчей с BO3.gg"""
    
    BASE_URL = "https://bo3.gg"
    
    def __init__(self, client: Optional[BO3Client] = None):
        self.client = client or BO3Client(headless=True)
        self._own_client = client is None
    
    def __enter__(self):
        if self._own_client:
            self.client.start()
        return self
    
    def __exit__(self, *args):
        if self._own_client:
            self.client.stop()
    
    def scrape_all_matches(self) -> List[Dict[str, Any]]:
        """Собирает все матчи: live + upcoming."""
        logger.info("📅 Сбор всех матчей с BO3.gg...")
        
        html = self.client.get("/matches/current", wait_seconds=3.0)
        tree = HTMLParser(html)
        
        matches = []
        seen_urls = set()
        
        for row in tree.css('.table-row'):
            if row.css_first('.table-head'):
                continue
            
            match_data = self._parse_match_row(row)
            if match_data and match_data.get('url'):
                url = match_data['url']
                if url not in seen_urls:
                    seen_urls.add(url)
                    matches.append(match_data)
        
        live = [m for m in matches if m['status'] == 'live']
        upcoming = [m for m in matches if m['status'] == 'upcoming']
        
        logger.info(f"✅ Найдено: {len(live)} live, {len(upcoming)} upcoming")
        return live + upcoming
    
    def scrape_live_matches(self) -> List[Dict[str, Any]]:
        all_matches = self.scrape_all_matches()
        return [m for m in all_matches if m['status'] == 'live']
    
    def scrape_upcoming_matches(self) -> List[Dict[str, Any]]:
        all_matches = self.scrape_all_matches()
        return [m for m in all_matches if m['status'] == 'upcoming']
    
    def _parse_match_row(self, row) -> Optional[Dict[str, Any]]:
        try:
            classes = row.attrs.get('class', '')
            
            if 'table-row--current' in classes:
                status = 'live'
            elif 'table-row--upcoming' in classes:
                status = 'upcoming'
            elif 'table-row--finished' in classes:
                status = 'finished'
            else:
                status = 'upcoming'
            
            teams = row.css('.team-name')
            if len(teams) < 2:
                return None
            
            team1 = teams[0].text(strip=True)
            team2 = teams[1].text(strip=True)
            
            if team1 == 'TBD' or team2 == 'TBD':
                return None
            
            link = row.css_first('a[href*="/matches/"]')
            url = None
            if link:
                href = link.attrs.get('href', '')
                url = f"{self.BASE_URL}{href}" if href.startswith('/') else href
            
            event_el = row.css_first('.tournament-name')
            event = event_el.text(strip=True) if event_el else None
            
            time_el = row.css_first('.time')
            match_time = time_el.text(strip=True) if time_el else None
            
            score_el = row.css_first('.c-match-score')
            team1_score = None
            team2_score = None
            if score_el:
                score_text = score_el.text(strip=True)
                scores = re.findall(r'\d+', score_text)
                if len(scores) >= 2:
                    team1_score = int(scores[0])
                    team2_score = int(scores[1])
            
            winner = None
            if status == 'finished':
                winner_class = row.css_first('.c-match__team.winner')
                if winner_class:
                    winner = team1 if teams[0].parent == winner_class else team2
            
            return {
                'team1_name': team1,
                'team2_name': team2,
                'team1_score': team1_score,
                'team2_score': team2_score,
                'winner': winner,
                'status': status,
                'url': url,
                'event': event,
                'match_time': match_time,
                'source': 'bo3',
            }
            
        except Exception as e:
            logger.debug(f"⚠️ Ошибка парсинга строки: {e}")
            return None


_scraper: Optional[MatchScraper] = None

def get_match_scraper() -> MatchScraper:
    global _scraper
    if _scraper is None:
        _scraper = MatchScraper()
    return _scraper
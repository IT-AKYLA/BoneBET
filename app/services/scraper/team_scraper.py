"""Скрапер команд и составов с BO3.gg/teams/earnings"""

from typing import List, Dict, Any, Optional
from selectolax.parser import HTMLParser
from loguru import logger
import re
from app.services.scraper.bo3_client import BO3Client


class TeamScraper:
    BASE_URL = "https://bo3.gg"
    REAL_NICKS = {
        '910', 'b1t', '3gl', '957', '0SAMAS', '1eeR', 
        '7kick', '9z', '1win', '2K', '3ARK00', '4glory',
        '5try', '6son', '7oX1C', '8pack', '9INE'
    }
    
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
    
    def _clean_nickname(self, nick: str) -> str:
        if not nick:
            return ""
        
        if nick in self.REAL_NICKS:
            return nick
        
        if nick[0].isdigit() and '.' not in nick[:3]:
            return nick
        
        return re.sub(r'^[\d.]+\s*', '', nick).strip()
    
    
    def scrape_all_teams(self, pages: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        all_teams = {}
        
        for page in range(1, pages + 1):
            url = f"/teams/earnings?page={page}" if page > 1 else "/teams/earnings"
            logger.info(f"📄 Страница {page}: {url}")
            
            html = self.client.get(url, wait_seconds=3.0)
            tree = HTMLParser(html)
            
            rows = tree.css('.table-row')
            
            for row in rows:
                if row.css_first('.table-head'):
                    continue
                
                team_data = self._parse_team_row(row)
                if team_data:
                    team_name = team_data['name']
                    if team_name not in all_teams:
                        all_teams[team_name] = team_data['players']
        
        return all_teams
    
    def _parse_team_row(self, row) -> Optional[Dict[str, Any]]:
        try:
            team_link = row.css_first('.team-title')
            if not team_link:
                return None
            
            team_name_el = team_link.css_first('.team-name')
            if not team_name_el:
                return None
            
            full_text = team_name_el.text(strip=True)
            country_el = team_name_el.css_first('.country-name')
            if country_el:
                country = country_el.text(strip=True)
                team_name = full_text.replace(country, '').strip()
            else:
                team_name = full_text
            
            players = []
            player_cells = row.css('.c-table-cell-players .o-list-bare__item')
            
            for cell in player_cells:
                player_link = cell.css_first('a')
                if player_link:
                    raw_nick = player_link.text(strip=True)
                else:
                    default_el = cell.css_first('.default')
                    raw_nick = default_el.text(strip=True) if default_el else cell.text(strip=True)
                
                nickname = self._clean_nickname(raw_nick)
                if nickname and nickname != 'TBD':
                    players.append({'nickname': nickname})
            
            return {'name': team_name, 'players': players}
            
        except Exception as e:
            logger.debug(f"⚠️ Ошибка парсинга: {e}")
            return None
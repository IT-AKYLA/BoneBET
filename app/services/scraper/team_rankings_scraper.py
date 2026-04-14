"""Скрапер рейтинга команд с BO3.gg/teams/earnings"""

import re
import time
from typing import List, Dict, Any, Optional
from selectolax.parser import HTMLParser
from loguru import logger

from app.services.scraper.bo3_client import BO3Client


class TeamRankingsScraper:
    """Парсер рейтинга команд с BO3.gg/teams/earnings"""
    
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
    
    def scrape_rankings(self, limit: int = 50) -> List[Dict[str, Any]]:
        all_teams = []
        page = 1
        
        logger.info(f"📊 Сбор рейтинга команд (лимит: {limit})")
        
        while len(all_teams) < limit:
            url = f"{self.BASE_URL}/teams/earnings"
            if page > 1:
                url += f"?page={page}"
            
            logger.info(f"   📄 Страница {page}")
            html = self.client.get(url, wait_seconds=3.0)
            tree = HTMLParser(html)
            
            rows = tree.css('.table-row')
            
            for row in rows:
                if row.css_first('.table-head'):
                    continue
                
                team_data = self._parse_ranking_row(row)
                if team_data:
                    all_teams.append(team_data)
                    
                if len(all_teams) >= limit:
                    break
            
            if len(all_teams) >= limit:
                break
            
            page += 1
            time.sleep(1)
        
        logger.info(f"✅ Всего собрано команд: {len(all_teams)}")
        return all_teams[:limit]
    
    def _parse_ranking_row(self, row) -> Optional[Dict[str, Any]]:
        try:
            team_el = row.css_first('.team-name')
            if not team_el:
                return None
            
            full_text = team_el.text(strip=True)
            country_el = team_el.css_first('.country-name')
            country = country_el.text(strip=True) if country_el else None
            team_name = full_text.replace(country, '').strip() if country else full_text
            
            team_link = row.css_first('.team-title')
            slug = None
            if team_link:
                href = team_link.attrs.get('href', '')
                slug = href.split('/')[-1] if href else None
            
            return {
                'name': team_name,
                'slug': slug,
                'country': country,
            }
            
        except Exception as e:
            logger.debug(f"⚠️ Ошибка парсинга: {e}")
            return None
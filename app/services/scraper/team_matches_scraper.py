"""Скрапер истории матчей команды"""

import re
import time
from typing import List, Dict, Any, Optional
from selectolax.parser import HTMLParser
from loguru import logger

from app.services.scraper.bo3_client import BO3Client


class TeamMatchesScraper:
    """Парсер истории матчей команды с BO3.gg"""
    
    BASE_URL = "https://bo3.gg"
    
    def __init__(self, client: Optional[BO3Client] = None):
        self.client = client or BO3Client(headless=True)
        self._own_client = client is None
    
    def find_team_slug(self, team_name: str) -> Optional[str]:
        return self._get_team_slug(team_name)
    
    def __enter__(self):
        if self._own_client:
            self.client.start()
        return self
    
    def __exit__(self, *args):
        if self._own_client:
            self.client.stop()
    
    def _parse_match_row(self, row) -> Optional[Dict[str, Any]]:
        """Парсит строку матча."""
        try:
            classes = row.attrs.get('class', '')

            # Техническое поражение
            if 'table-row--defwin' in classes:
                return self._parse_defwin_match(row)

            # Завершенный матч
            if 'table-row--finished' in classes:
                return self._parse_finished_match(row)

            return None

        except Exception as e:
            logger.debug(f"⚠️ Ошибка парсинга: {e}")
            return None


    def _parse_finished_match(self, row) -> Optional[Dict[str, Any]]:
        """Парсит завершенный матч."""
        teams = row.css('.team-name')
        if len(teams) < 2:
            return None

        team1 = teams[0].text(strip=True)
        team2 = teams[1].text(strip=True)

        # Победитель
        winner_class = row.css_first('.c-match__team.winner')
        is_team1_winner = winner_class and teams[0].parent == winner_class
        winner = team1 if is_team1_winner else team2

        # Счет
        score_el = row.css_first('.c-match-score')
        score_text = score_el.text(strip=True) if score_el else ''
        scores = re.findall(r'\d+', score_text)

        return {
            'team1': team1,
            'team2': team2,
            'winner': winner,
            'team1_score': int(scores[0]) if len(scores) > 0 else None,
            'team2_score': int(scores[1]) if len(scores) > 1 else None,
        }


    def _parse_defwin_match(self, row) -> Optional[Dict[str, Any]]:
        """Парсит техническое поражение."""
        teams = row.css('.team-name')
        if len(teams) < 2:
            return None

        team1 = teams[0].text(strip=True)
        team2 = teams[1].text(strip=True)

        winner_class = row.css_first('.c-match__team.winner')
        is_team1_winner = winner_class and teams[0].parent == winner_class

        return {
            'team1': team1,
            'team2': team2,
            'winner': team1 if is_team1_winner else team2,
            'team1_score': None,
            'team2_score': None,
        }
    
    def _get_team_slug(self, team_name: str) -> str:
        """Конвертирует название команды в slug для BO3.gg."""
        slug_map = {
            "Vitality": "vitality",
            "G2": "g2",
            "Spirit": "spirit",
            "Liquid": "liquid",
            "Falcons": "falcons-esports",
            "NAVI": "natus-vincere",
            "Natus Vincere": "natus-vincere",
            "MOUZ": "mousesports",
            "FaZe": "faze",
            "FURIA": "furia",
            "3DMAX": "3dmax",
            "Passion UA": "passion-ua",
            "B8": "b8",
            "Aurora": "aurora-gaming",
            "HOTU": "hotu",
            "Legacy": "legacy-br",
            "RED Canids": "red-canids-cs-go",
            "Gentle Mates": "gentle-mates-cs",
        }

        if team_name in slug_map:
            return slug_map[team_name]

        # Fallback: генерируем slug
        return team_name.lower().replace(' ', '-').replace('.', '')

    def scrape_team_matches(self, team_name: str, with_details: bool = False) -> List[Dict]:
        """Собирает матчи команды."""
        slug = self._get_team_slug(team_name)
        url = f"/teams/{slug}/matches"

        logger.info(f"📊 Сбор матчей для {team_name} (slug: {slug})")

        all_matches = []
        page = 1

        while page <= 3:  # Максимум 3 страницы истории
            page_url = f"{url}?page={page}" if page > 1 else url

            try:
                html = self.client.get(page_url, wait_seconds=3.0)
                tree = HTMLParser(html)

                rows = tree.css('.table-row')
                page_matches = 0

                for row in rows:
                    if row.css_first('.table-head'):
                        continue
                    
                    match_data = self._parse_match_row(row)
                    if match_data:
                        all_matches.append(match_data)
                        page_matches += 1

                # Проверяем, есть ли следующая страница
                next_btn = tree.css_first('.pagination .next:not(.disabled)')
                if not next_btn or page_matches == 0:
                    break

            except Exception as e:
                logger.error(f"Ошибка парсинга страницы {page}: {e}")
                break
            
            page += 1

        logger.info(f"✅ Найдено матчей для {team_name}: {len(all_matches)}")
        return all_matches
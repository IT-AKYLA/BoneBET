"""BO3.gg HTTP client using Selenium with browser singleton."""

from typing import Optional
import time
from loguru import logger
from selenium.webdriver.support.ui import WebDriverWait

from app.services.scraper.browser_singleton import BrowserSingleton


class BO3Client:
    """Клиент для BO3.gg — загрузка страниц."""
    
    BASE_URL = "https://bo3.gg"
    _driver_started = False
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait: Optional[WebDriverWait] = None
        self._started = False
    
    def start(self):
        """Подключается к синглтону браузера."""
        self.driver = BrowserSingleton.get_driver(self.headless)
        self.wait = WebDriverWait(self.driver, 10)
        self._started = True
        return self
    
    def stop(self) -> None:
        """НЕ закрывает браузер."""
        self._started = False
        self.driver = None
        self.wait = None
    
    def get(self, url: str, wait_seconds: float = 3.0) -> str:
        """Загружает страницу и возвращает HTML."""
        if self.driver is None:
            self.start()
        
        full_url = url if url.startswith('http') else f"{self.BASE_URL}{url}"
        
        try:
            self.driver.get(full_url)
            time.sleep(wait_seconds)
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}, перезапускаю браузер...")
            BrowserSingleton.quit_driver()
            self.driver = BrowserSingleton.get_driver(self.headless)
            self.driver.get(full_url)
            time.sleep(wait_seconds)
            return self.driver.page_source
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
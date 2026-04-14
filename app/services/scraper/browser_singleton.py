from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from loguru import logger
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class BrowserSingleton:    
    _driver: Optional[webdriver.Chrome] = None
    
    @classmethod
    def get_driver(cls, headless: bool = True) -> webdriver.Chrome:
        if cls._driver is None:
            logger.info("🚀 Запуск браузера (синглтон)...")
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            if headless:
                options.add_argument('--headless=new')

            # Автоматический подбор драйвера
            service = Service(ChromeDriverManager().install())
            cls._driver = webdriver.Chrome(service=service, options=options)
            cls._driver.set_page_load_timeout(30)
            logger.info("✅ Браузер запущен")

        return cls._driver
    
    @classmethod
    def quit_driver(cls):
        if cls._driver:
            cls._driver.quit()
            cls._driver = None
            logger.info("👋 Браузер остановлен")
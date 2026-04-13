"""Universal LLM client supporting free providers."""

import os
from typing import Optional, Dict, Any
from enum import Enum

import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers."""
    OPENROUTER = "openrouter"      # Бесплатные модели через OpenRouter
    GROQ = "groq"                  # Бесплатный API Groq
    OLLAMA = "ollama"              # Локальный Ollama
    DEEPSEEK = "deepseek"          # DeepSeek (бесплатно)


class LLMClient:
    """Universal client for free LLM providers."""
    
    FREE_MODELS = {
        AIProvider.OPENROUTER: [
            "meta-llama/llama-3.3-70b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
        ],
        AIProvider.GROQ: [
            "llama-3.3-70b-versatile",  # Llama 3.3 70B
            "llama-3.1-8b-instant",     # Llama 3.1 8B (быстрая)
            "mixtral-8x7b-32768",       # Mixtral
            "gemma2-9b-it",             # Gemma 2
        ],
        AIProvider.OLLAMA: [
            "llama3.2",      
            "mistral",       
            "qwen2.5",       
        ],
        AIProvider.DEEPSEEK: [
            "deepseek-chat",  
        ],
    }
    
    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        # Пробуем загрузить из конфига
        try:
            from app.config import get_settings
            settings = get_settings()
            
            # Определяем провайдера
            if provider is None:
                provider_str = getattr(settings, 'AI_PROVIDER', 'openrouter')
                provider = AIProvider(provider_str)
            
            # API ключ
            if api_key is None:
                if provider == AIProvider.OPENROUTER:
                    api_key = settings.OPENROUTER_API_KEY
                elif provider == AIProvider.GROQ:
                    api_key = settings.GROQ_API_KEY
                elif provider == AIProvider.DEEPSEEK:
                    api_key = settings.DEEPSEEK_API_KEY
            
            # Модель
            if model is None:
                if provider == AIProvider.OPENROUTER:
                    model = getattr(settings, 'OPENROUTER_MODEL', None)
        except Exception:
            pass
        
        self.provider = provider or AIProvider.OPENROUTER
        self.api_key = api_key or os.getenv(f"{self.provider.name}_API_KEY")
        self.model = model or self._get_default_model()
        self.base_url = base_url or self._get_base_url()
        self._client: Optional[httpx.AsyncClient] = None
    
    def _get_default_model(self) -> str:
        """Get default free model for provider."""
        models = self.FREE_MODELS.get(self.provider, [])
        return models[0] if models else "llama-3.2-3b-preview"
    
    def _get_base_url(self) -> str:
        """Get base URL for provider."""
        urls = {
            AIProvider.OPENROUTER: "https://openrouter.ai/api/v1",
            AIProvider.GROQ: "https://api.groq.com/openai/v1",
            AIProvider.OLLAMA: "http://localhost:11434/v1",
            AIProvider.DEEPSEEK: "https://api.deepseek.com/v1",
        }
        return urls.get(self.provider, "http://localhost:11434/v1")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
            }
            
            if self.provider == AIProvider.OPENROUTER:
                headers["Authorization"] = f"Bearer {self.api_key}"
                headers["HTTP-Referer"] = "http://localhost:8000"
                headers["X-Title"] = "BoneBET"
            elif self.provider in (AIProvider.GROQ, AIProvider.DEEPSEEK):
                headers["Authorization"] = f"Bearer {self.api_key}"
            # Ollama не требует API ключа
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=120.0,
            )
        
        return self._client
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        Send completion request to LLM.
        
        Returns:
            {"text": "...", "model": "...", "usage": {...}}
        """
        client = await self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        logger.info(f"Calling LLM: {self.provider}/{self.model}")
        
        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            return {
                "text": data["choices"][0]["message"]["content"],
                "model": data.get("model", self.model),
                "usage": data.get("usage", {}),
                "provider": self.provider.value,
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class MockLLMClient(LLMClient):
    """Mock client for testing without API keys."""
    
    def __init__(self):
        # Пропускаем инициализацию родителя
        self.provider = AIProvider.OPENROUTER
        self.model = "mock"
        self._client = None
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """Return mock response."""
        logger.info("Using MockLLMClient")
        
        return {
            "text": """## Анализ матча (MOCK)

**Прогноз:** На основе предоставленной статистики, команда с более высоким Firepower и лучшей формой имеет преимущество.

**Ключевые факторы:**
- Разница в рейтинге и форме команд
- История личных встреч

**Рекомендация:** Ставка на победу фаворита с форой (-1.5).""",
            "model": "mock",
            "usage": {"prompt_tokens": len(prompt), "completion_tokens": 100},
            "provider": "mock",
        }
    
    async def close(self):
        pass
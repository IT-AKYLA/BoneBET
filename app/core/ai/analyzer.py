"""AI Analyzer - combines metrics with LLM analysis."""

from typing import Dict, Any, Optional
from app.core.ai.client import LLMClient, AIProvider, MockLLMClient
from app.core.ai.prompts import PromptTemplates
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIAnalyzer:
    """Main AI analyzer using free LLM providers."""
    
    def __init__(self, use_mock: bool = False):
        self.settings = get_settings()
        
        if use_mock:
            self.client = MockLLMClient()
        else:
            provider_str = self.settings.AI_PROVIDER
            provider = AIProvider(provider_str) if provider_str else AIProvider.OLLAMA
            
            api_key = None
            if provider == AIProvider.OPENROUTER:
                api_key = self.settings.OPENROUTER_API_KEY
            elif provider == AIProvider.GROQ:
                api_key = self.settings.GROQ_API_KEY
            elif provider == AIProvider.DEEPSEEK:
                api_key = self.settings.DEEPSEEK_API_KEY
            
            self.client = LLMClient(
                provider=provider,
                api_key=api_key,
            )
        
        self.prompts = PromptTemplates()
    
    async def analyze_match(
        self,
        team1_data: Dict[str, Any],
        team2_data: Dict[str, Any],
        stats_prediction: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run full AI analysis for a match."""
        
        prompt = self.prompts.match_analysis(
            team1_data=team1_data,
            team2_data=team2_data,
            stats_prediction=stats_prediction,
        )
        
        system_prompt = PromptTemplates.system_prompt()
        
        logger.info(f"Running AI analysis for {team1_data.get('name')} vs {team2_data.get('name')}")
        
        try:
            response = await self.client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            
            return {
                "prompt": prompt,
                "analysis": response["text"],
                "model": response["model"],
                "provider": response["provider"],
                "usage": response["usage"],
            }
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "prompt": prompt,
                "analysis": None,
                "error": str(e),
            }
    
    async def close(self):
        """Close client."""
        await self.client.close()


_analyzer: Optional[AIAnalyzer] = None


def get_ai_analyzer(use_mock: bool = False) -> AIAnalyzer:
    """Get or create AI analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = AIAnalyzer(use_mock=use_mock)
    return _analyzer
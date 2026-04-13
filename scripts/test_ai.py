"""Test AI analysis with real OpenRouter."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.ai import get_ai_analyzer


async def test_ai():
    print("\n" + "="*60)
    print("🤖 Testing OpenRouter AI Analysis")
    print("="*60)
    
    # Mock data
    team1 = {
        "name": "Vitality",
        "ranking": 31,
        "firepower": 6.65,
        "carry_index": 1.11,
        "recent_win_rate": {"score": 85.0},
        "h2h_win_rate": {"wins": 2, "losses": 0, "total_matches": 2},
        "players": [
            {"nickname": "ZywOo", "true_rating": {"true_rating": 7.36}, "form_trend": {"trend_direction": "stable"}},
            {"nickname": "ropz", "true_rating": {"true_rating": 6.79}, "form_trend": {"trend_direction": "stable"}},
            {"nickname": "flameZ", "true_rating": {"true_rating": 7.08}, "form_trend": {"trend_direction": "stable"}},
            {"nickname": "mezii", "true_rating": {"true_rating": 6.06}, "form_trend": {"trend_direction": "stable"}},
            {"nickname": "apEX", "true_rating": {"true_rating": 5.95}, "form_trend": {"trend_direction": "stable"}},
        ]
    }
    
    team2 = {
        "name": "Natus Vincere",
        "ranking": 35,
        "firepower": 6.24,
        "carry_index": 1.09,
        "recent_win_rate": {"score": 65.0},
        "h2h_win_rate": {"wins": 0, "losses": 2, "total_matches": 2},
        "players": [
            {"nickname": "b1t", "true_rating": {"true_rating": 6.06}, "form_trend": {"trend_direction": "stable"}},
            {"nickname": "iM", "true_rating": {"true_rating": 6.49}, "form_trend": {"trend_direction": "stable"}},
            {"nickname": "w0nderful", "true_rating": {"true_rating": 6.32}, "form_trend": {"trend_direction": "stable"}},
            {"nickname": "makazze", "true_rating": {"true_rating": 6.78}, "form_trend": {"trend_direction": "stable"}},
            {"nickname": "Aleksib", "true_rating": {"true_rating": 5.53}, "form_trend": {"trend_direction": "stable"}},
        ]
    }
    
    stats = {
        "team1_win_prob": 62.5,
        "team2_win_prob": 37.5,
        "confidence": "medium",
    }
    
    # Real OpenRouter
    print("\n📡 Calling OpenRouter (Gemini Flash - FREE)...")
    analyzer = get_ai_analyzer(use_mock=False)
    
    result = await analyzer.analyze_match(team1, team2, stats)
    
    print("\n" + "="*60)
    print("📊 AI ANALYSIS")
    print("="*60)
    print(f"\nModel: {result.get('model', 'N/A')}")
    print(f"Provider: {result.get('provider', 'N/A')}")
    
    if result.get('usage'):
        usage = result['usage']
        print(f"Tokens: {usage.get('prompt_tokens', 0)} prompt + {usage.get('completion_tokens', 0)} completion")
    
    print("\n" + "-"*60)
    print("ANALYSIS:")
    print("-"*60)
    print(result['analysis'])
    
    await analyzer.close()


if __name__ == "__main__":
    asyncio.run(test_ai())
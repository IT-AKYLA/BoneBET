"""Test full AI pipeline: players → teams → prediction."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.player_analysis_service import PlayerAnalysisService
from app.services.bet_service import BetService
from app.core.ai.prompts import PromptTemplates
from app.core.ai import get_ai_analyzer


async def test_pipeline(team1: str, team2: str):
    print("\n" + "█"*80)
    print(f"AI PIPELINE: {team1} vs {team2}")
    print("█"*80)
    
    service = PlayerAnalysisService()
    bet_service = BetService()
    
    # ШАГ 1: Анализ игроков
    print("\n📍 STEP 1: Analyzing players...")
    print("-"*40)
    
    team1_players = await service.analyze_team_players(team1, force_refresh=True)
    team2_players = await service.analyze_team_players(team2, force_refresh=True)
    
    print(f"\n{team1} players:")
    for p in team1_players:
        print(f"  {p['nickname']}: {p['role']}, {p['dynamic']}, TR {p['true_rating']}")
    
    print(f"\n{team2} players:")
    for p in team2_players:
        print(f"  {p['nickname']}: {p['role']}, {p['dynamic']}, TR {p['true_rating']}")
    
    # ШАГ 2: Командное сравнение
    print("\n📍 STEP 2: Team comparison...")
    print("-"*40)
    
    # Get True Win Rates
    top_teams = await bet_service._fetch_top_teams()
    top_50_teams = {t['id']: t['world_ranking'] for t in top_teams}
    
    wr1 = await bet_service._calculate_team_win_rate(team1, top_50_teams)
    wr2 = await bet_service._calculate_team_win_rate(team2, top_50_teams)
    
    prompt = PromptTemplates.team_comparison(
        team1_name=team1,
        team1_players=team1_players,
        team2_name=team2,
        team2_players=team2_players,
        team1_win_rate=wr1,
        team2_win_rate=wr2,
    )
    
    ai = get_ai_analyzer(use_mock=False)
    result = await ai.client.complete(
        prompt=prompt,
        system_prompt="Ты — CS2 аналитик. Отвечай строго по формату.",
        temperature=0.3,
        max_tokens=500,
    )
    await ai.close()
    
    print("\n" + "="*40)
    print("FINAL PREDICTION")
    print("="*40)
    print(result['text'])


if __name__ == "__main__":
    asyncio.run(test_pipeline("Spirit", "Liquid"))
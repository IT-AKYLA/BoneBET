"""Check what's in the database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal, init_db
from app.models.player import Player
from app.models.team import Team
from sqlalchemy import select


async def check_db():
    """Check database contents."""
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Teams
        result = await session.execute(select(Team))
        teams = result.scalars().all()
        
        print(f"\n📊 TEAMS ({len(teams)}):")
        print("-" * 60)
        for team in teams:
            print(f"  ID: {team.id}")
            print(f"  Name: {team.name}")
            print(f"  Ranking: #{team.world_ranking}")
            print(f"  Roster: {team.current_roster}")
            print("-" * 40)
        
        # Players
        result = await session.execute(select(Player))
        players = result.scalars().all()
        
        print(f"\n🎮 PLAYERS ({len(players)}):")
        print("-" * 60)
        for player in players[:10]:  # First 10
            print(f"  ID: {player.id}")
            print(f"  Nickname: {player.nickname}")
            print(f"  Team ID: {player.current_team_id}")
            print(f"  Team Name: {player.current_team_name}")
            print(f"  Official Rating: {player.official_avg_rating}")
            print(f"  Official K/D: {player.official_avg_kd}")
            print(f"  Official ADR: {player.official_avg_adr}")
            print("-" * 40)
        
        if len(players) > 10:
            print(f"  ... and {len(players) - 10} more players")


if __name__ == "__main__":
    asyncio.run(check_db())
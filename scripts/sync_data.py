"""Test script for data synchronization."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal, init_db
from app.services.sync_service import SyncService


async def main():
    """Run sync test."""
    print("\n" + "="*60)
    print("🔄 BoneBET - Data Sync Test")
    print("="*60)
    
    await init_db()
    
    async with AsyncSessionLocal() as session:
        sync_service = SyncService(session)
        
        try:
            # Test: Sync specific player
            print("\n📡 Testing player sync...")
            players = await sync_service.sync_specific_players(["donk"])
            for p in players:
                print(f"   ✅ {p.nickname}: ELO={p.faceit_elo}, Rating={p.official_avg_rating}")
            
            # Test: Sync top teams (limit to 5 for test)
            print("\n📡 Syncing top 5 teams...")
            stats = await sync_service.sync_all(top_teams_limit=5)
            print(f"   ✅ Teams: {stats['teams_synced']}")
            print(f"   ✅ Players: {stats['players_synced']}")
            if stats['errors']:
                print(f"   ⚠️ Errors: {len(stats['errors'])}")
            
        except Exception as e:
            print(f"\n❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await sync_service.close()
    
    print("\n" + "="*60)
    print("✅ Sync test completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
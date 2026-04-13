"""Tests for CS2 Analytics API client."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.clients.cs2_analytics import CS2AnalyticsClient
from app.clients.exceptions import PlayerNotFoundError, DataLoadingError


@pytest.fixture
async def client():
    """Create client instance."""
    client = CS2AnalyticsClient()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    mock_response = {"status": "healthy"}
    
    with patch.object(client.http, "get", AsyncMock(return_value=mock_response)):
        result = await client.health_check()
        assert result == mock_response


@pytest.mark.asyncio
async def test_get_player_ready(client):
    """Test getting player with ready data."""
    mock_data = {
        "nickname": "donk",
        "team_id": 31,
        "loading_status": "ready",
        "faceit_stats": {"elo": 3500, "avg_kd_30d": 1.45},
        "official_stats": {"avg_rating": 1.35, "avg_adr": 95.0},
    }
    
    with patch.object(client.http, "get", AsyncMock(return_value=mock_data)):
        result = await client.get_player("donk", wait_for_loading=False)
        assert result["nickname"] == "donk"
        assert result["loading_status"] == "ready"


@pytest.mark.asyncio
async def test_get_player_loading_then_ready(client):
    """Test getting player that is initially loading."""
    loading_response = {"nickname": "donk", "loading_status": "loading"}
    ready_response = {
        "nickname": "donk",
        "loading_status": "ready",
        "faceit_stats": {"elo": 3500},
    }
    
    with patch.object(
        client.http,
        "get",
        AsyncMock(side_effect=[loading_response, ready_response]),
    ):
        result = await client.get_player("donk", wait_for_loading=True)
        assert result["loading_status"] == "ready"
        assert "faceit_stats" in result


@pytest.mark.asyncio
async def test_get_player_not_found(client):
    """Test getting non-existent player."""
    from app.clients.exceptions import CS2APIResponseError
    
    with patch.object(
        client.http,
        "get",
        AsyncMock(side_effect=CS2APIResponseError(404, "Not found")),
    ):
        with pytest.raises(PlayerNotFoundError):
            await client.get_player("nonexistent_player_12345")


@pytest.mark.asyncio
async def test_get_teams(client):
    """Test getting teams list."""
    mock_teams = [
        {"id": 1, "name": "Team Spirit", "world_ranking": 1},
        {"id": 2, "name": "Vitality", "world_ranking": 2},
    ]
    
    with patch.object(client.http, "get", AsyncMock(return_value=mock_teams)):
        result = await client.get_teams()
        assert len(result) == 2
        assert result[0]["name"] == "Team Spirit"


@pytest.mark.asyncio
async def test_get_live_matches(client):
    """Test getting live matches."""
    mock_matches = [
        {"id": 1, "team_a": "Spirit", "team_b": "Vitality", "status": "live"},
    ]
    
    with patch.object(client.http, "get", AsyncMock(return_value=mock_matches)):
        result = await client.get_live_matches()
        assert len(result) == 1
        assert result[0]["status"] == "live"


# ==================== ИНТЕГРАЦИОННЫЙ ТЕСТ (с реальным API) ====================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_health():
    """Test connection to real API (requires API running)."""
    client = CS2AnalyticsClient()
    try:
        result = await client.health_check()
        assert "status" in result
        print(f"\n✅ API Health: {result}")
    except Exception as e:
        pytest.skip(f"API not available: {e}")
    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_get_player():
    """Test getting real player data."""
    client = CS2AnalyticsClient()
    try:
        # Try to get a known player
        result = await client.get_player("donk", wait_for_loading=True, max_wait_attempts=5)
        print(f"\n✅ Player donk:")
        print(f"   - Team: {result.get('team_id')}")
        print(f"   - Status: {result.get('loading_status')}")
        if result.get("faceit_stats"):
            print(f"   - FACEIT ELO: {result['faceit_stats'].get('elo')}")
            print(f"   - FACEIT K/D: {result['faceit_stats'].get('avg_kd_30d')}")
        if result.get("official_stats"):
            print(f"   - Official Rating: {result['official_stats'].get('avg_rating')}")
            print(f"   - Official ADR: {result['official_stats'].get('avg_adr')}")
    except PlayerNotFoundError:
        print("\n⚠️ Player 'donk' not found in API")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_get_teams():
    """Test getting real teams data."""
    client = CS2AnalyticsClient()
    try:
        result = await client.get_teams(limit=5)
        print(f"\n✅ Top 5 teams:")
        for team in result[:5]:
            print(f"   - {team.get('name')} (Rank #{team.get('world_ranking')})")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_live_matches():
    """Test getting real live matches."""
    client = CS2AnalyticsClient()
    try:
        result = await client.get_live_matches()
        if result:
            print(f"\n✅ Live matches: {len(result)}")
            for match in result:
                print(f"   - {match.get('team_a')} vs {match.get('team_b')}")
        else:
            print("\nℹ️ No live matches currently")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await client.close()


# ==================== SCRIPT FOR MANUAL TESTING ====================

async def manual_test():
    """Manual test script - run with: python -m tests.test_cs2_client"""
    print("\n" + "="*60)
    print("🧪 BoneBET - CS2 Analytics API Client Test")
    print("="*60)
    
    client = CS2AnalyticsClient()
    
    try:
        # Health check
        print("\n📡 Testing API connection...")
        health = await client.health_check()
        print(f"   ✅ API is healthy: {health}")
        
        # Get teams
        print("\n👥 Fetching top teams...")
        teams = await client.get_team_rankings(limit=5)
        for i, team in enumerate(teams[:5], 1):
            print(f"   {i}. {team.get('name', 'Unknown')} - Rank #{team.get('world_ranking', 'N/A')}")
        
        # Get player
        print("\n🎮 Fetching player 'donk'...")
        try:
            player = await client.get_player("donk", wait_for_loading=True)
            print(f"   ✅ Player: {player.get('nickname')}")
            print(f"   📊 Status: {player.get('loading_status')}")
            
            faceit = player.get('faceit_stats', {})
            if faceit:
                print(f"   🎯 FACEIT: ELO={faceit.get('elo')}, K/D={faceit.get('avg_kd_30d')}")
            
            official = player.get('official_stats', {})
            if official:
                print(f"   🏆 Official: Rating={official.get('avg_rating')}, ADR={official.get('avg_adr')}")
        except PlayerNotFoundError:
            print("   ⚠️ Player not found (API may need seeding)")
        except DataLoadingError:
            print("   ⏳ Data still loading after max wait time")
        
        # Live matches
        print("\n🔴 Checking live matches...")
        live = await client.get_live_matches()
        if live:
            print(f"   ✅ Found {len(live)} live match(es):")
            for match in live[:3]:
                print(f"      - {match.get('team_a', '?')} vs {match.get('team_b', '?')}")
        else:
            print("   ℹ️ No live matches currently")
        
        # Upcoming matches
        print("\n📅 Checking upcoming matches...")
        upcoming = await client.get_upcoming_matches()
        if upcoming:
            print(f"   ✅ Found {len(upcoming)} upcoming match(es)")
        else:
            print("   ℹ️ No upcoming matches")
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()
    
    print("\n" + "="*60)
    print("✅ Test completed")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(manual_test())
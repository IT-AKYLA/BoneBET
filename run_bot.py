import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.bot.telegram_bot import run_bot

if __name__ == "__main__":
    asyncio.run(run_bot())
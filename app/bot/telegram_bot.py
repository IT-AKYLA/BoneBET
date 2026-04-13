"""Telegram bot for BoneBET."""

import asyncio
from typing import Dict, Any, List

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

from app.services.bet_service import BetService
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BoneBETBot:
    """Telegram bot for CS2 match predictions."""
    
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.bet_service = BetService()
        self.app = Application.builder().token(self.token).build()
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("bet", self.bet_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = "🎲 *BoneBET*\n\n*/bet* — прогнозы на матчи\n*/bet 8* — 8 матчей"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def bet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        limit = 5
        
        for arg in args:
            if arg.isdigit():
                limit = min(int(arg), 10)
        
        msg = await update.message.reply_text("🔍 Анализ...")
        
        try:
            matches = await self.bet_service.analyze_matches(
                limit=limit, tier_filter="all", use_ai=False, force_refresh=False
            )
            
            if not matches:
                await msg.edit_text("❌ Матчи не найдены")
                return
            
            await msg.delete()
            
            # Отправляем всё одним сообщением
            text = self._format_matches(matches)
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Bet error: {e}")
            await msg.edit_text("❌ Ошибка")
    
    def _format_matches(self, matches: List[Dict]) -> str:
        """Краткий формат всех матчей."""
        lines = ["🎲 *BoneBET — Прогнозы*\n"]
        
        for m in matches:
            t1 = m['team1']['name']
            t2 = m['team2']['name']
            p = m['prediction']
            winner = p['winner']
            prob = p['team1_win_prob'] if winner == t1 else p['team2_win_prob']
            
            # Только дата, команды и винрейт
            time_str = m.get('scheduled_at', '—')
            if ':' in str(time_str):
                time_str = time_str[:5]  # Только часы:минуты
            
            lines.append(
                f"🕐 {time_str}  *{t1}* vs *{t2}*\n"
                f"   → {winner} ({prob:.0f}%)\n"
            )
        
        return '\n'.join(lines)
    
    async def start(self):
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("BoneBET Bot started")
    
    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()


_bot: BoneBETBot = None

def get_bot() -> BoneBETBot:
    global _bot
    if _bot is None:
        _bot = BoneBETBot()
    return _bot

async def run_bot():
    bot = get_bot()
    try:
        await bot.start()
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await bot.stop()
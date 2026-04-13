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
        text = (
            "🎲 *BoneBET*\n\n"
            "Прогнозы на CS2 матчи с AI анализом\n\n"
            "*/bet* — все матчи\n"
            "*/bet 5* — только топ-5\n"
            "*/bet tier1* — элитный уровень"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def bet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        limit = 20  # все матчи
        tier_filter = "all"
        
        for arg in args:
            if arg.isdigit():
                limit = int(arg)
            elif arg.lower() == "tier1":
                tier_filter = "tier1"
        
        msg = await update.message.reply_text("🔍 BoneBET анализирует матчи...")
        
        try:
            matches = await self.bet_service.analyze_matches(
                limit=limit, tier_filter=tier_filter, use_ai=True, force_refresh=False
            )
            
            if not matches:
                await msg.edit_text("❌ Матчи не найдены")
                return
            
            await msg.delete()
            
            # Группируем по турнирам
            by_tournament = {}
            for m in matches:
                tour = m.get('tournament', 'Другие')
                if tour not in by_tournament:
                    by_tournament[tour] = []
                by_tournament[tour].append(m)
            
            # Отправляем сгруппированные
            for tour, tour_matches in by_tournament.items():
                text = self._format_tournament_matches(tour, tour_matches)
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Bet error: {e}")
            await msg.edit_text("❌ Ошибка анализа. Попробуй позже")
    
    def _format_tournament_matches(self, tournament: str, matches: List[Dict]) -> str:
        """Форматирование матчей турнира."""
        lines = [f"🏆 *{tournament}*\n"]
        
        for m in matches:
            t1 = m['team1']['name']
            t2 = m['team2']['name']
            p = m['prediction']
            winner = p['winner']
            prob = p['team1_win_prob'] if winner == t1 else p['team2_win_prob']
            
            time_str = m.get('scheduled_at', 'LIVE') if m.get('status') != 'live' else '🔴 LIVE'
            if ':' in str(time_str):
                time_str = time_str[:5]
            
            conf = p['confidence']
            conf_icon = "🟢" if conf == "high" else "🟡" if conf == "medium" else ""
            
            lines.append(
                f"{time_str}  *{t1}* vs *{t2}*\n"
                f"└ {winner} · {prob:.0f}% {conf_icon}\n"
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
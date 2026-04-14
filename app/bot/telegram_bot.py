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
        self.app.add_handler(CommandHandler("live", self.live_command))
        self.app.add_handler(CommandHandler("refresh", self.refresh_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🎲 *BoneBET*\n\n"
            "Прогнозы на CS2 матчи с AI анализом\n\n"
            "*/bet* — все матчи\n"
            "*/live* — только LIVE\n"
            "*/refresh* — сбросить ВЕСЬ кэш\n"
            "*/bet 5* — топ-5\n"
            "*/bet tier1* — элитный уровень"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def refresh_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбросить ВЕСЬ кэш и получить свежий анализ."""
        msg = await update.message.reply_text("🔄 Сбрасываю весь кэш...")

        try:
            deleted = await self.bet_service.invalidate_all_cache()
            await msg.edit_text(
                f"✅ Кэш полностью сброшен ({deleted} ключей)\n"
                f"Используй /bet для свежего анализа"
            )
        except Exception as e:
            logger.error(f"Refresh error: {e}")
            await msg.edit_text("❌ Ошибка сброса кэша")
    
    async def live_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.message.reply_text("🔴 BoneBET ищет LIVE матчи...")

        try:
            matches = await self.bet_service.analyze_matches(
                limit=20, tier_filter="all", use_ai=True, force_refresh=False
            )

            live_matches = [m for m in matches if m.get('status') == 'live']

            if not live_matches:
                await msg.edit_text("🔴 Нет LIVE матчей")
                return

            await msg.delete()

            text = self._format_live_matches(live_matches)
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Live error: {e}")
            try:
                await msg.edit_text("❌ Ошибка")
            except:
                pass
    
    async def bet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        limit = 20
        tier_filter = "all"
        live_only = False
        
        for arg in args:
            if arg.isdigit():
                limit = int(arg)
            elif arg.lower() == "tier1":
                tier_filter = "tier1"
            elif arg.lower() == "live":
                live_only = True
        
        msg = await update.message.reply_text("🔍 BoneBET анализирует матчи...")
        
        try:
            matches = await self.bet_service.analyze_matches(
                limit=limit, tier_filter=tier_filter, use_ai=True, force_refresh=False
            )
            
            if live_only:
                matches = [m for m in matches if m.get('status') == 'live']
            
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
            
            for tour, tour_matches in by_tournament.items():
                text = self._format_tournament_matches(tour, tour_matches)
                await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Bet error: {e}")
            await msg.edit_text("❌ Ошибка анализа. Попробуй позже")
    
    def _format_live_matches(self, matches: List[Dict]) -> str:
        """Форматирование LIVE матчей."""
        lines = ["🔴 *BoneBET — LIVE Матчи*\n"]

        for m in matches:
            t1 = m['team1']['name']
            t2 = m['team2']['name']
            p = m['prediction']
            winner = p['winner']
            prob = p['team1_win_prob'] if winner == t1 else p['team2_win_prob']
            tour = m.get('tournament', '—')
            conf = p['confidence']
            conf_icon = "🟢" if conf == "high" else "🟡" if conf == "medium" else ""

            lines.append(
                f"🏆 {tour}\n"
                f"*{t1}* vs *{t2}*\n"
                f"└ {winner} · {prob:.0f}% {conf_icon}\n"
            )

        return '\n'.join(lines)
    
    def _format_tournament_matches(self, tournament: str, matches: List[Dict]) -> str:
        """Форматирование матчей турнира."""
        lines = [f"🏆 *{tournament}*\n"]

        for m in matches:
            t1 = m['team1']['name']
            t2 = m['team2']['name']
            p = m['prediction']
            winner = p['winner']
            prob = p['team1_win_prob'] if winner == t1 else p['team2_win_prob']

            status = m.get('status', '')
            if status == 'live':
                time_str = '🔴 LIVE'
            else:
                time_str = m.get('scheduled_at', '—')
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
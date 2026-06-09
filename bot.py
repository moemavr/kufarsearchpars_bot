"""
KufarScan Telegram Bot
Запуск: python bot.py
Переменные окружения:
  BOT_TOKEN   — токен от @BotFather
  WEBAPP_URL  — URL задеплоенного бэкенда (например https://kufarscan.up.railway.app)
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-app.up.railway.app")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton(
            "📡 Открыть KufarScan",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]]
    await update.message.reply_text(
        "👋 *KufarScan* — парсер цен kufar.by\n\n"
        "Нажми кнопку, чтобы открыть приложение прямо здесь в Telegram.\n\n"
        "Или отправь поисковый запрос — пришлю топ-5 объявлений текстом.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        return

    await update.message.reply_text(f"🔍 Ищу *{query}* на Куфаре...", parse_mode="Markdown")

    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{WEBAPP_URL}/search",
                params={"q": query, "size": 5},
                timeout=15.0,
            )
            data = resp.json()
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка сервера: {e}")
        return

    if not data.get("ok") or not data.get("listings"):
        await update.message.reply_text("😔 Ничего не найдено. Попробуй другой запрос.")
        return

    stats = data.get("stats", {})
    listings = data["listings"]

    # Шапка со статистикой
    header = (
        f"📊 *{query}* — найдено {data.get('total_found', len(listings))} объявлений\n"
        f"💰 Средняя цена: *{stats.get('avg', '—')} BYN*  |  "
        f"Медиана: *{stats.get('median', '—')} BYN*\n"
        f"📉 Мин: {stats.get('min', '—')}  |  📈 Макс: {stats.get('max', '—')} BYN\n\n"
        f"*Топ-5 объявлений:*"
    )
    await update.message.reply_text(header, parse_mode="Markdown")

    # Карточки объявлений
    for i, l in enumerate(listings[:5], 1):
        price_str = f"{l['price']:.0f} BYN" if l['price'] > 0 else "Договорная"
        diff = l.get("price_diff_pct")
        diff_str = ""
        if diff is not None:
            arrow = "🟢" if diff < 0 else "🔴"
            diff_str = f"{arrow} {'+' if diff > 0 else ''}{diff}% от средней\n"
        deal_str = "🔥 *ВЫГОДНО!*\n" if l.get("is_deal") else ""

        text = (
            f"{i}. *{l['title'][:60]}{'…' if len(l['title'])>60 else ''}*\n"
            f"💵 *{price_str}*\n"
            f"{deal_str}"
            f"{diff_str}"
            f"📍 {l['city']}  |  📦 {l['condition']}\n"
        )
        keyboard = [[InlineKeyboardButton("🔗 Открыть объявление", url=l["link"])]]

        if l.get("thumbnail"):
            try:
                await update.message.reply_photo(
                    photo=l["thumbnail"],
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                continue
            except Exception:
                pass

        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )

    # Кнопка открыть Mini App
    keyboard = [[InlineKeyboardButton(
        "📡 Все результаты в приложении",
        web_app=WebAppInfo(url=f"{WEBAPP_URL}?q={query}")
    )]]
    await update.message.reply_text(
        "👆 Открой приложение для полного анализа с фильтрами и AI-аналитикой",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *KufarScan* — парсер цен Куфара\n\n"
        "📌 Команды:\n"
        "/start — главное меню\n"
        "/help — справка\n\n"
        "💬 Просто напиши что ищешь, например:\n"
        "`iPhone 15` или `велосипед` или `ноутбук`",
        parse_mode="Markdown",
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 KufarScan Bot запущен")
    app.run_polling()

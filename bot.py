"""
AI Profit Promts 2026 — Seller Bot (Final Version)
Только Telegram Stars
"""

import os
import logging
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

DB_PATH = "data/bot.db"

bot.py

async def init_db():
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                referrer_id INTEGER,
                is_premium BOOLEAN DEFAULT 0,
                premium_until TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def has_premium(user_id):
    user = await get_user(user_id)
    if not user or not user.get("is_premium"):
        return False
    if user.get("premium_until"):
        return datetime.fromisoformat(user["premium_until"]) > datetime.now()
    return False

SAMPLE_PROMPTS = {
    "Бизнес и продажи": [
        "Создай продающий текст для [продукт] длиной 300 слов.",
        "Напиши 5 возражений клиента и ответы на них."
    ],
    "Контент и SMM": [
        "Напиши 7 идей постов для Telegram-канала.",
        "Создай вирусный hook для поста."
    ]
}

def main_menu_kb(has_prem):
    buttons = [
        [InlineKeyboardButton(text="🔍 Поиск промптов", callback_data="search_prompts")],
        [InlineKeyboardButton(text="💎 Мой доступ", callback_data="my_access")],
        [InlineKeyboardButton(text="👥 Реферальная программа", callback_data="referral")],
    ]
    if not has_prem:
        buttons.append([InlineKeyboardButton(text="🚀 Купить доступ (1500 Stars)", callback_data="buy_premium")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def buy_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Купить за 1500 Stars", callback_data="pay_stars")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await create_or_update_user(user_id, message.from_user.username or "", message.from_user.first_name or "Друг")
    has_prem = await has_premium(user_id)
    await message.answer(f"Привет, {message.from_user.first_name}!\n\nБот для продажи доступа к промптам AI Profit Promts 2026.", reply_markup=main_menu_kb(has_prem))

@router.callback_query(F.data == "search_prompts")
async def search_prompts(callback: CallbackQuery):
    has_prem = await has_premium(callback.from_user.id)
    if not has_prem:
        await callback.message.edit_text("Доступно только с премиумом.", reply_markup=buy_kb())
        return
    text = "📚 Выбери категорию:"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")] for cat in SAMPLE_PROMPTS] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery):
    cat = callback.data.replace("cat_", "")
    prompts = SAMPLE_PROMPTS.get(cat, [])
    text = f"📂 {cat}\n\n" + "\n\n".join([f"{i+1}. {p}" for i, p in enumerate(prompts)])
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Купить полный доступ", callback_data="buy_premium")], [InlineKeyboardButton(text="⬅️ Назад", callback_data="search_prompts")]])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    await callback.message.edit_text("🚀 Премиум-доступ\n\nЦена: 1500 Stars", reply_markup=buy_kb())

@router.callback_query(F.data == "pay_stars")
async def pay_stars(callback: CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="AI Profit Promts 2026 — 30 дней",
        description="Полный доступ",
        payload="premium_30_days",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="30 дней", amount=1500)],
    )

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    await give_premium(message.from_user.id, 30)
    await message.answer("🎉 Премиум активирован на 30 дней!")

async def main():
    await init_db()
    dp.include_router(router)
    if WEBHOOK_URL:
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        from aiohttp import web
        app = web.Application()
        SimpleRequestHandler(dp, bot).register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
        web.run_app(app, host="0.0.0.0", port=8080)
    else:
        await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

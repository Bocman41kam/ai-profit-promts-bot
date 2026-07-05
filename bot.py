"""
AI Profit Promts 2026 — Seller Bot (Final Version)
Только Telegram Stars. Готов к деплою.
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
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
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

async def get_user(user_id: int) -> Dict[str, Any] | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def create_or_update_user(user_id: int, username: str, first_name: str, referrer_id: int | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, referrer_id, is_premium)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name, referrer_id))
        await db.commit()

async def give_premium(user_id: int, days: int = 30):
    until = (datetime.now() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
            (until, user_id)
        )
        await db.commit()

async def has_premium(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user or not user.get("is_premium"):
        return False
    if user.get("premium_until"):
        return datetime.fromisoformat(user["premium_until"]) > datetime.now()
    return False

# Пример промптов
SAMPLE_PROMPTS = {
    "Бизнес и продажи": [
        "Создай продающий текст для [продукт] длиной 300 слов с акцентом на выгоду клиента.",
        "Напиши 5 возражений клиента и мощные ответы на них для [ниша]."
    ],
    "Контент и SMM": [
        "Напиши 7 идей постов для Telegram-канала в нише [ниша] на следующую неделю.",
        "Создай вирусный hook для поста про [тема] (до 15 слов)."
    ],
    "Личный бренд": [
        "Напиши продающее описание услуги для Telegram-канала.",
        "Создай 5 мощных вопросов для прогрева аудитории."
    ]
}

def main_menu_kb(has_prem: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔍 Поиск промптов", callback_data="search_prompts")],
        [InlineKeyboardButton(text="💎 Мой доступ", callback_data="my_access")],
        [InlineKeyboardButton(text="👥 Реферальная программа", callback_data="referral")],
    ]
    if not has_prem:
        buttons.append([InlineKeyboardButton(text="🚀 Купить доступ (1500 Stars)", callback_data="buy_premium")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def buy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Купить за 1500 Stars", callback_data="pay_stars")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "Друг"

    referrer_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
        except:
            pass

    await create_or_update_user(user_id, username, first_name, referrer_id)
    has_prem = await has_premium(user_id)

    text = f"Привет, <b>{first_name}</b>!\n\nЯ — бот для продажи доступа к базе промптов AI Profit Promts 2026.\n\nВыбери действие:"
    await message.answer(text, reply_markup=main_menu_kb(has_prem))

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    has_prem = await has_premium(callback.from_user.id)
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb(has_prem))
    await callback.answer()

@router.callback_query(F.data == "search_prompts")
async def search_prompts(callback: CallbackQuery):
    has_prem = await has_premium(callback.from_user.id)
    if not has_prem:
        await callback.message.edit_text("Эта функция доступна только с премиум-доступом.", reply_markup=buy_kb())
        await callback.answer()
        return

    text = "📚 <b>Выбери категорию:</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")] for cat in SAMPLE_PROMPTS
    ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery):
    cat = callback.data.replace("cat_", "")
    prompts = SAMPLE_PROMPTS.get(cat, [])
    text = f"📂 <b>{cat}</b>\n\n" + "\n\n".join([f"{i+1}. {p}" for i, p in enumerate(prompts)])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Купить полный доступ", callback_data="buy_premium")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="search_prompts")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "my_access")
async def my_access(callback: CallbackQuery):
    has_prem = await has_premium(callback.from_user.id)
    text = "✅ У тебя активен Премиум-доступ." if has_prem else "❌ У тебя нет активного премиум-доступа."
    await callback.message.edit_text(text, reply_markup=main_menu_kb(has_prem))
    await callback.answer()

@router.callback_query(F.data == "referral")
async def referral(callback: CallbackQuery):
    user_id = callback.from_user.id
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start=ref_{user_id}"
    text = f"👥 <b>Реферальная программа</b>\n\nПриглашай друзей и получай 25% с их платежей.\n\nТвоя ссылка:\n<code>{ref_link}</code>"
    await callback.message.edit_text(text, reply_markup=main_menu_kb(await has_premium(user_id)))
    await callback.answer()

@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    text = "🚀 <b>Премиум-доступ</b>\n\n• Полный доступ ко всем промптам\n• Цена: 1500 Stars"
    await callback.message.edit_text(text, reply_markup=buy_kb())
    await callback.answer()

@router.callback_query(F.data == "pay_stars")
async def pay_stars(callback: CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="AI Profit Promts 2026 — 30 дней",
        description="Полный доступ ко всем промптам",
        payload="premium_30_days",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="30 дней", amount=1500)],
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    await give_premium(message.from_user.id, days=30)
    await message.answer("🎉 Премиум активирован на 30 дней! Напиши /start")

async def main():
    await init_db()
    dp.include_router(router)

    if WEBHOOK_URL:
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        from aiohttp import web
        app = web.Application()
        webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}", drop_pending_updates=True)
        web.run_app(app, host="0.0.0.0", port=8080)
    else:
        await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

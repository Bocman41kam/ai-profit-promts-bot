# AI Profit Promts 2026 — Seller Bot (Final)

Готовый Telegram-бот для продажи доступа к базе промптов через **Telegram Stars**.

## Что входит

- Полностью рабочий бот на aiogram 3.7
- Оплата через Telegram Stars (1500 Stars = 30 дней)
- Реферальная программа
- Простая база данных (SQLite)
- Готов к деплою

## Быстрый старт (локально)

```bash
cp .env.example .env
# Заполни BOT_TOKEN
docker compose -f docker-compose.dev.yml up --build

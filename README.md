# KufarScan — Telegram Mini App

Парсер цен kufar.by в виде Telegram Mini App.

## Структура

```
kufarscan-tg/
├── main.py          # FastAPI бэкенд (парсит Куфар + раздаёт Mini App)
├── bot.py           # Telegram бот
├── requirements.txt
├── Procfile         # для Railway
├── railway.json     # конфиг Railway
└── static/
    └── index.html   # Mini App (открывается внутри Telegram)
```

---

## Шаг 1 — Создать бота в Telegram

1. Открой [@BotFather](https://t.me/BotFather)
2. Отправь `/newbot` → задай имя → получи **BOT_TOKEN**
3. Отправь `/newapp` → выбери бота → задай Short Name (например `kufarscan`)
   - Web App URL пока поставь любой, потом обновим

---

## Шаг 2 — Задеплоить бэкенд на Railway

1. Зарегистрируйся на [railway.app](https://railway.app) (бесплатно, GitHub login)
2. **New Project → Deploy from GitHub repo**
   - Загрузи эту папку в GitHub репозиторий
3. Railway автоматически найдёт `Procfile` и задеплоит
4. Зайди в **Settings → Networking → Generate Domain**
   - Получишь URL вида `https://kufarscan-xxx.up.railway.app`

**Переменные окружения** (Settings → Variables):
```
BOT_TOKEN=твой_токен_от_BotFather
WEBAPP_URL=https://kufarscan-xxx.up.railway.app
PORT=8000
```

---

## Шаг 3 — Обновить URL в BotFather

1. Открой @BotFather → `/myapps`
2. Выбери своё приложение
3. Обнови Web App URL на `https://kufarscan-xxx.up.railway.app`

---

## Шаг 4 — Запустить бота

На Railway добавь второй сервис (или запусти локально):
```bash
pip install -r requirements.txt
BOT_TOKEN=xxx WEBAPP_URL=https://kufarscan-xxx.up.railway.app python bot.py
```

На Railway: добавь в Variables `BOT_TOKEN` и `WEBAPP_URL`, в Procfile можно добавить отдельный worker:
```
web: python main.py
worker: python bot.py
```

---

## Локальный запуск (для теста)

```bash
pip install -r requirements.txt

# Терминал 1 — бэкенд
uvicorn main:app --reload --port 8000

# Терминал 2 — бот
BOT_TOKEN=xxx WEBAPP_URL=http://localhost:8000 python bot.py
```

Открой бота в Telegram → /start → кнопка откроет Mini App.

> ⚠️ Для теста Mini App локально Telegram требует HTTPS.
> Используй [ngrok](https://ngrok.com): `ngrok http 8000`
> и подставь ngrok URL в WEBAPP_URL.

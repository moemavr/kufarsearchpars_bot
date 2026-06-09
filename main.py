"""
KufarScan — FastAPI бэкенд + Telegram Mini App
Запуск локально: uvicorn main:app --reload --port 8000
Деплой: Railway / Render (автоматически читает PORT из env)
"""

import os
import statistics
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="KufarScan API")

# Разрешаем все источники (Mini App грузится с tg-серверов)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Регионы ───────────────────────────────────────────────────
REGION_MAP = {
    "Минск":             {"city": "minsk"},
    "Минская обл.":      {"region": "minsk_region"},
    "Брест":             {"city": "brest"},
    "Брестская обл.":    {"region": "brest_region"},
    "Гродно":            {"city": "grodno"},
    "Гродненская обл.":  {"region": "grodno_region"},
    "Гомель":            {"city": "gomel"},
    "Гомельская обл.":   {"region": "gomel_region"},
    "Витебск":           {"city": "vitebsk"},
    "Витебская обл.":    {"region": "vitebsk_region"},
    "Могилёв":           {"city": "mogilev"},
    "Могилёвская обл.":  {"region": "mogilev_region"},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.kufar.by/",
}


def build_url(query, region=None, price_min=None, price_max=None,
              condition=None, cursor=None, size=30):
    params = {"query": query, "size": size, "sort": "lst.d", "currency": "BYR"}
    if region and region in REGION_MAP:
        loc = REGION_MAP[region]
        if "city" in loc:
            params["city"] = loc["city"]
        else:
            params["region"] = loc["region"]
    if price_min:
        params["prc.gte"] = int(price_min) * 100
    if price_max:
        params["prc.lte"] = int(price_max) * 100
    if condition == "new":
        params["cnd"] = "1"
    elif condition == "used":
        params["cnd"] = "2"
    if cursor:
        params["cursor"] = cursor
    return "https://api.kufar.by/search-api/v2/search/rendered-paginated?" + urlencode(params)


def parse_ad(item: dict) -> dict:
    ad = item.get("ad", item)

    # Цена
    price_raw = ad.get("price_byn") or ad.get("price", {})
    if isinstance(price_raw, dict):
        price = round(price_raw.get("amount", 0) / 100, 2)
    elif isinstance(price_raw, (int, float)):
        price = round(float(price_raw) / 100, 2)
    else:
        price = 0.0

    # Фото
    images = []
    for img in ad.get("images", []):
        if isinstance(img, dict):
            uid = img.get("id", "")
            if uid:
                images.append(f"https://rms.kufar.by/v1/gallery/{uid}/image.jpg")
        elif isinstance(img, str) and img.startswith("http"):
            images.append(img)

    # Город
    city = (
        ad.get("location", {}).get("city_name")
        or ad.get("location", {}).get("region_name")
        or ad.get("city") or "—"
    )

    # Состояние
    prms = {p.get("p", ""): p.get("v", "") for p in ad.get("ad_parameters", [])}
    cond_map = {"1": "Новое", "2": "Б/у"}
    condition = cond_map.get(str(prms.get("condition", "")), "—")

    ad_id = str(ad.get("ad_id") or ad.get("id") or "")
    slug = ad.get("account_parameters", {}).get("slug", "")
    link = f"https://www.kufar.by/item/{slug}-{ad_id}" if ad_id else "https://www.kufar.by"

    return {
        "id": ad_id,
        "title": ad.get("subject") or ad.get("title") or "Без названия",
        "price": price,
        "city": city,
        "condition": condition,
        "images": images,
        "thumbnail": images[0] if images else None,
        "link": link,
        "date": ad.get("list_time") or ad.get("refresh_time") or "",
        "description": (ad.get("body") or "")[:500],
        "views": ad.get("views_count") or 0,
    }


# ── Endpoints ──────────────────────────────────────────────────

@app.get("/ping")
async def ping():
    return {"ok": True}


@app.get("/search")
async def search(
    q: str = Query(...),
    region: Optional[str] = Query(None),
    price_min: Optional[int] = Query(None),
    price_max: Optional[int] = Query(None),
    condition: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=50),
):
    cursor = str((page - 1) * size) if page > 1 else None
    url = build_url(q, region, price_min, price_max, condition, cursor, size)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e), "listings": []}, status_code=502)

    raw = data.get("ads") or data.get("data", {}).get("ads") or []
    listings = [parse_ad(a) for a in raw if a]

    prices = [l["price"] for l in listings if l["price"] > 0]
    stats = {}
    if prices:
        avg = round(statistics.mean(prices), 2)
        stats = {
            "count": len(listings),
            "avg": avg,
            "median": round(statistics.median(prices), 2),
            "min": min(prices),
            "max": max(prices),
        }
        for l in listings:
            if l["price"] > 0:
                diff = round((l["price"] - avg) / avg * 100, 1)
                l["price_diff_pct"] = diff
                l["is_deal"] = diff < -15
            else:
                l["price_diff_pct"] = None
                l["is_deal"] = False

    pag = data.get("pagination") or {}
    return {
        "ok": True,
        "query": q,
        "page": page,
        "has_next": bool(pag.get("next_token") or pag.get("next")),
        "stats": stats,
        "listings": listings,
        "total_found": data.get("total") or len(listings),
    }


# Отдаём Mini App (index.html + статика) из папки /static
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

# routes.py

import os
import math
from zoneinfo import ZoneInfo
import aiohttp 
import logging
import aiosqlite
import hmac, hashlib
from urllib.parse import parse_qsl
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request

from places import safe_avatar_url, places_router
from screens import safe_screen_template
from utils import haversine_km, now_iso, parse_float, parse_int

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("meet_eat")

router = APIRouter()

import asyncio
import json


async def edit_message_reply_markup(chat_id: int = None, message_id: int = None, inline_message_id: str = None, reply_markup: dict = None):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup"
    payload = {}
    if chat_id is not None and message_id is not None:
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id
    elif inline_message_id is not None:
        payload["inline_message_id"] = inline_message_id
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    try:
        async with aiohttp.ClientSession() as sess:
            await sess.post(url, json=payload, timeout=5)
    except Exception:
        logging.exception("editMessageReplyMarkup failed")


async def edit_message_text(chat_id: int = None, message_id: int = None, inline_message_id: str = None, text: str = None):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {"parse_mode": "HTML"}
    if chat_id is not None and message_id is not None:
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id
    elif inline_message_id is not None:
        payload["inline_message_id"] = inline_message_id
    payload["text"] = text or ""
    try:
        async with aiohttp.ClientSession() as sess:
            await sess.post(url, json=payload, timeout=5)
    except Exception:
        logging.exception("editMessageText failed")



# helper — формирует телеграм inline keyboard (Yes/No)
# def telegram_survey_keyboard(invite_id):
#     return {
#         "inline_keyboard": [
#             [{"text":"Да","callback_data": f"survey:{invite_id}:yes"}],
#             [{"text":"Нет","callback_data": f"survey:{invite_id}:no"}]
#         ]
#     }

async def dispatch_surveys_once():
    """Ищет accepted invites с ответом >=1 час назад и survey_sent=0, создает notifications и отправляет telegram."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # выбираем все приглашения, принятые >= 1 час назад и для которых опрос ещё не отправлен
        cur = await db.execute("""
            SELECT i.id, i.from_user_id, i.to_user_id, i.place_name, i.responded_at,
                fu.tg_id AS from_tg, tu.tg_id AS to_tg, fu.name AS from_name, tu.name AS to_name
            FROM invites i
            JOIN users fu ON fu.id = i.from_user_id
            JOIN users tu ON tu.id = i.to_user_id
            WHERE i.status = 'accepted' AND IFNULL(i.survey_sent,0) = 0
                AND strftime('%s', replace(replace(i.responded_at,'T',' '),'Z','')) <= strftime('%s', 'now', '-10 seconds')
        """)
            #   AND datetime(i.responded_at) <= datetime('now', '-1 hour')
        rows = await cur.fetchall()
        if not rows:
            return

        for r in rows:
            invite_id = r["id"]

            # пытаемся пометить invite как отправленный (только если ещё не помечен)
            await db.execute("UPDATE invites SET survey_sent = 1 WHERE id = ? AND IFNULL(survey_sent,0) = 0", (invite_id,))
            await db.commit()
            cur_changes = await db.execute("SELECT changes() AS cnt")
            ch = await cur_changes.fetchone()
            if not ch or int(ch["cnt"]) == 0:
                continue

            # payload для уведомления в мини-аппе
            # отправим каждому участнику персонализованный payload
            # payload_from => инициатор (отправителю оповещения о том, что нужно ответить)
            payload_from = {
                "invite_id": invite_id,
                "place_name": r["place_name"],
                "partner_name": r["to_name"],
                "partner_tg": r["to_tg"],
                "role": "initiator"
            }
            payload_to = {
                "invite_id": invite_id,
                "place_name": r["place_name"],
                "partner_name": r["from_name"],
                "partner_tg": r["from_tg"],
                "role": "responder"
            }

            # вставляем в таблицу notifications (инициатор)
            await db.execute(
                "INSERT INTO notifications (user_id, type, payload, read, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                (r["from_user_id"], "survey", json.dumps(payload_from, ensure_ascii=False))
            )
            # для респондента
            await db.execute(
                "INSERT INTO notifications (user_id, type, payload, read, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                (r["to_user_id"], "survey", json.dumps(payload_to, ensure_ascii=False))
            )
            await db.commit()

            # попробуем отправить Telegram (best-effort)
            try:
                # initiator
                if r["from_tg"]:
                    text = f'Сходили ли вы с "{r["to_name"]}" в "{r["place_name"]}"?'
                    # await send_telegram_message(r["from_tg"], text, reply_markup=telegram_survey_keyboard(invite_id))
                    await send_telegram_message(r["from_tg"], text)
                # responder
                if r["to_tg"]:
                    text2 = f'Сходили ли вы с "{r["from_name"]}" в "{r["place_name"]}"?'
                    # await send_telegram_message(r["to_tg"], text2, reply_markup=telegram_survey_keyboard(invite_id))
                    await send_telegram_message(r["to_tg"], text2)
            except Exception:
                logging.exception("survey send telegram failed for invite %s", invite_id)

        await db.commit()

async def survey_dispatcher_loop(
    poll_interval=2
    # poll_interval=60
):
    await asyncio.sleep(5)
    while True:
        try:
            await dispatch_surveys_once()
        except asyncio.CancelledError:
            break
        except Exception:
            logging.exception("survey_dispatcher_loop failed")
        await asyncio.sleep(poll_interval)

# функция для прикрепления воркера к FastAPI app (вызвать из main)
def attach_survey_worker(app):
    @app.on_event("startup")
    async def start_survey_worker():
        app.state._survey_task = asyncio.create_task(survey_dispatcher_loop())

    @app.on_event("shutdown")
    async def stop_survey_worker():
        t = getattr(app.state, "_survey_task", None)
        if t:
            t.cancel()





ALLOWED_REACTIONS = [
    "Приятный собеседник",
    "Мыслит нестандартно",
    "Крутой нетворкер",
    "Любит свое дело",
    "Позитивный и энергичный"
]

# Проектный корень
BASE_FILE = os.path.abspath(__file__)
def find_project_root(start_file=__file__, max_levels=4):
    d = os.path.dirname(os.path.abspath(start_file))
    for _ in range(max_levels + 1):
        if os.path.exists(os.path.join(d, "static")) or os.path.exists(os.path.join(d, "templates")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(os.path.abspath(start_file))

PROJECT_ROOT = find_project_root(__file__, max_levels=5)

# Папки
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
SCREENS_TEMPLATES_DIR = os.path.join(TEMPLATES_DIR, "screens")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

DB_PATH = "db.sqlite3"
import hashlib, hmac
BOT_TOKEN = "8430676291:AAFr9yilHXr2Fel35y297btCjln6N6cR7l8"
secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()


SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "")

import html as _html

async def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None):
    if not BOT_TOKEN:
        logging.warning("send_telegram_message: BOT_TOKEN not set")
        return None
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # экранируем текст при parse_mode="HTML"
    safe_text = _html.escape(text)
    payload = {"chat_id": chat_id, "text": safe_text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, json=payload, timeout=10) as resp:
                j = await resp.json()
                if not j.get("ok"):
                    logging.warning("telegram send failed: %s", j)
                
                logging.info("telegram send response: %s", j)
                
                return j
    except Exception:
        logging.exception("send_telegram_message failed")
        return None


async def answer_callback_query(callback_query_id: str, text: str = None, show_alert: bool = False):
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id, "show_alert": bool(show_alert)}
    if text:
        payload["text"] = text
    try:
        async with aiohttp.ClientSession() as sess:
            await sess.post(url, json=payload, timeout=5)
    except Exception:
        logging.exception("answerCallbackQuery failed")


async def handle_invite_response(invite_id: int, responder_tg: int, action: str):
    if action not in ("accept", "decline"):
        raise ValueError("invalid action")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT i.id, i.status, i.from_user_id, i.to_user_id, i.place_name, i.time_iso, i.meal_type, fu.tg_id AS from_tg, tu.tg_id AS to_tg, fu.name AS from_name "
            "FROM invites i JOIN users fu ON fu.id = i.from_user_id JOIN users tu ON tu.id = i.to_user_id WHERE i.id = ?",
            (invite_id,)
        )
        inv = await cur.fetchone()
        if not inv:
            return {"ok": False, "error": "invite not found"}
       
        # --- безопасная проверка: responder имеет право отвечать на это приглашение ---
        try:
            stored_to_tg = inv["to_tg"]
        except Exception:
            stored_to_tg = None

        # Если в БД нет to_tg или он не совпадает с приславшим запрос — отказ
        try:
            if stored_to_tg is None or int(stored_to_tg) != int(responder_tg):
                return {"ok": False, "error": "not authorized"}
        except Exception:
            return {"ok": False, "error": "not authorized"}

        if inv["status"] != "pending":
            return {"ok": False, "error": f"already {inv['status']}"}

        new_status = "accepted" if action == "accept" else "declined"
        # now_s = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        # найдем responder_user_id
        cur = await db.execute("SELECT id, name, username, tg_id FROM users WHERE tg_id = ?", (responder_tg,))
        r = await cur.fetchone()
        responder_user_id = r["id"] if r else None
        responder_name = None
        responder_username = None
        if r:
            responder_name = r["name"] or None
            responder_username = (r["username"] or None)

        # await db.execute(
        #     "UPDATE invites SET status = ?, responder_user_id = ?, responded_at = ?, updated_at = ? WHERE id = ?",
        #     (new_status, responder_user_id, now_s, now_s, invite_id))
        # await db.commit()
        await db.execute(
            "UPDATE invites SET status = ?, responder_user_id = ?, responded_at = datetime('now'), updated_at = datetime('now') WHERE id = ?",
            (new_status, responder_user_id, invite_id))
        await db.commit()

        # --- подготовка читаемого времени (Asia/Almaty) ---
        time_readable = ""
        raw_time = inv["time_iso"]
        if raw_time:
            try:
                t = raw_time
                if t.endswith("Z"):
                    t = t[:-1]
                try:
                    dt = datetime.fromisoformat(t)
                except Exception:
                    dt = datetime.strptime(raw_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                try:
                    almaty = ZoneInfo("Asia/Almaty")
                    dt_local = dt.astimezone(almaty)
                except Exception:
                    dt_local = dt.astimezone(timezone.utc)
                ru_months = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"]
                hhmm = dt_local.strftime("%H:%M")
                day = dt_local.day
                month = ru_months[dt_local.month - 1]
                time_readable = f"{hhmm} {day} {month}"
            except Exception:
                logging.exception("time parse failed")

        # --- Формирование текста уведомления для инициатора ---
        place_text = f' в "{inv["place_name"]}"' if inv["place_name"] else ""
        meal_type = inv["meal_type"] or "встречу"

        status_text = "принято" if new_status == "accepted" else "отказано"
        emojis = "🥳🥳🥳" if new_status == "accepted" else "😭😭😭"

        # responder_display = responder_name or ("@" + str(responder_tg)) if responder_tg else "пользователь"
        if responder_name:
            responder_display = responder_name
        elif responder_username:
            responder_display = "@" + str(responder_username)
        elif responder_tg:
            responder_display = "@" + str(responder_tg)
        else:
            responder_display = "пользователь"

        when_part = f"в {time_readable}" if time_readable else (f"в {inv['time_iso']}" if inv["time_iso"] else "")

        # При принятии добавляем отдельную строку с username (если есть) — как просил
        contact_line = ""
        if new_status == "accepted":
            if responder_username:
                contact_line = f"\n\nСвяжись с @{responder_username}"
            elif responder_tg:
                contact_line = f"\n\nСвяжись с @{responder_tg}"

        telegram_text = f'Ваше приглашение{place_text} с {responder_display} на {meal_type} {when_part} было {status_text} {emojis}{contact_line}'

        # Отправим Telegram (best-effort)
        try:
            await send_telegram_message(inv["from_tg"], telegram_text)
        except Exception:
            logging.exception("failed to send telegram notify to initiator")

        # --- Создадим запись в notifications для мини-аппа инициатора ---
        notif_payload = {
            "invite_id": invite_id,
            "place_name": inv["place_name"],
            "meal_type": meal_type,
            "time_readable": time_readable,
            "responder_name": responder_display,
            "status": new_status
        }
        try:
            await db.execute(
                "INSERT INTO notifications (user_id, type, payload, read, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                (inv["from_user_id"], "invite_response", json.dumps(notif_payload, ensure_ascii=False))
            )
            await db.commit()
        except Exception:
            logging.exception("failed to insert notification")

        return {"ok": True, "invite_id": invite_id, "status": new_status}



places_router(router, DB_PATH, templates)

@router.get("/")
async def index(request: Request):
    """Рендерит templates/index.html через Jinja2."""
    tpl = os.path.join(TEMPLATES_DIR, "index.html")
    if not os.path.exists(tpl):
        static_index = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(static_index):
            return FileResponse(static_index, media_type="text/html")
        raise HTTPException(status_code=404, detail="index.html not found")
    context = {"request": request}
    return templates.TemplateResponse("index.html", context)


@router.post("/start")
async def start_session(request: Request):
    data = await request.json()
    print("POST /start body:", data)
    if not isinstance(data, dict):
        raise HTTPException(400, "body must be json object")
    if "tg_id" not in data or "lat" not in data or "lon" not in data:
        raise HTTPException(400, "tg_id, lat and lon are required")

    tg_id = parse_int(data["tg_id"], "tg_id")
    lat = parse_float(data["lat"], "lat")
    lon = parse_float(data["lon"], "lon")

    # now = datetime.now(timezone.utc)
    # expires = now + timedelta(hours=1)
    # now_s = now.isoformat()
    # expires_s = expires.isoformat()

    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)
    now_s = now.strftime('%Y-%m-%d %H:%M:%S')
    expires_s = expires.strftime('%Y-%m-%d %H:%M:%S')


    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if row is None:
            cur = await db.execute("INSERT INTO users (tg_id) VALUES (?)", (tg_id,))
            await db.commit()
            user_id = cur.lastrowid
        else:
            user_id = row["id"]

        await db.execute("UPDATE eat_sessions SET active = 0 WHERE user_id = ?", (user_id,))
        await db.execute(
            "INSERT INTO eat_sessions (user_id, lat, lon, started_at, expires_at, active) VALUES (?, ?, ?, ?, ?, 1)",
            (user_id, lat, lon, now_s, expires_s)
        )
        await db.commit()

    return {"status": "ok", "expires_at": expires_s}

@router.post("/stop")
async def stop_session(request: Request):
    data = await request.json()
    if not isinstance(data, dict) or "tg_id" not in data:
        raise HTTPException(400, "tg_id required")
    tg_id = parse_int(data["tg_id"], "tg_id")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if row is None:
            raise HTTPException(404, "user not found")
        user_id = row["id"]
        await db.execute("""
            UPDATE eat_sessions SET active = 0 WHERE user_id = ?
        """, (user_id,))
        await db.commit()

    return {"status": "ok"}


@router.get("/nearby")
async def nearby(tg_id: int, lat: float, lon: float, radius_km: float = 3.0, max_rows: int = 100):
    lat_deg = radius_km / 111.0
    lon_deg = radius_km / (111.0 * max(0.00001, math.cos(math.radians(lat))))
    min_lat, max_lat = lat - lat_deg, lat + lat_deg
    min_lon, max_lon = lon - lon_deg, lon + lon_deg

    now_s = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    # now_s = now_iso()
    items = []

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = """
            SELECT e.id AS sid, e.lat, e.lon, e.started_at, e.expires_at, u.id AS user_id, u.tg_id,
                   u.name AS name, u.avatar AS avatar, u.username AS username, u.age AS age
            FROM eat_sessions e
            JOIN users u ON u.id = e.user_id
            WHERE e.active = 1 AND e.expires_at > ?
              AND e.lat BETWEEN ? AND ?
              AND e.lon BETWEEN ? AND ?
            LIMIT ?
        """
        cur = await db.execute(q, (now_s, min_lat, max_lat, min_lon, max_lon, max_rows))
        rows = await cur.fetchall()
        for r in rows:
            if r["tg_id"] == tg_id:
                continue
            d = haversine_km(lat, lon, r["lat"], r["lon"])
            if d <= radius_km:
                items.append({
                    "user_id": r["user_id"],
                    "tg_id": r["tg_id"],
                    "name": r["name"],
                    "username": r["username"],
                    "avatar": safe_avatar_url(r["avatar"]),
                    "age": r["age"],
                    "distance_km": round(d, 3),
                    "started_at": r["started_at"],
                    "expires_at": r["expires_at"],
                })
    items.sort(key=lambda x: x["distance_km"])
    return {"nearby": items}








@router.get("/screens/{name}.html")
async def get_screen_with_ext(request: Request, name: str):
    """Рендерит templates/screens/<name>.html через Jinja2."""
    tmpl = safe_screen_template(name, SCREENS_TEMPLATES_DIR)
    context = {"request": request}
    return templates.TemplateResponse(tmpl, context)



@router.post("/api/survey/respond")
async def api_survey_respond(request: Request):
    body = await request.json()
    invite_id = int(body.get("invite_id"))
    tg_id = int(body.get("tg_id"))  # кто отвечает

    # 'yes' | 'no'
    answer = (body.get("answer") or "").lower()
    if answer not in ("yes", "no"):
        raise HTTPException(400, "answer must be 'yes' or 'no'")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # проверим user
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        user = await cur.fetchone()
        if not user:
            return {"ok": False, "error": "user not found"}
        user_id = user["id"]

        # не позволяем дважды отвечать
        cur = await db.execute("SELECT id FROM invite_surveys WHERE invite_id = ? AND user_id = ?", (invite_id, user_id))
        if await cur.fetchone():
            return {"ok": False, "error": "already answered"}

        # insert response
        await db.execute("INSERT INTO invite_surveys (invite_id, user_id, answer) VALUES (?, ?, ?)", (invite_id, user_id, answer))
        await db.commit()

        # get invite + partner info to craft follow-up
        cur = await db.execute("""
            SELECT i.id, i.from_user_id, i.to_user_id, i.place_name,
                   fu.tg_id AS from_tg, fu.name AS from_name,
                   tu.tg_id AS to_tg, tu.name AS to_name
            FROM invites i
            JOIN users fu ON fu.id = i.from_user_id
            JOIN users tu ON tu.id = i.to_user_id
            WHERE i.id = ?
        """, (invite_id,))
        inv = await cur.fetchone()
        if not inv:
            return {"ok": False, "error": "invite not found"}

        # определим партнёра
        if inv["from_user_id"] == user_id:
            partner_name = inv["to_name"]
            partner_tg = inv["to_tg"]
            partner_id = inv["to_user_id"]
        else:
            partner_name = inv["from_name"]
            partner_tg = inv["from_tg"]
            partner_id = inv["from_user_id"]

        # отправляем follow-up либо сообщение "Ничего страшного"
        if answer == "yes":
            # создаём notification prompting to leave review (mini-app)
            payload = {
                "invite_id": invite_id,
                "partner_name": partner_name,
                "place_name": inv["place_name"],
                "partner_tg": partner_tg,
                "prompt": f'Супер, оставьте отзыв об пользователе "{partner_name}"',
                "reactions": ALLOWED_REACTIONS
            }
            await db.execute(
                "INSERT INTO notifications (user_id, type, payload, read, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                (user_id, "survey_followup", json.dumps(payload, ensure_ascii=False))
            )

            # optional: send Telegram with reaction buttons (callback_data: review:<invite_id>:<reaction>)
            if partner_tg:
                try:
                    # Для Telegram — отправляем пользователю который ответил (not partner)
                    # kb = {"inline_keyboard": [[{"text": r, "callback_data": f"review:{invite_id}:{r}"}] for r in ALLOWED_REACTIONS]}
                    # await send_telegram_message(tg_id, payload["prompt"], reply_markup=kb)
                    await send_telegram_message(tg_id, payload["prompt"])
                except Exception:
                    logging.exception("telegram send followup failed")
            return {"ok": True, "action": "ask_review"}
        else:
            # answer == 'no'
            payload = {"message": f'Ничего страшного — найдете другого.'}
            await db.execute("INSERT INTO notifications (user_id, type, payload, read, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                             (user_id, "survey_negative", json.dumps(payload, ensure_ascii=False)))
            await db.commit()
            
            # optionally notify via telegram
            try:
                await send_telegram_message(tg_id, payload["message"])
            except Exception:
                pass
            return {"ok": True, "action": "noted"}


@router.get("/api/notifications")
async def api_notifications(tg_id: int, since_id: int = 0, limit: int = 20, include_read: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return {"ok": True, "notifications": []}
        user_id = row["id"]

        # Формируем SQL в зависимости от include_read и since_id
        if include_read:
            if since_id and since_id > 0:
                cur = await db.execute(
                    "SELECT id, type, payload, read, created_at FROM notifications WHERE user_id = ? AND id > ? ORDER BY id DESC LIMIT ?",
                    (user_id, since_id, limit)
                )
            else:
                cur = await db.execute(
                    "SELECT id, type, payload, read, created_at FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit)
                )
        else:
            # По умолчанию возвращаем только непрочитанные (read = 0)
            if since_id and since_id > 0:
                cur = await db.execute(
                    "SELECT id, type, payload, read, created_at FROM notifications WHERE user_id = ? AND read = 0 AND id > ? ORDER BY id DESC LIMIT ?",
                    (user_id, since_id, limit)
                )
            else:
                cur = await db.execute(
                    "SELECT id, type, payload, read, created_at FROM notifications WHERE user_id = ? AND read = 0 ORDER BY id DESC LIMIT ?",
                    (user_id, limit)
                )

        rows = await cur.fetchall()
        out = []
        for r in rows:
            try:
                pl = json.loads(r["payload"]) if r["payload"] else {}
            except Exception:
                pl = {}
            out.append({
                "id": r["id"],
                "type": r["type"],
                "payload": pl,
                "read": bool(r["read"]),
                "created_at": r["created_at"]
            })
        return {"ok": True, "notifications": out}


@router.post("/api/notifications/mark_read")
async def api_notifications_mark_read(request: Request):
    body = await request.json()
    tg_id = int(body.get("tg_id"))
    nid = int(body.get("notification_id"))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return {"ok": False}
        user_id = row["id"]
        await db.execute("UPDATE notifications SET read = 1 WHERE id = ? AND user_id = ?", (nid, user_id))
        await db.commit()
    return {"ok": True}


@router.get("/api/invites")
async def api_list_invites(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return {"ok": True, "invites": []}
        user_id = row["id"]
        cur = await db.execute("""SELECT i.id, fu.tg_id AS from_tg, fu.name AS from_name, i.time_iso, i.meal_type, i.message, i.status, i.place_id, i.place_name, i.created_at
                                  FROM invites i
                                  JOIN users fu ON fu.id = i.from_user_id
                                  WHERE i.to_user_id = ? AND i.status = 'pending'
                                  ORDER BY i.created_at DESC
                              """, (user_id,))
        rows = await cur.fetchall()
        out = []
        for r in rows:
            out.append({
                "id": r["id"],
                "from_tg": r["from_tg"],
                "from_name": r["from_name"],
                "time_iso": r["time_iso"],
                "meal_type": r["meal_type"],
                "message": r["message"],
                "status": r["status"],
                "place_id": r["place_id"],
                "place_name": r["place_name"],
                "created_at": r["created_at"]
            })
        return {"ok": True, "invites": out}


@router.post("/api/invite")
async def api_invite(request: Request):
    """body: { from_tg_id: int, to_tg_id: int, time_iso: str, meal_type: str, message?: str }
    """
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="json body required")

    try:
        from_tg = int(body.get("from_tg_id"))
        to_tg = int(body.get("to_tg_id"))
    except Exception:
        raise HTTPException(status_code=400, detail="from_tg_id and to_tg_id required")

    time_iso = body.get("time_iso")
    meal_type = body.get("meal_type") or None
    message = body.get("message") or None

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # ensure both users exist (create lightweight record if missing)
        async def ensure_user(tg):
            cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg,))
            r = await cur.fetchone()
            if r:
                return r["id"]
            await db.execute("INSERT INTO users (tg_id, created_at, updated_at) VALUES (?, datetime('now'), datetime('now'))", (tg,))
            await db.commit()
            cur2 = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg,))
            rr = await cur2.fetchone()
            return rr["id"]

        from_id = await ensure_user(from_tg)
        to_id = await ensure_user(to_tg)

        cur = await db.execute(
            "INSERT INTO invites (from_user_id, to_user_id, time_iso, meal_type, message, place_id, place_name, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'))",
            (from_id, to_id, time_iso, meal_type, message, body.get("place_id"), body.get("place_name"))
        )

        await db.commit()
        invite_id = cur.lastrowid

    # optional: try to notify target via telegram bot (best-effort, failures ignored)
    async def notify_target():
        if not BOT_TOKEN:
            return

        # попробуем взять имя отправителя из БД (может быть null)
        sender_name = None
        try:
            async with aiosqlite.connect(DB_PATH) as db2:
                db2.row_factory = aiosqlite.Row
                cur = await db2.execute("SELECT name, username FROM users WHERE id = ?", (from_id,))
                r = await cur.fetchone()
                if r:
                    sender_name = r["name"] or (("@" + str(r["username"])) if r["username"] else None)
        except Exception:
            logging.exception("failed to lookup sender name")

        from_display = sender_name or (f"@{from_tg}" if from_tg else str(from_tg))

        # place
        place_text = f' в "{body.get("place_name")}"' if body.get("place_name") else ""
        meal = body.get("meal_type") or "встречу"

        # форматируем время — если есть, парсим ISO и переводим в Asia/Almaty
        time_readable = ""
        raw_time = body.get("time_iso")
        if raw_time:
            try:
                # учтём возможный суффикс Z
                t = raw_time
                if t.endswith("Z"):
                    t = t[:-1]
                # попытки парсинга с микросекундами и без
                try:
                    dt = datetime.fromisoformat(t)
                except Exception:
                    # fallback: общий формат с миллисекундами
                    dt = datetime.strptime(raw_time, "%Y-%m-%dT%H:%M:%S.%fZ")
                # если dt naive — считаем что это UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                # переводим в Asia/Almaty
                try:
                    almaty = ZoneInfo("Asia/Almaty")
                    dt_local = dt.astimezone(almaty)
                except Exception:
                    dt_local = dt.astimezone(timezone.utc)
                # читаем месяц по-русски через ручную карту (надёжно)
                ru_months = ["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"]
                hhmm = dt_local.strftime("%H:%M")
                day = dt_local.day
                month = ru_months[dt_local.month - 1]
                time_readable = f"{hhmm} {day} {month}"
            except Exception:
                logging.exception("time parse failed")

        # сформируем текст: если есть время — вставим отформатированное, иначе опустим
        when_part = (f"в {time_readable}" if time_readable else (f"в {body.get('time_iso')}" if body.get('time_iso') else ""))
        
        # сообщение — добавляем только если есть и не пустое
        msg = body.get("message")
        if msg:
            text = f"У вас новое приглашение{place_text} от {from_display} на {meal} {when_part}.\n\nСообщение: {msg}"
        else:
            text = f"У вас новое приглашение{place_text} от {from_display} на {meal} {when_part}."

        # inline keyboard with callback_data
        # keyboard_buttons = [
        #     [
        #         {"text": "Принять", "callback_data": f"invite:{invite_id}:accept"},
        #         {"text": "Отказать", "callback_data": f"invite:{invite_id}:decline"}
        #     ]
        # ]
        # if SERVER_BASE_URL:
        #     profile_url = SERVER_BASE_URL.rstrip('/') + f"/#user_profile_view?tg_id={from_tg}"
        #     keyboard_buttons.append([{"text": "Открыть профиль", "url": profile_url}])

        # keyboard = {"inline_keyboard": keyboard_buttons}

        try:
            # resp = await send_telegram_message(to_tg, text, reply_markup=keyboard)
            resp = await send_telegram_message(to_tg, text)
            logging.info("telegram notify result for invite %s -> %s : %s", invite_id, to_tg, resp)
        except Exception:
            logging.exception("telegram notify failed for invite")


    # fire-and-forget notify (do not await to not slow down response)
    try:
        import asyncio
        asyncio.create_task(notify_target())
    except Exception:
        pass

    return {"ok": True, "invite_id": invite_id}


async def handle_survey_response(invite_id: int, responder_tg: int, ans: str):
    """Helper: обработать ответ на survey (можно вызывать из webhook и из API)."""
    answer = (ans or "").lower()
    if answer not in ("yes", "no"):
        return {"ok": False, "error": "invalid answer"}

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # проверим user
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (responder_tg,))
        user = await cur.fetchone()
        if not user:
            return {"ok": False, "error": "user not found"}
        user_id = user["id"]

        # не позволяем дважды отвечать
        cur = await db.execute("SELECT id FROM invite_surveys WHERE invite_id = ? AND user_id = ?", (invite_id, user_id))
        if await cur.fetchone():
            return {"ok": False, "error": "already answered"}

        # insert response
        await db.execute("INSERT INTO invite_surveys (invite_id, user_id, answer, created_at) VALUES (?, ?, ?, datetime('now'))", (invite_id, user_id, answer))
        await db.commit()

        # get invite + partner info to craft follow-up
        cur = await db.execute("""
            SELECT i.id, i.from_user_id, i.to_user_id, i.place_name,
                   fu.tg_id AS from_tg, fu.name AS from_name,
                   tu.tg_id AS to_tg, tu.name AS to_name
            FROM invites i
            JOIN users fu ON fu.id = i.from_user_id
            JOIN users tu ON tu.id = i.to_user_id
            WHERE i.id = ?
        """, (invite_id,))
        inv = await cur.fetchone()
        if not inv:
            return {"ok": False, "error": "invite not found"}

        # определим партнёра
        if inv["from_user_id"] == user_id:
            partner_name = inv["to_name"]
            partner_tg = inv["to_tg"]
            partner_id = inv["to_user_id"]
        else:
            partner_name = inv["from_name"]
            partner_tg = inv["from_tg"]
            partner_id = inv["from_user_id"]

        # отправляем follow-up либо сообщение "Ничего страшного"
        if answer == "yes":
            payload = {
                "invite_id": invite_id,
                "partner_name": partner_name,
                "partner_tg": partner_tg,
                "place_name": inv["place_name"],
                "prompt": f'Супер, оставьте отзыв об пользователе "{partner_name}"',
                "reactions": ALLOWED_REACTIONS
            }

            await db.execute(
                "INSERT INTO notifications (user_id, type, payload, read, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                (user_id, "survey_followup", json.dumps(payload, ensure_ascii=False))
            )
            await db.commit()
            # send telegram with reaction buttons to the user who answered
            try:
                # kb = {"inline_keyboard": [[{"text": r, "callback_data": f"review:{invite_id}:{r}"}] for r in ALLOWED_REACTIONS]}
                # await send_telegram_message(responder_tg, payload["prompt"], reply_markup=kb)
                await send_telegram_message(responder_tg, payload["prompt"])
            except Exception:
                logging.exception("telegram send followup failed")
            return {"ok": True, "action": "ask_review"}
        else:
            payload = {"message": f'Ничего страшного — найдете другого.'}
            await db.execute("INSERT INTO notifications (user_id, type, payload, read, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
                             (user_id, "survey_negative", json.dumps(payload, ensure_ascii=False)))
            await db.commit()
            try:
                await send_telegram_message(responder_tg, payload["message"])
            except Exception:
                logging.exception("telegram send negative failed")
            return {"ok": True, "action": "noted"}


@router.post("/api/invite/respond")
async def api_invite_respond(request: Request):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="json body required")
    try:
        invite_id = int(body.get("invite_id"))
        responder_tg = int(body.get("responder_tg_id"))
        action = (body.get("action") or "").lower()
    except Exception:
        raise HTTPException(status_code=400, detail="invite_id/responder_tg_id/action required")
    if action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="invalid action")
    res = await handle_invite_response(invite_id, responder_tg, action)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "failed"))
    return {"ok": True, "invite_id": invite_id, "status": res["status"]}


@router.post("/api/review/toggle")
async def api_toggle_review(request: Request):
    """body: { reviewer_tg_id: int, target_tg_id: int, reaction: str }
    Toggles one reaction: если есть - удаляет, иначе добавляет.
    """
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "json body required")
    try:
        reviewer_tg = int(body.get("reviewer_tg_id"))
        target_tg = int(body.get("target_tg_id"))
    except Exception:
        raise HTTPException(400, "reviewer_tg_id and target_tg_id required")
    reaction = (body.get("reaction") or "").strip()
    if reaction not in ALLOWED_REACTIONS:
        raise HTTPException(400, "invalid reaction")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async def ensure_user(tg):
            cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg,))
            r = await cur.fetchone()
            if r: return r["id"]
            await db.execute("INSERT INTO users (tg_id, created_at, updated_at) VALUES (?, datetime('now'), datetime('now'))", (tg,))
            await db.commit()
            cur2 = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg,))
            rr = await cur2.fetchone()
            return rr["id"]

        reviewer_id = await ensure_user(reviewer_tg)
        target_id = await ensure_user(target_tg)

        cur = await db.execute("SELECT id FROM reviews WHERE reviewer_id = ? AND target_user_id = ? AND reaction = ?", (reviewer_id, target_id, reaction))
        row = await cur.fetchone()
        if row:
            await db.execute("DELETE FROM reviews WHERE id = ?", (row["id"],))
            await db.commit()
            return {"ok": True, "action": "removed", "reaction": reaction}
        else:
            await db.execute("INSERT INTO reviews (reviewer_id, target_user_id, reaction, created_at) VALUES (?, ?, ?, datetime('now'))", (reviewer_id, target_id, reaction))
            await db.commit()
            return {"ok": True, "action": "added", "reaction": reaction}



@router.get("/api/reviews")
async def api_get_reviews(tg_id: int, limit: int = 20, viewer_tg_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return {"ok": False, "error": "user not found", "counts": {}, "recent": [], "viewer": []}
        user_id = row["id"]

        cur = await db.execute("SELECT reaction, COUNT(*) AS cnt FROM reviews WHERE target_user_id = ? GROUP BY reaction", (user_id,))
        rows = await cur.fetchall()
        counts = {r["reaction"]: int(r["cnt"]) for r in rows}

        cur = await db.execute("""
            SELECT r.reaction, r.comment, r.created_at, u.tg_id AS reviewer_tg, u.name AS reviewer_name, u.avatar AS reviewer_avatar
            FROM reviews r
            LEFT JOIN users u ON u.id = r.reviewer_id
            WHERE r.target_user_id = ?
            ORDER BY r.created_at DESC
            LIMIT ?
        """, (user_id, limit))
        recent = []
        for r in await cur.fetchall():
            recent.append({
                "reaction": r["reaction"],
                "comment": r["comment"],
                "created_at": r["created_at"],
                "reviewer_tg": r["reviewer_tg"],
                "reviewer_name": r["reviewer_name"],
                "reviewer_avatar": safe_avatar_url(r["reviewer_avatar"])
            })

        viewer_reactions = []
        if viewer_tg_id:
            cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (viewer_tg_id,))
            vr = await cur.fetchone()
            if vr:
                v_id = vr["id"]
                cur = await db.execute("SELECT reaction FROM reviews WHERE reviewer_id = ? AND target_user_id = ?", (v_id, user_id))
                viewer_reactions = [r["reaction"] for r in await cur.fetchall()]

    return {"ok": True, "counts": counts, "recent": recent, "viewer": viewer_reactions}


@router.post("/verify_init")
async def verify_init(request: Request):
    logging.info("VERIFY_INIT start")
    payload = await request.json()
    logging.info("VERIFY_INIT payload raw: %s", payload)

    # Получаем initData - может быть строкой (raw query) или объектом
    init_raw = payload.get("initData")
    if isinstance(init_raw, str):
        # parse_qsl корректно декодирует %-encoding и возвращает пары
        pairs = parse_qsl(init_raw, keep_blank_values=True)
        init_data = {k: v for k, v in pairs}
    else:
        init_data = dict(init_raw or {})

    if not init_data:
        logging.warning("verify_init: missing initData")
        raise HTTPException(status_code=400, detail="initData required")

    if not BOT_TOKEN:
        logging.error("BOT_TOKEN not set")
        raise HTTPException(status_code=500, detail="BOT_TOKEN not set on server")

    # If client parsed `user` to object, convert it back to compact JSON string
    try:
        import json
        if "user" in init_data and isinstance(init_data["user"], dict):
            init_data["user"] = json.dumps(init_data["user"], separators=(",", ":"), ensure_ascii=False)
    except Exception as e:
        logging.exception("error normalizing user field: %s", e)

    # Ensure all values are strings (Telegram sends strings)
    for k, v in list(init_data.items()):
        if v is None:
            init_data[k] = ""
        elif not isinstance(v, str):
            init_data[k] = str(v)

    # Build data_check_string exactly like Telegram expects
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(init_data.items()) if k != "hash")
    logging.info("data_check_string:\n%s", data_check_string)

    # compute HMAC
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hmac = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    provided_hash = init_data.get("hash", "")
    logging.info("computed_hmac=%s provided_hash=%s", computed_hmac, provided_hash)

    if not hmac.compare_digest(computed_hmac, provided_hash):
        logging.warning("HMAC mismatch - invalid initData")
        raise HTTPException(status_code=403, detail="invalid initData")

    # далее проверка auth_date и upsert
    try:
        auth_date = int(init_data.get("auth_date", 0))
    except Exception:
        auth_date = 0
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if auth_date == 0 or (now_ts - auth_date) > 24 * 3600:
        logging.warning("initData expired: auth_date=%s now_ts=%s", auth_date, now_ts)
        raise HTTPException(status_code=403, detail="initData expired")

    try:
        tg_id = int(init_data.get("id") or init_data.get("user", "") and (json.loads(init_data.get("user")) or {}).get("id"))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid id in initData")

    # извлекаем поля профиля (если они есть прямо в init_data или внутри user JSON)
    first_name = init_data.get("first_name")
    username = init_data.get("username")
    avatar = init_data.get("photo_url") or init_data.get("photo") or None

    # если данные про профиль в user JSON - попробуем достать оттуда при необходимости
    try:
        if not first_name or not username or not avatar:
            user_raw = init_data.get("user")
            if user_raw:
                import json as _json
                try:
                    u = _json.loads(user_raw)
                    first_name = first_name or u.get("first_name")
                    username = username or u.get("username")
                    avatar = avatar or u.get("photo_url") or u.get("photo")
                except Exception:
                    pass
    except Exception:
        pass

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Обновляем/вставляем пользователя (tg_id)
        await db.execute(
            "UPDATE users SET name = ?, avatar = ? WHERE tg_id = ?",
            (first_name or username or None, avatar, tg_id)
        )
        await db.commit()
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute("""
                INSERT INTO users (tg_id, name, avatar, username, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(tg_id) DO UPDATE SET
                name = excluded.name,
                avatar = excluded.avatar,
                username = excluded.username,
                updated_at = datetime('now');
            """, (tg_id, first_name or username or None, avatar, username))
            await db.commit()

    logging.info("VERIFY_INIT ok for tg_id=%s name=%s", tg_id, first_name)
    return {
        "ok": True,
        "tg_id": tg_id,
        "name": first_name,
        "username": username,
        "avatar": avatar
    }





# ----------------------
# API: профиль с тегами и "последними контактами"
# ----------------------
@router.get("/api/profile")
async def api_profile(tg_id: int):
    """Возвращает профиль пользователя + теги + последние другие пользователи (recent_contacts)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id, tg_id, name, avatar, username, age, created_at FROM users WHERE tg_id = ?", (tg_id,))
        user = await cur.fetchone()
        if user is None:
            return {"ok": False, "error": "user not found"}

        user_id = user["id"]

        # теги
        cur = await db.execute("SELECT tag FROM user_tags WHERE user_id = ? ORDER BY tag COLLATE NOCASE", (user_id,))
        tags = [r["tag"] for r in await cur.fetchall()]

        # последние сессии текущего пользователя
        cur = await db.execute("""
            SELECT lat, lon, started_at, expires_at, active
            FROM eat_sessions
            WHERE user_id = ?
            ORDER BY started_at DESC
            LIMIT 10
        """, (user_id,))
        sessions = [dict(r) for r in await cur.fetchall()]

        # recent other users: последних N других пользователей, отсортированных по последней активности
        cur = await db.execute("""
            SELECT u.tg_id, u.name, u.avatar, u.username, u.age, max(e.started_at) AS last_seen
            FROM users u
            JOIN eat_sessions e ON e.user_id = u.id
            WHERE u.id != ?
            GROUP BY u.id
            ORDER BY last_seen DESC
            LIMIT 10
        """, (user_id,))
        contacts = []
        for r in await cur.fetchall():
            contacts.append({
                "tg_id": r["tg_id"],
                "name": r["name"],
                "username": r["username"],
                "avatar": safe_avatar_url(r["avatar"]),
                "age": r["age"],
                "last_seen": r["last_seen"]
            })

        # reviews counts (опционально)
        cur_reaction = await db.execute("SELECT reaction, COUNT(*) AS cnt FROM reviews WHERE target_user_id = ? GROUP BY reaction", (user_id,))
        rows = await cur_reaction.fetchall()
        review_counts = {r["reaction"]: int(r["cnt"]) for r in rows}

        result = {
            "ok": True,
            "user": {
                "tg_id": user["tg_id"],
                "name": user["name"],
                "avatar": safe_avatar_url(user["avatar"]),
                "username": user["username"],
                "age": user["age"],
                "created_at": user["created_at"]
            },
            "tags": tags,
            "sessions": sessions,
            "recent_contacts": contacts,
            "review_counts": review_counts
        }
        return result

# ----------------------
# API: get tags
# ----------------------
@router.get("/api/profile/tags")
async def api_profile_get_tags(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return {"ok": False, "error": "user not found"}
        user_id = row["id"]
        cur = await db.execute("SELECT tag FROM user_tags WHERE user_id = ? ORDER BY tag COLLATE NOCASE", (user_id,))
        tags = [r["tag"] for r in await cur.fetchall()]
        return {"ok": True, "tags": tags}

# ----------------------
# API: replace tags (POST) - body: {tg_id:int, tags: [str,...]}
# ----------------------
@router.post("/api/profile/tags")
async def api_profile_set_tags(request: Request):
    body = await request.json()
    if not isinstance(body, dict) or "tg_id" not in body or "tags" not in body:
        raise HTTPException(status_code=400, detail="tg_id and tags required")
    tg_id = int(body["tg_id"])
    tags = body["tags"]
    if not isinstance(tags, list):
        raise HTTPException(status_code=400, detail="tags must be list")

    # normalize: trim, lower, remove empty, unique, max length
    norm = []
    seen = set()
    for t in tags:
        try:
            st = (str(t) or "").strip()
        except Exception:
            st = ""
        if not st:
            continue
        st = st[:64]
        st = st.lower()
        if st in seen:
            continue
        seen.add(st)
        norm.append(st)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return {"ok": False, "error": "user not found"}
        user_id = row["id"]

        # replace tags in transaction
        await db.execute("BEGIN")
        try:
            await db.execute("DELETE FROM user_tags WHERE user_id = ?", (user_id,))
            for t in norm:
                await db.execute("INSERT OR IGNORE INTO user_tags (user_id, tag) VALUES (?, ?)", (user_id, t))
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return {"ok": True, "tags": norm}


# ----------------------
# API: update profile (name/avatar/age) - body: {tg_id, name?, avatar?, age?}
# ----------------------
@router.post("/api/profile/update")
async def api_profile_update(request: Request):
    body = await request.json()
    if not isinstance(body, dict) or "tg_id" not in body:
        raise HTTPException(status_code=400, detail="tg_id required")
    tg_id = int(body["tg_id"])
    name = body.get("name")
    avatar = body.get("avatar")
    age = body.get("age")
    username = body.get("username")

    if avatar:
        avatar = safe_avatar_url(avatar)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if row is None:
            # create basic user record (include username)
            await db.execute("INSERT INTO users (tg_id, name, avatar, username, age, created_at, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
                             (tg_id, name, avatar, username, age))
            await db.commit()
        else:
            # update fields present
            fields = []
            params = []
            if name is not None:
                fields.append("name = ?")
                params.append(name)
            if avatar is not None:
                fields.append("avatar = ?")
                params.append(avatar)
            if age is not None:
                try:
                    a = int(age)
                except Exception:
                    a = None
                fields.append("age = ?")
                params.append(a)
            if username is not None:
                fields.append("username = ?")
                params.append(username)
            if fields:
                params.append(tg_id)
                q = "UPDATE users SET " + ", ".join(fields) + ", updated_at = datetime('now') WHERE tg_id = ?"
                await db.execute(q, tuple(params))
                await db.commit()

    return {"ok": True}


@router.get("/api/users/similar")
async def api_users_similar(tg_id: int, limit: int = 10):
    """Возвращает пользователей с пересечением по тегам, отсортированных по числу совпадений и активности."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # найдём user_id
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return {"ok": False, "error": "user not found", "users": []}
        user_id = row["id"]

        # получаем теги текущего пользователя
        cur = await db.execute("SELECT tag FROM user_tags WHERE user_id = ?", (user_id,))
        user_tags = [r["tag"] for r in await cur.fetchall()]

        if not user_tags:
            # fallback: вернём последние активные контакты (как в profile)
            cur = await db.execute("""
                SELECT u.tg_id, u.name, u.avatar, u.username, u.age, max(e.started_at) AS last_seen
                FROM users u
                JOIN eat_sessions e ON e.user_id = u.id
                WHERE u.id != ?
                GROUP BY u.id
                ORDER BY last_seen DESC
                LIMIT ?
            """, (user_id, limit))
            rows = await cur.fetchall()
            res = []
            for r in rows:
                res.append({
                    "tg_id": r["tg_id"],
                    "name": r["name"],
                    "username": r["username"],
                    "avatar": safe_avatar_url(r["avatar"]),
                    "age": r["age"],
                    "tags": [],
                    "common": 0,
                    "last_seen": r["last_seen"]
                })
            return {"ok": True, "users": res}

        # ищем других пользователей, у которых есть пересекающиеся теги
        placeholders = ",".join("?" for _ in user_tags)
        q = f"""
            SELECT u.id AS uid, u.tg_id, u.name, u.avatar, u.username, u.age,
                   GROUP_CONCAT(DISTINCT ut.tag) AS tags,
                   COUNT(DISTINCT ut.tag) AS common,
                   MAX(e.started_at) AS last_seen
            FROM user_tags ut
            JOIN users u ON u.id = ut.user_id
            LEFT JOIN eat_sessions e ON e.user_id = u.id
            WHERE ut.tag IN ({placeholders}) AND u.id != ?
            GROUP BY u.id
            ORDER BY common DESC, last_seen DESC
            LIMIT ?
        """
        params = user_tags + [user_id, limit]
        cur = await db.execute(q, params)
        rows = await cur.fetchall()
        out = []
        for r in rows:
            tags = (r["tags"] or "").split(",") if r["tags"] else []
            out.append({
                "tg_id": r["tg_id"],
                "name": r["name"],
                "username": r["username"],
                "avatar": safe_avatar_url(r["avatar"]),
                "age": r["age"],
                "tags": tags,
                "common": int(r["common"] or 0),
                "last_seen": r["last_seen"]
            })
        return {"ok": True, "users": out}

@router.get("/api/tags")
async def api_tags(limit: int = 100):
    """Возвращает список популярных тегов с count, отсортированных по популярности.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT tag, COUNT(*) AS cnt
            FROM user_tags
            GROUP BY tag
            ORDER BY cnt DESC, tag ASC
            LIMIT ?
        """, (limit,))
        rows = await cur.fetchall()
        tags = [{"tag": r["tag"], "count": r["cnt"]} for r in rows]
        return {"ok": True, "tags": tags}








async def handle_review_from_survey(invite_id: int, reviewer_tg: int, reaction: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT from_user_id, to_user_id FROM invites WHERE id = ?", (invite_id,))
        inv = await cur.fetchone()
        if not inv:
            return {"ok": False, "error": "invite not found"}
        # определить target (если reviewer == from_user -> target = to_user_id и наоборот)
        cur = await db.execute("SELECT id FROM users WHERE tg_id = ?", (reviewer_tg,))
        r = await cur.fetchone()
        if not r: return {"ok": False, "error": "reviewer not found"}
        reviewer_id = r["id"]
        if reviewer_id == inv["from_user_id"]:
            target_id = inv["to_user_id"]
        else:
            target_id = inv["from_user_id"]

        # тут можно добавлять в reviews или вызывать существующую логику
        await db.execute("INSERT INTO reviews (reviewer_id, target_user_id, reaction, created_at) VALUES (?, ?, ?, datetime('now'))",
                         (reviewer_id, target_id, reaction))
        await db.commit()
        return {"ok": True}



@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    # handle callback_query
    if "callback_query" in data:
        cq = data["callback_query"]
        cq_id = cq.get("id")
        from_user = cq.get("from", {})
        tg_user_id = from_user.get("id")
        data_str = cq.get("data", "") or ""

        try:
            if data_str.startswith("invite:"):
                _, sid, action = data_str.split(":", 2)
                iid = int(sid)
                if action not in ("accept", "decline"):
                    await answer_callback_query(cq_id, "Неверная команда", show_alert=True)
                    return {"ok": True}
                res = await handle_invite_response(iid, tg_user_id, action)
                if res.get("ok"):
                    await answer_callback_query(cq_id, f"Вы {('приняли' if action=='accept' else 'отклонили')} приглашение", show_alert=False)
                else:
                    await answer_callback_query(cq_id, res.get("error", "Ошибка"), show_alert=True)
                return {"ok": True}

            # после успешной обработки invite:
            if res.get("ok"):
                await answer_callback_query(cq_id, f"Вы {('приняли' if action=='accept' else 'отклонили')} приглашение", show_alert=False)
                # попробуем обновить текст и убрать кнопки в исходном сообщении (если callback пришёл из сообщения)
                try:
                    msg = cq.get("message")
                    if msg and "chat" in msg and "message_id" in msg:
                        chat_id = msg["chat"]["id"]
                        mid = msg["message_id"]
                        # пометить в тексте
                        new_text = (msg.get("text") or "") + ("\n\n✅ Вы приняли" if action=="accept" else "\n\n❌ Вы отказались")
                        await edit_message_text(chat_id=chat_id, message_id=mid, text=new_text)
                        await edit_message_reply_markup(chat_id=chat_id, message_id=mid, reply_markup={"inline_keyboard": []})
                except Exception:
                    logging.exception("failed to update invite message after callback")

            if data_str.startswith("survey:"):
                # формат: survey:<invite_id>:<answer>
                _, sid, ans = data_str.split(":", 2)
                iid = int(sid)
                if ans not in ("yes", "no"):
                    await answer_callback_query(cq_id, "Неверный ответ", show_alert=True)
                else:
                    res = await handle_survey_response(iid, tg_user_id, ans)
                    if res.get("ok"):
                        await answer_callback_query(cq_id, "Спасибо, ответ принят", show_alert=False)
                    else:
                        await answer_callback_query(cq_id, res.get("error","Ошибка"), show_alert=True)
                return {"ok": True}
            
            if res.get("ok"):
                await answer_callback_query(cq_id, "Спасибо, ответ принят", show_alert=False)
                try:
                    msg = cq.get("message")
                    if msg and "chat" in msg and "message_id" in msg:
                        chat_id = msg["chat"]["id"]
                        mid = msg["message_id"]
                        choice = "Да" if ans=="yes" else "Нет"
                        new_text = (msg.get("text") or "") + f"\n\nВы ответили: {choice} ✅"
                        await edit_message_text(chat_id=chat_id, message_id=mid, text=new_text)
                        await edit_message_reply_markup(chat_id=chat_id, message_id=mid, reply_markup={"inline_keyboard": []})
                except Exception:
                    logging.exception("failed to update survey message after callback")


            if data_str.startswith("review:"):
                # формат: review:<invite_id>:<reaction_label>
                _, sid, reaction = data_str.split(":", 2)
                iid = int(sid)
                res = await handle_review_from_survey(iid, tg_user_id, reaction)
                if res.get("ok"):
                    await answer_callback_query(cq_id, "Отзыв сохранён — спасибо!", show_alert=False)
                else:
                    await answer_callback_query(cq_id, res.get("error","Ошибка"), show_alert=True)
                return {"ok": True}
            
            if res.get("ok"):
                await answer_callback_query(cq_id, "Отзыв сохранён — спасибо!", show_alert=False)
                try:
                    msg = cq.get("message")
                    if msg and "chat" in msg and "message_id" in msg:
                        chat_id = msg["chat"]["id"]
                        mid = msg["message_id"]
                        new_text = (msg.get("text") or "") + "\n\n✅ Отзыв сохранён"
                        await edit_message_text(chat_id=chat_id, message_id=mid, text=new_text)
                        await edit_message_reply_markup(chat_id=chat_id, message_id=mid, reply_markup={"inline_keyboard": []})
                except Exception:
                    logging.exception("failed to update review message after callback")
        except Exception:
            logging.exception("telegram callback handling failed")
            await answer_callback_query(cq_id, "Ошибка при обработке", show_alert=True)
            return {"ok": True}

    return {"ok": True}

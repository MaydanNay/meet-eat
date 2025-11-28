# app/telegram_utils.py

import json
import asyncio
import aiohttp 
import logging
import aiosqlite
import html as _html

from routes import DB_PATH
from app.config import BOT_TOKEN

# если будете передавать session извне — лучше. Но функция сама умеет создать сессию.
async def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None, sess: aiohttp.ClientSession = None):
    if not BOT_TOKEN:
        logging.warning("send_telegram_message: BOT_TOKEN not set")
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    safe_text = _html.escape(text)
    payload = {"chat_id": chat_id, "text": safe_text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)

    created_session = False
    try:
        if sess is None:
            sess = aiohttp.ClientSession()
            created_session = True

        # внутри app/telegram_utils.py -> send_telegram_message
        MAX_ATTEMPTS = 3
        TIMEOUT = 15  # seconds
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                async with sess.post(url, json=payload, timeout=TIMEOUT) as resp:
                    try:
                        j = await resp.json()
                    except Exception:
                        j = {"ok": False, "http_status": resp.status}
                    if not j.get("ok"):
                        logging.warning("telegram send failed (chat=%s) resp=%s", chat_id, j)
                    return j
            except asyncio.TimeoutError:
                logging.warning("send_telegram_message timeout for chat_id=%s attempt=%d", chat_id, attempt)
                if attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(1.0 * attempt)
                    continue
                return None
            except aiohttp.ClientError as e:
                logging.warning("send_telegram_message client error for chat_id=%s: %s", chat_id, e)
                return None

    finally:
        if created_session and sess is not None:
            await sess.close()



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

            partner_from_name = r["from_name"] or r["from_tg"] or "партнёр"
            partner_to_name = r["to_name"] or r["to_tg"] or "партнёр"
            meal = (r["meal_type"] or "встречу").strip()
            place = r["place_name"] or ""
            place_part = f' в "{place}"' if place else ""

            # формируем строки для отправки каждому участнику
            text_for_from = f'Сходили ли вы с "{partner_to_name}" {meal}{place_part}?'
            text_for_to   = f'Сходили ли вы с "{partner_from_name}" {meal}{place_part}?'

            # попытка пометить и отправить
            try:
                if r.get("from_tg"):
                    await send_telegram_message(r["from_tg"], text_for_from)
                if r.get("to_tg"):
                    await send_telegram_message(r["to_tg"], text_for_to)
            except Exception:
                logging.exception("survey send telegram failed for invite %s", invite_id)

        await db.commit()

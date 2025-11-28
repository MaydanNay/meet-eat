# app/telegram_utils.py

import aiohttp, json, logging, html as _html
from app.config import BOT_TOKEN

async def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None):
    if not BOT_TOKEN:
        logging.warning("send_telegram_message: BOT_TOKEN not set")
        return None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    safe_text = _html.escape(text)
    payload = {"chat_id": chat_id, "text": safe_text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, json=payload, timeout=10) as resp:
                return await resp.json()
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

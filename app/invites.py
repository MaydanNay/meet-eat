# # app/invites.py
# from fastapi import APIRouter, HTTPException, Request
# import aiosqlite, json, logging
# from .config import DB_PATH, SERVER_BASE_URL
# from .telegram_utils import send_telegram_message

# router = APIRouter()

# @router.post("/api/invite")
# async def api_invite(request: Request):
#     body = await request.json()
#     # ... валидация, ensure_user (можно вынести в db.py)
#     # insert invite
#     # create notify_target task (вынеси notify_target в отдельную функцию)
#     return {"ok": True, "invite_id": invite_id}

# async def handle_invite_response(invite_id: int, responder_tg: int, action: str):
#     # перенеси существующую реализацию сюда
#     # используй send_telegram_message из telegram_utils
#     return {"ok": True}

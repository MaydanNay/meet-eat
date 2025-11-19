# routes.py

import os
import math
import logging
import aiosqlite
import hmac, hashlib
from urllib.parse import parse_qsl
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request

from screens import safe_screen_template
from utils import haversine_km, now_iso, parse_float, parse_int

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("meet_eat")

router = APIRouter()

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

print("PROJECT_ROOT=", PROJECT_ROOT)
print("STATIC_DIR=", STATIC_DIR)
print("TEMPLATES_DIR=", TEMPLATES_DIR)
print("index template exists:", os.path.exists(os.path.join(TEMPLATES_DIR, "index.html")))

templates = Jinja2Templates(directory=TEMPLATES_DIR)

DB_PATH = "db.sqlite3"
import hashlib, hmac
BOT_TOKEN = "7642738760:AAEZ-8IwR1wNbxvbQyjuo4mTNKGYgJAXy5E"
secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
print(secret_key.hex())



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

    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)
    now_s = now.isoformat()
    expires_s = expires.isoformat()

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

    now_s = now_iso()
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





@router.post("/verify_init")
async def verify_init(request: Request):
    log.info("VERIFY_INIT start")
    payload = await request.json()
    log.info("VERIFY_INIT payload raw: %s", payload)

    # Получаем initData — может быть строкой (raw query) или объектом
    init_raw = payload.get("initData")
    if isinstance(init_raw, str):
        # parse_qsl корректно декодирует %-encoding и возвращает пары
        pairs = parse_qsl(init_raw, keep_blank_values=True)
        init_data = {k: v for k, v in pairs}
    else:
        init_data = dict(init_raw or {})

    if not init_data:
        log.warning("verify_init: missing initData")
        raise HTTPException(status_code=400, detail="initData required")

    if not BOT_TOKEN:
        log.error("BOT_TOKEN not set")
        raise HTTPException(status_code=500, detail="BOT_TOKEN not set on server")

    # If client parsed `user` to object, convert it back to compact JSON string
    try:
        import json
        if "user" in init_data and isinstance(init_data["user"], dict):
            init_data["user"] = json.dumps(init_data["user"], separators=(",", ":"), ensure_ascii=False)
    except Exception as e:
        log.exception("error normalizing user field: %s", e)

    # Ensure all values are strings (Telegram sends strings)
    for k, v in list(init_data.items()):
        if v is None:
            init_data[k] = ""
        elif not isinstance(v, str):
            init_data[k] = str(v)

    # Build data_check_string exactly like Telegram expects
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(init_data.items()) if k != "hash")
    log.info("data_check_string:\n%s", data_check_string)

    # compute HMAC
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hmac = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    provided_hash = init_data.get("hash", "")
    log.info("computed_hmac=%s provided_hash=%s", computed_hmac, provided_hash)

    if not hmac.compare_digest(computed_hmac, provided_hash):
        log.warning("HMAC mismatch - invalid initData")
        raise HTTPException(status_code=403, detail="invalid initData")

    # далее проверка auth_date и upsert
    try:
        auth_date = int(init_data.get("auth_date", 0))
    except Exception:
        auth_date = 0
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if auth_date == 0 or (now_ts - auth_date) > 24 * 3600:
        log.warning("initData expired: auth_date=%s now_ts=%s", auth_date, now_ts)
        raise HTTPException(status_code=403, detail="initData expired")

    try:
        tg_id = int(init_data.get("id") or init_data.get("user", "") and (json.loads(init_data.get("user")) or {}).get("id"))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid id in initData")

    # извлекаем поля профиля (если они есть прямо в init_data или внутри user JSON)
    first_name = init_data.get("first_name")
    username = init_data.get("username")
    avatar = init_data.get("photo_url") or init_data.get("photo") or None

    # если данные про профиль в user JSON — попробуем достать оттуда при необходимости
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

    log.info("VERIFY_INIT ok for tg_id=%s name=%s", tg_id, first_name)
    return {
        "ok": True,
        "tg_id": tg_id,
        "name": first_name,
        "username": username,
        "avatar": avatar
    }





# ----------------------
# Helper: validate avatar url + placeholder
# ----------------------
from urllib.parse import urlparse

PLACEHOLDER_AVATAR = "/static/images/default_avatar.svg"  # положите файл в static/images/

def safe_avatar_url(url):
    """Возвращаем безопасный URL для аватара: только http/https и короткая длина.
       Если невалидный — возвращаем PLACEHOLDER_AVATAR.
    """
    try:
        if not url or not isinstance(url, str):
            return PLACEHOLDER_AVATAR
        url = url.strip()
        if len(url) > 1000:
            return PLACEHOLDER_AVATAR
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return PLACEHOLDER_AVATAR
        # Дополнительно: можно ограничить домены, но пока пропускаем любые http(s)
        return url
    except Exception:
        return PLACEHOLDER_AVATAR

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
            "recent_contacts": contacts
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
# API: replace tags (POST) — body: {tg_id:int, tags: [str,...]}
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
# API: update profile (name/avatar/age) — body: {tg_id, name?, avatar?, age?}
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


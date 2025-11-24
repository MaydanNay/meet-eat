# main.py

import asyncio
import aiosqlite
from utils import now_iso
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

from routes import router as api_router

DB_PATH = "db.sqlite3"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # users table (age may be added if missing)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                name TEXT,
                avatar TEXT,
                username TEXT,
                age INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)

        # user_tags for interests
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                UNIQUE(user_id, tag),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # eat_sessions unchanged
        await db.execute("""
            CREATE TABLE IF NOT EXISTS eat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                started_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_tags_tag 
                ON user_tags(tag);
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,            -- например "invite_response"
                payload TEXT,                  -- json string с деталями
                read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                time_iso TEXT,
                meal_type TEXT,
                place_id INTEGER,
                place_name TEXT,
                message TEXT,
                status TEXT DEFAULT 'pending',
                responder_user_id INTEGER,
                responded_at TEXT,

                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(from_user_id) REFERENCES users(id),
                FOREIGN KEY(to_user_id) REFERENCES users(id)
            );
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_invites_to 
                ON invites(to_user_id);
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_id INTEGER NOT NULL,
                target_user_id INTEGER NOT NULL,
                reaction TEXT NOT NULL,
                comment TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY(reviewer_id) REFERENCES users(id),
                FOREIGN KEY(target_user_id) REFERENCES users(id),
                UNIQUE(reviewer_id, target_user_id, reaction)
            );
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_target 
                ON reviews(target_user_id);
        """)

        # places (заведения)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                rating REAL DEFAULT 0.0,
                open_time TEXT,   -- формат "HH:MM"
                close_time TEXT,  -- формат "HH:MM"
                address TEXT,
                photo TEXT,       -- url к картинке
                created_by_tg_id INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_places_category ON places(category);
        """)

        await db.commit()

        try:
            await db.commit()
        except Exception:
            pass


async def cleanup_task(stop_event: asyncio.Event):
    try:
        while not stop_event.is_set():
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE eat_sessions SET active = 0 WHERE expires_at <= datetime('now') AND active = 1"
                    )
                    await db.commit()
            except Exception as e:
                print("cleanup error:", e)
            await asyncio.wait_for(stop_event.wait(), timeout=60.0)
    except asyncio.CancelledError:
        pass



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    stop_event = asyncio.Event()
    task = asyncio.create_task(cleanup_task(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        task.cancel()
        try:
            await task
        except Exception:
            pass

app = FastAPI(lifespan=lifespan, title="meet&eat")
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.middleware("http")
async def add_ngrok_header(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["ngrok-skip-browser-warning"] = "1"
    return resp
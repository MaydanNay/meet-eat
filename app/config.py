# app/config.py

import os

DB_PATH = os.getenv("DB_PATH", "db.sqlite3")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "")

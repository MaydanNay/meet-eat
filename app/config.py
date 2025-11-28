# app/config.py

import os

DB_PATH = os.getenv("DB_PATH", "db.sqlite3")
# BOT_TOKEN = os.getenv("BOT_TOKEN", "8430676291:AAFr9yilHXr2Fel35y297btCjln6N6cR7l8")
BOT_TOKEN='8430676291:AAFr9yilHXr2Fel35y297btCjln6N6cR7l8'
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "")

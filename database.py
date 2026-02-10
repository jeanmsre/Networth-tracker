import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# fallback local sqlite
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///networth.db"

engine = create_engine(DATABASE_URL, echo=False)


def get_connection():
    return engine.connect()


def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount REAL,
            note TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            networth REAL
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS balance (
            id INTEGER PRIMARY KEY,
            amount REAL
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """))

        # init balance
        result = conn.execute(text("SELECT COUNT(*) FROM balance")).fetchone()[0]
        if result == 0:
            conn.execute(text("INSERT INTO balance (id, amount) VALUES (1, 0)"))

        # init default settings
        setting_check = conn.execute(text("SELECT COUNT(*) FROM settings")).fetchone()[0]
        if setting_check == 0:
            conn.execute(text("INSERT INTO settings (key, value) VALUES ('starting_balance', '0')"))
            conn.execute(text("INSERT INTO settings (key, value) VALUES ('starting_date', '2026-01-01')"))
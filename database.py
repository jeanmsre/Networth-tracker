import os
from sqlalchemy import create_engine, text

# ---------------- DATABASE URL ----------------
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix for old postgres:// prefix (Render sometimes uses it)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback local sqlite if DATABASE_URL is not defined
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///networth.db"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)


# ---------------- INIT DB ----------------
def init_db():
    with engine.begin() as conn:

        # TRANSACTIONS
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            date TEXT,
            type TEXT,
            category TEXT,
            amount DOUBLE PRECISION,
            note TEXT
        )
        """))

        # SNAPSHOTS
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id SERIAL PRIMARY KEY,
            date TEXT UNIQUE,
            networth DOUBLE PRECISION
        )
        """))

        # BALANCE (optional table)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS balance (
            id INTEGER PRIMARY KEY,
            amount DOUBLE PRECISION
        )
        """))

        # SETTINGS
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """))

        # ---------------- INIT BALANCE ROW ----------------
        result = conn.execute(text("SELECT COUNT(*) FROM balance")).fetchone()[0]
        if result == 0:
            conn.execute(text("INSERT INTO balance (id, amount) VALUES (1, 0)"))

        # ---------------- INIT DEFAULT SETTINGS ----------------
        check_starting_balance = conn.execute(
            text("SELECT COUNT(*) FROM settings WHERE key='starting_balance'")
        ).fetchone()[0]

        if check_starting_balance == 0:
            conn.execute(
                text("INSERT INTO settings (key, value) VALUES ('starting_balance', '0')")
            )

        check_starting_date = conn.execute(
            text("SELECT COUNT(*) FROM settings WHERE key='starting_date'")
        ).fetchone()[0]

        if check_starting_date == 0:
            conn.execute(
                text("INSERT INTO settings (key, value) VALUES ('starting_date', '2026-01-01')")
            )
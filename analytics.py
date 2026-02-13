import pandas as pd
from datetime import date
from sqlalchemy import text
import streamlit as st
from database import engine


# ---------------- TRANSACTIONS ----------------
@st.cache_data(ttl=20)
def load_transactions():
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM transactions ORDER BY date ASC", conn)
    return df


# ---------------- SNAPSHOTS ----------------
@st.cache_data(ttl=20)
def load_snapshots():
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM snapshots ORDER BY date ASC", conn)
    return df


# ---------------- BALANCE ----------------
def get_balance():
    with engine.connect() as conn:
        row = conn.execute(text("SELECT amount FROM balance WHERE id=1")).fetchone()
    return float(row[0]) if row else 0.0


def set_balance(amount):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE balance SET amount=:amount WHERE id=1"),
            {"amount": float(amount)}
        )


# ---------------- SNAPSHOT SAVE ----------------
def save_snapshot():
    today_str = str(date.today())
    balance = get_balance()

    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO snapshots (date, networth)
            VALUES (:date, :networth)
            ON CONFLICT (date) DO NOTHING
            """),
            {"date": today_str, "networth": float(balance)}
        )


# ---------------- MONTHLY SUMMARY ----------------
def monthly_summary(df):
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)

    grouped = df.groupby(["month", "type"])["amount"].sum().reset_index()
    grouped = grouped.sort_values("month")

    return grouped


# ---------------- SETTINGS ----------------
def get_setting(key):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT value FROM settings WHERE key=:key"),
            {"key": key}
        ).fetchone()

    return row[0] if row else None


def set_setting(key, value):
    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO settings (key, value)
            VALUES (:key, :value)
            ON CONFLICT (key) DO UPDATE SET value=:value
            """),
            {"key": key, "value": str(value)}
        )


# ---------------- NET WORTH TIMELINE ----------------
@st.cache_data(ttl=20)
def build_balance_timeline():
    starting_balance = float(get_setting("starting_balance") or 0)
    starting_date_str = get_setting("starting_date") or str(date.today())

    df = load_transactions()

    if df.empty:
        return pd.DataFrame(columns=["date", "balance"])

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values("date")

    start_date = pd.to_datetime(starting_date_str).date()
    end_date = df["date"].max()

    if end_date < start_date:
        end_date = start_date

    all_days = pd.date_range(start=start_date, end=end_date, freq="D").date

    balance = starting_balance
    timeline = []

    for day in all_days:
        day_tx = df[df["date"] == day]

        if not day_tx.empty:
            for _, row in day_tx.iterrows():
                if row["type"] == "income":
                    balance += float(row["amount"])
                elif row["type"] == "expense":
                    balance -= float(row["amount"])

        timeline.append({
            "date": str(day),
            "balance": balance
        })

    return pd.DataFrame(timeline)
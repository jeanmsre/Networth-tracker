import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px

from database import init_db, get_connection
from analytics import (
    load_transactions,
    load_snapshots,
    get_balance,
    set_balance,
    save_snapshot,
    monthly_summary,
    build_balance_timeline,
    get_setting,
    set_setting
)

# ---------------- SETUP ----------------
init_db()
st.set_page_config(page_title="NetWorth Tracker", layout="wide")

st.title("💰 NetWorth Tracker ")

menu = st.sidebar.radio("📌 Menu", [
    "Dashboard",
    "Transactions",
    "Timeline",
    "Export",
    "Settings"
])

# Always save snapshot for today
save_snapshot()

# Month mapping
month_names = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

# ---------------- DASHBOARD ----------------
if menu == "Dashboard":
    st.subheader("📊 Dashboard")

    transactions_df = load_transactions()

    # ---------------- NET WORTH LIVE ----------------
    st.subheader("💎 Net Worth (Live)")

    starting_balance = float(get_setting("starting_balance") or 0)

    if not transactions_df.empty:
        total_income_all = transactions_df[transactions_df["type"] == "income"]["amount"].sum()
        total_expense_all = transactions_df[transactions_df["type"] == "expense"]["amount"].sum()
    else:
        total_income_all = 0
        total_expense_all = 0

    networth_today = starting_balance + total_income_all - total_expense_all

    colA, colB, colC = st.columns(3)
    colA.metric("💰 Net Worth Today", f"{networth_today:,.2f} €")
    colB.metric("📈 Total Income (All Time)", f"{total_income_all:,.2f} €")
    colC.metric("📉 Total Expenses (All Time)", f"{total_expense_all:,.2f} €")

    st.divider()

    st.subheader("📉 Net Worth Curve (Daily)")

    timeline_df = build_balance_timeline()

    if not timeline_df.empty:
        fig_nw = px.line(
            timeline_df,
            x="date",
            y="balance",
            markers=True,
            title="Net Worth Evolution (Daily)"
        )

        fig_nw.update_xaxes(type="category")
        fig_nw.update_layout(
            xaxis_title="Date",
            yaxis_title="Balance (€)"
        )

        st.plotly_chart(fig_nw, use_container_width=True)
    else:
        st.info("No timeline data available yet.")

    st.divider()

    # ---------------- THIS MONTH KPI ----------------
    st.subheader("📌 This Month Overview")

    today = date.today()
    current_month = today.strftime("%Y-%m")

    if not transactions_df.empty:
        df_temp = transactions_df.copy()
        df_temp["date"] = pd.to_datetime(df_temp["date"])
        df_temp["month"] = df_temp["date"].dt.to_period("M").astype(str)

        expenses_month = df_temp[(df_temp["type"] == "expense") & (df_temp["month"] == current_month)]["amount"].sum()
        income_month = df_temp[(df_temp["type"] == "income") & (df_temp["month"] == current_month)]["amount"].sum()
    else:
        expenses_month = 0
        income_month = 0

    col1, col2 = st.columns(2)
    col1.metric("📉 Expenses (This Month)", f"{expenses_month:,.2f} €")
    col2.metric("📈 Income (This Month)", f"{income_month:,.2f} €")

    st.divider()

    # ---------------- MONTH NAVIGATION ----------------
    st.subheader("📅 Month Navigation")

    if "selected_year" not in st.session_state:
        st.session_state.selected_year = today.year

    if "selected_month" not in st.session_state:
        st.session_state.selected_month = today.month

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

    with col_nav1:
        if st.button("⬅️ Previous Month"):
            if st.session_state.selected_month == 1:
                st.session_state.selected_month = 12
                st.session_state.selected_year -= 1
            else:
                st.session_state.selected_month -= 1

    with col_nav3:
        if st.button("Next Month ➡️"):
            if st.session_state.selected_month == 12:
                st.session_state.selected_month = 1
                st.session_state.selected_year += 1
            else:
                st.session_state.selected_month += 1

    with col_nav2:
        st.markdown(
            f"<h3 style='text-align: center;'>📌 {month_names[st.session_state.selected_month]} {st.session_state.selected_year}</h3>",
            unsafe_allow_html=True
        )

    col_year, col_month = st.columns(2)

    with col_year:
        year_list = list(range(2020, 2051))
        st.session_state.selected_year = st.selectbox(
            "Select Year",
            year_list,
            index=year_list.index(st.session_state.selected_year)
        )

    with col_month:
        st.session_state.selected_month = st.selectbox(
            "Select Month",
            list(range(1, 13)),
            format_func=lambda m: month_names[m],
            index=st.session_state.selected_month - 1
        )

    selected_year = st.session_state.selected_year
    selected_month = st.session_state.selected_month

    st.divider()

    # ---------------- DISPLAY MODE ----------------
    st.subheader("📌 Display Mode")

    display_mode = st.radio(
    "Choose display mode:",
    ["Daily (Normal)", "Cumulative (Month)", "Cumulative (Year)"],
    index=1,
    horizontal=True
)

    show_balance = st.checkbox("Show balance curve (Net Worth)", value=False)

    st.divider()

    # ---------------- PREPARE TRANSACTIONS DF ----------------
    if not transactions_df.empty:
        df_all = transactions_df.copy()
        df_all["date"] = pd.to_datetime(df_all["date"]).dt.date
    else:
        df_all = pd.DataFrame()

    # ---------------- DEFINE PERIOD ----------------
    if display_mode == "Cumulative (Year)":
        start_date = date(selected_year, 1, 1)
        end_date = date(selected_year + 1, 1, 1)
    else:
        start_date = date(selected_year, selected_month, 1)
        if selected_month == 12:
            end_date = date(selected_year + 1, 1, 1)
        else:
            end_date = date(selected_year, selected_month + 1, 1)

    if not df_all.empty:
        df_period = df_all[(df_all["date"] >= start_date) & (df_all["date"] < end_date)].copy()
    else:
        df_period = pd.DataFrame()

    # ---------------- GRAPH INCOME/EXPENSE ----------------
    st.subheader("📈 Income / Expenses")

    if not df_all.empty:
        daily_summary = df_period.groupby(["date", "type"])["amount"].sum().reset_index()

        income_daily = daily_summary[daily_summary["type"] == "income"].rename(columns={"amount": "income"})
        expense_daily = daily_summary[daily_summary["type"] == "expense"].rename(columns={"amount": "expense"})

        merged = pd.merge(
            income_daily[["date", "income"]],
            expense_daily[["date", "expense"]],
            on="date",
            how="outer"
        ).fillna(0)

        merged = merged.sort_values("date")

        # Fill missing days
        all_days = pd.date_range(start=start_date, end=end_date - pd.Timedelta(days=1), freq="D").date
        merged = merged.set_index("date").reindex(all_days, fill_value=0).reset_index()
        merged = merged.rename(columns={"index": "date"})

        # Apply cumulative mode
        if display_mode in ["Cumulative (Month)", "Cumulative (Year)"]:
            merged["income"] = merged["income"].cumsum()
            merged["expense"] = merged["expense"].cumsum()

        # Add balance if requested
        if show_balance:
            timeline_df = build_balance_timeline()
            timeline_df["date"] = pd.to_datetime(timeline_df["date"]).dt.date

            merged = pd.merge(merged, timeline_df, on="date", how="left")
            merged["balance"] = merged["balance"].fillna(method="ffill").fillna(0)

        # Title
        if display_mode == "Cumulative (Year)":
            title = f"{display_mode} - {selected_year}"
        else:
            title = f"{display_mode} - {month_names[selected_month]} {selected_year}"

        # Select Y columns
        y_cols = ["income", "expense"]
        if show_balance:
            y_cols.append("balance")

        fig = px.line(
            merged,
            x="date",
            y=y_cols,
            markers=True,
            title=title
        )

        fig.update_xaxes(type="category")
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Amount (€)",
            legend_title="Metrics"
        )

        # Colors (income green apple, expense red, balance grey)
        for trace in fig.data:
            if trace.name == "income":
                trace.line.color = "#7CFC00"  # apple green
            elif trace.name == "expense":
                trace.line.color = "red"
            elif trace.name == "balance":
                trace.line.color = "gray"

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No transactions yet.")

    st.divider()

    # ---------------- TOTALS ----------------
    st.subheader("📌 Totals (Selected Period)")

    if not df_period.empty:
        total_income_period = df_period[df_period["type"] == "income"]["amount"].sum()
        total_expense_period = df_period[df_period["type"] == "expense"]["amount"].sum()

        colx, coly = st.columns(2)
        colx.metric("📈 Total Income", f"{total_income_period:,.2f} €")
        coly.metric("📉 Total Expenses", f"{total_expense_period:,.2f} €")
    else:
        st.info("No transactions in this selected period.")

    st.divider()

    # ---------------- PIE CHART CATEGORY (MONTH ONLY) ----------------
    st.subheader("🍕 Expenses by Category (Selected Month)")

    if display_mode != "Cumulative (Year)" and not df_period.empty:
        expenses_df = df_period[df_period["type"] == "expense"]

        if not expenses_df.empty:
            cat = expenses_df.groupby("category")["amount"].sum().reset_index()

            fig_pie = px.pie(
                cat,
                names="category",
                values="amount",
                title=f"Expenses by Category ({month_names[selected_month]} {selected_year})"
            )

            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No expenses for this month.")
    else:
        st.info("Pie chart available only for Month view.")

    st.divider()

    # ---------------- MONTHLY CASHFLOW ALL TIME ----------------
    st.subheader("📅 Monthly Income vs Expenses (All Time)")

    if not transactions_df.empty:
        monthly = monthly_summary(transactions_df)

        if not monthly.empty:
            fig_monthly = px.bar(
                monthly,
                x="month",
                y="amount",
                color="type",
                title="Monthly Income vs Expenses"
            )
            st.plotly_chart(fig_monthly, use_container_width=True)

# ---------------- TRANSACTIONS ----------------
elif menu == "Transactions":
    st.subheader("🧾 Transactions")

    balance = get_balance()

    with st.form("add_transaction"):
        t_date = st.date_input("Date", value=date.today())
        t_type = st.selectbox("Type", ["expense", "income"])

        category_list = ["rent", "elec", "agua", "wifi", "food, gas, outfit", "other"]
        t_category = st.selectbox("Category", category_list)

        if t_category == "other":
            custom_category = st.text_input("Custom category")
            if custom_category.strip() != "":
                t_category = custom_category.strip().lower()

        t_amount = st.number_input("Amount (€)", min_value=0.0, step=1.0)
        t_note = st.text_input("Note (optional)")

        submitted = st.form_submit_button("➕ Add Transaction")

        if submitted:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO transactions (date, type, category, amount, note)
            VALUES (?, ?, ?, ?, ?)
            """, (str(t_date), t_type, t_category, t_amount, t_note))

            conn.commit()
            conn.close()

            # Update balance
            if t_type == "expense":
                balance -= t_amount
            else:
                balance += t_amount

            set_balance(balance)
            save_snapshot()

            st.success(f"Transaction added! New balance: {balance:,.2f} €")
            st.rerun()

    st.divider()

    df = load_transactions()

    if df.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(df, use_container_width=True)

        st.subheader("🗑️ Delete Transaction (Auto reverse impact)")

        selected_id = st.selectbox("Select Transaction ID", df["id"].tolist())

        if st.button("Delete selected transaction"):
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT type, amount FROM transactions WHERE id=?", (selected_id,))
            row = cursor.fetchone()

            if row:
                t_type, t_amount = row

                current_balance = get_balance()

                # Reverse effect
                if t_type == "expense":
                    current_balance += t_amount
                else:
                    current_balance -= t_amount

                set_balance(current_balance)

                cursor.execute("DELETE FROM transactions WHERE id=?", (selected_id,))
                conn.commit()

            conn.close()
            save_snapshot()

            st.success("Transaction deleted and balance corrected.")
            st.rerun()

# ---------------- TIMELINE ----------------
elif menu == "Timeline":
    st.subheader("📈 Net Worth Evolution (Transaction-Based)")

    timeline_df = build_balance_timeline()

    if timeline_df.empty:
        st.info("No timeline data available yet.")
    else:
        col1, col2 = st.columns(2)

        col1.metric("📌 Starting Balance", f"{float(get_setting('starting_balance') or 0):,.2f} €")
        col2.metric("📅 Starting Date", str(get_setting("starting_date")))

        st.divider()

        fig = px.line(
            timeline_df,
            x="date",
            y="balance",
            markers=True,
            title="📈 Net Worth Curve (Daily)"
        )

        fig.update_xaxes(type="category")
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Balance (€)"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("📋 Timeline Data")
        st.dataframe(timeline_df, use_container_width=True)

# ---------------- EXPORT ----------------
elif menu == "Export":
    st.subheader("📤 Export Data")

    transactions_df = load_transactions()
    snapshots_df = load_snapshots()
    timeline_df = build_balance_timeline()

    st.download_button(
        "⬇️ Download Transactions CSV",
        transactions_df.to_csv(index=False).encode("utf-8"),
        "transactions.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Download Snapshots CSV",
        snapshots_df.to_csv(index=False).encode("utf-8"),
        "snapshots.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Download Timeline CSV",
        timeline_df.to_csv(index=False).encode("utf-8"),
        "timeline.csv",
        "text/csv"
    )

    st.success("Export ready.")

# ---------------- SETTINGS ----------------
elif menu == "Settings":
    st.subheader("⚙️ Settings")

    balance = get_balance()
    st.metric("Main Balance", f"{balance:,.2f} €")

    st.divider()

    st.subheader("📌 Timeline Settings")

    starting_balance = float(get_setting("starting_balance") or 0)
    starting_date_str = get_setting("starting_date") or str(date.today())

    new_starting_balance = st.number_input(
        "Starting balance (€)",
        value=float(starting_balance),
        step=100.0
    )

    new_starting_date = st.date_input(
        "Starting date",
        value=pd.to_datetime(starting_date_str)
    )

    if st.button("💾 Save Timeline Settings"):
        set_setting("starting_balance", str(new_starting_balance))
        set_setting("starting_date", str(new_starting_date))
        st.success("Timeline settings saved!")
        st.rerun()

    st.divider()

    st.subheader("⚠️ Manual Balance Override")

    new_balance = st.number_input(
        "Set Main Balance (€)",
        value=float(balance),
        step=100.0
    )

    if st.button("💾 Update Main Balance"):
        set_balance(new_balance)
        save_snapshot()
        st.success("Balance updated!")
        st.rerun()
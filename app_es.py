import os
import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
from sqlalchemy import text
from streamlit_cookies_manager import CookieManager

from database import init_db, engine
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

# ---------------- INIT DB ----------------
init_db()

# ---------------- STREAMLIT CONFIG ----------------
st.set_page_config(page_title="NetWorth Tracker", layout="wide")

# ---------------- COOKIES (PERSISTENT LOGIN) ----------------
cookies = CookieManager()

if not cookies.ready():
    st.stop()

# ---------------- PASSWORD PROTECTION ----------------
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Auto login from cookie
if cookies.get("auth") == "1":
    st.session_state.authenticated = True

if APP_PASSWORD != "":
    if not st.session_state.authenticated:
        st.title("🔒 NetWorth Tracker Protegido")

        password_input = st.text_input("Introduce la contraseña", type="password")

        if st.button("Iniciar sesión"):
            if password_input == APP_PASSWORD:
                st.session_state.authenticated = True
                cookies["auth"] = "1"
                cookies.save()
                st.success("Bienvenido Sir 😈")
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")

        st.stop()

# ---------------- TITLE ----------------
st.title("💰 NetWorth Tracker (1 Cuenta de Capital)")

# ---------------- SIDEBAR MENU ----------------
menu = st.sidebar.radio("📌 Menú", [
    "Panel",
    "Transacciones",
    "Evolución",
    "Exportar",
    "Configuración"
])

# Logout
if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.authenticated = False
    cookies["auth"] = "0"
    cookies.save()
    st.rerun()

# Month mapping (Spanish)
month_names = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# ---------------- DASHBOARD ----------------
if menu == "Panel":
    st.subheader("📊 Panel")

    transactions_df = load_transactions()
    starting_balance = float(get_setting("starting_balance") or 0)

    # ---------------- NET WORTH LIVE ----------------
    st.subheader("💎 Patrimonio Neto (En Vivo)")

    if not transactions_df.empty:
        total_income_all = transactions_df[transactions_df["type"] == "income"]["amount"].sum()
        total_expense_all = transactions_df[transactions_df["type"] == "expense"]["amount"].sum()
    else:
        total_income_all = 0
        total_expense_all = 0

    networth_today = starting_balance + total_income_all - total_expense_all

    colA, colB, colC = st.columns(3)
    colA.metric("💰 Patrimonio Hoy", f"{networth_today:,.2f} €")
    colB.metric("📈 Ingresos Totales (Histórico)", f"{total_income_all:,.2f} €")
    colC.metric("📉 Gastos Totales (Histórico)", f"{total_expense_all:,.2f} €")

    st.divider()

    # ---------------- NET WORTH CURVE ----------------
    st.subheader("📉 Curva del Patrimonio (Diaria)")

    timeline_df = build_balance_timeline()

    if not timeline_df.empty:
        fig_nw = px.line(
            timeline_df,
            x="date",
            y="balance",
            markers=True,
            title="Evolución del Patrimonio Neto (Diario)"
        )

        fig_nw.update_xaxes(type="category")
        fig_nw.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Balance (€)"
        )

        st.plotly_chart(fig_nw, use_container_width=True)
    else:
        st.info("Todavía no hay datos de evolución.")

    st.divider()

    # ---------------- MONTH NAVIGATION ----------------
    st.subheader("📅 Navegación Mensual")

    today = date.today()

    if "selected_year" not in st.session_state:
        st.session_state.selected_year = today.year

    if "selected_month" not in st.session_state:
        st.session_state.selected_month = today.month

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])

    with col_nav1:
        if st.button("⬅️ Mes anterior"):
            if st.session_state.selected_month == 1:
                st.session_state.selected_month = 12
                st.session_state.selected_year -= 1
            else:
                st.session_state.selected_month -= 1

    with col_nav3:
        if st.button("Mes siguiente ➡️"):
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
            "Seleccionar año",
            year_list,
            index=year_list.index(st.session_state.selected_year)
        )

    with col_month:
        st.session_state.selected_month = st.selectbox(
            "Seleccionar mes",
            list(range(1, 13)),
            format_func=lambda m: month_names[m],
            index=st.session_state.selected_month - 1
        )

    selected_year = st.session_state.selected_year
    selected_month = st.session_state.selected_month

    st.divider()

    # ---------------- DISPLAY MODE ----------------
    st.subheader("📌 Modo de Visualización")

    display_mode = st.radio(
        "Selecciona el modo:",
        ["Diario (Normal)", "Acumulado (Mes)", "Acumulado (Año)"],
        index=1,
        horizontal=True
    )

    show_balance = st.checkbox("Mostrar curva de balance (Patrimonio Neto)", value=False)

    st.divider()

    if not transactions_df.empty:
        df_all = transactions_df.copy()
        df_all["date"] = pd.to_datetime(df_all["date"]).dt.date
    else:
        df_all = pd.DataFrame()

    if display_mode == "Acumulado (Año)":
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

    st.subheader("📈 Ingresos / Gastos")

    if not df_all.empty:
        daily_summary = df_period.groupby(["date", "type"])["amount"].sum().reset_index()
        pivot = daily_summary.pivot(index="date", columns="type", values="amount").fillna(0)

        if "income" not in pivot.columns:
            pivot["income"] = 0
        if "expense" not in pivot.columns:
            pivot["expense"] = 0

        pivot = pivot.sort_index()
        merged = pivot.reset_index()[["date", "income", "expense"]]

        all_days = pd.date_range(start=start_date, end=end_date - pd.Timedelta(days=1), freq="D").date
        merged["date"] = pd.to_datetime(merged["date"]).dt.date
        merged = merged.set_index("date").reindex(all_days, fill_value=0).reset_index()
        merged = merged.rename(columns={"index": "date"})

        if display_mode in ["Acumulado (Mes)", "Acumulado (Año)"]:
            merged["income"] = merged["income"].cumsum()
            merged["expense"] = merged["expense"].cumsum()

        if show_balance:
            timeline_df2 = build_balance_timeline()
            timeline_df2["date"] = pd.to_datetime(timeline_df2["date"]).dt.date
            merged = pd.merge(merged, timeline_df2, on="date", how="left")
            merged["balance"] = merged["balance"].ffill().fillna(0)

        if display_mode == "Acumulado (Año)":
            title = f"{display_mode} - {selected_year}"
        else:
            title = f"{display_mode} - {month_names[selected_month]} {selected_year}"

        y_cols = ["income", "expense"]
        if show_balance:
            y_cols.append("balance")

        fig = px.line(merged, x="date", y=y_cols, markers=True, title=title)

        fig.update_xaxes(type="category")
        fig.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Cantidad (€)",
            legend_title="Métricas"
        )

        for trace in fig.data:
            if trace.name == "income":
                trace.line.color = "#7CFC00"
            elif trace.name == "expense":
                trace.line.color = "red"
            elif trace.name == "balance":
                trace.line.color = "gray"

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Todavía no hay transacciones.")

    st.divider()

    st.subheader("📌 Totales (Periodo Seleccionado)")

    if not df_period.empty:
        total_income_period = df_period[df_period["type"] == "income"]["amount"].sum()
        total_expense_period = df_period[df_period["type"] == "expense"]["amount"].sum()

        colx, coly = st.columns(2)
        colx.metric("📈 Ingresos Totales", f"{total_income_period:,.2f} €")
        coly.metric("📉 Gastos Totales", f"{total_expense_period:,.2f} €")
    else:
        st.info("No hay transacciones en este periodo.")

    st.divider()

    st.subheader("🍕 Gastos por Categoría (Mes Seleccionado)")

    if display_mode != "Acumulado (Año)" and not df_period.empty:
        expenses_df = df_period[df_period["type"] == "expense"]

        if not expenses_df.empty:
            cat = expenses_df.groupby("category")["amount"].sum().reset_index()

            fig_pie = px.pie(
                cat,
                names="category",
                values="amount",
                title=f"Gastos ({month_names[selected_month]} {selected_year})"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay gastos este mes.")
    else:
        st.info("El gráfico circular solo está disponible en modo Mes.")

    st.divider()

    st.subheader("📅 Ingresos vs Gastos Mensuales (Histórico)")

    if not transactions_df.empty:
        monthly = monthly_summary(transactions_df)
        if not monthly.empty:
            fig_monthly = px.bar(
                monthly,
                x="month",
                y="amount",
                color="type",
                title="Ingresos vs Gastos Mensuales"
            )
            st.plotly_chart(fig_monthly, use_container_width=True)


# ---------------- TRANSACTIONS ----------------
elif menu == "Transacciones":
    st.subheader("🧾 Transacciones")

    balance = get_balance()

    with st.form("add_transaction"):
        t_date = st.date_input("Fecha", value=date.today())
        t_type = st.selectbox("Tipo", ["expense", "income"], format_func=lambda x: "Gasto" if x == "expense" else "Ingreso")

        category_list = ["rent", "elec", "agua", "wifi", "food", "gas", "outfit", "other"]
        t_category = st.selectbox("Categoría", category_list)

        if t_category == "other":
            custom_category = st.text_input("Categoría personalizada")
            if custom_category.strip() != "":
                t_category = custom_category.strip().lower()

        t_amount = st.number_input("Cantidad (€)", min_value=0.0, step=1.0)
        t_note = st.text_input("Nota (opcional)")

        submitted = st.form_submit_button("➕ Agregar transacción")

        if submitted:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    INSERT INTO transactions (date, type, category, amount, note)
                    VALUES (:date, :type, :category, :amount, :note)
                    """),
                    {
                        "date": str(t_date),
                        "type": t_type,
                        "category": t_category,
                        "amount": float(t_amount),
                        "note": t_note
                    }
                )

            if t_type == "expense":
                balance -= float(t_amount)
            else:
                balance += float(t_amount)

            set_balance(balance)
            save_snapshot()

            st.cache_data.clear()
            st.success(f"Transacción agregada! Nuevo balance: {balance:,.2f} €")
            st.rerun()

    st.divider()

    df = load_transactions()

    if df.empty:
        st.info("Todavía no hay transacciones.")
    else:
        st.dataframe(df, use_container_width=True)

        st.divider()

        st.subheader("🗑️ Eliminar transacción (corrige balance automáticamente)")

        selected_id = st.selectbox("Seleccionar ID de transacción", df["id"].tolist())

        if st.button("Eliminar transacción seleccionada"):
            with engine.begin() as conn:
                row = conn.execute(
                    text("SELECT type, amount FROM transactions WHERE id=:id"),
                    {"id": int(selected_id)}
                ).fetchone()

                if row:
                    t_type = row[0]
                    t_amount = float(row[1])

                    current_balance = get_balance()

                    if t_type == "expense":
                        current_balance += t_amount
                    else:
                        current_balance -= t_amount

                    set_balance(current_balance)

                    conn.execute(
                        text("DELETE FROM transactions WHERE id=:id"),
                        {"id": int(selected_id)}
                    )

            save_snapshot()
            st.cache_data.clear()
            st.success("Transacción eliminada y balance corregido.")
            st.rerun()


# ---------------- TIMELINE ----------------
elif menu == "Evolución":
    st.subheader("📈 Evolución del Patrimonio Neto (Basado en transacciones)")

    starting_balance = float(get_setting("starting_balance") or 0)
    starting_date_str = get_setting("starting_date") or str(date.today())

    colA, colB = st.columns(2)
    colA.metric("📌 Balance Inicial Actual", f"{starting_balance:,.2f} €")
    colB.metric("📅 Fecha Inicial Actual", starting_date_str)

    st.divider()

    st.subheader("⚙️ Editar punto de inicio de la evolución")

    with st.form("update_timeline_settings"):
        new_starting_balance = st.number_input(
            "Balance Inicial (€)",
            value=float(starting_balance),
            step=100.0
        )

        new_starting_date = st.date_input(
            "Fecha Inicial",
            value=pd.to_datetime(starting_date_str)
        )

        submitted = st.form_submit_button("💾 Guardar punto de inicio")

        if submitted:
            set_setting("starting_balance", str(new_starting_balance))
            set_setting("starting_date", str(new_starting_date))

            st.cache_data.clear()
            st.success("Punto de inicio actualizado correctamente!")
            st.rerun()

    st.divider()

    timeline_df = build_balance_timeline()

    if timeline_df.empty:
        st.info("No hay datos disponibles todavía.")
    else:
        fig = px.line(
            timeline_df,
            x="date",
            y="balance",
            markers=True,
            title="📈 Curva del Patrimonio Neto (Diaria)"
        )

        fig.update_xaxes(type="category")
        fig.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Balance (€)"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("📋 Datos de evolución")
        st.dataframe(timeline_df, use_container_width=True)


# ---------------- EXPORT ----------------
elif menu == "Exportar":
    st.subheader("📤 Exportar Datos")

    transactions_df = load_transactions()
    snapshots_df = load_snapshots()
    timeline_df = build_balance_timeline()

    st.download_button(
        "⬇️ Descargar Transacciones CSV",
        transactions_df.to_csv(index=False).encode("utf-8"),
        "transactions.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Descargar Snapshots CSV",
        snapshots_df.to_csv(index=False).encode("utf-8"),
        "snapshots.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Descargar Timeline CSV",
        timeline_df.to_csv(index=False).encode("utf-8"),
        "timeline.csv",
        "text/csv"
    )

    st.success("Exportación lista.")


# ---------------- SETTINGS ----------------
elif menu == "Configuración":
    st.subheader("⚙️ Configuración")

    balance = get_balance()
    st.metric("Balance Principal (DB)", f"{balance:,.2f} €")

    st.divider()

    st.subheader("⚠️ Modificación Manual del Balance")

    new_balance = st.number_input(
        "Actualizar Balance Principal (€)",
        value=float(balance),
        step=100.0
    )

    if st.button("💾 Guardar nuevo balance"):
        set_balance(new_balance)
        save_snapshot()

        st.cache_data.clear()
        st.success("Balance actualizado!")
        st.rerun()
import numpy as np
import pandas as pd
import streamlit as st

# =========================================================
# PAGE CONFIG & TITLE
# =========================================================
st.set_page_config(
    page_title="Stock Valuation & Portfolio Capacity Engine", layout="wide"
)
st.title("📈 Stock Valuation & Portfolio Capacity Engine")

# =========================================================
# INITIAL DATASETS
# =========================================================


def get_initial_portfolio():
    return pd.DataFrame(
        [
            {
                "Ticker": "AXA",
                "Name": "AXA SA",
                "Sector": "Financial Services",
                "Shares": 188.0,
                "Price_EUR": 43.73,
            },
            {
                "Ticker": "ALV.DE",
                "Name": "Allianz SE",
                "Sector": "Financial Services",
                "Shares": 10.0,
                "Price_EUR": 450.00,
            },
        ]
    )


@st.cache_data
def load_mock_universe():
    return pd.DataFrame(
        [
            {
                "Ticker": "AXA",
                "Name": "AXA SA",
                "Sector": "Financial Services",
                "Fair_Value": 62.15,
                "Current_Price": 43.72,
                "PER": 11.8,
                "Beta": 0.59,
                "Plausibility_Status": "🟢 Robust",
            },
            {
                "Ticker": "NVDA",
                "Name": "NVIDIA Corp.",
                "Sector": "Technology",
                "Fair_Value": 110.00,
                "Current_Price": 125.00,
                "PER": 45.2,
                "Beta": 1.68,
                "Plausibility_Status": "🟡 KGV Hoch",
            },
            {
                "Ticker": "SAP.DE",
                "Name": "SAP SE",
                "Sector": "Technology",
                "Fair_Value": 190.00,
                "Current_Price": 195.00,
                "PER": 32.0,
                "Beta": 0.95,
                "Plausibility_Status": "🟢 Robust",
            },
            {
                "Ticker": "AAPL",
                "Name": "Apple Inc.",
                "Sector": "Technology",
                "Fair_Value": 220.00,
                "Current_Price": 210.00,
                "PER": 30.0,
                "Beta": 1.05,
                "Plausibility_Status": "🟢 Robust",
            },
            {
                "Ticker": "MSFT",
                "Name": "Microsoft Corp.",
                "Sector": "Technology",
                "Fair_Value": 430.00,
                "Current_Price": 415.00,
                "PER": 34.0,
                "Beta": 0.90,
                "Plausibility_Status": "🟢 Robust",
            },
        ]
    )


if "portfolio_list" not in st.session_state:
    st.session_state.portfolio_list = get_initial_portfolio().to_dict(
        "records"
    )

df_universe = load_mock_universe()

# =========================================================
# SIDEBAR CONFIGURATION
# =========================================================
st.sidebar.header("⚙️ Depot-Parameter")

cash_balance = st.sidebar.number_input(
    "Cash-Bestand (€)", value=55000.0, step=1000.0
)
target_stock_quote_max = st.sidebar.slider(
    "Max. Ziel-Aktienquote (%)", 10.0, 100.0, 50.0
)
limit_pct_input = st.sidebar.slider(
    "Max. Einzelposition (% vom Depot)", 1.0, 20.0, 10.0
)
sector_limit_pct_input = st.sidebar.slider(
    "Max. Sektor-Limit (% vom Gesamtdepot)", 5.0, 50.0, 25.0
)

# =========================================================
# NAVIGATION TABS
# =========================================================
tab_a, tab_b, tab_c = st.tabs(
    [
        "🔍 Tab A: Aktien-Analyse",
        "📊 Tab B: Depot-Verwaltung",
        "🎯 Tab C: Kauf-Simulation & Tranchen",
    ]
)

# ---------------------------------------------------------
# TAB A: AKTIEN-ANALYSE (MEHRKRITERIEN-BEWERTUNG)
# ---------------------------------------------------------
with tab_a:
    st.header("Einzelaktien-Bewertung nach Kriterien")
    selected_ticker = st.selectbox(
        "Aktie zur Analyse auswählen:", df_universe["Ticker"].tolist()
    )

    stock_data = df_universe[df_universe["Ticker"] == selected_ticker].iloc[0]
    mos = (
        (stock_data["Fair_Value"] - stock_data["Current_Price"])
        / stock_data["Current_Price"]
    ) * 100

    st.markdown("---")
    st.markdown(
        "**Bewerte die Aktie anhand verschiedener Qualitäts- und Fundamentalkriterien:**"
    )

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        crit_fcf = st.checkbox(
            "Positive Cashflow-Metriken", value=True, key="c_fcf"
        )
        crit_growth = st.checkbox(
            "Starkes Gewinnwachstum (>10%)", value=True, key="c_growth"
        )
        crit_moat = st.checkbox(
            "Intakter Trend / Momentum", value=True, key="c_moat"
        )
    with col_c2:
        crit_balance = st.checkbox(
            "Gesunde Bilanz / geringe Schulden", value=True, key="c_balance"
        )
        crit_margin = st.checkbox(
            "Hohe operative Marge", value=False, key="c_margin"
        )
        crit_valuation = st.checkbox(
            "Attraktive Bewertung (DCF/KGV)", value=True, key="c_val"
        )

    criteria_list = [
        crit_fcf,
        crit_growth,
        crit_moat,
        crit_balance,
        crit_margin,
        crit_valuation,
    ]
    score = sum(criteria_list)
    max_score = len(criteria_list)
    score_pct = int((score / max_score) * 100)

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Quality Score", f"{score_pct} / 100", delta=f"{score} von {max_score} Kriterien")
    col2.metric("Fair Value", f"{stock_data['Fair_Value']:.2f} €")
    col3.metric(
        "Aktueller Kurs",
        f"{stock_data['Current_Price']:.2f} €",
        delta=f"{mos:+.1f} % MOS",
    )
    col4.metric("KGV / Beta", f"{stock_data['PER']} | {stock_data['Beta']}")

    if score_pct >= 80:
        st.success("🟢 Starkes Setup: Aktie erfüllt die Mehrheit der Qualitätskriterien.")
    elif score_pct >= 50:
        st.warning("🟡 Moderates Setup: Einige Kriterien sind noch offen.")
    else:
        st.error("🔴 Schwaches Setup: Kriterien-Anforderungen nicht ausreichend erfüllt.")

    st.info(f"**Modell-Status:** {stock_data['Plausibility_Status']}")

# ---------------------------------------------------------
# TAB B: DEPOT-VERWALTUNG (MOBILE-OPTIMIERTES FORMULAR)
# ---------------------------------------------------------
with tab_b:
    st.header("Aktueller Depot-Status & Verwaltung")

    with st.expander("➕ Position hinzufügen oder anpassen", expanded=True):
        all_tickers = df_universe["Ticker"].tolist() + ["Manuell eintragen"]
        select_tick = st.selectbox("Aktie auswählen:", all_tickers)

        if select_tick != "Manuell eintragen":
            match = df_universe[df_universe["Ticker"] == select_tick].iloc[0]
            default_ticker = match["Ticker"]
            default_name = match["Name"]
            default_sector = match["Sector"] if "Sector" in match else "Financial Services"
            default_price = float(match["Current_Price"])
        else:
            default_ticker = ""
            default_name = ""
            default_sector = "Financial Services"
            default_price = 0.0

        form_ticker = st.text_input("Ticker Symbol:", value=default_ticker)
        form_name = st.text_input("Name der Aktie:", value=default_name)

        sectors_list = [
            "Financial Services",
            "Technology",
            "Healthcare",
            "Industrials",
            "Consumer Discretionary",
            "Energy",
            "Sonstige",
        ]
        sector_idx = (
            sectors_list.index(default_sector)
            if default_sector in sectors_list
            else 0
        )
        form_sector = st.selectbox(
            "Sektor:", sectors_list, index=sector_idx
        )

        form_shares = st.number_input(
            "Stückzahl:", min_value=0.0, value=10.0, step=1.0
        )
        form_price = st.number_input(
            "Kaufpreis / Kurs (€):", min_value=0.0, value=default_price, step=1.0
        )

        if st.button("💾 Position im Depot speichern"):
            if form_ticker.strip() != "":
                st.session_state.portfolio_list = [
                    p
                    for p in st.session_state.portfolio_list
                    if p["Ticker"] != form_ticker.strip()
                ]
                st.session_state.portfolio_list.append(
                    {
                        "Ticker": form_ticker.strip(),
                        "Name": form_name.strip(),
                        "Sector": form_sector,
                        "Shares": float(form_shares),
                        "Price_EUR": float(form_price),
                    }
                )
                st.success(f"Position {form_ticker} gespeichert!")
                st.rerun()

    st.subheader("Bestehende Positionen")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🗑️ Depot komplett leeren"):
            st.session_state.portfolio_list = []
            st.rerun()
    with col_b2:
        if st.button("🔄 Standard-Depot laden"):
            st.session_state.portfolio_list = (
                get_initial_portfolio().to_dict("records")
            )
            st.rerun()

    if len(st.session_state.portfolio_list) > 0:
        df_portfolio = pd.DataFrame(st.session_state.portfolio_list)
        df_portfolio["Position_Value"] = (
            df_portfolio["Shares"] * df_portfolio["Price_EUR"]
        )
        total_stock_value = df_portfolio["Position_Value"].sum()

        for idx, item in enumerate(st.session_state.portfolio_list):
            pos_val = item["Shares"] * item["Price_EUR"]
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(
                    f"**{item['Ticker']}** ({item['Name']}) - *{item['Sector']}*  \n{item['Shares']:.0f} Stk. × {item['Price_EUR']:.2f} € = **{pos_val:,.2f} €**"
                )
            with c2:
                if st.button("🗑️", key=f"del_{item['Ticker']}_{idx}"):
                    st.session_state.portfolio_list.pop(idx)
                    st.rerun()
            st.divider()
    else:
        df_portfolio = pd.DataFrame(
            columns=[
                "Ticker",
                "Name",
                "Sector",
                "Shares",
                "Price_EUR",
                "Position_Value",
            ]
        )
        total_stock_value = 0.0

    total_portfolio_value = total_stock_value + cash_balance

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Gesamtdepotwert", f"{total_portfolio_value:,.2f} €")
    m2.metric("Aktienwert", f"{total_stock_value:,.2f} €")
    m3.metric(
        "Aktienquote",
        f"{(total_stock_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0:.1f} %",
    )

# ---------------------------------------------------------
# TAB C: KAUF-SIMULATION & TRANCHEN-STEUERUNG
# ---------------------------------------------------------
with tab_c:
    st.header("Depot-Integration & Kaufgrößen-Prüfung")

    sim_ticker = st.selectbox(
        "Zu simulierende Aktie:",
        df_universe["Ticker"].tolist(),
        key="sim_select",
    )
    sim_amount = st.number_input(
        "Geplante Kaufsumme (€):", value=1000.0, step=250.0
    )

    sim_data = df_universe[df_universe["Ticker"] == sim_ticker].iloc[
        0
    ].to_dict()

    if not df_portfolio.empty:
        existing_pos_val = df_portfolio[df_portfolio["Ticker"] == sim_ticker][
            "Position_Value"
        ].sum()
        existing_sector_val = df_portfolio[
            df_portfolio["Sector"] == sim_data["Sector"]
        ]["Position_Value"].sum()
    else:
        existing_pos_val = 0.0
        existing_sector_val = 0.0

    new_total_portfolio = total_portfolio_value + sim_amount
    new_total_stock = total_stock_value + sim_amount
    new_pos_val = existing_pos_val + sim_amount
    new_sector_val = existing_sector_val + sim_amount

    quote_before = (
        (total_stock_value / total_portfolio_value * 100)
        if total_portfolio_value > 0
        else 0
    )
    quote_after = (
        (new_total_stock / new_total_portfolio * 100)
        if new_total_portfolio > 0
        else 0
    )
    new_pos_weight = (
        (new_pos_val / new_total_portfolio * 100)
        if new_total_portfolio > 0
        else 0
    )

    sector_share_in_stocks = (
        (new_sector_val / new_total_stock * 100) if new_total_stock > 0 else 0
    )

    # 3-Stufige Depot-Logik
    if sector_share_in_stocks > 80.0 and total_stock_value > 0:
        tranche_status = "🔴 WARTEN"
        drossel_headline = "🔴 WARTEN – SEKTORBEREICH BEREITS ÜBERWIEGEND DOMINIERT"
        drossel_reason = f"Der Sektor `{sim_data['Sector']}` macht **{sector_share_in_stocks:.1f} %** deines Aktiendepots aus. Vorrang sollte der Aufbau anderer Sektoren haben."
        max_recommended_buy = 0.0
    elif sector_share_in_stocks >= 50.0 and total_stock_value > 0:
        tranche_status = "🟠 GEDROSSELT"
        drossel_headline = (
            "🟠 KAUF MÖGLICH – GEDROSSELTE ERST-TRANCHE (MAX. 1.000 €)"
        )
        drossel_reason = f"Fundamental attraktiv, aber Sektor `{sim_data['Sector']}` stellt bereits **{sector_share_in_stocks:.1f} %** des Aktienanteils."
        max_recommended_buy = min(1000.0, sim_amount)
    else:
        tranche_status = "🟢 NORMAL"
        drossel_headline = "🟢 NORMAL KAUFEN – DIREKTES SETUP OPTIMAL"
        drossel_reason = f"Sektor `{sim_data['Sector']}` ist im Aktiendepot ausgeglichen gewichtet."
        max_recommended_buy = sim_amount

    st.divider()
    st.markdown(
        f"### Simulation: Kauf von **{sim_amount:,.2f} €** in `{sim_data['Ticker']}`"
    )

    s1, s2, s3, s4 = st.columns(4)
    s1.metric(
        "Aktienquote",
        f"{quote_before:.1f} % ➔ {quote_after:.1f} %",
        delta=f"Ziel-Max: {target_stock_quote_max}%",
    )
    s2.metric(
        "Positionsgewicht",
        f"{new_pos_weight:.1f} %",
        delta=f"Max: {limit_pct_input}%",
    )
    s3.metric(
        "Sektor im Aktiendepot",
        f"{sector_share_in_stocks:.1f} %",
        delta="Schwelle: 50 %",
        delta_color="inverse"
        if sector_share_in_stocks >= 50
        else "normal",
    )
    s4.metric(
        "Empfehlung",
        tranche_status,
        delta=f"Max: {max_recommended_buy:,.0f} €",
    )

    if sector_share_in_stocks > 80.0 and total_stock_value > 0:
        st.error(f"### {drossel_headline}\nℹ️ {drossel_reason}")
    elif sector_share_in_stocks >= 50.0 and total_stock_value > 0:
        st.warning(f"### {drossel_headline}\nℹ️ {drossel_reason}")
    else:
        st.success(f"### {drossel_headline}\nℹ️ {drossel_reason}")

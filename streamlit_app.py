import streamlit as st
import pandas as pd
import numpy as np

# =========================================================
# PAGE CONFIG & TITLE
# =========================================================
st.set_page_config(page_title="Portfolio & Valuation Engine", layout="wide")
st.title("📈 Stock Valuation & Portfolio Capacity Engine")

# =========================================================
# INITIAL DATASETS
# =========================================================
def get_initial_portfolio():
    return [
        {"Ticker": "AAPL", "Name": "Apple Inc.", "Sector": "Technology", "Shares": 15.0, "Price_EUR": 210.00},
        {"Ticker": "MSFT", "Name": "Microsoft Corp.", "Sector": "Technology", "Shares": 8.0, "Price_EUR": 415.00},
        {"Ticker": "ALV.DE", "Name": "Allianz SE", "Sector": "Financial Services", "Shares": 20.0, "Price_EUR": 260.00},
        {"Ticker": "NOVN.SW", "Name": "Novartis AG", "Sector": "Healthcare", "Shares": 30.0, "Price_EUR": 92.00},
    ]

@st.cache_data
def load_mock_universe():
    return pd.DataFrame([
        {
            "Ticker": "AXA", "Name": "AXA SA", "Sector": "Financial Services", 
            "Quality_Score": 89, "Fair_Value": 62.15, "Current_Price": 43.72, 
            "PER": 11.8, "Beta": 0.59, "Plausibility_Status": "🟢 Robust"
        },
        {
            "Ticker": "NVDA", "Name": "NVIDIA Corp.", "Sector": "Technology", 
            "Quality_Score": 92, "Fair_Value": 110.00, "Current_Price": 125.00, 
            "PER": 45.2, "Beta": 1.68, "Plausibility_Status": "🟡 KGV Hoch"
        },
        {
            "Ticker": "SAP.DE", "Name": "SAP SE", "Sector": "Technology", 
            "Quality_Score": 85, "Fair_Value": 190.00, "Current_Price": 195.00, 
            "PER": 32.0, "Beta": 0.95, "Plausibility_Status": "🟢 Robust"
        },
        {
            "Ticker": "AAPL", "Name": "Apple Inc.", "Sector": "Technology", 
            "Quality_Score": 90, "Fair_Value": 220.00, "Current_Price": 210.00, 
            "PER": 30.0, "Beta": 1.05, "Plausibility_Status": "🟢 Robust"
        },
        {
            "Ticker": "MSFT", "Name": "Microsoft Corp.", "Sector": "Technology", 
            "Quality_Score": 94, "Fair_Value": 430.00, "Current_Price": 415.00, 
            "PER": 34.0, "Beta": 0.90, "Plausibility_Status": "🟢 Robust"
        }
    ])

# Portfolio im Session State halten
if "portfolio_list" not in st.session_state:
    st.session_state.portfolio_list = get_initial_portfolio()

df_universe = load_mock_universe()

# =========================================================
# SIDEBAR CONFIGURATION
# =========================================================
st.sidebar.header("⚙️ Depot-Parameter")

cash_balance = st.sidebar.number_input("Cash-Bestand (€)", value=25000.0, step=1000.0)
target_stock_quote_max = st.sidebar.slider("Max. Ziel-Aktienquote (%)", 10.0, 100.0, 50.0)
limit_pct_input = st.sidebar.slider("Max. Einzelposition (% vom Depot)", 1.0, 20.0, 5.0)
sector_limit_pct_input = st.sidebar.slider("Max. Sektor-Limit (% vom Gesamtdepot)", 5.0, 50.0, 25.0)

# =========================================================
# NAVIGATION TABS
# =========================================================
tab_a, tab_b, tab_c = st.tabs(["🔍 Tab A: Aktien-Analyse", "📊 Tab B: Depot-Verwaltung", "🎯 Tab C: Kauf-Simulation & Tranchen"])

# ---------------------------------------------------------
# TAB A: AKTIEN-ANALYSE
# ---------------------------------------------------------
with tab_a:
    st.header("Einzelaktien-Bewertung")
    selected_ticker = st.selectbox("Aktie zur Analyse auswählen:", df_universe["Ticker"].tolist())
    
    stock_data = df_universe[df_universe["Ticker"] == selected_ticker].iloc[0]
    mos = ((stock_data["Fair_Value"] - stock_data["Current_Price"]) / stock_data["Current_Price"]) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Quality Score", f"{stock_data['Quality_Score']} / 100")
    col2.metric("Fair Value", f"{stock_data['Fair_Value']:.2f} €")
    col3.metric("Aktueller Kurs", f"{stock_data['Current_Price']:.2f} €", delta=f"{mos:+.1f} % MOS")
    col4.metric("KGV / Beta", f"{stock_data['PER']} | {stock_data['Beta']}")
    
    st.info(f"**Modell-Status:** {stock_data['Plausibility_Status']}")

# ---------------------------------------------------------
# TAB B: DEPOT-VERWALTUNG (FEHLERFREIES SPEICHERN)
# ---------------------------------------------------------
with tab_b:
    st.header("Aktueller Depot-Status & Verwaltung")
    
    # --- FORMULAR ZUM HINZUFÜGEN / BEARBEITEN ---
    with st.expander("➕ Position hinzufügen oder anpassen", expanded=True):
        all_tickers = df_universe["Ticker"].tolist() + ["Manuell eintragen"]
        select_tick = st.selectbox("Aktie auswählen:", all_tickers)
        
        if select_tick != "Manuell eintragen":
            match = df_universe[df_universe["Ticker"] == select_tick].iloc[0]
            default_ticker = match["Ticker"]
            default_name = match["Name"]
            default_sector = match["Sector"]
            default_price = float(match["Current_Price"])
        else:
            default_ticker = ""
            default_name = ""
            default_sector = "Technology"
            default_price = 0.0

        form_ticker = st.text_input("Ticker Symbol:", value=default_ticker)
        form_name = st.text_input("Name der Aktie:", value=default_name)
        
        sectors_list = sorted(list(set(df_universe["Sector"].tolist() + [
            "Technology", "Financial Services", "Healthcare", "Industrials", 
            "Consumer Discretionary", "Energy", "Sonstige"
        ])))
        sector_idx = sectors_list.index(default_sector) if default_sector in sectors_list else 0
        form_sector = st.selectbox("Sektor:", sectors_list, index=sector_idx)
        
        form_shares = st.number_input("Stückzahl:", min_value=0.0, value=10.0, step=1.0)
        form_price = st.number_input("Kaufpreis / Kurs (€):", min_value=0.0, value=default_price, step=1.0)

        if st.button("💾 Position im Depot speichern"):
            if form_ticker.strip() != "":
                clean_ticker = form_ticker.strip().upper()
                
                # 1. Entferne vorherige Version der Aktie (falls bereits in der Liste), um Duplikate zu vermeiden
                st.session_state.portfolio_list = [
                    p for p in st.session_state.portfolio_list 
                    if p["Ticker"].upper() != clean_ticker
                ]
                
                # 2. Hänge die neue Aktie an die bestehende Liste an
                st.session_state.portfolio_list.append({
                    "Ticker": clean_ticker,
                    "Name": form_name.strip(),
                    "Sector": form_sector,
                    "Shares": float(form_shares),
                    "Price_EUR": float(form_price)
                })
                
                st.success(f"Position {clean_ticker} erfolgreich gespeichert!")
                st.rerun()

    # --- LISTE DER BESTEHENDEN POSITIONEN ---
    st.subheader("Bestehende Positionen")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🗑️ Depot komplett leeren"):
            st.session_state.portfolio_list = []
            st.rerun()
    with col_b2:
        if st.button("🔄 Standard-Depot laden"):
            st.session_state.portfolio_list = get_initial_portfolio()
            st.rerun()

    # Berechnungen der Einzelwerte und Gesamtsummen
    if len(st.session_state.portfolio_list) > 0:
        df_portfolio = pd.DataFrame(st.session_state.portfolio_list)
        df_portfolio["Position_Value"] = df_portfolio["Shares"] * df_portfolio["Price_EUR"]
        total_stock_value = df_portfolio["Position_Value"].sum()

        # Liste der Positionen rendern
        for idx, item in enumerate(st.session_state.portfolio_list):
            pos_val = item["Shares"] * item["Price_EUR"]
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(
                    f"**{item['Ticker']}** ({item['Name']}) - *{item['Sector']}*  \n"
                    f"{item['Shares']:.0f} Stk. × {item['Price_EUR']:.2f} € = **{pos_val:,.2f} €**"
                )
            with c2:
                if st.button("🗑️", key=f"del_{item['Ticker']}_{idx}"):
                    st.session_state.portfolio_list.pop(idx)
                    st.rerun()
            st.divider()
    else:
        df_portfolio = pd.DataFrame(columns=["Ticker", "Name", "Sector", "Shares", "Price_EUR", "Position_Value"])
        total_stock_value = 0.0

    # Gesamtdepotwert = Summe aller Aktienwerte + Cash aus Sidebar
    total_portfolio_value = total_stock_value + cash_balance

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Gesamtdepotwert", f"{total_portfolio_value:,.2f} €")
    m2.metric("Aktienwert", f"{total_stock_value:,.2f} €")
    m3.metric("Aktienquote", f"{(total_stock_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0:.1f} %")

# ---------------------------------------------------------
# TAB C: KAUF-SIMULATION & TRANCHEN-STEUERUNG
# ---------------------------------------------------------
with tab_c:
    st.header("Depot-Integration & Kaufgrößen-Prüfung")
    
    sim_ticker = st.selectbox("Zu simulierende Aktie:", df_universe["Ticker"].tolist(), key="sim_select")
    sim_amount = st.number_input("Geplante Kaufsumme (€):", value=1000.0, step=250.0)
    
    sim_data = df_universe[df_universe["Ticker"] == sim_ticker].iloc[0].to_dict()
    sim_data["raw_mos"] = ((sim_data["Fair_Value"] - sim_data["Current_Price"]) / sim_data["Current_Price"]) * 100
    
    if not df_portfolio.empty:
        existing_pos_val = df_portfolio[df_portfolio["Ticker"] == sim_ticker]["Position_Value"].sum()
        existing_sector_val = df_portfolio[df_portfolio["Sector"] == sim_data["Sector"]]["Position_Value"].sum()
    else:
        existing_pos_val = 0.0
        existing_sector_val = 0.0

    new_total_portfolio = total_portfolio_value + sim_amount
    new_total_stock = total_stock_value + sim_amount
    new_pos_val = existing_pos_val + sim_amount
    new_sector_val = existing_sector_val + sim_amount
    
    quote_before = (total_stock_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
    quote_after = (new_total_stock / new_total_portfolio * 100) if new_total_portfolio > 0 else 0
    new_pos_weight = (new_pos_val / new_total_portfolio * 100) if new_total_portfolio > 0 else 0
    sector_share_equities_after = (new_sector_val / new_total_stock * 100) if new_total_stock > 0 else 0
    
    max_pos_eur = total_portfolio_value * (limit_pct_input / 100.0)
    max_sector_eur = total_portfolio_value * (sector_limit_pct_input / 100.0)
    max_target_eur = total_portfolio_value * (target_stock_quote_max / 100.0)
    
    hard_limit_ok = (
        new_pos_val <= max_pos_eur and 
        new_sector_val <= max_sector_eur and 
        new_total_stock <= max_target_eur
    )

    raw_hard_limit_space = max(0.0, min(
        max_pos_eur - existing_pos_val,
        max_sector_eur - existing_sector_val,
        max_target_eur - total_stock_value
    ))

    sec_share = sector_share_equities_after

    if sec_share > 50.0:
        max_recommended_buy = 0.0
        is_drossel_active = True
        tranche_status = "🔴 SEKTOR-SPERRE"
        drossel_headline = "🔴 SEKTOR-SPERRE"
        drossel_reason = f"Sektor `{sim_data['Sector']}` macht **{sec_share:.1f} %** deines Aktienportfolios aus (> 50 %)."
    elif sec_share >= 40.0:
        max_recommended_buy = min(1000.0, raw_hard_limit_space)
        is_drossel_active = True
        tranche_status = "🟠 GEDROSSELTE TRANCHE"
        drossel_headline = f"🟠 KAUF MÖGLICH – GEDROSSELTE ERST-TRANCHE (MAX. {max_recommended_buy:,.0f} €)"
        drossel_reason = f"Sektor `{sim_data['Sector']}` stellt **{sec_share:.1f} %** deines Aktienportfolios."
    elif sec_share >= 30.0:
        max_recommended_buy = min(1500.0, raw_hard_limit_space)
        is_drossel_active = True
        tranche_status = "🟡 ERST-TRANCHE"
        drossel_headline = "🟡 KAUF MÖGLICH – ERST-TRANCHE BEACHTEN"
        drossel_reason = f"Sektor `{sim_data['Sector']}` erreicht **{sec_share:.1f} %** des Aktienportfolios."
    else:
        max_recommended_buy = raw_hard_limit_space
        is_drossel_active = False
        tranche_status = "🟢 UNBESCHRÄNKT"
        drossel_headline = "🟢 NORMAL KAUFEN"
        drossel_reason = f"Sektor `{sim_data['Sector']}` ist mit **{sec_share:.1f} %** optimal diversifiziert."

    st.divider()
    st.markdown(f"### Simulation: Kauf von **{sim_amount:,.2f} €** in `{sim_data['Ticker']}` ({sim_data['Name']})")
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Aktienquote", f"{quote_before:.1f} % ➔ {quote_after:.1f} %", delta=f"Ziel-Max: {target_stock_quote_max}%")
    s2.metric("Positionsgewicht", f"{new_pos_weight:.1f} %", delta=f"Max: {limit_pct_input:.1f}%")
    s3.metric("Sektoranteil", f"{sec_share:.1f} %", delta="Schwelle: 40 %", delta_color="inverse" if sec_share >= 40 else "normal")
    s4.metric("Max. Erst-Tranche", f"{max_recommended_buy:,.0f} €", delta=tranche_status, delta_color="inverse" if is_drossel_active else "normal")

    if not hard_limit_ok or sim_amount > (max_recommended_buy + 0.01):
        st.error(f"### 🔴 KAUFVOLUMEN BLOCKIERT\nℹ️ Max. erlaubte Erst-Tranche: **{max_recommended_buy:,.2f} €**")
    elif is_drossel_active:
        st.warning(f"### {drossel_headline}\nℹ️ {drossel_reason}")
    else:
        st.success(f"### {drossel_headline}\nℹ️ Alle Kennzahlen grün.")

import streamlit as st
import pandas as pd
import numpy as np

# =========================================================
# PAGE CONFIG & TITLE
# =========================================================
st.set_page_config(page_title="Portfolio & Valuation Engine", layout="wide")
st.title("📈 Stock Valuation & Portfolio Capacity Engine")

# =========================================================
# MOCK DATASETS & HELPERS
# =========================================================
@st.cache_data
def load_mock_portfolio():
    return pd.DataFrame([
        {"Ticker": "AAPL", "Name": "Apple Inc.", "Sector": "Technology", "Shares": 15, "Price_EUR": 210.00},
        {"Ticker": "MSFT", "Name": "Microsoft Corp.", "Sector": "Technology", "Shares": 8, "Price_EUR": 415.00},
        {"Ticker": "ALV.DE", "Name": "Allianz SE", "Sector": "Financial Services", "Shares": 20, "Price_EUR": 260.00},
        {"Ticker": "NOVN.SW", "Name": "Novartis AG", "Sector": "Healthcare", "Shares": 30, "Price_EUR": 92.00},
    ])

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
        }
    ])

df_portfolio = load_mock_portfolio()
df_universe = load_mock_universe()

# Calculate Portfolio Metrics
df_portfolio["Position_Value"] = df_portfolio["Shares"] * df_portfolio["Price_EUR"]
total_stock_value = df_portfolio["Position_Value"].sum()

# =========================================================
# SIDEBAR CONFIGURATION
# =========================================================
st.sidebar.header("⚙️ Depot-Parameter")

cash_balance = st.sidebar.number_input("Cash-Bestand (€)", value=25000.0, step=1000.0)
target_stock_quote_max = st.sidebar.slider("Max. Ziel-Aktienquote (%)", 10.0, 100.0, 50.0)
limit_pct_input = st.sidebar.slider("Max. Einzelposition (% vom Depot)", 1.0, 20.0, 5.0)
sector_limit_pct_input = st.sidebar.slider("Max. Sektor-Limit (% vom Depot)", 5.0, 50.0, 25.0)

total_portfolio_value = total_stock_value + cash_balance

# =========================================================
# NAVIGATION TABS
# =========================================================
tab_a, tab_b, tab_c = st.tabs(["🔍 Tab A: Aktien-Analyse", "📊 Tab B: Depot-Übersicht", "🎯 Tab C: Kauf-Simulation & Tranchen"])

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
# TAB B: DEPOT-ÜBERSICHT
# ---------------------------------------------------------
with tab_b:
    st.header("Aktueller Depot-Status")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Gesamtdepotwert", f"{total_portfolio_value:,.2f} €")
    m2.metric("Aktienwert", f"{total_stock_value:,.2f} €")
    m3.metric("Aktienquote", f"{(total_stock_value / total_portfolio_value) * 100:.1f} %")
    
    st.subheader("Bestehende Positionen")
    st.dataframe(df_portfolio[["Ticker", "Name", "Sector", "Shares", "Price_EUR", "Position_Value"]], use_container_width=True)

# ---------------------------------------------------------
# TAB C: KAUF-SIMULATION & TRANCHEN-STEUERUNG
# ---------------------------------------------------------
with tab_c:
    st.header("Depot-Integration & Kaufgrößen-Prüfung")
    
    sim_ticker = st.selectbox("Zu simulierende Aktie:", df_universe["Ticker"].tolist(), key="sim_select")
    sim_amount = st.number_input("Geplante Kaufsumme (€):", value=1000.0, step=250.0)
    
    sim_data = df_universe[df_universe["Ticker"] == sim_ticker].iloc[0].to_dict()
    sim_data["raw_mos"] = ((sim_data["Fair_Value"] - sim_data["Current_Price"]) / sim_data["Current_Price"]) * 100
    
    # Existing allocations
    existing_pos_val = df_portfolio[df_portfolio["Ticker"] == sim_ticker]["Position_Value"].sum()
    existing_sector_val = df_portfolio[df_portfolio["Sector"] == sim_data["Sector"]]["Position_Value"].sum()
    
    # After simulation
    new_total_portfolio = total_portfolio_value + sim_amount
    new_total_stock = total_stock_value + sim_amount
    new_pos_val = existing_pos_val + sim_amount
    new_sector_val = existing_sector_val + sim_amount
    
    quote_before = (total_stock_value / total_portfolio_value) * 100
    quote_after = (new_total_stock / new_total_portfolio) * 100
    new_pos_weight = (new_pos_val / new_total_portfolio) * 100
    sector_weight_before = (existing_sector_val / total_portfolio_value) * 100
    new_sector_weight = (new_sector_val / new_total_portfolio) * 100
    
    # Core metric: Sector weight within equities only
    sector_share_equities_after = (new_sector_val / new_total_stock) * 100
    
    # Limits calculations (EUR)
    max_pos_eur = total_portfolio_value * (limit_pct_input / 100.0)
    max_sector_eur = total_portfolio_value * (sector_limit_pct_input / 100.0)
    max_target_eur = total_portfolio_value * (target_stock_quote_max / 100.0)
    
    hard_limit_ok = (
        new_pos_val <= max_pos_eur and 
        new_sector_val <= max_sector_eur and 
        new_total_stock <= max_target_eur
    )

    # =========================================================
    # DROSSEL-, TRANCHEN- UND KONZENTRATIONSLOGIK
    # =========================================================
    STANDARD_TRANCHE_EUR = 1000.0
    SOFT_CONCENTRATION_WARN = 40.0  # Ab 40% Aktienanteil reduzierte Tranche
    SOFT_CONCENTRATION_STOP = 75.0  # Ab 75% Aktienanteil Drossel / Folgekauf-Stopp

    raw_hard_limit_space = min(
        max_pos_eur - existing_pos_val,
        max_sector_eur - existing_sector_val,
        max_target_eur - total_stock_value
    )
    raw_hard_limit_space = max(0.0, raw_hard_limit_space)

    # Differenzierte Tranchen-Bewertung
    if sector_share_equities_after > SOFT_CONCENTRATION_STOP:
        max_recommended_buy = min(STANDARD_TRANCHE_EUR, raw_hard_limit_space)
        is_drossel_active = True
        
        if sim_amount > max_recommended_buy:
            tranche_status = "🔴 VOLUMEN ZU HOCH"
            drossel_reason = f"Geplanter Kauf ({sim_amount:,.0f} €) übersteigt die maximal erlaubte Erst-Tranche von {max_recommended_buy:,.0f} €. Sektor `{sim_data['Sector']}` dominiert das Aktienportfolio ({sector_share_equities_after:.1f} %)."
        else:
            tranche_status = "🟠 ERST-TRANCHE FREIGEGEBEN"
            drossel_reason = f"Erlaubt ist **ausschließlich eine Erst-Tranche von max. {max_recommended_buy:,.0f} €**. Weitere Nachkäufe in `{sim_data['Sector']}` sind blockiert, bis andere Sektoren ausgebaut wurden."

    elif sector_share_equities_after > SOFT_CONCENTRATION_WARN:
        max_recommended_buy = min(1500.0, raw_hard_limit_space)
        is_drossel_active = True
        tranche_status = "🟡 GEDROSSELTE TRANCHE"
        drossel_reason = f"Sektor-Konzentration erhöht ({sector_share_equities_after:.1f} % des Aktienanteils). Kauf auf max. {max_recommended_buy:,.0f} € drosseln."
    else:
        max_recommended_buy = raw_hard_limit_space
        is_drossel_active = False
        tranche_status = "🟢 NORMAL"
        drossel_reason = "Gute Sektor-Diversifikation im Aktienanteil."

    # Dashboard Metrics Display
    st.divider()
    st.markdown(f"### Simulation: Kauf von **{sim_amount:,.2f} €** in `{sim_data['Ticker']}` ({sim_data['Name']})")
    st.caption(f"Sektor: **{sim_data['Sector']}**")
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Gesamte Aktienquote", f"{quote_before:.1f} % ➔ {quote_after:.1f} %", delta=f"Ziel: {target_stock_quote_max}%")
    s2.metric("Positionsgewicht", f"{new_pos_weight:.1f} %", delta=f"Max: {limit_pct_input:.1f}%")
    s3.metric("Sektor am Gesamtdepot", f"{sector_weight_before:.1f} % ➔ {new_sector_weight:.1f} %", delta=f"Max: {sector_limit_pct_input:.1f}%")
    s4.metric("Empfohlene Tranche", f"Max. {max_recommended_buy:,.0f} €", delta=tranche_status, delta_color="inverse" if is_drossel_active else "normal")

    # =========================================================
    # NEUES ENDURTEIL MIT EXPLIZITER TRANCHEN-STEUERUNG
    # =========================================================
    if not hard_limit_ok or "🔴 Daten-/Modellwarnung" in sim_data["Plausibility_Status"] or sim_data["raw_mos"] <= 0 or sim_amount > (max_recommended_buy + 0.01):
        if sim_amount > max_recommended_buy and hard_limit_ok and sim_data["raw_mos"] > 0:
            st.error(f"### 🔴 KAUFVOLUMEN BLOCKIERT\nℹ️ **Tranchen-Limit überschritten:** Geplante Summe ({sim_amount:,.2f} €) liegt über dem Sektor-Cap.  \n👉 **Maximal zulässig:** **{max_recommended_buy:,.2f} €** als Erst-Tranche.")
        else:
            st.error("### 🔴 KEIN KAUF / WARTEN\nℹ️ **Grund:** Hard Limit gerissen, Qualität unzureichend (<50) oder Bewertung ohne Puffer.")
    
    elif is_drossel_active:
        st.warning(f"### 🟠 KAUF MÖGLICH – NUR ERST-TRANCHE (MAX. {max_recommended_buy:,.0f} €)\nℹ️ **Kapital-Disziplin:** Aktie ist fundamental stark, aber `{sim_data['Sector']}` stellt {sector_share_equities_after:.1f} % deines Aktienportfolios.  \n👉 **Handlungsanweisung:** 1.000 € Erst-Tranche möglich. **Weitere Nachkäufe erst nach Aufbau anderer Sektoren.**")
    
    elif "🟡" in sim_data["Plausibility_Status"]:
        st.warning("### 🟡 KAUF MÖGLICH\nℹ️ **Hinweis:** Kauf ist möglich, leichte Modell- / Sektorhinweise beachten.")
    else:
        st.success("### 🟢 NORMAL KAUFEN\nℹ️ **Optimal:** Alle Kennzahlen grün, hervorragende Depot-Integration und saubere Streuung.")

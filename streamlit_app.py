import streamlit as st
import pandas as pd
import numpy as np

# =========================================================
# PAGE CONFIG & TITLE
# =========================================================
st.set_page_config(page_title="Portfolio & Valuation Engine", layout="wide")
st.title("📈 Stock Valuation & Portfolio Capacity Engine")

# =========================================================
# INITIAL MOCK DATASETS
# =========================================================
def get_initial_portfolio():
    return pd.DataFrame([
        {"Ticker": "AAPL", "Name": "Apple Inc.", "Sector": "Technology", "Shares": 15.0, "Price_EUR": 210.00},
        {"Ticker": "MSFT", "Name": "Microsoft Corp.", "Sector": "Technology", "Shares": 8.0, "Price_EUR": 415.00},
        {"Ticker": "ALV.DE", "Name": "Allianz SE", "Sector": "Financial Services", "Shares": 20.0, "Price_EUR": 260.00},
        {"Ticker": "NOVN.SW", "Name": "Novartis AG", "Sector": "Healthcare", "Shares": 30.0, "Price_EUR": 92.00},
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

# Session State für interaktives Portfolio initialisieren
if "portfolio_data" not in st.session_state:
    st.session_state.portfolio_data = get_initial_portfolio()

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
# TAB B: DEPOT-VERWALTUNG (INTERAKTIVER EDITOR)
# ---------------------------------------------------------
with tab_b:
    st.header("Aktueller Depot-Status & Verwaltung")
    st.caption("Füge neue Aktien hinzu, ändere Stückzahlen/Kurse oder lösche verkaufte Positionen direkt in der Tabelle.")
    
    # Interaktiver Data Editor
    edited_df = st.data_editor(
        st.session_state.portfolio_data,
        num_rows="dynamic",
        use_container_width=True,
        key="portfolio_editor",
        column_config={
            "Shares": st.column_config.NumberColumn("Stückzahl", min_value=0, step=1),
            "Price_EUR": st.column_config.NumberColumn("Kurs (€)", min_value=0.0, format="%.2f €"),
        }
    )

    # Aktualisierte Daten im Session State speichern
    st.session_state.portfolio_data = edited_df

    # Live-Berechnung des Aktienwerts
    df_portfolio = edited_df.copy()
    if not df_portfolio.empty and "Shares" in df_portfolio.columns and "Price_EUR" in df_portfolio.columns:
        df_portfolio["Position_Value"] = df_portfolio["Shares"].fillna(0) * df_portfolio["Price_EUR"].fillna(0)
        total_stock_value = df_portfolio["Position_Value"].sum()
    else:
        df_portfolio["Position_Value"] = 0.0
        total_stock_value = 0.0

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
    
    # Bereits existierende Allokationen ermitteln
    if not df_portfolio.empty and "Ticker" in df_portfolio.columns and "Sector" in df_portfolio.columns:
        existing_pos_val = df_portfolio[df_portfolio["Ticker"] == sim_ticker]["Position_Value"].sum()
        existing_sector_val = df_portfolio[df_portfolio["Sector"] == sim_data["Sector"]]["Position_Value"].sum()
    else:
        existing_pos_val = 0.0
        existing_sector_val = 0.0

    # Werte nach der Simulation
    new_total_portfolio = total_portfolio_value + sim_amount
    new_total_stock = total_stock_value + sim_amount
    new_pos_val = existing_pos_val + sim_amount
    new_sector_val = existing_sector_val + sim_amount
    
    quote_before = (total_stock_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
    quote_after = (new_total_stock / new_total_portfolio * 100) if new_total_portfolio > 0 else 0
    new_pos_weight = (new_pos_val / new_total_portfolio * 100) if new_total_portfolio > 0 else 0
    sector_weight_before = (existing_sector_val / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
    new_sector_weight = (new_sector_val / new_total_portfolio * 100) if new_total_portfolio > 0 else 0
    
    # Sektor-Anteil nur am Aktienportfolio
    sector_share_equities_after = (new_sector_val / new_total_stock * 100) if new_total_stock > 0 else 0
    
    # Hard Limits (in EUR)
    max_pos_eur = total_portfolio_value * (limit_pct_input / 100.0)
    max_sector_eur = total_portfolio_value * (sector_limit_pct_input / 100.0)
    max_target_eur = total_portfolio_value * (target_stock_quote_max / 100.0)
    
    hard_limit_ok = (
        new_pos_val <= max_pos_eur and 
        new_sector_val <= max_sector_eur and 
        new_total_stock <= max_target_eur
    )

    # =========================================================
    # 4-STUFEN KONZENTRATIONSLOGIK (AKTIENPORTFOLIO)
    # =========================================================
    raw_hard_limit_space = min(
        max_pos_eur - existing_pos_val,
        max_sector_eur - existing_sector_val,
        max_target_eur - total_stock_value
    )
    raw_hard_limit_space = max(0.0, raw_hard_limit_space)

    sec_share = sector_share_equities_after

    if sec_share > 50.0:
        # STUFE 4: > 50% -> STRATEGISCHE SEKTOR-SPERRE
        max_recommended_buy = 0.0
        is_drossel_active = True
        tranche_status = "🔴 SEKTOR-SPERRE"
        drossel_headline = "🔴 SEKTOR-SPERRE"
        drossel_reason = (
            f"Sektor `{sim_data['Sector']}` macht **{sec_share:.1f} %** deines Aktienportfolios aus (> 50 %-Schwelle). "
            f"Weitere Nachkäufe sind vollständig blockiert, bis andere Sektoren ausgebaut wurden."
        )

    elif sec_share >= 40.0:
        # STUFE 3: 40 - 50% -> GEDROSSELTE ERST-TRANCHE
        max_recommended_buy = min(1000.0, raw_hard_limit_space)
        is_drossel_active = True
        tranche_status = "🟠 GEDROSSELTE TRANCHE"
        drossel_headline = f"🟠 KAUF MÖGLICH – GEDROSSELTE ERST-TRANCHE (MAX. {max_recommended_buy:,.0f} €)"
        drossel_reason = (
            f"Sektor `{sim_data['Sector']}` stellt **{sec_share:.1f} %** deines Aktienportfolios (Schwelle: 40–50 %). "
            f"Ein Einstieg ist nur als **gedrosselte Erst-Tranche (max. {max_recommended_buy:,.0f} €)** gestattet. "
            f"Folgekäufe erst nach Diversifikation."
        )

    elif sec_share >= 30.0:
        # STUFE 2: 30 - 40% -> NORMALE ERST-TRANCHE
        max_recommended_buy = min(1500.0, raw_hard_limit_space)
        is_drossel_active = True
        tranche_status = "🟡 ERST-TRANCHE"
        drossel_headline = "🟡 KAUF MÖGLICH – ERST-TRANCHE BEACHTEN"
        drossel_reason = (
            f"Sektor `{sim_data['Sector']}` erreicht **{sec_share:.1f} %** des Aktienportfolios (Schwelle: 30–40 %). "
            f"Empfohlene Erst-Tranche: max. {max_recommended_buy:,.0f} €."
        )

    else:
        # STUFE 1: < 30% -> NORMALER KAUF
        max_recommended_buy = raw_hard_limit_space
        is_drossel_active = False
        tranche_status = "🟢 UNBESCHRÄNKT"
        drossel_headline = "🟢 NORMAL KAUFEN"
        drossel_reason = f"Sektor `{sim_data['Sector']}` ist mit **{sec_share:.1f} %** am Aktienportfolio optimal diversifiziert (< 30 %)."

    # =========================================================
    # UI METRICS DISPLAY
    # =========================================================
    st.divider()
    st.markdown(f"### Simulation: Kauf von **{sim_amount:,.2f} €** in `{sim_data['Ticker']}` ({sim_data['Name']})")
    st.caption(f"Sektor: **{sim_data['Sector']}**")
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Gesamte Aktienquote", f"{quote_before:.1f} % ➔ {quote_after:.1f} %", delta=f"Ziel-Max: {target_stock_quote_max}%")
    s2.metric("Positionsgewicht (Depot)", f"{new_pos_weight:.1f} %", delta=f"Max: {limit_pct_input:.1f}%")
    s3.metric("Sektor am Aktienanteil", f"{sec_share:.1f} %", delta="Schwelle: 40 %", delta_color="inverse" if sec_share >= 40 else "normal")
    s4.metric(
        "Max. Erst-Tranche", 
        f"{max_recommended_buy:,.0f} €", 
        delta=tranche_status, 
        delta_color="inverse" if is_drossel_active else "normal",
        help="Maximale Erst-Tranche unter den aktuellen Depotbedingungen zur Wahrung der Kapital-Disziplin."
    )

    # =========================================================
    # DECISION DISPLAY (ENDURTEIL)
    # =========================================================
    if not hard_limit_ok or "🔴 Daten-/Modellwarnung" in sim_data["Plausibility_Status"] or sim_data["raw_mos"] <= 0 or sim_amount > (max_recommended_buy + 0.01):
        if sim_amount > max_recommended_buy and hard_limit_ok and sim_data["raw_mos"] > 0:
            st.error(
                f"### 🔴 KAUFVOLUMEN BLOCKIERT\n"
                f"ℹ️ **Geplante Kaufsumme ({sim_amount:,.2f} €) überschreitet das Tranchen-Cap.**  \n"
                f"👉 **Max. erlaubte Erst-Tranche:** **{max_recommended_buy:,.2f} €** unter den aktuellen Sektorgewichtungen."
            )
        else:
            st.error("### 🔴 KEIN KAUF / WARTEN\nℹ️ **Grund:** Hard Limit gerissen, Qualität unzureichend (<50) oder Bewertung ohne Puffer.")
    
    elif is_drossel_active:
        st.warning(f"### {drossel_headline}\nℹ️ **Kapital-Disziplin:** {drossel_reason}")
    
    elif "🟡" in sim_data["Plausibility_Status"]:
        st.warning("### 🟡 KAUF MÖGLICH\nℹ️ **Hinweis:** Kauf ist möglich, leichte Modell- / Sektorhinweise beachten.")
    else:
        st.success(f"### {drossel_headline}\nℹ️ **Optimal:** Alle Kennzahlen grün, hervorragende Depot-Integration.")

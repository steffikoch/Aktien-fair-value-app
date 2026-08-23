import pandas as pd
import streamlit as st

# Layout auf 'centered' stellen für mobile Bildschirme
st.set_page_config(
    page_title="Stock Manager", layout="centered", initial_sidebar_state="collapsed"
)

# Kürzere Tab-Namen für kompakte Smartphone-Anzeige
tab1, tab2, tab3 = st.tabs(["📊 Depot", "🧮 DCF", "⚙️ Stop-Loss"])

# =========================================================
# TAB 1: DEPOT & KLUMPENRISIKO
# =========================================================
with tab1:
    st.subheader("Depot- & Kaufgrößen-Prüfung")

    if "portfolio_data" not in st.session_state:
        st.session_state.portfolio_data = pd.DataFrame(
            [
                {
                    "Ticker": "CS.PA",
                    "Name": "AXA SA",
                    "Sektor": "Finanzen",
                    "Wert": 1000.00,
                },
                {
                    "Ticker": "MUV2.DE",
                    "Name": "Münchener Rück",
                    "Sektor": "Finanzen",
                    "Wert": 2000.00,
                },
                {
                    "Ticker": "AAPL",
                    "Name": "Apple Inc.",
                    "Sektor": "Technologie",
                    "Wert": 4000.00,
                },
                {
                    "Ticker": "MSFT",
                    "Name": "Microsoft Corp.",
                    "Sektor": "Technologie",
                    "Wert": 3000.00,
                },
            ]
        )

    SEKTOR_MAPPING = {
        "ALV.DE": ("Allianz SE", "Finanzen"),
        "ALLIANZ": ("Allianz SE", "Finanzen"),
        "CS.PA": ("AXA SA", "Finanzen"),
        "MUV2.DE": ("Münchener Rück", "Finanzen"),
        "DTE.DE": ("Deutsche Telekom", "Telekommunikation"),
        "AAPL": ("Apple Inc.", "Technologie"),
    }

    MAX_POSITION_WEIGHT = 5.0
    MAX_SEKTOR_WEIGHT = 20.0
    TARGET_AKTIENQUOTE = 50.0

    if "sim_ticker" not in st.session_state:
        st.session_state.sim_ticker = "ALV.DE"

    # Untereinander statt nebeneinander für Smartphones
    sim_ticker_input = (
        st.text_input(
            "Aktie (Ticker):",
            value=st.session_state.sim_ticker,
            key="t1_input",
        )
        .strip()
        .upper()
    )

    buy_amount = st.number_input(
        "Kaufsumme (€):",
        value=1000.0,
        step=100.0,
        min_value=0.0,
        key="t1_amount",
    )

    # Schnellwahl-Buttons
    col_b1, col_b2, col_b3 = st.columns(3)
    if col_b1.button("🔄 Allianz"):
        st.session_state.sim_ticker = "ALV.DE"
        st.rerun()

    if col_b2.button("🍏 Apple"):
        st.session_state.sim_ticker = "AAPL"
        st.rerun()

    if col_b3.button("📞 Telekom"):
        st.session_state.sim_ticker = "DTE.DE"
        st.rerun()

    # Berechnungen
    stock_name, stock_sektor = SEKTOR_MAPPING.get(
        sim_ticker_input, (sim_ticker_input, "Sonstiges")
    )
    df_current = st.session_state.portfolio_data.copy()

    bisheriges_depot_gesamtwert = df_current["Wert"].sum()
    neues_depot_gesamtwert = bisheriges_depot_gesamtwert + buy_amount

    bisheriger_aktien_wert = df_current[
        df_current["Ticker"] == sim_ticker_input
    ]["Wert"].sum()
    neuer_aktien_wert = bisheriger_aktien_wert + buy_amount
    neues_positionsgewicht = (neuer_aktien_wert / neues_depot_gesamtwert) * 100

    bisheriger_sektor_wert = df_current[df_current["Sektor"] == stock_sektor][
        "Wert"
    ].sum()
    neuer_sektor_wert = bisheriger_sektor_wert + buy_amount
    neuer_sektor_anteil = (neuer_sektor_wert / neues_depot_gesamtwert) * 100

    st.markdown("---")
    st.markdown(
        f"**Simulation:** {buy_amount:,.0f} € in **{sim_ticker_input}** ({stock_name})"
    )

    # Kennzahlen übersichtlich untereinander/kompakt
    st.metric(
        label=f"Sektoranteil ({stock_sektor})",
        value=f"{neuer_sektor_anteil:.1f} %",
    )
    if neuer_sektor_anteil > MAX_SEKTOR_WEIGHT:
        st.error(f"🚨 KLUMPENRISIKO! Sektor-Limit ({MAX_SEKTOR_WEIGHT}%) überschritten!")

    st.metric(label="Positionsgewicht", value=f"{neues_positionsgewicht:.1f} %")
    if neues_positionsgewicht > MAX_POSITION_WEIGHT:
        st.error(f"⚠️ Max. {MAX_POSITION_WEIGHT}% erlaubt!")

    if neuer_sektor_anteil > MAX_SEKTOR_WEIGHT:
        st.error(
            f"**Sektorkonzentration:** Sektor **'{stock_sektor}'** klettert auf **{neuer_sektor_anteil:.1f}%** (Limit: {MAX_SEKTOR_WEIGHT}%)."
        )
    elif neues_positionsgewicht <= MAX_POSITION_WEIGHT:
        st.success("✅ Kauf liegt innerhalb der Risikogrenzen.")


# =========================================================
# TAB 2: DCF RECHNER
# =========================================================
with tab2:
    st.subheader("🧮 DCF Bewertung")

    fcf = st.number_input(
        "Free Cash Flow (Mio. €):", value=500.0, step=50.0, key="dcf_fcf"
    )
    growth_rate = st.slider(
        "Wachstum p.a. (%):", 0.0, 30.0, 8.0, key="dcf_growth"
    )
    discount_rate = st.slider(
        "WACC / Abzinsung (%):", 5.0, 15.0, 9.0, key="dcf_wacc"
    )

    fair_value_demo = fcf * (1 + growth_rate / 100) / (discount_rate / 100)
    st.markdown("---")
    st.metric(
        label="Fairer Wert (Indikation Mio. €)",
        value=f"{fair_value_demo:,.2f} €",
    )


# =========================================================
# TAB 3: TRAILING-STOP
# =========================================================
with tab3:
    st.subheader("⚙️ Trailing-Stop Rechner")

    current_price = st.number_input(
        "Aktueller Kurs (€):", value=100.0, step=1.0, key="ts_price"
    )
    stop_pct = st.slider(
        "Stop-Abstand (%):", 1.0, 20.0, 8.0, key="ts_pct"
    )

    calculated_stop = current_price * (1 - stop_pct / 100)

    st.markdown("---")
    st.metric(
        label="Berechneter Stop-Loss Kurs", value=f"{calculated_stop:.2f} €"
    )
    st.caption(f"Max. Verlust: -{stop_pct:.1f}%")

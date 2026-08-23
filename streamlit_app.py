import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Stock Valuation & Portfolio Manager", layout="wide"
)

# ---------------------------------------------------------
# REITER-NAVIGATION Ganz Oben (Ideal für Smartphones)
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(
    [
        "📊 Depot & Klumpenrisiko",
        "🧮 DCF & Bewertung",
        "⚙️ Trailing-Stop & Regeln",
    ]
)

# =========================================================
# TAB 1: DEPOT-INTEGRATION & KAUFGRÖSSEN-PRÜFUNG
# =========================================================
with tab1:
    st.title("Depot-Integration & Kaufgrößen-Prüfung")

    # Simulierte Portfolio-Datenbank
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

    # Sektor-Mapping
    SEKTOR_MAPPING = {
        "ALV.DE": ("Allianz SE", "Finanzen"),
        "ALLIANZ": ("Allianz SE", "Finanzen"),
        "CS.PA": ("AXA SA", "Finanzen"),
        "AXA": ("AXA SA", "Finanzen"),
        "MUV2.DE": ("Münchener Rück", "Finanzen"),
        "DTE.DE": ("Deutsche Telekom", "Telekommunikation"),
        "ZSCALER": ("Zscaler", "Technologie"),
        "AAPL": ("Apple Inc.", "Technologie"),
        "MSFT": ("Microsoft Corp.", "Technologie"),
    }

    # Risikogrenzen
    MAX_POSITION_WEIGHT = 5.0  # Max. 5% pro Einzelwert
    MAX_SEKTOR_WEIGHT = 20.0  # Max. 20% pro Sektor
    TARGET_AKTIENQUOTE = 50.0

    if "sim_ticker" not in st.session_state:
        st.session_state.sim_ticker = "ALV.DE"

    col_input, col_sum = st.columns(2)
    with col_input:
        sim_ticker_input = (
            st.text_input(
                "Zu simulierende Aktie (Ticker z. B. AAPL, ALV.DE):",
                value=st.session_state.sim_ticker,
                key="t1_input",
            )
            .strip()
            .upper()
        )

    with col_sum:
        buy_amount = st.number_input(
            "Geplante Kaufsumme (€):",
            value=1000.0,
            step=100.0,
            min_value=0.0,
            key="t1_amount",
        )

    # Quick-Buttons für das Smartphone
    col_b1, col_b2, col_b3 = st.columns(3)
    if col_b1.button("🔄 Auf Allianz setzen"):
        st.session_state.sim_ticker = "ALV.DE"
        st.rerun()

    if col_b2.button("🍏 Auf Apple (Entwarnung)"):
        st.session_state.sim_ticker = "AAPL"
        st.rerun()

    if col_b3.button("📞 Auf Telekom setzen"):
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
    st.subheader(
        f"Simulation: Kauf von {buy_amount:,.2f} € in {sim_ticker_input} ({stock_name})"
    )

    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric(
            label="Aktienquote",
            value=f"{TARGET_AKTIENQUOTE}% → {TARGET_AKTIENQUOTE}%",
        )
        st.caption(f"↑ Ziel-Max: {TARGET_AKTIENQUOTE}%")

    with m_col2:
        st.metric(
            label="Positionsgewicht", value=f"{neues_positionsgewicht:.1f} %"
        )
        if neues_positionsgewicht > MAX_POSITION_WEIGHT:
            st.error(f"⚠️ Max. {MAX_POSITION_WEIGHT}% erlaubt!")
        else:
            st.caption(f"↑ Max: {MAX_POSITION_WEIGHT}%")

    with m_col3:
        st.metric(
            label=f"Sektoranteil ({stock_sektor})",
            value=f"{neuer_sektor_anteil:.1f} %",
        )
        if neuer_sektor_anteil > MAX_SEKTOR_WEIGHT:
            st.error(
                f"🚨 KLUMPENRISIKO! Sektor-Limit ({MAX_SEKTOR_WEIGHT}%) überschritten!"
            )
        else:
            st.caption(f"↑ Max Sektor-Limit: {MAX_SEKTOR_WEIGHT}%")

    st.markdown("---")
    if neuer_sektor_anteil > MAX_SEKTOR_WEIGHT:
        st.error(
            f"**Warnung vor Sektorkonzentration:** Durch den Kauf von **{stock_name}** steigt der Anteil des Sektors "
            f"**'{stock_sektor}'** im Gesamtdepot auf **{neuer_sektor_anteil:.1f}%**. Das festgelegte Maximallimit liegt bei **{MAX_SEKTOR_WEIGHT}%**."
        )
    elif neues_positionsgewicht > MAX_POSITION_WEIGHT:
        st.warning(
            f"**Einzelwert-Warnung:** Das Positionsgewicht von **{sim_ticker_input}** überschreitet mit "
            f"**{neues_positionsgewicht:.1f}%** das erlaubte Limit von **{MAX_POSITION_WEIGHT}%**."
        )
    else:
        st.success("✅ Der Kauf liegt innerhalb aller festgelegten Risikogrenzen.")


# =========================================================
# TAB 2: DCF & VALUATION RECHNER
# =========================================================
with tab2:
    st.title("🧮 DCF & Aktienbewertung")
    st.info("Hier kannst du als Nächstes deine Bewertungsmodelle testen.")

    col_dcf1, col_dcf2 = st.columns(2)
    with col_dcf1:
        fcf = st.number_input(
            "Free Cash Flow (in Mio. €):", value=500.0, step=50.0, key="dcf_fcf"
        )
        growth_rate = st.slider(
            "Wachstumsrate Jahre 1-5 (%):", 0.0, 30.0, 8.0, key="dcf_growth"
        )

    with col_dcf2:
        discount_rate = st.slider(
            "Abzinsungssatz / WACC (%):", 5.0, 15.0, 9.0, key="dcf_wacc"
        )
        terminal_growth = st.slider(
            "Ewige Wachstumsrate (%):", 0.0, 5.0, 2.0, key="dcf_term"
        )

    # Einfache Vereinfachte DCF-Demo
    fair_value_demo = fcf * (1 + growth_rate / 100) / (discount_rate / 100)
    st.metric(
        label="Indikativer Fairer Wert (Mio. €)",
        value=f"{fair_value_demo:,.2f} €",
    )


# =========================================================
# TAB 3: TRAILING-STOP & PORTFOLIO-REGELN
# =========================================================
with tab3:
    st.title("⚙️ Trailing-Stop & Risikomanagement")

    col_ts1, col_ts2 = st.columns(2)
    with col_ts1:
        current_price = st.number_input(
            "Aktueller Kurs (€):", value=100.0, step=1.0, key="ts_price"
        )
        stop_pct = st.slider(
            "Trailing-Stop Abstand (%):", 1.0, 20.0, 8.0, key="ts_pct"
        )

    calculated_stop = current_price * (1 - stop_pct / 100)

    with col_ts2:
        st.metric(
            label="Berechneter Stop-Loss Kurs", value=f"{calculated_stop:.2f} €"
        )
        st.caption(f"Verlust bei Auslösung: -{stop_pct:.1f}%")

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Stock Manager",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Die exakten 3 Reiter oben nebeneinander
tab1, tab2, tab3 = st.tabs(
    ["📊 Depot & Klumpenrisiko", "🧮 DCF & Bewertung", "⚙️ Trailing-Stop & Regeln"]
)

# =========================================================
# TAB 1: DEPOT & KLUMPENRISIKO
# =========================================================
with tab1:
    st.subheader("Aktueller Depot-Status & Verwaltung")
    st.markdown("Trage deine Aktien ein. Werte werden sofort verrechnet!")

    if "depot_df" not in st.session_state:
        st.session_state.depot_df = pd.DataFrame(
            [
                {
                    "Name": "AXA SA",
                    "Sektor": "Finanzen",
                    "Stückzahl": 188,
                    "Kurs (€)": 43.73,
                }
            ]
        )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Depot leeren", use_container_width=True):
            st.session_state.depot_df = pd.DataFrame(
                columns=["Name", "Sektor", "Stückzahl", "Kurs (€)"]
            )
            st.rerun()
    with col_btn2:
        if st.button("🔄 Standard laden", use_container_width=True):
            st.session_state.depot_df = pd.DataFrame(
                [
                    {
                        "Name": "AXA SA",
                        "Sektor": "Finanzen",
                        "Stückzahl": 188,
                        "Kurs (€)": 43.73,
                    }
                ]
            )
            st.rerun()

    edited_df = st.data_editor(
        st.session_state.depot_df, num_rows="dynamic", key="depot_editor"
    )
    st.session_state.depot_df = edited_df

    try:
        edited_df["Gesamtwert"] = (
            edited_df["Stückzahl"].astype(float)
            * edited_df["Kurs (€)"].astype(float)
        )
        aktienwert = edited_df["Gesamtwert"].sum()
    except Exception:
        aktienwert = 0.0

    cash_reserve = st.number_input(
        "Verfügbares Cash / Puffer (€):",
        value=25000.0,
        step=1000.0,
        key="depot_cash",
    )
    gesamtdepotwert = aktienwert + cash_reserve
    aktienquote = (aktienwert / gesamtdepotwert * 100) if gesamtdepotwert > 0 else 0

    st.markdown("---")
    st.metric(label="Gesamtdepotwert", value=f"{gesamtdepotwert:,.2f} €")
    st.metric(label="Aktienwert", value=f"{aktienwert:,.2f} €")
    st.metric(label="Aktienquote", value=f"{aktienquote:.1f} %")


# =========================================================
# TAB 2: DCF & BEWERTUNG
# =========================================================
with tab2:
    st.subheader("🧮 DCF & Bewertung")

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
# TAB 3: TRAILING-STOP & REGELN
# =========================================================
with tab3:
    st.subheader("⚙️ Trailing-Stop & Risikomanagement")

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
    st.caption(f"Maximaler Verlust bei Auslösung: -{stop_pct:.1f}%")

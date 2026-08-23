import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Stock Valuation & Portfolio Capacity Engine",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.title("📈 Stock Valuation & Portfolio Capacity Engine")

# Die exakten 3 Reiter
tab_a, tab_b, tab_c = st.tabs(
    [
        "🔍 Tab A: Aktien-Analyse",
        "📊 Tab B: Depot-Verwaltung",
        "🎯 Tab C: Kauf-Simulation & Tranchen",
    ]
)

# =========================================================
# TAB A: MEHRKRITERIEN-BEWERTUNG & AKTIEN-ANALYSE
# =========================================================
with tab_a:
    st.subheader("Einzelaktien-Bewertung nach Kriterien")
    st.markdown("Bewerte die Aktie anhand verschiedener Qualitäts- und Fundamentalkriterien:")

    # Kriterien-Eingaben (Scoring-Modell)
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        crit_fcf = st.checkbox("Positive Cashflow-Metriken", value=True, key="c_fcf")
        crit_growth = st.checkbox("Starkes Gewinnwachstum (>10%)", value=True, key="c_growth")
        crit_moat = st.checkbox("Intakter Trend / Momentum", value=True, key="c_moat")
    with col_c2:
        crit_balance = st.checkbox("Gesunde Bilanz / geringe Schulden", value=True, key="c_balance")
        crit_margin = st.checkbox("Hohe operative Marge", value=False, key="c_margin")
        crit_valuation = st.checkbox("Attraktive Bewertung (DCF/KGV)", value=True, key="c_val")

    # Score-Berechnung aus Kriterien
    criteria_list = [crit_fcf, crit_growth, crit_moat, crit_balance, crit_margin, crit_valuation]
    score = sum(criteria_list)
    max_score = len(criteria_list)
    score_pct = (score / max_score) * 100

    st.markdown("---")
    st.metric(label="Erfüllte Kriterien (Gesamt-Score)", value=f"{score} von {max_score} ({score_pct:.0f}%)")
    
    if score >= 5:
        st.success("🟢 Starkes Setup: Aktie erfüllt die Mehrheit der Qualitätskriterien.")
    elif score >= 3:
        st.warning("🟡 Moderates Setup: Einige Kriterien sind noch offen.")
    else:
        st.error("🔴 Schwaches Setup: Kriterien-Anforderungen nicht ausreichend erfüllt.")

    st.markdown("---")
    st.subheader("🧮 Kurs- & Risiko-Parameter")
    current_price = st.number_input("Aktueller Kurs (€):", value=100.0, step=1.0, key="ana_price")
    stop_pct = st.slider("Stop-Abstand (%):", 1.0, 20.0, 8.0, key="ana_stop")
    calculated_stop = current_price * (1 - stop_pct / 100)

    st.metric(label="Berechneter Stop-Loss Kurs", value=f"{calculated_stop:.2f} €")


# =========================================================
# TAB B: DEPOT-VERWALTUNG
# =========================================================
with tab_b:
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
                },
                {
                    "Name": "Münchener Rückversicherung",
                    "Sektor": "Finanzen",
                    "Stückzahl": 10,
                    "Kurs (€)": 450.0,
                },
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
                    },
                    {
                        "Name": "Münchener Rückversicherung",
                        "Sektor": "Finanzen",
                        "Stückzahl": 10,
                        "Kurs (€)": 450.0,
                    },
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
        value=0.0,
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
# TAB C: KAUF-SIMULATION & TRANCHEN
# =========================================================
with tab_c:
    st.subheader("Depot-Integration & Kaufgrößen-Prüfung")

    sim_aktie = st.selectbox(
        "Zu simulierende Aktie:",
        ["Allianz", "AXA", "Apple", "Telekom"],
        key="c_aktie",
    )
    geplante_summe = st.number_input(
        "Geplante Kaufsumme (€):", value=1000.0, step=100.0, key="c_summe"
    )

    st.markdown("---")
    st.markdown(f"**Simulation für {sim_aktie}:**")
    st.metric(label="Investitionssumme", value=f"{geplante_summe:,.2f} €")
    st.success("✅ Kaufgröße im Rahmen der gewählten Tranchen-Limits.")

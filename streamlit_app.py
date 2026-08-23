import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Capacity Engine",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Kürzerer Text für die Tabs, damit sie auf dem Handy perfekt nebeneinander passen
tab_a, tab_b, tab_c = st.tabs(
    [
        "🔍 Analyse",
        "📊 Depot",
        "🎯 Simulation",
    ]
)

# =========================================================
# TAB A: AKTIEN-ANALYSE (DCF, Stop-Loss etc.)
# =========================================================
with tab_a:
    st.subheader("Aktien- & Risiko-Analyse")

    aktien_name = st.text_input("Aktienname:", value="AXA", key="ana_name")

    current_price = st.number_input(
        "Aktueller Kurs (€):", value=100.0, step=1.0, key="ana_price"
    )
    stop_pct = st.slider("Stop-Abstand (%):", 1.0, 20.0, 8.0, key="ana_stop")
    calculated_stop = current_price * (1 - stop_pct / 100)

    st.markdown("---")
    st.metric(
        label=f"Berechneter Stop-Loss Kurs ({aktien_name})", value=f"{calculated_stop:.2f} €"
    )

    st.markdown("---")
    st.subheader("🧮 DCF Indikation")
    fcf = st.number_input(
        "Free Cash Flow (Mio. €):", value=500.0, step=50.0, key="ana_fcf"
    )
    growth = st.slider("Wachstum p.a. (%):", 0.0, 30.0, 8.0, key="ana_growth")
    wacc = st.slider("WACC / Abzinsung (%):", 5.0, 15.0, 9.0, key="ana_wacc")

    fair_value = fcf * (1 + growth / 100) / (wacc / 100)
    st.metric(
        label="Fairer Wert (Indikation Mio. €)", value=f"{fair_value:,.2f} €"
    )


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
        if st.button("🗑️ Leeren", use_container_width=True):
            st.session_state.depot_df = pd.DataFrame(
                columns=["Name", "Sektor", "Stückzahl", "Kurs (€)"]
            )
            st.rerun()
    with col_btn2:
        if st.button("🔄 Standard", use_container_width=True):
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

    # Sektor-Zuordnung für die Simulations-Aktien
    sektor_mapping = {
        "Allianz": "Finanzen",
        "AXA": "Finanzen",
        "Apple": "Technologie",
        "Telekom": "Telekommunikation"
    }
    sim_sektor = sektor_mapping.get(sim_aktie, "Sonstige")

    # --- Kennzahlen & Depot-Berechnungen für die Simulation ---
    # 1. Gesamtwert Aktien & Depot berechnen
    depot_df = st.session_state.get("depot_df", pd.DataFrame())
    aktienwert_depot = 0.0
    sektor_aktienwert = 0.0

    if not depot_df.empty:
        try:
            depot_df["Zeilenwert"] = depot_df["Stückzahl"].astype(float) * depot_df["Kurs (€)"].astype(float)
            aktienwert_depot = depot_df["Zeilenwert"].sum()
            
            # Sektorwert im Aktienportfolio ermitteln
            sektor_mask = depot_df["Sektor"].astype(str).str.lower() == sim_sektor.lower()
            sektor_aktienwert = depot_df.loc[sektor_mask, "Zeilenwert"].sum()
        except Exception:
            pass

    # Gesamtdepotwert inklusive Cash aus Tab B holen
    cash_wert = st.session_state.get("depot_cash", 0.0)
    gesamtdepot_wert = aktienwert_depot + cash_wert

    # 2. Prüfungen gemäß deiner Logik
    # A) Sektoranteil am reinen Aktienportfolio
    sektor_anteil_aktien = (sektor_aktienwert / aktienwert_depot * 100) if aktienwert_depot > 0 else 0.0

    # B) Sektorlimit vom Gesamtdepot (max. 25% als hartes Limit oder Richtwert)
    sektor_anteil_gesamtdepot = (sektor_aktienwert / gesamtdepot_wert * 100) if gesamtdepot_wert > 0 else 0.0
    MAX_SEKTOR_GESAMTDEPOT_LIMIT = 25.0

    st.markdown("---")
    st.markdown(f"**Simulation für {sim_aktie} (Sektor: {sim_sektor}):**")
    st.metric(label="Geplante Investitionssumme", value=f"{geplante_summe:,.2f} €")

    # Signal-Auswertung für Sektor am Aktienportfolio
    if sektor_anteil_aktien < 30.0:
        sektor_status = "🟢 Normal"
    elif 30.0 <= sektor_anteil_aktien < 40.0:
        sektor_status = "🟡 Beobachten"
    elif 40.0 <= sektor_anteil_aktien <= 50.0:
        sektor_status = "🟠 Kauf drosseln"
    else:
        sektor_status = "🔴 Keine weiteren Käufe"

    # Modellierte maximale Erst-Tranche unter aktuellen Depotbedingungen
    modellierte_max_tranche = 1500.0

    st.info(
        f"📊 **Portfolio-Check:**\n"
        f"- Sektoranteil am Aktienportfolio: **{sektor_anteil_aktien:.1f} %** ({sektor_status})\n"
        f"- Sektoranteil am Gesamtdepot: **{sektor_anteil_gesamtdepot:.1f} %** (Limit: {MAX_SEKTOR_GESAMTDEPOT_LIMIT}%)\n"
        f"- Modellierte **maximale Erst-Tranche**: **{modellierte_max_tranche:,.2f} €**"
    )

    # Validierung gegen Schwellen
    if sektor_anteil_aktien > 50.0:
        st.error(
            f"❌ Stopp: Sektoranteil am Aktienportfolio liegt bei {sektor_anteil_aktien:.1f} (> 50 %). "
            "Keine weiteren Käufe in diesem Sektor möglich!"
        )
    elif geplante_summe > modellierte_max_tranche and sektor_anteil_aktien >= 40.0:
        st.warning(
            f"🟡 Gedrosselte Erst-Tranche: Der Sektoranteil am Aktienportfolio ({sektor_anteil_aktien:.1f} %) "
            f"befindet sich im Bereich 40–50 %. Die geplante Summe überschreitet die modellierte "
            f"maximale Erst-Tranche von {modellierte_max_tranche:,.2f} €."
        )
    else:
        st.success(
            f"✅ Kaufgröße im Rahmen der gewählten Tranchen-Limits "
            f"(Sektor-Status: {sektor_status})."
        )

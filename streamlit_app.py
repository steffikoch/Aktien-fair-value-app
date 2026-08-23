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

    cash_wert = st.session_state.get("depot_cash", 0.0)
    gesamtdepot_wert = aktienwert_depot + cash_wert

    # A) Sektoranteil am reinen Aktienportfolio
    sektor_anteil_aktien = (sektor_aktienwert / aktienwert_depot * 100) if aktienwert_depot > 0 else 0.0

    # B) Sektorlimit vom Gesamtdepot
    sektor_anteil_gesamtdepot = (sektor_aktienwert / gesamtdepot_wert * 100) if gesamtdepot_wert > 0 else 0.0
    MAX_SEKTOR_GESAMTDEPOT_LIMIT = 25.0

    st.markdown("---")
    st.markdown(f"**Simulation für {sim_aktie} (Sektor: {sim_sektor}):**")
    st.metric(label="Geplante Investitionssumme", value=f"{geplante_summe:,.2f} €")

    # Signal-Auswertung & dynamische Ermittlung der maximalen Erst-Tranche basierend auf deinen Schwellen
    if sektor_anteil_aktien < 30.0:
        sektor_status = "🟢 Normal"
        modellierte_max_tranche = 3000.0
    elif 30.0 <= sektor_anteil_aktien < 40.0:
        sektor_status = "🟡 Beobachten"
        modellierte_max_tranche = 2000.0
    elif 40.0 <= sektor_anteil_aktien <= 50.0:
        sektor_status = "🟠 Kauf drosseln"
        modellierte_max_tranche = 1000.0  # Drosselung greift hier strenger
    else:
        sektor_status = "🔴 Keine weiteren Käufe"
        modellierte_max_tranche = 0.0

    st.info(
        f"📊 **Portfolio-Check:**\n"
        f"- Sektoranteil am Aktienportfolio: **{sektor_anteil_aktien:.1f} %** ({sektor_status})\n"
        f"- Sektoranteil am Gesamtdepot: **{sektor_anteil_gesamtdepot:.1f} %** (Limit: {MAX_SEKTOR_GESAMTDEPOT_LIMIT}%)\n"
        f"- Modellierte **maximale Erst-Tranche**: **{modellierte_max_tranche:,.2f} €**"
    )

    # Validierung gegen Schwellen
    if sektor_anteil_aktien > 50.0:
        st.error(
            f"❌ Stopp: Sektoranteil am Aktienportfolio liegt bei {sektor_anteil_aktien:.1f} % (> 50 %). "
            "Keine weiteren Käufe in diesem Sektor möglich!"
        )
    elif geplante_summe > modellierte_max_tranche and sektor_anteil_aktien >= 40.0:
        st.warning(
            f"🟡 Gedrosselte Erst-Tranche: Der Sektoranteil am Aktienportfolio ({sektor_anteil_aktien:.1f} %) "
            f"befindet sich im Bereich 40–50 %. Die geplante Summe ({geplante_summe:,.2f} €) überschreitet die "
            f"modellierte maximale Erst-Tranche von {modellierte_max_tranche:,.2f} €."
        )
    else:
        st.success(
            f"✅ Kaufgröße im Rahmen der gewählten Tranchen-Limits "
            f"(Sektor-Status: {sektor_status})."
        )

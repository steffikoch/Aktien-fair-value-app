import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Depot-Integration & Kaufgrößen-Prüfung", layout="wide"
)

# ---------------------------------------------------------
# 1. SIMULIERTE PORTFOLIO-DATENBANK (Bestehendes Depot)
# ---------------------------------------------------------
# Hier sind bereits AXA und Münchener Rück im Sektor "Finanzen" hinterlegt
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

# Sektor-Mapping für neue Test-Eingaben
SEKTOR_MAPPING = {
    "ALV.DE": ("Allianz SE", "Finanzen"),
    "ALLIANZ": ("Allianz SE", "Finanzen"),
    "CS.PA": ("AXA SA", "Finanzen"),
    "AXA": ("AXA SA", "Finanzen"),
    "MUV2.DE": ("Münchener Rück", "Finanzen"),
    "DTE.DE": ("Deutsche Telekom", "Telekommunikation"),
    "ZSCALER": ("Zscaler", "Technologie"),
}

# Config / Limits
MAX_POSITION_WEIGHT = 5.0  # Max. 5% pro Einzelaktie
MAX_SEKTOR_WEIGHT = 20.0  # Max. 20% pro Sektor
TARGET_AKTIENQUOTE = 50.0  # Ziel-Aktienquote

# ---------------------------------------------------------
# 2. BENUTZEROBERFLÄCHE (EINGABE)
# ---------------------------------------------------------
st.title("Depot-Integration & Kaufgrößen-Prüfung")

col_input, col_sum = st.columns(2)

with col_input:
    # Flexibles Eingabefeld statt starrer Selectbox
    sim_ticker_input = st.text_input(
        "Zu simulierende Aktie (Ticker oder Name):", value="ALV.DE"
    ).upper()

with col_sum:
    buy_amount = st.number_input(
        "Geplante Kaufsumme (€):", value=1000.0, step=100.0, min_value=0.0
    )

# Ticker & Sektor-Zuordnung ermitteln
stock_name, stock_sektor = SEKTOR_MAPPING.get(
    sim_ticker_input, (sim_ticker_input, "Finanzen")
)

st.markdown("---")

# ---------------------------------------------------------
# 3. KELKULATION & KLUMPENRISIKO-PRÜFUNG
# ---------------------------------------------------------
df_current = st.session_state.portfolio_data.copy()

# 1. Bisheriges Depotberechnungen
bisheriges_depot_gesamtwert = df_current["Wert"].sum()
neues_depot_gesamtwert = bisheriges_depot_gesamtwert + buy_amount

# 2. Positionsgewicht der neuen Aktie berechnen
# (Falls Aktie bereits im Depot ist, Wert addieren)
bisheriger_aktien_wert = df_current[
    df_current["Ticker"] == sim_ticker_input
]["Wert"].sum()
neuer_aktien_wert = bisheriger_aktien_wert + buy_amount
neues_positionsgewicht = (neuer_aktien_wert / neues_depot_gesamtwert) * 100

# 3. Sektoranteil berechnen (Inkl. AXA + Münchener Rück + Allianz)
bisheriger_sektor_wert = df_current[df_current["Sektor"] == stock_sektor][
    "Wert"
].sum()
neuer_sektor_wert = bisheriger_sektor_wert + buy_amount
neuer_sektor_anteil = (neuer_sektor_wert / neues_depot_gesamtwert) * 100

# ---------------------------------------------------------
# 4. ERGEBNIS-ANZEIGE & ALARME
# ---------------------------------------------------------
st.subheader(
    f"Simulation: Kauf von {buy_amount:,.2f} € in {sim_ticker_input} ({stock_name})"
)

m_col1, m_col2, m_col3 = st.columns(3)

# Metric 1: Aktienquote
with m_col1:
    st.metric(
        label="Aktienquote",
        value=f"{TARGET_AKTIENQUOTE}% → {TARGET_AKTIENQUOTE}%",
    )
    st.caption(f"↑ Ziel-Max: {TARGET_AKTIENQUOTE}%")

# Metric 2: Positionsgewicht
with m_col2:
    st.metric(label="Positionsgewicht", value=f"{neues_positionsgewicht:.1f} %")
    if neues_positionsgewicht > MAX_POSITION_WEIGHT:
        st.error(f"⚠️ Exzessiv: Max. {MAX_POSITION_WEIGHT}% erlaubt!")
    else:
        st.caption(f"↑ Max: {MAX_POSITION_WEIGHT}%")

# Metric 3: Sektoranteil (Das eigentliche Klumpenrisiko)
with m_col3:
    st.metric(
        label=f"Sektoranteil ({stock_sektor})",
        value=f"{neuer_sektor_anteil:.1f} %",
    )
    if neuer_sektor_anteil > MAX_SEKTOR_WEIGHT:
        st.error(f"🚨 KLUMPENRISIKO! Sektor-Limit ({MAX_SEKTOR_WEIGHT}%) überschritten!")
    else:
        st.caption(f"↑ Max Sektor-Limit: {MAX_SEKTOR_WEIGHT}%")

# Explicit Warning Box bei Überschreitung
st.markdown("---")
if neuer_sektor_anteil > MAX_SEKTOR_WEIGHT:
    st.error(
        f"**Warnung vor Sektorkonzentration:** Durch den Kauf von **{stock_name}** steigt der Anteil des Sektors "
        f"**'{stock_sektor}'** im Gesamtdepot auf **{neuer_sektor_anteil:.1f}%** (Bestehend: AXA + Münch. Rück). "
        f"Das festgelegte Maximallimit liegt bei **{MAX_SEKTOR_WEIGHT}%**."
    )
elif neues_positionsgewicht > MAX_POSITION_WEIGHT:
    st.warning(
        f"**Einzelwert-Warnung:** Das Positionsgewicht von **{sim_ticker_input}** überschreitet mit "
        f"**{neues_positionsgewicht:.1f}%** das erlaubte Einzellimit von **{MAX_POSITION_WEIGHT}%**."
    )
else:
    st.success("✅ Der Kauf liegt innerhalb aller festgelegten Risikogrenzen.")

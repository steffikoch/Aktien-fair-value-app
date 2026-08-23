import numpy as np
import pandas as pd
import streamlit as st

# =========================================================
# STREAMLIT CONFIG
# =========================================================
st.set_page_config(
    page_title="Aktien Fair Value & Depot-Engine",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Aktien Fair Value & Portfolio Capacity Engine")
st.caption("Einzelanalyse unabhängig vom Depot • Reales Depot • Kaufsimulation")

# =========================================================
# AKTIEN-UNIVERSUM
# Hinweis: Werte sind Modell-/Beispieldaten und keine Live-Kurse.
# =========================================================
def load_universe():
    return pd.DataFrame([
        {
            "Ticker": "AXA",
            "Name": "AXA SA",
            "Sector": "Financial Services",
            "Fair_Value": 62.15,
            "Current_Price": 43.72,
            "PER": 11.8,
            "Beta": 0.59,
            "Quality": 89,
            "Confidence": "🟢 Robust",
        },
        {
            "Ticker": "MUV2.DE",
            "Name": "Münchener Rück",
            "Sector": "Financial Services",
            "Fair_Value": 650.00,
            "Current_Price": 550.00,
            "PER": 12.5,
            "Beta": 0.62,
            "Quality": 88,
            "Confidence": "🟢 Robust",
        },
        {
            "Ticker": "ALV.DE",
            "Name": "Allianz SE",
            "Sector": "Financial Services",
            "Fair_Value": 510.00,
            "Current_Price": 450.00,
            "PER": 11.0,
            "Beta": 0.95,
            "Quality": 86,
            "Confidence": "🟢 Robust",
        },
        {
            "Ticker": "DTE.DE",
            "Name": "Deutsche Telekom",
            "Sector": "Communication Services",
            "Fair_Value": 37.08,
            "Current_Price": 28.94,
            "PER": 15.0,
            "Beta": 0.75,
            "Quality": 67,
            "Confidence": "🟢 Hoch",
        },
        {
            "Ticker": "SAP.DE",
            "Name": "SAP SE",
            "Sector": "Technology",
            "Fair_Value": 220.00,
            "Current_Price": 195.00,
            "PER": 32.0,
            "Beta": 0.95,
            "Quality": 84,
            "Confidence": "🟢 Robust",
        },
        {
            "Ticker": "NVDA",
            "Name": "NVIDIA Corp.",
            "Sector": "Technology",
            "Fair_Value": 110.00,
            "Current_Price": 125.00,
            "PER": 45.2,
            "Beta": 1.68,
            "Quality": 78,
            "Confidence": "🟡 KGV hoch",
        },
        {
            "Ticker": "AAPL",
            "Name": "Apple Inc.",
            "Sector": "Technology",
            "Fair_Value": 220.00,
            "Current_Price": 210.00,
            "PER": 30.0,
            "Beta": 1.05,
            "Quality": 82,
            "Confidence": "🟢 Robust",
        },
        {
            "Ticker": "MSFT",
            "Name": "Microsoft Corp.",
            "Sector": "Technology",
            "Fair_Value": 430.00,
            "Current_Price": 415.00,
            "PER": 34.0,
            "Beta": 0.90,
            "Quality": 90,
            "Confidence": "🟢 Robust",
        },
    ])


UNIVERSE = load_universe()

# =========================================================
# SESSION STATE
# =========================================================
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

if "cash" not in st.session_state:
    st.session_state.cash = 55000.0


def universe_row(ticker):
    rows = UNIVERSE[UNIVERSE["Ticker"] == ticker]
    return rows.iloc[0] if not rows.empty else None


def portfolio_df():
    if not st.session_state.portfolio:
        return pd.DataFrame(
            columns=[
                "Ticker", "Name", "Sector", "Shares",
                "Buy_Price", "Current_Price", "Position_Value"
            ]
        )

    df = pd.DataFrame(st.session_state.portfolio)
    df["Position_Value"] = df["Shares"] * df["Current_Price"]
    return df


def calculate_fair_value_metrics(row):
    price = float(row["Current_Price"])
    fv = float(row["Fair_Value"])
    mos = (fv - price) / price * 100 if price > 0 else 0
    buy_limit_10 = fv * 0.90
    return mos, buy_limit_10


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("⚙️ Depot-Parameter")

cash_input = st.sidebar.number_input(
    "Cash-Bestand (€)",
    min_value=0.0,
    value=float(st.session_state.cash),
    step=500.0,
)
st.session_state.cash = cash_input

target_stock_quote_max = st.sidebar.slider(
    "Max. Ziel-Aktienquote (%)",
    min_value=10.0,
    max_value=100.0,
    value=50.0,
    step=1.0,
)

max_position_pct = st.sidebar.slider(
    "Max. Einzelposition (% vom Depot)",
    min_value=1.0,
    max_value=20.0,
    value=5.0,
    step=0.5,
)

sector_limit_pct = st.sidebar.slider(
    "Max. Sektor-Limit (% vom Gesamtdepot)",
    min_value=5.0,
    max_value=50.0,
    value=25.0,
    step=1.0,
)

st.sidebar.divider()
st.sidebar.info(
    "💡 Die Einzelaktienanalyse berücksichtigt das Depot nicht. "
    "Die Kaufsimulation berücksichtigt dagegen Bestand, Cash, "
    "Aktienquote, Positionslimit und Sektorkonzentration."
)

# =========================================================
# DEPOT-KENNZAHLEN
# =========================================================
df_portfolio = portfolio_df()
stock_value = float(df_portfolio["Position_Value"].sum()) if not df_portfolio.empty else 0.0
cash_value = float(st.session_state.cash)
total_depot = stock_value + cash_value
stock_quote = stock_value / total_depot * 100 if total_depot > 0 else 0.0

# =========================================================
# TABS
# =========================================================
tab_a, tab_b, tab_c = st.tabs([
    "🔍 A. Einzelaktien-Analyse",
    "📊 B. Reales Depot",
    "🎯 C. Kauf-Simulation & Tranchen",
])

# =========================================================
# TAB A — UNABHÄNGIGE AKTIENANALYSE
# =========================================================
with tab_a:
    st.header("Einzelaktien-Bewertung")
    st.info(
        "ℹ️ Depotdaten werden hier vollständig ignoriert. "
        "Die Analyse beantwortet nur: Ist die Aktie fundamental interessant und günstig?"
    )

    selected = st.selectbox(
        "Aktie zur Analyse auswählen:",
        UNIVERSE["Ticker"].tolist(),
        format_func=lambda x: f"{x} – {universe_row(x)['Name']}",
    )

    row = universe_row(selected)
    mos, buy_limit = calculate_fair_value_metrics(row)

    st.subheader(f"{row['Name']} ({row['Ticker']})")
    st.write(f"**Sektor:** {row['Sector']}")

    if mos >= 30:
        verdict = "🟢 ATTRAKTIV BEWERTET"
    elif mos >= 10:
        verdict = "🟡 MODERAT ATTRAKTIV"
    elif mos >= 0:
        verdict = "🟠 FAIR BEWERTET"
    else:
        verdict = "🔴 ÜBER FAIR VALUE"

    st.markdown(f"### Urteil: {verdict}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quality Score", f"{row['Quality']}/100")
    c2.metric("Fair Value", f"{row['Fair_Value']:.2f} €")
    c3.metric("Aktueller Kurs", f"{row['Current_Price']:.2f} €",
              delta=f"{mos:+.1f}% MOS")
    c4.metric("KGV / Beta", f"{row['PER']} / {row['Beta']}")

    st.divider()

    s1, s2, s3 = st.columns(3)
    s1.metric("Bear / Base / Bull", 
              f"{row['Fair_Value']*0.75:.2f} / "
              f"{row['Fair_Value']:.2f} / "
              f"{row['Fair_Value']*1.25:.2f} €")
    s2.metric("Empfohlenes Kauflimit (-10%)", f"{buy_limit:.2f} €")
    s3.metric("Modell-Status", row["Confidence"])

    st.divider()

    if selected == "AXA":
        st.success(
            "AXA: Quality Score 89/100 und deutlicher Fair-Value-Puffer. "
            "Da AXA ein Versicherungs-/Finanzwert ist, wird FCF nicht als "
            "primäres Bewertungskriterium verwendet."
        )
    elif selected == "MUV2.DE":
        st.success(
            "Münchener Rück: hoher Qualitätswert. Bei der Depotentscheidung "
            "wird die gemeinsame Financial-Services-Exponierung berücksichtigt."
        )
    else:
        st.write(
            "Die Fundamentalanalyse ist unabhängig davon, ob die Aktie bereits "
            "im Depot vorhanden ist."
        )

# =========================================================
# TAB B — ECHTES DEPOT
# =========================================================
with tab_b:
    st.header("Reales Depot – Bestand & G&V")

    with st.expander("➕ Aktie im Depot hinzufügen / bearbeiten", expanded=True):
        ticker_options = ["Manuell"] + UNIVERSE["Ticker"].tolist()

        selected_ticker = st.selectbox(
            "Aktie auswählen:",
            ticker_options,
            format_func=lambda x: (
                "Manuell eintragen"
                if x == "Manuell"
                else f"{x} – {universe_row(x)['Name']}"
            ),
        )

        if selected_ticker != "Manuell":
            u = universe_row(selected_ticker)
            default_ticker = u["Ticker"]
            default_name = u["Name"]
            default_sector = u["Sector"]
            default_current = float(u["Current_Price"])
        else:
            default_ticker = ""
            default_name = ""
            default_sector = "Sonstige"
            default_current = 0.0

        ticker = st.text_input("Ticker", value=default_ticker)
        name = st.text_input("Name", value=default_name)

        sectors = [
            "Financial Services",
            "Technology",
            "Communication Services",
            "Healthcare",
            "Industrials",
            "Energy",
            "Consumer Discretionary",
            "Sonstige",
        ]

        sector_index = sectors.index(default_sector) if default_sector in sectors else 0
        sector = st.selectbox("Sektor", sectors, index=sector_index)

        shares = st.number_input(
            "Stückzahl",
            min_value=0.0,
            value=0.0,
            step=1.0,
        )

        buy_price = st.number_input(
            "Kaufkurs (€)",
            min_value=0.0,
            value=default_current,
            step=0.01,
        )

        current_price = st.number_input(
            "Aktueller Kurs (€)",
            min_value=0.0,
            value=default_current,
            step=0.01,
        )

        if st.button("💾 Position speichern", type="primary"):
            if ticker.strip() and shares > 0 and current_price > 0:
                clean_ticker = ticker.strip().upper()

                st.session_state.portfolio = [
                    p for p in st.session_state.portfolio
                    if p["Ticker"].upper() != clean_ticker
                ]

                st.session_state.portfolio.append({
                    "Ticker": clean_ticker,
                    "Name": name.strip() or clean_ticker,
                    "Sector": sector,
                    "Shares": float(shares),
                    "Buy_Price": float(buy_price),
                    "Current_Price": float(current_price),
                })

                st.success(f"✅ {clean_ticker} wurde im Depot gespeichert.")
                st.rerun()
            else:
                st.error("Bitte Ticker, Stückzahl und aktuellen Kurs eingeben.")

    st.divider()

    if df_portfolio.empty:
        st.warning("Noch keine Positionen im echten Depot eingetragen.")
    else:
        display_df = df_portfolio.copy()

        display_df["Einstand"] = (
            display_df["Shares"] * display_df["Buy_Price"]
        )
        display_df["G&V €"] = (
            display_df["Position_Value"] - display_df["Einstand"]
        )
        display_df["G&V %"] = np.where(
            display_df["Einstand"] > 0,
            display_df["G&V €"] / display_df["Einstand"] * 100,
            0,
        )
        display_df["Depotgewicht %"] = (
            display_df["Position_Value"] / total_depot * 100
            if total_depot > 0 else 0
        )

        st.dataframe(
            display_df[
                [
                    "Ticker", "Name", "Sector", "Shares",
                    "Buy_Price", "Current_Price",
                    "Position_Value", "G&V €",
                    "G&V %", "Depotgewicht %"
                ]
            ].rename(columns={
                "Ticker": "Ticker",
                "Name": "Name",
                "Sector": "Sektor",
                "Shares": "Stück",
                "Buy_Price": "Kaufkurs",
                "Current_Price": "Kurs",
                "Position_Value": "Wert",
                "G&V €": "G&V €",
                "G&V %": "G&V %",
                "Depotgewicht %": "Depotgewicht %",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Depotübersicht")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Gesamtdepot", f"{total_depot:,.2f} €")
        m2.metric("Aktienwert", f"{stock_value:,.2f} €")
        m3.metric("Cash", f"{cash_value:,.2f} €")
        m4.metric("Aktienquote", f"{stock_quote:.1f} %")

        if stock_quote <= target_stock_quote_max:
            st.success(
                f"🟢 Aktienquote {stock_quote:.1f}% – unter deinem Maximum "
                f"von {target_stock_quote_max:.1f}%."
            )
        else:
            st.error(
                f"🔴 Aktienquote {stock_quote:.1f}% – über deinem Maximum "
                f"von {target_stock_quote_max:.1f}%."
            )

        st.subheader("Sektorverteilung")

        sector_table = (
            df_portfolio.groupby("Sector", as_index=False)["Position_Value"]
            .sum()
            .sort_values("Position_Value", ascending=False)
        )

        sector_table["% Gesamtdepot"] = (
            sector_table["Position_Value"] / total_depot * 100
            if total_depot > 0 else 0
        )
        sector_table["% Aktienportfolio"] = (
            sector_table["Position_Value"] / stock_value * 100
            if stock_value > 0 else 0
        )

        st.dataframe(
            sector_table.rename(columns={
                "Sector": "Sektor",
                "Position_Value": "Wert",
            }),
            use_container_width=True,
            hide_index=True,
        )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Depot komplett leeren"):
            st.session_state.portfolio = []
            st.rerun()

    with col2:
        if st.button("🔄 Beispieldepot laden"):
            st.session_state.portfolio = [
                {
                    "Ticker": "AXA",
                    "Name": "AXA SA",
                    "Sector": "Financial Services",
                    "Shares": 188.0,
                    "Buy_Price": 40.00,
                    "Current_Price": 43.72,
                },
                {
                    "Ticker": "MUV2.DE",
                    "Name": "Münchener Rück",
                    "Sector": "Financial Services",
                    "Shares": 10.0,
                    "Buy_Price": 500.00,
                    "Current_Price": 550.00,
                },
                {
                    "Ticker": "DTE.DE",
                    "Name": "Deutsche Telekom",
                    "Sector": "Communication Services",
                    "Shares": 20.0,
                    "Buy_Price": 27.00,
                    "Current_Price": 28.94,
                },
            ]
            st.rerun()

# =========================================================
# TAB C — KAUFSIMULATION
# =========================================================
with tab_c:
    st.header("Kauf-Simulation & Tranchen")
    st.info(
        "Die Simulation verändert dein echtes Depot nicht. "
        "Sie berechnet nur, was bei einem zusätzlichen Kauf passieren würde."
    )

    sim_ticker = st.selectbox(
        "Zu simulierende Aktie:",
        UNIVERSE["Ticker"].tolist(),
        format_func=lambda x: f"{x} – {universe_row(x)['Name']}",
        key="sim_ticker",
    )

    sim_amount = st.number_input(
        "Geplante Kaufsumme (€):",
        min_value=0.0,
        value=1000.0,
        step=250.0,
        key="sim_amount",
    )

    sim = universe_row(sim_ticker)

    existing_position = 0.0
    existing_sector = 0.0

    if not df_portfolio.empty:
        existing_position = float(
            df_portfolio.loc[
                df_portfolio["Ticker"] == sim_ticker,
                "Position_Value"
            ].sum()
        )

        existing_sector = float(
            df_portfolio.loc[
                df_portfolio["Sector"] == sim["Sector"],
                "Position_Value"
            ].sum()
        )

    # Ein Kauf verschiebt Cash in Aktien.
    simulated_stock_value = stock_value + sim_amount
    simulated_cash = max(0.0, cash_value - sim_amount)
    simulated_total_depot = simulated_stock_value + simulated_cash

    simulated_position = existing_position + sim_amount
    simulated_sector = existing_sector + sim_amount

    before_quote = stock_quote
    after_quote = (
        simulated_stock_value / simulated_total_depot * 100
        if simulated_total_depot > 0 else 0
    )

    position_weight_after = (
        simulated_position / simulated_total_depot * 100
        if simulated_total_depot > 0 else 0
    )

    sector_total_pct_after = (
        simulated_sector / simulated_total_depot * 100
        if simulated_total_depot > 0 else 0
    )

    sector_stock_share_after = (
        simulated_sector / simulated_stock_value * 100
        if simulated_stock_value > 0 else 0
    )

    st.markdown(
        f"### Simulation: Kauf von **{sim_amount:,.2f} €** in "
        f"**{sim['Ticker']} ({sim['Name']})**"
    )
    st.write(f"**Sektor:** {sim['Sector']}")

    a, b, c, d = st.columns(4)
    a.metric(
        "Aktienquote",
        f"{before_quote:.1f}% ➜ {after_quote:.1f}%",
        f"Max {target_stock_quote_max:.1f}%",
    )
    b.metric(
        "Positionsgewicht",
        f"{position_weight_after:.1f}%",
        f"Max {max_position_pct:.1f}%",
    )
    c.metric(
        "Sektor am Gesamtdepot",
        f"{sector_total_pct_after:.1f}%",
        f"Max {sector_limit_pct:.1f}%",
    )
    d.metric(
        "Sektor im Aktienportfolio",
        f"{sector_stock_share_after:.1f}%",
        "Konzentrationsprüfung",
    )

    st.divider()

    # =====================================================
    # KAPAZITÄTSBERECHNUNG
    # =====================================================
    capacity_cash = cash_value

    # Maximaler Kauf, damit Aktienquote nicht über das Ziel-Maximum steigt.
    if target_stock_quote_max < 100 and stock_value > 0:
        max_by_stock_quote = max(
            0.0,
            (target_stock_quote_max / 100 * total_depot - stock_value)
            / (1 - target_stock_quote_max / 100)
        )
    else:
        max_by_stock_quote = capacity_cash

    # Maximaler Kauf bis zum Einzelpositionslimit.
    max_position_value = total_depot * max_position_pct / 100
    max_by_position = max(
        0.0,
        max_position_value - existing_position
    )

    # Maximaler Kauf bis zum Sektorlimit am Gesamtdepot.
    max_sector_value = total_depot * sector_limit_pct / 100
    max_by_sector = max(
        0.0,
        max_sector_value - existing_sector
    )

    # Verfügbare Gesamtkapazität.
    structural_capacity = min(
        capacity_cash,
        max_by_stock_quote,
        max_by_position,
        max_by_sector,
    )

    # =====================================================
    # SEKTOR-KONZENTRATION
    # =====================================================
    if stock_value <= 0:
        concentration_status = "🟢 KEINE BESTEHENDE AKTIENPOSITION"
        recommended = min(sim_amount, structural_capacity)
        headline = "🟢 KAUF MÖGLICH – ERSTE AKTIENPOSITION"
        reason = "Noch kein Aktienportfolio vorhanden."
    elif sector_stock_share_after > 80:
        concentration_status = "🔴 SEHR HOHE KONZENTRATION"
        recommended = 0.0
        headline = "🔴 WARTEN – SEKTOR ZU STARK KONZENTRIERT"
        reason = (
            f"Financial Services würde {sector_stock_share_after:.1f}% "
            "des Aktienportfolios ausmachen."
        )
    elif sector_stock_share_after >= 50:
        concentration_status = "🔴 HOHE KONZENTRATION"
        recommended = min(sim_amount, structural_capacity, 500.0)
        headline = "🟠 KAUF NUR STARK GEDROSSELT"
        reason = (
            f"Der Sektor {sim['Sector']} würde {sector_stock_share_after:.1f}% "
            "des Aktienportfolios ausmachen."
        )
    elif sector_stock_share_after >= 40:
        concentration_status = "🟡 ERHÖHTE KONZENTRATION"
        recommended = min(sim_amount, structural_capacity, 1000.0)
        headline = "🟠 KAUF MÖGLICH – GEDROSSELTE ERST-TRANCHE"
        reason = (
            f"Der Sektor {sim['Sector']} liegt bei "
            f"{sector_stock_share_after:.1f}% des Aktienportfolios "
            "(Schwelle 40–50%)."
        )
    else:
        concentration_status = "🟢 AUSGEWOGEN"
        recommended = min(sim_amount, structural_capacity)
        headline = "🟢 KAUF MÖGLICH"
        reason = (
            f"Die Sektorkonzentration bleibt mit "
            f"{sector_stock_share_after:.1f}% unter 40%."
        )

    # Kein Kauf, wenn Cash/Limit/Aktienquote bereits blockieren.
    if structural_capacity <= 0:
        recommended = 0.0
        headline = "🔴 KAUF NICHT MÖGLICH"
        reason = (
            "Cash, Aktienquote, Einzelpositionslimit oder Sektorlimit "
            "lassen keinen zusätzlichen Kauf zu."
        )

    st.markdown("### 🎯 Portfolio-Fit")

    if recommended == 0:
        st.error(f"### {headline}")
    elif recommended < sim_amount:
        st.warning(f"### {headline}")
    else:
        st.success(f"### {headline}")

    st.write(f"ℹ️ {reason}")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Max. nach Cash", f"{capacity_cash:,.0f} €")
    r2.metric("Max. nach Aktienquote", f"{max_by_stock_quote:,.0f} €")
    r3.metric("Max. nach Position", f"{max_by_position:,.0f} €")
    r4.metric("Max. nach Sektor", f"{max_by_sector:,.0f} €")

    st.divider()

    st.subheader("8-Punkte-Check")

    checks = [
        ("Bewertung", "🟢" if float(sim["Fair_Value"]) > float(sim["Current_Price"]) else "🔴",
         f"MOS {calculate_fair_value_metrics(sim)[0]:+.1f}%"),
        ("Qualität", "🟢" if sim["Quality"] >= 80 else "🟡",
         f"{sim['Quality']}/100"),
        ("Einzelposition", "🟢" if position_weight_after <= max_position_pct else "🔴",
         f"{position_weight_after:.1f}% / {max_position_pct:.1f}%"),
        ("Aktienquote", "🟢" if after_quote <= target_stock_quote_max else "🔴",
         f"{after_quote:.1f}% / {target_stock_quote_max:.1f}%"),
        ("Sektor Gesamtdepot", "🟢" if sector_total_pct_after <= sector_limit_pct else "🔴",
         f"{sector_total_pct_after:.1f}% / {sector_limit_pct:.1f}%"),
        ("Sektorkonzentration", "🟢" if sector_stock_share_after < 40 else "🟡" if sector_stock_share_after < 50 else "🔴",
         f"{sector_stock_share_after:.1f}% der Aktien"),
        ("Cash", "🟢" if sim_amount <= cash_value else "🔴",
         f"{cash_value:,.0f} € verfügbar"),
        ("Modellstatus", "🟢" if "Robust" in sim["Confidence"] else "🟡",
         sim["Confidence"]),
    ]

    for title, icon, detail in checks:
        st.write(f"{icon} **{title}:** {detail}")

    st.divider()

    if recommended > 0:
        st.info(
            f"👉 **Empfohlene Tranche: {recommended:,.2f} €**\n\n"
            f"Geplante Kaufsumme: {sim_amount:,.2f} €"
        )
    else:
        st.error("👉 **Empfohlene Tranche: 0 €**")

    # Wichtig: Simulation verändert das echte Depot NICHT.
    st.caption(
        "Hinweis: Die Simulation ist nur ein Fit-Test. "
        "Dein echtes Depot wird erst durch die Eingabe in Tab B verändert."
    )

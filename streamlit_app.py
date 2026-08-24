import streamlit as st
import pandas as pd
from datetime import datetime

# =========================================================
# SEITENKONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Stock Valuation & Portfolio Engine",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Stock Valuation & Portfolio Capacity Engine")


# =========================================================
# AKTIEN-UNIVERSE
# =========================================================

DEFAULT_UNIVERSE = {

    "AXA": {
        "name": "AXA SA",
        "sector": "Finanzen",
        "price": 43.72,
        "fair_value": 62.15,
        "quality": 89,
        "per": 11.8,
        "beta": 0.59,
        "return_3y": 17.75,
        "reval_share": 12.4,
    },

    "MUV2.DE": {
        "name": "Münchener Rückversicherung",
        "sector": "Finanzen",
        "price": 516.14,
        "fair_value": 556.00,
        "quality": 80,
        "per": 15.0,
        "beta": 0.70,
        "return_3y": 10.00,
        "reval_share": 2.00,
    },

    "ALV.DE": {
        "name": "Allianz SE",
        "sector": "Finanzen",
        "price": 450.00,
        "fair_value": 510.00,
        "quality": 86,
        "per": 12.5,
        "beta": 0.90,
        "return_3y": 11.5,
        "reval_share": 4.2,
    },

    "DTE.DE": {
        "name": "Deutsche Telekom",
        "sector": "Kommunikation",
        "price": 28.94,
        "fair_value": 37.08,
        "quality": 67,
        "per": 13.0,
        "beta": 0.70,
        "return_3y": 8.89,
        "reval_share": 4.8,
    },

    "SAP.DE": {
        "name": "SAP SE",
        "sector": "Technologie",
        "price": 195.00,
        "fair_value": 220.00,
        "quality": 88,
        "per": 32.0,
        "beta": 0.95,
        "return_3y": 10.5,
        "reval_share": 4.0,
    },

    "CSCO": {
        "name": "Cisco Systems",
        "sector": "Technologie",
        "price": 58.88,
        "fair_value": 68.00,
        "quality": 82,
        "per": 25.0,
        "beta": 0.90,
        "return_3y": 8.0,
        "reval_share": 2.0,
    },

    "AVGO": {
        "name": "Broadcom",
        "sector": "Technologie",
        "price": 320.98,
        "fair_value": 370.00,
        "quality": 91,
        "per": 35.0,
        "beta": 1.25,
        "return_3y": 15.0,
        "reval_share": 5.0,
    },

    "AAPL": {
        "name": "Apple Inc.",
        "sector": "Technologie",
        "price": 210.00,
        "fair_value": 220.00,
        "quality": 91,
        "per": 30.0,
        "beta": 1.05,
        "return_3y": 9.0,
        "reval_share": 2.0,
    },

    "MSFT": {
        "name": "Microsoft Corp.",
        "sector": "Technologie",
        "price": 415.00,
        "fair_value": 430.00,
        "quality": 94,
        "per": 34.0,
        "beta": 0.90,
        "return_3y": 10.0,
        "reval_share": 2.5,
    },

    "NVDA": {
        "name": "NVIDIA Corp.",
        "sector": "Technologie",
        "price": 125.00,
        "fair_value": 110.00,
        "quality": 92,
        "per": 45.2,
        "beta": 1.68,
        "return_3y": 8.0,
        "reval_share": 0.0,
    },
}


# =========================================================
# SESSION STATE
# =========================================================

if "universe" not in st.session_state:
    st.session_state.universe = DEFAULT_UNIVERSE.copy()

if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}

if "transactions" not in st.session_state:
    st.session_state.transactions = []

if "cash" not in st.session_state:
    st.session_state.cash = 55000.0


UNIVERSE = st.session_state.universe


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def portfolio_dataframe():

    rows = []

    for ticker, pos in st.session_state.portfolio.items():

        data = UNIVERSE.get(ticker, {})

        current_price = data.get(
            "price",
            pos.get("last_price", pos["avg_price"])
        )

        current_value = pos["shares"] * current_price

        cost = pos["shares"] * pos["avg_price"]

        pnl = current_value - cost

        pnl_pct = (
            pnl / cost * 100
            if cost > 0
            else 0
        )

        rows.append({
            "Ticker": ticker,
            "Name": pos["name"],
            "Sektor": pos["sector"],
            "Stück": pos["shares"],
            "Ø Kaufkurs": pos["avg_price"],
            "Kurs": current_price,
            "Einstand": cost,
            "Wert": current_value,
            "G&V": pnl,
            "G&V %": pnl_pct,
        })

    return pd.DataFrame(rows)


def total_stock_value():

    df = portfolio_dataframe()

    if df.empty:
        return 0.0

    return df["Wert"].sum()


def total_depot_value():

    return (
        st.session_state.cash
        + total_stock_value()
    )


def stock_quote():

    total = total_depot_value()

    if total <= 0:
        return 0.0

    return (
        total_stock_value()
        / total
        * 100
    )


def recommendation(ticker):

    data = UNIVERSE[ticker]

    price = data["price"]
    fair = data["fair_value"]

    discount = (
        (fair - price)
        / fair
        * 100
    )

    quality = data["quality"]

    if discount >= 20 and quality >= 80:
        return "🟢 KAUFEN"

    if discount >= 10 and quality >= 75:
        return "🟢 KAUFEN / ERSTE TRANCHE"

    if discount >= 0 and quality >= 70:
        return "🟢 HALTEN"

    if discount < 0 and quality >= 80:
        return "🟡 ABWARTEN"

    if discount < -10:
        return "🔴 VERKAUFEN / PRÜFEN"

    return "🟡 ABWARTEN"


def buy_stock(ticker, shares, price):

    data = UNIVERSE[ticker]

    amount = shares * price

    # Cash prüfen
    if amount > st.session_state.cash:
        return False, "Nicht genügend Cash."

    old = st.session_state.portfolio.get(ticker)

    if old:

        old_shares = old["shares"]
        old_avg = old["avg_price"]

        new_shares = old_shares + shares

        new_avg = (
            (old_shares * old_avg)
            + (shares * price)
        ) / new_shares

        old["shares"] = new_shares
        old["avg_price"] = new_avg
        old["last_price"] = price

    else:

        st.session_state.portfolio[ticker] = {
            "name": data["name"],
            "sector": data["sector"],
            "shares": shares,
            "avg_price": price,
            "last_price": price,
        }

    # Cash reduzieren
    st.session_state.cash -= amount

    st.session_state.transactions.append({
        "Datum": datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        ),
        "Typ": "KAUF",
        "Ticker": ticker,
        "Stück": shares,
        "Kurs": price,
        "Betrag": amount,
    })

    return True, "Kauf erfolgreich."


def sell_stock(ticker, shares, price):

    if ticker not in st.session_state.portfolio:
        return False

    pos = st.session_state.portfolio[ticker]

    if shares > pos["shares"]:
        return False

    amount = shares * price

    pos["shares"] -= shares

    # Cash erhöhen
    st.session_state.cash += amount

    st.session_state.transactions.append({
        "Datum": datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        ),
        "Typ": "VERKAUF",
        "Ticker": ticker,
        "Stück": shares,
        "Kurs": price,
        "Betrag": amount,
    })

    if pos["shares"] <= 0.000001:
        del st.session_state.portfolio[ticker]

    return True


def sector_values():

    values = {}

    df = portfolio_dataframe()

    if df.empty:
        return values

    for _, row in df.iterrows():

        sector = row["Sektor"]

        values[sector] = (
            values.get(sector, 0)
            + row["Wert"]
        )

    return values


def sector_weight(sector):

    total = total_depot_value()

    if total <= 0:
        return 0

    values = sector_values()

    return (
        values.get(sector, 0)
        / total
        * 100
    )


def sector_stock_weight(sector):

    stocks = total_stock_value()

    if stocks <= 0:
        return 0

    values = sector_values()

    return (
        values.get(sector, 0)
        / stocks
        * 100
    )


def position_weight(ticker):

    total = total_depot_value()

    if total <= 0:
        return 0

    if ticker not in st.session_state.portfolio:
        return 0

    pos = st.session_state.portfolio[ticker]

    price = UNIVERSE[ticker]["price"]

    value = pos["shares"] * price

    return value / total * 100


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("⚙️ Depot-Parameter")

st.session_state.cash = st.sidebar.number_input(
    "Cash-Bestand (€)",
    min_value=0.0,
    value=float(st.session_state.cash),
    step=500.0
)

max_stock_quote = st.sidebar.slider(
    "Max. Ziel-Aktienquote (%)",
    10.0,
    100.0,
    50.0
)

max_position = st.sidebar.slider(
    "Max. Einzelposition (%)",
    1.0,
    30.0,
    5.0
)

max_sector = st.sidebar.slider(
    "Max. Sektor-Limit (%)",
    5.0,
    80.0,
    25.0
)

st.sidebar.divider()

st.sidebar.subheader("⚠️ Warnschwellen")

sector_stock_warning = st.sidebar.slider(
    "Sektor-Warnung Aktienanteil (%)",
    30.0,
    100.0,
    50.0
)

st.sidebar.divider()

if st.sidebar.button(
    "🗑️ ALLES ZURÜCKSETZEN"
):

    st.session_state.portfolio = {}
    st.session_state.transactions = []
    st.session_state.cash = 55000.0

    st.rerun()


# =========================================================
# TABS
# =========================================================

tab_a, tab_b, tab_c, tab_d, tab_e = st.tabs([
    "🔍 Aktien-Analyse",
    "📊 Depot",
    "🎯 Kaufsimulation",
    "🧾 Transaktionen",
    "➕ Aktie hinzufügen"
])


# =========================================================
# TAB A – AKTIENANALYSE
# =========================================================

with tab_a:

    st.header("🔍 Einzelaktien-Analyse")

    ticker = st.selectbox(
        "Aktie auswählen:",
        list(UNIVERSE.keys()),
        key="analysis_ticker"
    )

    data = UNIVERSE[ticker]

    price = data["price"]
    fair = data["fair_value"]

    upside = (
        fair / price - 1
    ) * 100

    recommendation_text = recommendation(ticker)

    st.subheader(
        f"{data['name']} ({ticker})"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Aktueller Kurs",
        f"{price:.2f} €"
    )

    c2.metric(
        "Fair Value",
        f"{fair:.2f} €",
        f"{upside:+.1f}%"
    )

    c3.metric(
        "Quality Score",
        f"{data['quality']}/100"
    )

    c4.metric(
        "KGV",
        f"{data['per']}"
    )

    st.divider()

    if "🟢" in recommendation_text:

        st.success(
            f"### {recommendation_text}"
        )

    elif "🔴" in recommendation_text:

        st.error(
            f"### {recommendation_text}"
        )

    else:

        st.warning(
            f"### {recommendation_text}"
        )

    st.write(
        f"**Sektor:** {data['sector']}"
    )

    st.write(
        f"**Erwartete Rendite 3 Jahre:** "
        f"{data['return_3y']:.2f}% p.a."
    )

    st.write(
        f"**Davon Neubewertung:** "
        f"{data['reval_share']:.2f}% p.a."
    )

    st.write(
        f"**Beta:** {data['beta']:.2f}"
    )

    st.divider()

    st.subheader("🎯 Bewertungszonen")

    buy_10 = fair * 0.90
    buy_20 = fair * 0.80

    z1, z2, z3 = st.columns(3)

    z1.metric(
        "Fair Value",
        f"{fair:.2f} €"
    )

    z2.metric(
        "Kauflimit -10%",
        f"{buy_10:.2f} €"
    )

    z3.metric(
        "Kauflimit -20%",
        f"{buy_20:.2f} €"
    )


# =========================================================
# TAB B – DEPOT
# =========================================================

with tab_b:

    st.header("📊 Mein Depot")

    df = portfolio_dataframe()

    total_value = total_depot_value()
    stocks = total_stock_value()
    cash_value = st.session_state.cash
    quote = stock_quote()

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Gesamtdepot",
        f"{total_value:,.2f} €"
    )

    m2.metric(
        "Aktien",
        f"{stocks:,.2f} €"
    )

    m3.metric(
        "Cash",
        f"{cash_value:,.2f} €"
    )

    m4.metric(
        "Aktienquote",
        f"{quote:.1f}%"
    )

    st.divider()


    # =====================================================
    # AUTOMATISCHE DEPOTWARNUNGEN
    # =====================================================

    if not df.empty:

        st.subheader("⚠️ Depot-Check")

        warnings_found = False

        # Aktienquote
        if quote > max_stock_quote:

            st.error(
                f"🔴 **Aktienquote zu hoch:** "
                f"{quote:.1f}% "
                f"(Limit {max_stock_quote:.1f}%)"
            )

            warnings_found = True

        # Sektoren
        sectors = sector_values()

        for sector, value in sectors.items():

            depot_weight = (
                value
                / total_value
                * 100
            )

            stock_weight = (
                value
                / stocks
                * 100
                if stocks > 0
                else 0
            )

            if depot_weight > max_sector:

                st.error(
                    f"🔴 **Sektor {sector}:** "
                    f"{depot_weight:.1f}% "
                    f"des Gesamtdepots "
                    f"(Limit {max_sector:.1f}%)"
                )

                warnings_found = True

            elif stock_weight >= sector_stock_warning:

                st.warning(
                    f"🟠 **Sektor {sector} stark konzentriert:** "
                    f"{stock_weight:.1f}% des Aktienanteils."
                )

                warnings_found = True

        # Einzelpositionen
        for _, row in df.iterrows():

            weight = (
                row["Wert"]
                / total_value
                * 100
            )

            if weight > max_position:

                st.warning(
                    f"🟠 **Einzelposition {row['Ticker']}:** "
                    f"{weight:.1f}% des Depots "
                    f"(Limit {max_position:.1f}%)"
                )

                warnings_found = True

        if not warnings_found:

            st.success(
                "🟢 **Depotstruktur aktuell innerhalb deiner Limits.**"
            )

    else:

        st.info(
            "Noch keine Aktien im Depot."
        )


    st.divider()


    # =====================================================
    # KAUF
    # =====================================================

    st.subheader("➕ Aktie kaufen")

    buy_ticker = st.selectbox(
        "Aktie",
        list(UNIVERSE.keys()),
        key="buy_ticker"
    )

    buy_col1, buy_col2 = st.columns(2)

    with buy_col1:

        buy_shares = st.number_input(
            "Stückzahl",
            min_value=0.01,
            value=10.0,
            step=1.0,
            key="buy_shares"
        )

    with buy_col2:

        buy_price = st.number_input(
            "Kaufkurs (€)",
            min_value=0.01,
            value=float(
                UNIVERSE[buy_ticker]["price"]
            ),
            step=0.01,
            key="buy_price"
        )

    buy_amount = (
        buy_shares
        * buy_price
    )

    st.info(
        f"Kaufwert: **{buy_amount:,.2f} €**"
    )

    if buy_amount > st.session_state.cash:

        st.error(
            f"❌ Nicht genügend Cash. "
            f"Verfügbar: "
            f"{st.session_state.cash:,.2f} €"
        )

    if st.button(
        "💰 KAUF AUSFÜHREN",
        key="execute_buy"
    ):

        success, message = buy_stock(
            buy_ticker,
            buy_shares,
            buy_price
        )

        if success:

            st.success(
                f"✅ {buy_shares:g} Stück "
                f"{buy_ticker} gekauft."
            )

            st.rerun()

        else:

            st.error(
                f"❌ {message}"
            )


    st.divider()


    # =====================================================
    # VERKAUF
    # =====================================================

    st.subheader("➖ Aktie verkaufen")

    if df.empty:

        st.info(
            "Noch keine Aktien im Depot."
        )

    else:

        sell_ticker = st.selectbox(
            "Position auswählen",
            df["Ticker"].tolist(),
            key="sell_ticker"
        )

        current_pos = (
            st.session_state.portfolio[
                sell_ticker
            ]
        )

        s_col1, s_col2 = st.columns(2)

        with s_col1:

            sell_shares = st.number_input(
                "Zu verkaufende Stückzahl",
                min_value=0.01,
                max_value=float(
                    current_pos["shares"]
                ),
                value=min(
                    1.0,
                    float(
                        current_pos["shares"]
                    )
                ),
                step=1.0,
                key="sell_shares"
            )

        with s_col2:

            sell_price = st.number_input(
                "Verkaufskurs (€)",
                min_value=0.01,
                value=float(
                    UNIVERSE.get(
                        sell_ticker,
                        {}
                    ).get(
                        "price",
                        current_pos["last_price"]
                    )
                ),
                step=0.01,
                key="sell_price"
            )

        sell_amount = (
            sell_shares
            * sell_price
        )

        st.info(
            f"Verkaufswert: "
            f"**{sell_amount:,.2f} €**"
        )

        vc1, vc2 = st.columns(2)

        with vc1:

            if st.button(
                "➖ TEILVERKAUF",
                key="partial_sell"
            ):

                if sell_stock(
                    sell_ticker,
                    sell_shares,
                    sell_price
                ):

                    st.success(
                        f"✅ {sell_shares:g} Stück "
                        f"{sell_ticker} verkauft."
                    )

                    st.rerun()

                else:

                    st.error(
                        "❌ Verkauf nicht möglich."
                    )

        with vc2:

            if st.button(
                "🔴 KOMPLETT VERKAUFEN",
                key="full_sell"
            ):

                full_amount = (
                    current_pos["shares"]
                    * sell_price
                )

                if sell_stock(
                    sell_ticker,
                    current_pos["shares"],
                    sell_price
                ):

                    st.success(
                        f"✅ Position "
                        f"{sell_ticker} komplett verkauft. "
                        f"{full_amount:,.2f} € wurden "
                        f"dem Cash gutgeschrieben."
                    )

                    st.rerun()


    st.divider()


    # =====================================================
    # DEPOTÜBERSICHT
    # =====================================================

    st.subheader("📋 Depotübersicht")

    if df.empty:

        st.info(
            "Das Depot enthält noch keine Positionen."
        )

    else:

        display_df = df.copy()

        display_df["Ø Kaufkurs"] = (
            display_df["Ø Kaufkurs"]
            .map(lambda x: f"{x:,.2f} €")
        )

        display_df["Kurs"] = (
            display_df["Kurs"]
            .map(lambda x: f"{x:,.2f} €")
        )

        display_df["Einstand"] = (
            display_df["Einstand"]
            .map(lambda x: f"{x:,.2f} €")
        )

        display_df["Wert"] = (
            display_df["Wert"]
            .map(lambda x: f"{x:,.2f} €")
        )

        display_df["G&V"] = (
            display_df["G&V"]
            .map(lambda x: f"{x:,.2f} €")
        )

        display_df["G&V %"] = (
            display_df["G&V %"]
            .map(lambda x: f"{x:+.2f}%")
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# TAB C – KAUFSIMULATION
# =========================================================

with tab_c:

    st.header(
        "🎯 Kaufsimulation & Portfolio Fit"
    )

    sim_ticker = st.selectbox(
        "Aktie simulieren:",
        list(UNIVERSE.keys()),
        key="sim_ticker"
    )

    sim_amount = st.number_input(
        "Geplante Kaufsumme (€)",
        min_value=0.0,
        value=1000.0,
        step=250.0,
        key="sim_amount"
    )

    sim_data = UNIVERSE[sim_ticker]

    current_stock_value = total_stock_value()

    current_total = total_depot_value()

    # -----------------------------------------------------
    # WICHTIG:
    # Ein Kauf erhöht NICHT automatisch das Gesamtdepot.
    # Er verschiebt Cash in Aktien.
    # -----------------------------------------------------

    new_stock_value = (
        current_stock_value
        + sim_amount
    )

    new_total = current_total

    new_quote = (
        new_stock_value
        / new_total
        * 100
        if new_total > 0
        else 0
    )

    existing_position = 0

    if sim_ticker in st.session_state.portfolio:

        pos = st.session_state.portfolio[
            sim_ticker
        ]

        existing_position = (
            pos["shares"]
            * sim_data["price"]
        )

    new_position = (
        existing_position
        + sim_amount
    )

    position_weight = (
        new_position
        / new_total
        * 100
        if new_total > 0
        else 0
    )

    # -----------------------------------------------------
    # SEKTOR
    # -----------------------------------------------------

    sector_value = 0

    for ticker_key, pos in (
        st.session_state.portfolio.items()
    ):

        if (
            pos["sector"]
            == sim_data["sector"]
        ):

            sector_value += (
                pos["shares"]
                * UNIVERSE.get(
                    ticker_key,
                    {}
                ).get(
                    "price",
                    pos["last_price"]
                )
            )

    new_sector_value = (
        sector_value
        + sim_amount
    )

    sector_weight_depot = (
        new_sector_value
        / new_total
        * 100
        if new_total > 0
        else 0
    )

    sector_weight_stocks = (
        new_sector_value
        / new_stock_value
        * 100
        if new_stock_value > 0
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Aktienquote",
        f"{stock_quote():.1f}% ➜ "
        f"{new_quote:.1f}%"
    )

    c2.metric(
        "Positionsgewicht",
        f"{position_weight:.1f}%"
    )

    c3.metric(
        "Sektor / Depot",
        f"{sector_weight_depot:.1f}%"
    )

    c4.metric(
        "Sektor / Aktien",
        f"{sector_weight_stocks:.1f}%"
    )

    st.divider()


    # =====================================================
    # TRANCHENLOGIK
    # =====================================================

    if new_quote > max_stock_quote:

        status = "🔴 WARTEN"

        max_buy = 0

        st.error(
            "🔴 Kauf würde deine maximale "
            "Aktienquote überschreiten."
        )

    elif position_weight > max_position:

        status = "🟠 GEDROSSELT"

        max_buy = 0

        st.warning(
            "🟠 Kauf würde die maximale "
            "Einzelposition überschreiten."
        )

    elif sector_weight_depot > max_sector:

        status = "🟠 GEDROSSELT"

        max_buy = 0

        st.warning(
            "🟠 Kauf würde das Sektorlimit "
            "überschreiten."
        )

    elif (
        sector_weight_stocks
        >= sector_stock_warning
    ):

        status = "🟠 ERST-TRANCHE"

        max_buy = min(
            sim_amount,
            1000
        )

        st.warning(
            f"🟠 **Sektor bereits stark vertreten.** "
            f"{sector_weight_stocks:.1f}% "
            f"des Aktienanteils entfallen auf "
            f"{sim_data['sector']}. "
            f"Nur kleine Erst-Tranche."
        )

    else:

        status = "🟢 KAUF MÖGLICH"

        max_buy = sim_amount

        st.success(
            "🟢 Kauf passt zu den aktuellen "
            "Depotlimits."
        )

    st.metric(
        "Empfohlene Kaufgröße",
        f"{max_buy:,.0f} €"
    )

    st.write(
        f"**Fundamentales Urteil:** "
        f"{recommendation(sim_ticker)}"
    )


# =========================================================
# TAB D – TRANSAKTIONEN
# =========================================================

with tab_d:

    st.header("🧾 Transaktionshistorie")

    if (
        len(
            st.session_state.transactions
        )
        == 0
    ):

        st.info(
            "Noch keine Käufe oder Verkäufe gespeichert."
        )

    else:

        trans_df = pd.DataFrame(
            st.session_state.transactions
        )

        st.dataframe(
            trans_df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        total_buys = trans_df.loc[
            trans_df["Typ"] == "KAUF",
            "Betrag"
        ].sum()

        total_sales = trans_df.loc[
            trans_df["Typ"] == "VERKAUF",
            "Betrag"
        ].sum()

        c1, c2 = st.columns(2)

        c1.metric(
            "Käufe gesamt",
            f"{total_buys:,.2f} €"
        )

        c2.metric(
            "Verkäufe gesamt",
            f"{total_sales:,.2f} €"
        )


# =========================================================
# TAB E – NEUE AKTIE HINZUFÜGEN
# =========================================================

with tab_e:

    st.header("➕ Eigene Aktie hinzufügen")

    st.write(
        "Hier kannst du eine Aktie manuell in die "
        "Aktienliste aufnehmen."
    )

    st.info(
        "💡 Du musst dafür keinen bestehenden Eintrag löschen."
    )

    with st.form("add_stock_form"):

        col1, col2 = st.columns(2)

        with col1:

            new_ticker = st.text_input(
                "Ticker / Kürzel",
                placeholder="z.B. BASF.DE"
            )

            new_name = st.text_input(
                "Aktienname",
                placeholder="z.B. BASF SE"
            )

            new_sector = st.text_input(
                "Sektor",
                placeholder="z.B. Chemie"
            )

            new_price = st.number_input(
                "Aktueller Kurs (€)",
                min_value=0.01,
                value=100.0,
                step=0.01
            )

            new_fair_value = st.number_input(
                "Fair Value (€)",
                min_value=0.01,
                value=110.0,
                step=0.01
            )

        with col2:

            new_quality = st.number_input(
                "Quality Score",
                min_value=0,
                max_value=100,
                value=75,
                step=1
            )

            new_per = st.number_input(
                "KGV",
                min_value=0.0,
                value=15.0,
                step=0.1
            )

            new_beta = st.number_input(
                "Beta",
                min_value=0.0,
                value=1.0,
                step=0.01
            )

            new_return = st.number_input(
                "Erwartete Rendite 3 Jahre (% p.a.)",
                min_value=-100.0,
                value=8.0,
                step=0.1
            )

            new_reval = st.number_input(
                "Davon Neubewertung (% p.a.)",
                min_value=-100.0,
                value=2.0,
                step=0.1
            )

        submitted = st.form_submit_button(
            "➕ AKTIE HINZUFÜGEN"
        )

    if submitted:

        clean_ticker = (
            new_ticker
            .strip()
            .upper()
        )

        if not clean_ticker:

            st.error(
                "❌ Bitte ein Aktienkürzel eingeben."
            )

        elif not new_name.strip():

            st.error(
                "❌ Bitte einen Aktiennamen eingeben."
            )

        elif not new_sector.strip():

            st.error(
                "❌ Bitte einen Sektor eingeben."
            )

        elif clean_ticker in UNIVERSE:

            st.warning(
                f"⚠️ {clean_ticker} ist bereits vorhanden."
            )

        else:

            UNIVERSE[clean_ticker] = {

                "name": new_name.strip(),

                "sector": new_sector.strip(),

                "price": float(new_price),

                "fair_value": float(
                    new_fair_value
                ),

                "quality": int(
                    new_quality
                ),

                "per": float(new_per),

                "beta": float(new_beta),

                "return_3y": float(
                    new_return
                ),

                "reval_share": float(
                    new_reval
                ),
            }

            st.session_state.universe = UNIVERSE

            st.success(
                f"✅ {new_name} ({clean_ticker}) "
                f"wurde erfolgreich hinzugefügt."
            )

            st.rerun()


    st.divider()

    st.subheader(
        "📋 Aktuell verfügbare Aktien"
    )

    stock_list = []

    for ticker_key, data in UNIVERSE.items():

        stock_list.append({
            "Ticker": ticker_key,
            "Name": data["name"],
            "Sektor": data["sector"],
            "Kurs": data["price"],
            "Fair Value": data["fair_value"],
            "Quality": data["quality"],
        })

    stock_df = pd.DataFrame(
        stock_list
    )

    st.dataframe(
        stock_df,
        use_container_width=True,
        hide_index=True
    )

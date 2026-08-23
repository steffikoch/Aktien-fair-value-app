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
# BEISPIEL-AKTIEN / FUNDAMENTALDATEN
# =========================================================

UNIVERSE = {
    "AXA": {
        "name": "AXA SA",
        "sector": "Financial Services",
        "price": 43.72,
        "fair_value": 62.15,
        "quality": 89,
        "per": 11.8,
        "beta": 0.59,
        "return_3y": 17.75,
        "reval_share": 12.4,
    },

    "ALV.DE": {
        "name": "Allianz SE",
        "sector": "Financial Services",
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
        "sector": "Communication Services",
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
        "sector": "Technology",
        "price": 195.00,
        "fair_value": 220.00,
        "quality": 88,
        "per": 32.0,
        "beta": 0.95,
        "return_3y": 10.5,
        "reval_share": 4.0,
    },

    "AAPL": {
        "name": "Apple Inc.",
        "sector": "Technology",
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
        "sector": "Technology",
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
        "sector": "Technology",
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

if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}

if "transactions" not in st.session_state:
    st.session_state.transactions = []

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("⚙️ Depot-Parameter")

cash = st.sidebar.number_input(
    "Cash-Bestand (€)",
    min_value=0.0,
    value=55000.0,
    step=500.0
)

max_stock_quote = st.sidebar.slider(
    "Max. Ziel-Aktienquote (%)",
    10.0,
    100.0,
    50.0
)

max_position = st.sidebar.slider(
    "Max. Einzelposition (% vom Depot)",
    1.0,
    20.0,
    5.0
)

max_sector = st.sidebar.slider(
    "Max. Sektor-Limit (% vom Depot)",
    5.0,
    50.0,
    25.0
)

st.sidebar.divider()

if st.sidebar.button("🗑️ ALLES ZURÜCKSETZEN"):
    st.session_state.portfolio = {}
    st.session_state.transactions = []
    st.rerun()

# =========================================================
# HILFSFUNKTIONEN
# =========================================================

def portfolio_dataframe():

    rows = []

    for ticker, pos in st.session_state.portfolio.items():

        current_price = UNIVERSE.get(
            ticker,
            {}
        ).get(
            "price",
            pos["last_price"]
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
        return 0

    return df["Wert"].sum()


def total_depot_value():

    return cash + total_stock_value()


def stock_quote():

    total = total_depot_value()

    if total == 0:
        return 0

    return total_stock_value() / total * 100


def recommendation(ticker):

    data = UNIVERSE[ticker]

    price = data["price"]
    fair = data["fair_value"]

    discount = (fair - price) / fair * 100

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

    old = st.session_state.portfolio.get(ticker)

    if old:

        old_shares = old["shares"]
        old_avg = old["avg_price"]

        new_shares = old_shares + shares

        new_avg = (
            (old_shares * old_avg) +
            (shares * price)
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

    amount = shares * price

    st.session_state.transactions.append({
        "Datum": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "Typ": "KAUF",
        "Ticker": ticker,
        "Stück": shares,
        "Kurs": price,
        "Betrag": amount,
    })


def sell_stock(ticker, shares, price):

    if ticker not in st.session_state.portfolio:
        return False

    pos = st.session_state.portfolio[ticker]

    if shares > pos["shares"]:
        return False

    amount = shares * price

    pos["shares"] -= shares

    st.session_state.transactions.append({
        "Datum": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "Typ": "VERKAUF",
        "Ticker": ticker,
        "Stück": shares,
        "Kurs": price,
        "Betrag": amount,
    })

    if pos["shares"] <= 0.000001:
        del st.session_state.portfolio[ticker]

    return True


# =========================================================
# TABS
# =========================================================

tab_a, tab_b, tab_c, tab_d = st.tabs([
    "🔍 Aktien-Analyse",
    "📊 Depot",
    "🎯 Kaufsimulation",
    "🧾 Transaktionen"
])

# =========================================================
# TAB A – AKTIENANALYSE
# =========================================================

with tab_a:

    st.header("🔍 Einzelaktien-Analyse")

    ticker = st.selectbox(
        "Aktie auswählen:",
        list(UNIVERSE.keys())
    )

    data = UNIVERSE[ticker]

    price = data["price"]
    fair = data["fair_value"]

    upside = (fair / price - 1) * 100

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

    if "🟢 KAUFEN" in recommendation_text:
        st.success(
            f"### {recommendation_text}"
        )
    elif "🔴" in recommendation_text:
        st.error(
            f"### {recommendation_text}"
        )
    elif "🟡" in recommendation_text:
        st.warning(
            f"### {recommendation_text}"
        )
    else:
        st.info(
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

    st.header("📊 Reales Depot")

    df = portfolio_dataframe()

    total_value = total_depot_value()
    stocks = total_stock_value()
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
        f"{cash:,.2f} €"
    )

    m4.metric(
        "Aktienquote",
        f"{quote:.1f}%"
    )

    st.divider()

    # -----------------------------------------------------
    # KAUF
    # -----------------------------------------------------

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

    buy_amount = buy_shares * buy_price

    st.info(
        f"Kaufwert: **{buy_amount:,.2f} €**"
    )

    if st.button(
        "💰 KAUF AUSFÜHREN",
        key="execute_buy"
    ):

        if buy_amount > cash:

            st.error(
                "❌ Nicht genügend Cash."
            )

        else:

            buy_stock(
                buy_ticker,
                buy_shares,
                buy_price
            )

            st.success(
                f"✅ {buy_shares:g} Stück "
                f"{buy_ticker} gekauft."
            )

            st.rerun()

    st.divider()

    # -----------------------------------------------------
    # VERKAUF
    # -----------------------------------------------------

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

        current_pos = st.session_state.portfolio[
            sell_ticker
        ]

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
                    float(current_pos["shares"])
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

        sell_amount = sell_shares * sell_price

        st.info(
            f"Verkaufswert: **{sell_amount:,.2f} €**"
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

        with vc2:

            if st.button(
                "🔴 KOMPLETT VERKAUFEN",
                key="full_sell"
            ):

                if sell_stock(
                    sell_ticker,
                    current_pos["shares"],
                    sell_price
                ):

                    st.success(
                        f"✅ Position {sell_ticker} "
                        f"komplett verkauft."
                    )

                    st.rerun()

    st.divider()

    # -----------------------------------------------------
    # DEPOTÜBERSICHT
    # -----------------------------------------------------

    st.subheader("📋 Depotübersicht")

    if df.empty:

        st.info(
            "Das Depot enthält noch keine Positionen."
        )

    else:

        display_df = df.copy()

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
        step=250.0
    )

    sim_data = UNIVERSE[sim_ticker]

    current_stock_value = total_stock_value()
    current_total = total_depot_value()

    new_stock_value = (
        current_stock_value +
        sim_amount
    )

    new_total = (
        current_total +
        sim_amount
    )

    new_quote = (
        new_stock_value /
        new_total *
        100
        if new_total > 0
        else 0
    )

    existing_position = 0

    if sim_ticker in st.session_state.portfolio:

        pos = st.session_state.portfolio[
            sim_ticker
        ]

        existing_position = (
            pos["shares"] *
            sim_data["price"]
        )

    new_position = (
        existing_position +
        sim_amount
    )

    position_weight = (
        new_position /
        new_total *
        100
        if new_total > 0
        else 0
    )

    # Sektor

    sector_value = 0

    for ticker_key, pos in st.session_state.portfolio.items():

        if pos["sector"] == sim_data["sector"]:

            sector_value += (
                pos["shares"] *
                UNIVERSE.get(
                    ticker_key,
                    {}
                ).get(
                    "price",
                    pos["last_price"]
                )
            )

    new_sector_value = sector_value + sim_amount

    sector_weight_depot = (
        new_sector_value /
        new_total *
        100
        if new_total > 0
        else 0
    )

    stocks_after = new_stock_value

    sector_weight_stocks = (
        new_sector_value /
        stocks_after *
        100
        if stocks_after > 0
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Aktienquote",
        f"{stock_quote():.1f}% ➜ {new_quote:.1f}%"
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

    # -----------------------------------------------------
    # TRANCHENLOGIK
    # -----------------------------------------------------

    if new_quote > max_stock_quote:

        status = "🔴 WARTEN"
        max_buy = 0

        st.error(
            "🔴 Kauf würde deine maximale Aktienquote überschreiten."
        )

    elif position_weight > max_position:

        status = "🟠 GEDROSSELT"
        max_buy = 0

        st.warning(
            "🟠 Kauf würde die maximale Einzelposition überschreiten."
        )

    elif sector_weight_depot > max_sector:

        status = "🟠 GEDROSSELT"
        max_buy = 0

        st.warning(
            "🟠 Kauf würde das Sektorlimit überschreiten."
        )

    elif sector_weight_stocks >= 50:

        status = "🟠 ERST-TRANCHE"
        max_buy = min(
            sim_amount,
            1000
        )

        st.warning(
            "🟠 Sektor bereits stark im Aktienanteil vertreten. "
            "Nur kleine Erst-Tranche."
        )

    else:

        status = "🟢 KAUF MÖGLICH"
        max_buy = sim_amount

        st.success(
            "🟢 Kauf passt zu den aktuellen Depotlimits."
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

    if len(st.session_state.transactions) == 0:

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

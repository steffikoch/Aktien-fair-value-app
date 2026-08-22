import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Fair Value & Aktien-Score", layout="wide")
st.title("📈 Automatische Fair-Value- & Aktien-Analyse")

# Seitenleiste für Parameter
st.sidebar.header("⚙️ Bewertungsparameter")
discount_rate = st.sidebar.number_input("Diskontsatz (%)", min_value=1.0, max_value=20.0, value=10.0, step=0.5) / 100.0
terminal_growth = st.sidebar.number_input("Ewiges Wachstum (%)", min_value=0.0, max_value=5.0, value=2.0, step=0.1) / 100.0
target_pe = st.sidebar.number_input("Ziel-KGV", min_value=5.0, max_value=50.0, value=15.0, step=1.0)

# Hauptbereich: Ticker-Auswahl
quick_select = st.selectbox("Schnellauswahl oder eigene Eingabe:", ["ALV.DE", "AAPL", "MSFT", "SIE.DE", "Manuell"])

if quick_select == "Manuell":
    ticker_input = st.text_input("Gib Ticker oder ISIN ein:", "ALV.DE")
else:
    ticker_input = quick_select

ticker_symbol = ticker_input.upper().strip()

if st.button("Aktie analysieren", type="primary"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # Grunddaten & Währung
        currency = info.get("currency", "EUR")
        currency_symbol = "$" if currency == "USD" else "€" if currency == "EUR" else currency
        
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        eps = info.get("trailingEps", 0) or 0
        fcf = info.get("freeCashflow", 0) or 0
        shares = info.get("sharesOutstanding", 1) or 1
        
        pe_ratio = info.get("trailingPE", 0) or 0
        pb_ratio = info.get("priceToBook", 0) or 0
        ev_ebitda = info.get("enterpriseToEbitda", 0) or 0
        growth = info.get("earningsGrowth", 0.05) or 0.05
        debt_to_equity = (info.get("debtToEquity", 100) or 100) / 100.0

        # Dividenden-Daten
        div_yield = (info.get("dividendYield", 0) or 0) * 100
        payout_ratio = (info.get("payoutRatio", 0) or 0) * 100

        if not price or price == 0:
            st.error("Keine gültigen Kursdaten für diesen Ticker gefunden.")
            st.stop()

        fcf_per_share = fcf / shares if shares > 0 else 0

        # Fair-Value-Berechnungen
        fv_kgv = eps * target_pe if eps > 0 else None
        fv_fcf = fcf_per_share * target_pe if fcf_per_share > 0 else None

        # DCF-Modell
        if fcf_per_share > 0 and discount_rate > terminal_growth:
            cashflows = [fcf_per_share * ((1 + growth) ** i) for i in range(1, 6)]
            pv_cashflows = sum([cf / ((1 + discount_rate) ** i) for i, cf in enumerate(cashflows, 1)])
            terminal_value = (cashflows[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
            pv_terminal_value = terminal_value / ((1 + discount_rate) ** 5)
            fv_dcf = pv_cashflows + pv_terminal_value
        else:
            fv_dcf = None

        # Dynamische Mittelwertbildung (nur gültige Modelle nutzen)
        valid_models = [m for m in [fv_kgv, fv_fcf, fv_dcf] if m is not None]
        fair_value_total = sum(valid_models) / len(valid_models) if valid_models else price
        upside = ((fair_value_total - price) / price) * 100

        # Sterne-Bewertung
        score_growth = "⭐" * (5 if growth > 0.15 else 4 if growth > 0.08 else 3 if growth > 0.02 else 2)
        score_debt = "⭐" * (5 if debt_to_equity < 0.5 else 4 if debt_to_equity < 1.0 else 3 if debt_to_equity < 2.0 else 2)
        score_val = "⭐" * (5 if upside > 20 else 4 if upside > 0 else 2)

        verdict = "🟢 KAUFEN" if upside >= 15 else "🟡 HALTEN" if upside >= -5 else "🔴 VERKAUFEN"

        # Ausgabe
        st.subheader(f"Ergebnis für {info.get('longName', ticker_symbol)}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Aktueller Kurs", f"{price:.2f} {currency_symbol}")
        c2.metric("Gesamt-Fair-Value", f"{fair_value_total:.2f} {currency_symbol}")
        c3.metric("Sicherheitspuffer", f"{upside:+.1f} %")
        c4.metric("Urteil", verdict)

        st.divider()

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### 🎯 Fair-Value-Verfahren")
            st.write(f"**DCF-Modell:** {f'{fv_dcf:.2f} {currency_symbol}' if fv_dcf else 'N/A'}")
            st.write(f"**KGV-Modell:** {f'{fv_kgv:.2f} {currency_symbol}' if fv_kgv else 'N/A'}")
            st.write(f"**FCF-Modell:** {f'{fv_fcf:.2f} {currency_symbol}' if fv_fcf else 'N/A'}")
            st.write(f"**KGV:** {pe_ratio:.1f} | **KBV:** {pb_ratio:.1f} | **EV/EBITDA:** {ev_ebitda:.1f}")

        with col_r:
            st.markdown("### ⭐ Automatische Bewertung")
            st.write(f"**Wachstum:** {score_growth}")
            st.write(f"**Verschuldung:** {score_debt}")
            st.write(f"**Bewertung / Upside:** {score_val}")

        st.divider()

        # Neuer Bereich: Dividenden & Kursverlauf
        c_div, c_chart = st.columns(2)
        
        with c_div:
            st.markdown("### 💰 Dividenden-Analyse")
            st.write(f"**Dividendenrendite:** {div_yield:.2f} %")
            st.write(f"**Ausschüttungsquote (Payout Ratio):** {payout_ratio:.1f} %")

        with c_chart:
            st.markdown("### 📉 Kursverlauf (1 Jahr)")
            hist = ticker.history(period="1y")
            if not hist.empty:
                st.line_chart(hist["Close"])

    except Exception as e:
        st.error(f"Fehler bei der Analyse: {e}")
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Fair Value & Aktien-Score", layout="wide")
st.title("📈 Automatische Fair-Value- & Aktien-Analyse")

# Seitenleiste für Annahmen
st.sidebar.header("⚙️ Bewertungsparameter")
discount_rate = st.sidebar.number_input("Diskontsatz (%)", min_value=1.0, max_value=20.0, value=10.0, step=0.5) / 100.0
terminal_growth = st.sidebar.number_input("Ewiges Wachstum (%)", min_value=0.0, max_value=5.0, value=2.0, step=0.1) / 100.0
target_pe = st.sidebar.number_input("Ziel-KGV", min_value=5.0, max_value=50.0, value=15.0, step=1.0)

# Hauptbereich: Ticker-Auswahl
quick_select = st.selectbox("Schnellauswahl oder eigene Eingabe:", ["ALV.DE", "AAPL", "MSFT", "SIE.DE", "Manuell"])

if quick_select == "Manuell":
    ticker_input = st.text_input("Gib Ticker oder ISIN ein:", "ALV.DE")
else:
    ticker_input = quick_select

ticker_symbol = ticker_input.upper().strip()

if st.button("Aktie analysieren", type="primary"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # Grunddaten & Währung
        currency = info.get("currency", "EUR")
        currency_symbol = "$" if currency == "USD" else "€" if currency == "EUR" else currency
        
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        eps = info.get("trailingEps", 0) or 0
        fcf = info.get("freeCashflow", 0) or 0
        shares = info.get("sharesOutstanding", 1) or 1
        
        pe_ratio = info.get("trailingPE", 0) or 0
        pb_ratio = info.get("priceToBook", 0) or 0
        ev_ebitda = info.get("enterpriseToEbitda", 0) or 0
        growth = info.get("earningsGrowth", 0.05) or 0.05
        debt_to_equity = (info.get("debtToEquity", 100) or 100) / 100.0

        if not price or price == 0:
            st.error("Keine gültigen Kursdaten für diesen Ticker gefunden.")
            st.stop()

        fcf_per_share = fcf / shares if shares > 0 else 0

        # Fair-Value-Berechnungen
        fv_kgv = eps * target_pe if eps > 0 else price
        fv_fcf = fcf_per_share * target_pe if fcf_per_share > 0 else price

        # DCF-Modell
        if fcf_per_share > 0 and discount_rate > terminal_growth:
            cashflows = [fcf_per_share * ((1 + growth) ** i) for i in range(1, 6)]
            pv_cashflows = sum([cf / ((1 + discount_rate) ** i) for i, cf in enumerate(cashflows, 1)])
            terminal_value = (cashflows[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
            pv_terminal_value = terminal_value / ((1 + discount_rate) ** 5)
            fv_dcf = pv_cashflows + pv_terminal_value
        else:
            fv_dcf = price

        fair_value_total = (fv_kgv + fv_fcf + fv_dcf) / 3.0
        upside = ((fair_value_total - price) / price) * 100

        # Sterne-Bewertung
        score_growth = "⭐" * (5 if growth > 0.15 else 4 if growth > 0.08 else 3 if growth > 0.02 else 2)
        score_debt = "⭐" * (5 if debt_to_equity < 0.5 else 4 if debt_to_equity < 1.0 else 3 if debt_to_equity < 2.0 else 2)
        score_val = "⭐" * (5 if upside > 20 else 4 if upside > 0 else 2)

        verdict = "🟢 KAUFEN" if upside >= 15 else "🟡 HALTEN" if upside >= -5 else "🔴 VERKAUFEN"

        # Ausgabe
        st.subheader(f"Ergebnis für {info.get('longName', ticker_symbol)}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Aktueller Kurs", f"{price:.2f} {currency_symbol}")
        c2.metric("Gesamt-Fair-Value", f"{fair_value_total:.2f} {currency_symbol}")
        c3.metric("Sicherheitspuffer", f"{upside:+.1f} %")
        c4.metric("Urteil", verdict)

        st.divider()

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("### 🎯 Fair-Value-Verfahren")
            st.write(f"**DCF-Modell:** {fv_dcf:.2f} {currency_symbol}")
            st.write(f"**KGV-Modell:** {fv_kgv:.2f} {currency_symbol}")
            st.write(f"**FCF-Modell:** {fv_fcf:.2f} {currency_symbol}")
            st.write(f"**KGV:** {pe_ratio:.1f} | **KBV:** {pb_ratio:.1f} | **EV/EBITDA:** {ev_ebitda:.1f}")

        with col_r:
            st.markdown("### ⭐ Automatische Bewertung")
            st.write(f"**Wachstum:** {score_growth}")
            st.write(f"**Verschuldung:** {score_debt}")
            st.write(f"**Bewertung / Upside:** {score_val}")

    except Exception as e:
        st.error(f"Fehler bei der Analyse: {e}")


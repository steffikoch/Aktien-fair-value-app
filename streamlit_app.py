import streamlit as st
import yfinance as yf
import json
import os

st.set_page_config(page_title="Fair Value & Watchlist Alerts", layout="wide")
st.title("📈 Fair-Value-Analyse, Watchlist & Risikocheck")

WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"ALV.DE": 220.0, "AAPL": 170.0, "MSFT": 380.0, "VC": 95.0, "NEE": 80.0}

def save_watchlist(data):
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        st.error(f"Fehler beim Speichern der Watchlist: {e}")

if "watchlist_data" not in st.session_state:
    st.session_state.watchlist_data = load_watchlist()

# Seitenleiste: Parameter
st.sidebar.header("⚙️ Bewertungsparameter")
discount_rate = st.sidebar.number_input("Diskontsatz (%)", min_value=1.0, max_value=20.0, value=10.0, step=0.5) / 100.0
terminal_growth = st.sidebar.number_input("Ewiges Wachstum (%)", min_value=0.0, max_value=5.0, value=2.0, step=0.1) / 100.0
target_pe = st.sidebar.number_input("Ziel-KGV / Vielfaches", min_value=5.0, max_value=50.0, value=15.0, step=1.0)

tab1, tab2 = st.tabs(["🔍 Einzelanalyse", "📋 Watchlist & Kauflimits"])

# TAB 1: EINZELANALYSE
with tab1:
    quick_select = st.selectbox("Wähle aus deinen Favoriten oder gebe manuell ein:", ["Manuell"] + list(st.session_state.watchlist_data.keys()))
    ticker_input = st.text_input("Gib Ticker ein:", "NEE") if quick_select == "Manuell" else quick_select
    ticker_symbol = ticker_input.upper().strip()

    if st.button("Aktie analysieren", type="primary"):
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            currency = info.get("currency", "EUR")
            currency_symbol = "$" if currency == "USD" else "€" if currency == "EUR" else currency
            
            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            eps = info.get("trailingEps", 0) or 0
            shares = info.get("sharesOutstanding", 1) or 1
            fcf = info.get("freeCashflow", 0) or 0
            
            pe_ratio = info.get("trailingPE", 0) or 0
            pb_ratio = info.get("priceToBook", 0) or 0
            ev_ebitda = info.get("enterpriseToEbitda", 0) or 0
            
            beta = info.get("beta", 1.0) or 1.0
            profit_margins = (info.get("profitMargins", 0) or 0) * 100
            sector = info.get("sector", "")

            # Dividendenrendite sauber berechnen und Plausibilität prüfen
raw_div = info.get("dividendYield") or 0

if raw_div > 0:
    if raw_div > 1.0 and raw_div <= 20.0:
        div_yield = raw_div
    elif raw_div <= 1.0:
        div_yield = raw_div * 100
    else:
        div_rate = info.get("dividendRate") or 0
        div_yield = (div_rate / price * 100) if price > 0 and div_rate > 0 else 0.0
else:
    div_yield = 0.0

            

            if not price or price == 0:
                st.error("Keine gültigen Kursdaten für diesen Ticker gefunden.")
                st.stop()

            # 1. Basis-Metrik für Cashflow bestimmen
            fcf_per_share = fcf / shares if shares > 0 else 0
            base_cashflow_per_share = fcf_per_share

            # Korrektur für kapitalintensive Branchen (Utilities, Real Estate) oder hohes CapEx bei hoher Profitabilität
            fcf_correction_applied = False
            if sector in ["Utilities", "Real Estate", "Financial Services"] or (fcf_per_share < (eps * 0.5) and profit_margins > 10.0):
                base_cashflow_per_share = max(eps, fcf_per_share)
                fcf_correction_applied = True

            # 2. Wachstumsrate festlegen
            raw_growth = info.get("earningsGrowth", 0.05) or 0.05
            dcf_growth = max(0.04, min(raw_growth, 0.15))

            # 3. KGV-Modell
            if eps > 0 and (pe_ratio <= 80 or pe_ratio == 0):
                fv_kgv = eps * target_pe
            else:
                fv_kgv = None

            # 4. Cashflow / Multiplikator-Modell
            fv_fcf = base_cashflow_per_share * target_pe if base_cashflow_per_share > 0 else None

            # 5. DCF-Modell
            if base_cashflow_per_share > 0 and discount_rate > terminal_growth:
                cashflows = [base_cashflow_per_share * ((1 + dcf_growth) ** i) for i in range(1, 6)]
                pv_cashflows = sum([cf / ((1 + discount_rate) ** i) for i, cf in enumerate(cashflows, 1)])
                terminal_value = (cashflows[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
                fv_dcf = pv_cashflows + (terminal_value / ((1 + discount_rate) ** 5))
            else:
                fv_dcf = None

            # Gesamtwert berechnen
            valid_models = [m for m in [fv_kgv, fv_fcf, fv_dcf] if m is not None]
            fair_value_total = sum(valid_models) / len(valid_models) if valid_models else price
            upside = ((fair_value_total - price) / price) * 100

            # Optimierte Urteilslogik (Korridor -15% bis +15% als neutral/HALTEN)
            valuation_text = f"🟢 **Unterbewertet um {upside:.1f} %**" if upside > 0 else f"🔴 **Überbewertet um {abs(upside):.1f} %**"
            verdict = "🟢 KAUFEN" if upside >= 15 else "🟡 HALTEN" if upside >= -15 else "🔴 VERKAUFEN"

            st.subheader(f"Ergebnis für {info.get('longName', ticker_symbol)}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Aktueller Kurs", f"{price:.2f} {currency_symbol}")
            c2.metric("Gesamt-Fair-Value", f"{fair_value_total:.2f} {currency_symbol}")
            c3.metric("Sicherheitspuffer", f"{upside:+.1f} %")
            c4.metric("Urteil", verdict)

            st.info(f"Einschätzung zur Bewertung: {valuation_text}")
            if fcf_correction_applied:
                st.caption("ℹ️ **Hinweis:** Da es sich um ein kapitalintensives Unternehmen / Versorger handelt, wurde das FCF-/DCF-Modell auf Basis der Ertragskraft bereinigt.")
            
            st.divider()

            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown("### 🎯 Fair-Value-Verfahren")
                st.write(f"**DCF-Modell:** {f'{fv_dcf:.2f} {currency_symbol}' if fv_dcf else 'N/A'}")
                st.write(f"**KGV-Modell:** {f'{fv_kgv:.2f} {currency_symbol}' if fv_kgv else 'Ausreißer (Ignoriert)'}")
                st.write(f"**FCF-Modell:** {f'{fv_fcf:.2f} {currency_symbol}' if fv_fcf else 'N/A'}")
            with col_r:
                st.markdown("### 📊 Risikocheck & Qualität")
                st.write(f"**Beta (Schwankung):** {beta:.2f} " + ("🟢 (Ruhig)" if beta < 1 else "🔴 (Schwankungsintensiv)"))
                st.write(f"**Nettomarge:** {profit_margins:.1f} %")
                st.write(f"**KGV:** {pe_ratio:.1f} | **KBV:** {pb_ratio:.1f} | **EV/EBITDA:** {ev_ebitda:.1f}")
                st.write(f"**Dividendenrendite:** {div_yield:.2f} %")

            st.divider()
            hist = ticker.history(period="1y")
            if not hist.empty:
                st.markdown("### 📉 Kursverlauf (1 Jahr)")
                st.line_chart(hist["Close"])

        except Exception as e:
            st.error(f"Fehler bei der Analyse: {e}")

# TAB 2: WATCHLIST & PREIS-ALERTS
with tab2:
    st.subheader("📋 Watchlist & Kauflimits bearbeiten")

    edited_data = []
    for sym, limit in list(st.session_state.watchlist_data.items()):
        edited_data.append({"Ticker": sym, "Kauflimit": limit})

    st.write("Bearbeite deine Kauflimits direkt in der Tabelle (Änderungen werden automatisch gespeichert):")
    edited_df = st.data_editor(
        edited_data,
        num_rows="dynamic",
        key="watchlist_editor"
    )

    if edited_df is not None:
        new_dict = {}
        for row in edited_df:
            if row.get("Ticker"):
                t_name = str(row["Ticker"]).upper().strip()
                t_limit = float(row.get("Kauflimit", 0)) if row.get("Kauflimit") else 0.0
                new_dict[t_name] = t_limit
        
        if new_dict != st.session_state.watchlist_data:
            st.session_state.watchlist_data = new_dict
            save_watchlist(new_dict)

    st.divider()

    if st.button("🔄 Kurse & Signale prüfen", type="primary"):
        alerts_triggered = []
        rows = []

        for sym, target_price in st.session_state.watchlist_data.items():
            try:
                t = yf.Ticker(sym)
                i = t.info
                p = i.get("currentPrice") or i.get("regularMarketPrice", 0)
                curr = i.get("currency", "EUR")
                curr_sym = "$" if curr == "USD" else "€" if curr == "EUR" else curr
                
                diff_pct = ((p - target_price) / target_price) * 100 if target_price > 0 else 0
                
                if p <= target_price and target_price > 0:
                    status = "🚨 ZIELPREIS ERREICHT!"
                    alerts_triggered.append(f"**{sym}**: Kurs ({p:.2f} {curr_sym}) unter Limit ({target_price:.2f} {curr_sym})!")
                else:
                    status = f"⏳ Noch {diff_pct:.1f} % entfernt"

                rows.append({
                    "Ticker": sym,
                    "Name": i.get("shortName", sym),
                    "Aktueller Kurs": f"{p:.2f} {curr_sym}",
                    "Dein Kauflimit": f"{target_price:.2f} {curr_sym}",
                    "Status / Signal": status
                })
            except:
                rows.append({"Ticker": sym, "Name": "Fehler", "Aktueller Kurs": "-", "Dein Kauflimit": f"{target_price:.2f}", "Status / Signal": "Fehler"})

        if alerts_triggered:
            for alert in alerts_triggered:
                st.success(f"🎯 **KAUFSIGNAL:** {alert}")
        else:
            st.info("Aktuell hat keine Aktie in deiner Watchlist dein Kauflimit unterschritten.")

        st.table(rows)


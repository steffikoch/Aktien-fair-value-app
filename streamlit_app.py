import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page Config
st.set_page_config(page_title="4-Score Multi-Depot Engine", layout="wide", page_icon="📈")

st.title("📈 Multi-Aktien Depot- & Allokations-Engine")
st.caption("Vergleichende Analyse deines Depots (65.000 € Basis) mit 10%-Limit & 1.000 € Steuer-Freibetrag")

# =============================================================
# HELPER: ENHANCED 4-SCORE BERECHNUNG MIT FIXEM FREIBETRAG
# =============================================================
def analyze_stock_4score(symbol, current_position_val, total_portfolio_val, max_weight_limit=10.0, tax_free_allowance=1000.0):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
        if not price or price <= 0:
            return None

        curr = info.get('currency', 'EUR')
        curr_sym = "€" if curr == "EUR" else ("$" if curr == "USD" else curr)
        
        net_margin = (info.get('profitMargins') or 0.0) * 100
        roe = (info.get('returnOnEquity') or 0.0) * 100
        fcf = info.get('freeCashflow')
        eps_growth = (info.get('earningsGrowth') or 0.0) * 100
        rev_growth = (info.get('revenueGrowth') or 0.0) * 100
        beta = info.get('beta')
        total_cash = info.get('totalCash', 0) or 0
        total_debt = info.get('totalDebt', 0) or 0
        shares = info.get('sharesOutstanding', 0) or 0
        eps = info.get('forwardEps') or info.get('trailingEps') or 0.0
        ebitda = info.get('ebitda', 0) or 0
        
        net_cash_ps = ((total_cash - total_debt) / shares) if shares > 0 else 0.0
        medium_term_growth = (eps_growth * 0.6) + (rev_growth * 0.4)

        # 1. Quality Score
        p_score = 15 if net_margin >= 15 else (10 if net_margin >= 5 else (4 if net_margin > 0 else 0))
        p_score += 10 if roe >= 15 else (6 if roe >= 8 else (2 if roe > 0 else 0))
        g_score = 20 if medium_term_growth >= 12.0 else (13 if medium_term_growth >= 5.0 else (7 if medium_term_growth >= 0.0 else 2))
        
        if net_cash_ps > 0: b_score = 20
        else:
            debt_to_ebitda = (total_debt / ebitda) if ebitda > 0 else 99
            b_score = 15 if debt_to_ebitda < 3.0 else (10 if debt_to_ebitda < 5.0 and fcf and fcf > 0 else 4)

        c_score = 20 if fcf and fcf > 0 else (10 if fcf == 0 or fcf is None else 0)
        r_score = 15 if beta and beta < 1.0 else (9 if beta and beta < 1.3 else 3)
        quality_score = min(100, p_score + g_score + b_score + c_score + r_score)

        # 2. Fair Value
        target_pe = min(22.0, max(11.0, 12.0 + (max(0, medium_term_growth) * 0.4)))
        fv_vals = []
        if eps > 0: fv_vals.append((eps * target_pe) + max(0, net_cash_ps))
        if fcf and shares > 0 and fcf > 0: fv_vals.append(((fcf / shares) * target_pe) + max(0, net_cash_ps))
        
        fair_value = np.mean(fv_vals) if fv_vals else price
        mos = ((fair_value - price) / price) * 100 if fair_value > 0 else 0.0

        # 3. Steueroptimierte Renditeberechnung
        raw_div_yield = info.get('dividendYield') or 0.0
        div_yield_gross = raw_div_yield if raw_div_yield > 1.0 else raw_div_yield * 100.0
        cap_gain_5y_gross = (((fair_value / price) ** (1 / 5) - 1) * 100) if (price > 0 and fair_value > price) else 0.0
        
        gross_annual_income = (current_position_val * (div_yield_gross / 100.0)) + (current_position_val * (cap_gain_5y_gross / 100.0))
        
        TAX_RATE = 0.26375
        if gross_annual_income <= tax_free_allowance:
            net_div_yield = div_yield_gross
            net_cap_gain_5y = cap_gain_5y_gross
        else:
            taxable_ratio = (gross_annual_income - tax_free_allowance) / gross_annual_income if gross_annual_income > 0 else 1.0
            effective_tax_rate = TAX_RATE * taxable_ratio
            net_div_yield = div_yield_gross * (1.0 - effective_tax_rate)
            net_cap_gain_5y = cap_gain_5y_gross * (1.0 - effective_tax_rate)

        ret_5y_no_drip = net_cap_gain_5y + net_div_yield

        # 4. Depot-Allokation (10 % Limit = 6.500 € bei 65.000 € Depot)
        weight_pct = (current_position_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
        max_allowed_val = (max_weight_limit / 100.0) * total_portfolio_val
        max_buy_eur = max(0.0, max_allowed_val - current_position_val)

        # Urteil
        if weight_pct >= max_weight_limit:
            action = f"🔴 LIMIT ERREICHT ({weight_pct:.1f}%)"
        elif quality_score >= 65 and mos >= 12:
            action = "🟡 NACHKAUF GEDROSSELT" if weight_pct >= (max_weight_limit - 1.0) else "🟢 NACHKAUF"
        else:
            action = "🟡 BEOBACHTEN"

        return {
            "Ticker": symbol,
            "Name": info.get('shortName', symbol),
            "Kurs": f"{price:.2f} {curr_sym}",
            "Fair Value": f"{fair_value:.2f} {curr_sym}",
            "Puffer": f"{mos:+.1f} %",
            "Quality": f"{quality_score}/100",
            "Opt. Netto-Rendite 5J (p.a.)": f"{ret_5y_no_drip:.2f} %",
            "Bestand (€)": f"{current_position_val:,.2f} €",
            "Gewicht": f"{weight_pct:.1f} %",
            "Max. Nachkauf (€)": f"{max_buy_eur:,.2f} €",
            "Urteil": action
        }
    except Exception:
        return None

# =============================================================
# EINGABE SIDEBAR
# =============================================================
st.sidebar.header("⚙️ Depot-Konfiguration")
depot_val_input = st.sidebar.number_input("Gesamtdepot-Wert (€):", min_value=1.0, value=65000.0, step=1000.0)
limit_pct_input = st.sidebar.number_input("Max. Gewicht pro Aktie (%):", min_value=1.0, max_value=50.0, value=10.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.subheader("💶 Steuer-Einstellung")
tax_allowance_input = st.sidebar.number_input("Sparer-Pauschbetrag (€):", min_value=0.0, value=1000.0, step=100.0)

st.sidebar.markdown("---")
st.sidebar.subheader("➕ Aktie hinzufügen / bearbeiten")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = [
        {"ticker": "DTE.DE", "value": 5112.0},
        {"ticker": "AAPL", "value": 3200.0}
    ]

new_ticker = st.sidebar.text_input("Ticker (z. B. DTE.DE, AAPL, MSFT):", value="").strip().upper()
new_val = st.sidebar.number_input("Aktueller Positions-Wert (€):", min_value=0.0, value=0.0, step=100.0)

if st.sidebar.button("Aktie speichern / aktualisieren"):
    if new_ticker:
        found = False
        for item in st.session_state.portfolio:
            if item["ticker"] == new_ticker:
                item["value"] = new_val
                found = True
                break
        if not found:
            st.session_state.portfolio.append({"ticker": new_ticker, "value": new_val})
        st.sidebar.success(f"{new_ticker} gespeichert!")

# LÖSCH-FUNKTION IN DER SIDEBAR
if st.session_state.portfolio:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🗑️ Aktie entfernen")
    ticker_list = [item["ticker"] for item in st.session_state.portfolio]
    ticker_to_remove = st.sidebar.selectbox("Wähle eine Aktie zum Löschen:", options=ticker_list)
    
    if st.sidebar.button("Aktie aus Liste löschen"):
        st.session_state.portfolio = [item for item in st.session_state.portfolio if item["ticker"] != ticker_to_remove]
        st.sidebar.warning(f"{ticker_to_remove} wurde entfernt!")
        st.rerun()

# =============================================================
# HAUPTANSICHT: PORTFOLIO VERGLEICHSTABELLE
# =============================================================
st.subheader("📋 Depot-Vergleichsmatrix")

results = []
for item in st.session_state.portfolio:
    res = analyze_stock_4score(item["ticker"], item["value"], depot_val_input, limit_pct_input, tax_allowance_input)
    if res:
        results.append(res)

if results:
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)
    
    total_invested = sum(item["value"] for item in st.session_state.portfolio)
    cash_left = max(0.0, depot_val_input - total_invested)
    allocated_pct = (total_invested / depot_val_input) * 100
    
    st.markdown("---")
    st.markdown("### 📊 Depot-Gesamtübersicht")
    m1, m2, m3 = st.columns(3)
    m1.metric("Erfasstes Aktienvolumen", f"{total_invested:,.2f} €", f"{allocated_pct:.1f} % vom Gesamtdepot")
    m2.metric("Verbleibender Freiraum / ETF & Cash", f"{cash_left:,.2f} €", f"{100 - allocated_pct:.1f} % Ungebunden")
    m3.metric("Max. Limit pro Einzelaktie", f"{(depot_val_input * limit_pct_input / 100):,.2f} €", f"{limit_pct_input:.1f} % Obergrenze")
else:
    st.info("Keine Aktien im Portfolio. Füge Ticker über die Sidebar hinzu.")

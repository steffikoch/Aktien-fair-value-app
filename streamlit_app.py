import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="Depot-Steuerungs-Engine", layout="wide", page_icon="📈")

# Überschrift & Untertitel
st.title("📈 Depot-Steuerungs-Engine")
st.caption("Depotvergleich – 65.000 € Basis | 10 % Einzelpositionslimit | 1.000 € Sparer-Pauschbetrag")

# =============================================================
# HELPER: AUTOMATISCHE TICKER-SUCHE
# =============================================================
def search_ticker(query):
    """Sucht nach Unternehmensnamen/Kürzeln und gibt das beste Yahoo-Ticker-Symbol zurück."""
    clean_query = query.strip()
    if not clean_query:
        return ""
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={clean_query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if data.get('quotes') and len(data['quotes']) > 0:
            return data['quotes'][0]['symbol']
    except Exception:
        pass
    return clean_query.upper()

# =============================================================
# HELPER: ENHANCED 4-SCORE BERECHNUNG MIT G&V
# =============================================================
def analyze_stock_4score(symbol, shares_count, buy_price, total_portfolio_val, max_weight_limit=10.0, tax_free_allowance=1000.0):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
        if not price or price <= 0:
            return None

        curr = info.get('currency', 'EUR')
        curr_sym = "€" if curr == "EUR" else ("$" if curr == "USD" else curr)
        
        # Positions- und G&V-Berechnung
        cost_basis = shares_count * buy_price
        current_position_val = shares_count * price
        pnl_eur = current_position_val - cost_basis
        pnl_pct = ((price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0

        net_margin = (info.get('profitMargins') or 0.0) * 100
        roe = (info.get('returnOnEquity') or 0.0) * 100
        fcf = info.get('freeCashflow')
        eps_growth = (info.get('earningsGrowth') or 0.0) * 100
        rev_growth = (info.get('revenueGrowth') or 0.0) * 100
        beta = info.get('beta')
        total_cash = info.get('totalCash', 0) or 0
        total_debt = info.get('totalDebt', 0) or 0
        shares_out = info.get('sharesOutstanding', 0) or 0
        eps = info.get('forwardEps') or info.get('trailingEps') or 0.0
        ebitda = info.get('ebitda', 0) or 0
        
        net_cash_ps = ((total_cash - total_debt) / shares_out) if shares_out > 0 else 0.0
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

        # 2. Fair Value (Rein fundamental)
        target_pe = min(22.0, max(11.0, 12.0 + (max(0, medium_term_growth) * 0.4)))
        fv_vals = []
        if eps > 0: fv_vals.append((eps * target_pe) + max(0, net_cash_ps))
        if fcf and shares_out > 0 and fcf > 0: fv_vals.append(((fcf / shares_out) * target_pe) + max(0, net_cash_ps))
        
        fair_value = np.mean(fv_vals) if fv_vals else price
        mos = ((fair_value - price) / price) * 100 if fair_value > 0 else 0.0

        # 3. Netto-Rendite (inkl. Sparer-Pauschbetrag)
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

        # 4. Depot-Allokation & Freie Kapazität
        weight_pct = (current_position_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
        max_allowed_val = (max_weight_limit / 100.0) * total_portfolio_val
        remaining_cap_eur = max(0.0, max_allowed_val - current_position_val)

        # Ampel-Logik
        if weight_pct >= max_weight_limit:
            action = f"🔴 SPERRE ({weight_pct:.1f}%)"
        elif weight_pct >= 8.0:
            action = f"🟠 KLEINER NACHKAUF ({weight_pct:.1f}%)"
        elif weight_pct >= 6.0:
            action = f"🟡 GEDROSSELT ({weight_pct:.1f}%)"
        else:
            action = f"🟢 KAUF MÖGLICH ({weight_pct:.1f}%)"

        pnl_str = f"{'+' if pnl_eur >= 0 else ''}{pnl_eur:,.2f} € ({'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%)"

        return {
            "Ticker": symbol,
            "Name": info.get('shortName', symbol),
            "Stückzahl": f"{shares_count:,.2f}",
            "Kaufkurs": f"{buy_price:.2f} {curr_sym}",
            "Akt. Kurs": f"{price:.2f} {curr_sym}",
            "Einstand (€)": f"{cost_basis:,.2f} €",
            "Akt. Wert (€)": f"{current_position_val:,.2f} €",
            "G&V Total": pnl_str,
            "Fair Value": f"{fair_value:.2f} {curr_sym}",
            "Quality": f"{quality_score}/100",
            "Opt. Rendite": f"{ret_5y_no_drip:.2f} %",
            "Gewicht": f"{weight_pct:.1f} %",
            "Freie Kap. (€)": f"{remaining_cap_eur:,.2f} €",
            "Status": action,
            "raw_cost_basis": cost_basis,
            "raw_current_val": current_position_val,
            "raw_pnl": pnl_eur
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
st.sidebar.subheader("🎯 Aktienquote Zielbereich")
target_stock_quote_min = st.sidebar.slider("Ziel-Aktienquote Min (%)", 0, 100, 10)
target_stock_quote_max = st.sidebar.slider("Ziel-Aktienquote Max (%)", 0, 100, 20)

st.sidebar.markdown("---")
st.sidebar.subheader("💶 Steuer-Einstellung")
tax_allowance_input = st.sidebar.number_input("Sparer-Pauschbetrag (€):", min_value=0.0, value=1000.0, step=100.0)

st.sidebar.markdown("---")
st.sidebar.subheader("➕ Aktie hinzufügen / bearbeiten")

if "portfolio" not in st.session_state:
    st.session_state.portfolio = [
        {"ticker": "MUV2.DE", "shares": 14.0, "buy_price": 543.30}
    ]

input_search = st.sidebar.text_input("Name oder Ticker (z. B. Münchener Rück, DTE.DE):", value="").strip()
new_shares = st.sidebar.number_input("Stückzahl:", min_value=0.0, value=0.0, step=1.0)
new_buy_price = st.sidebar.number_input("Kaufkurs pro Aktie (€):", min_value=0.0, value=0.0, step=1.0)

if st.sidebar.button("Aktie speichern / aktualisieren"):
    if input_search and new_shares > 0 and new_buy_price > 0:
        with st.sidebar.status("Suche Ticker-Symbol..."):
            resolved_ticker = search_ticker(input_search)
        
        if resolved_ticker:
            found = False
            for item in st.session_state.portfolio:
                if item["ticker"] == resolved_ticker:
                    item["shares"] = new_shares
                    item["buy_price"] = new_buy_price
                    found = True
                    break
            if not found:
                st.session_state.portfolio.append({
                    "ticker": resolved_ticker, 
                    "shares": new_shares, 
                    "buy_price": new_buy_price
                })
            st.sidebar.success(f"{resolved_ticker} ({input_search}) gespeichert!")
            st.rerun()

# Löschfunktion
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
st.subheader("📋 Einzelaktien-Matrix, G&V & Kapazitäten")

results = []
for item in st.session_state.portfolio:
    res = analyze_stock_4score(
        item["ticker"], 
        item["shares"], 
        item["buy_price"], 
        depot_val_input, 
        limit_pct_input, 
        tax_allowance_input
    )
    if res:
        results.append(res)

if results:
    df_raw = pd.DataFrame(results)
    
    display_cols = [
        "Ticker", "Name", "Stückzahl", "Kaufkurs", "Akt. Kurs", 
        "Einstand (€)", "Akt. Wert (€)", "G&V Total", 
        "Fair Value", "Quality", "Opt. Rendite", 
        "Gewicht", "Freie Kap. (€)", "Status"
    ]
    st.dataframe(df_raw[display_cols], use_container_width=True)
    
    total_cost = df_raw["raw_cost_basis"].sum()
    total_current_val = df_raw["raw_current_val"].sum()
    total_pnl_eur = df_raw["raw_pnl"].sum()
    total_pnl_pct = ((total_current_val - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
    
    cash_left = max(0.0, depot_val_input - total_current_val)
    allocated_pct = (total_current_val / depot_val_input) * 100
    
    if allocated_pct < target_stock_quote_min:
        quote_status = f"🟢 {allocated_pct:.1f}% (Unterhalb Zielbereich {target_stock_quote_min}-{target_stock_quote_max}%)"
    elif allocated_pct <= target_stock_quote_max:
        quote_status = f"🟢 {allocated_pct:.1f}% (Im Zielbereich {target_stock_quote_min}-{target_stock_quote_max}%)"
    else:
        quote_status = f"🔴 {allocated_pct:.1f}% (Oberhalb Zielbereich {target_stock_quote_min}-{target_stock_quote_max}%)"

    st.markdown("---")
    st.markdown("### 📊 Depot-Gesamtübersicht & Performance")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gesamteinstand Aktien", f"{total_cost:,.2f} €")
    c2.metric("Aktueller Wert Aktien", f"{total_current_val:,.2f} €", f"{allocated_pct:.1f} % Quote")
    c3.metric("Gesamt G&V Aktien", f"{total_pnl_eur:,.2f} €", f"{total_pnl_pct:+.2f} %")
    c4.metric("ETF / Cash / Ungebunden", f"{cash_left:,.2f} €", f"{100 - allocated_pct:.1f} % Freiraum")
    
    st.info(f"**Aktienquote Status:** {quote_status}")
else:
    st.info("Keine Aktien im Portfolio. Füge Ticker oder Namen über die Sidebar hinzu.")

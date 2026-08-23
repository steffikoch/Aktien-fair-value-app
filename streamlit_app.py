import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="Depot-Steuerungs-Engine", layout="wide", page_icon="📈")

st.title("📈 Depot-Steuerungs-Engine")
st.caption("Depotvergleich – 65.000 € Basis | 10 % Einzelpositionslimit | 1.000 € Sparer-Pauschbetrag")

# =============================================================
# HELPER: AUTOMATISCHE TICKER-SUCHE
# =============================================================
def search_ticker(query):
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
# HELPER: BERECHNUNGS-ENGINE (4-SCORE & METRIKEN)
# =============================================================
def analyze_stock_full(symbol, shares_count=0.0, buy_price=0.0, total_portfolio_val=65000.0, max_weight_limit=10.0, tax_free_allowance=1000.0):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
        if not price or price <= 0:
            return None

        curr = info.get('currency', 'EUR')
        curr_sym = "€" if curr == "EUR" else ("$" if curr == "USD" else curr)
        
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

        # 2. Fair Value
        target_pe = min(22.0, max(11.0, 12.0 + (max(0, medium_term_growth) * 0.4)))
        fv_vals = []
        if eps > 0: fv_vals.append((eps * target_pe) + max(0, net_cash_ps))
        if fcf and shares_out > 0 and fcf > 0: fv_vals.append(((fcf / shares_out) * target_pe) + max(0, net_cash_ps))
        
        fair_value = np.mean(fv_vals) if fv_vals else price
        mos = ((fair_value - price) / price) * 100 if fair_value > 0 else 0.0

        # 3. Netto-Rendite
        raw_div_yield = info.get('dividendYield') or 0.0
        div_yield_gross = raw_div_yield if raw_div_yield > 1.0 else raw_div_yield * 100.0
        cap_gain_5y_gross = (((fair_value / price) ** (1 / 5) - 1) * 100) if (price > 0 and fair_value > price) else 0.0
        
        gross_annual_income = (current_position_val * (div_yield_gross / 100.0)) + (current_position_val * (cap_gain_5y_gross / 100.0)) if current_position_val > 0 else (price * (div_yield_gross / 100.0))
        
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

        # 4. Depot-Allokation
        weight_pct = (current_position_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
        max_allowed_val = (max_weight_limit / 100.0) * total_portfolio_val
        remaining_cap_eur = max(0.0, max_allowed_val - current_position_val)

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
            "raw_price": price,
            "Einstand (€)": f"{cost_basis:,.2f} €",
            "Akt. Wert (€)": f"{current_position_val:,.2f} €",
            "G&V Total": pnl_str,
            "Fair Value": f"{fair_value:.2f} {curr_sym}",
            "Puffer": f"{mos:+.1f} %",
            "Quality": f"{quality_score}/100",
            "raw_quality": quality_score,
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

# Session State Initialisierung
if "portfolio" not in st.session_state:
    st.session_state.portfolio = [
        {"ticker": "MUV2.DE", "shares": 14.0, "buy_price": 543.30}
    ]

# TAB-NAVIGATION: DREI MODI
tab_a, tab_b, tab_c = st.tabs([
    "🟢 A. Einzelaktie (Quick-Check)", 
    "🔵 B. Reales Depot (G&V & Allokation)", 
    "🟠 C. Kaufsimulation (Fit-Test)"
])

# =============================================================
# TAB A: EINZELAKTIE (QUICK-CHECK)
# =============================================================
with tab_a:
    st.subheader("🟢 A. Einzelaktien-Analyse")
    st.caption("Ist die Aktie gut und günstig? (Unabhängig von deinen Depot-Beständen)")
    
    query_a = st.text_input("Aktie oder Ticker eingeben (z. B. COCO, Münchener Rück, AAPL):", key="search_a").strip()
    
    if query_a:
        with st.spinner("Analysiere Daten..."):
            resolved_a = search_ticker(query_a)
            res_a = analyze_stock_full(resolved_a, shares_count=0, buy_price=0, total_portfolio_val=depot_val_input, tax_free_allowance=tax_allowance_input)
            
            if res_a:
                st.markdown(f"### {res_a['Name']} (`{res_a['Ticker']}`)")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Aktueller Kurs", res_a["Akt. Kurs"])
                col2.metric("Fairer Wert", res_a["Fair Value"], delta=res_a["Puffer"])
                col3.metric("Quality Score", res_a["Quality"])
                col4.metric("Opt. Netto-Rendite (p.a.)", res_a["Opt. Rendite"])
                
                st.divider()
                st.success(f"**Fazit:** Fairer Wert liegt bei **{res_a['Fair Value']}** (Sicherheitsmarge: **{res_a['Puffer']}**). Quality Score: **{res_a['Quality']}**.")
            else:
                st.error("Aktie konnte nicht gefunden oder analysiert werden.")

# =============================================================
# TAB B: REALES DEPOT
# =============================================================
with tab_b:
    st.subheader("🔵 B. Reales Depot & Bestandsübersicht")
    
    # Sidebar Erweiterung für Depot-Verwaltung
    with st.sidebar:
        st.markdown("---")
        st.subheader("➕ Aktie im Depot verwalten")
        input_b = st.text_input("Name/Ticker für Depot:", key="input_b").strip()
        shares_b = st.number_input("Stückzahl:", min_value=0.0, value=0.0, step=1.0)
        buy_price_b = st.number_input("Kaufkurs (€):", min_value=0.0, value=0.0, step=1.0)
        
        if st.button("Ins Depot speichern"):
            if input_b and shares_b > 0 and buy_price_b > 0:
                t_res = search_ticker(input_b)
                found = False
                for item in st.session_state.portfolio:
                    if item["ticker"] == t_res:
                        item["shares"] = shares_b
                        item["buy_price"] = buy_price_b
                        found = True
                        break
                if not found:
                    st.session_state.portfolio.append({"ticker": t_res, "shares": shares_b, "buy_price": buy_price_b})
                st.success(f"{t_res} aktualisiert!")
                st.rerun()

        if st.session_state.portfolio:
            st.markdown("---")
            t_rem = st.selectbox("Aktie löschen:", [x["ticker"] for x in st.session_state.portfolio])
            if st.button("Löschen"):
                st.session_state.portfolio = [x for x in st.session_state.portfolio if x["ticker"] != t_rem]
                st.rerun()

    results_b = []
    for item in st.session_state.portfolio:
        res = analyze_stock_full(item["ticker"], item["shares"], item["buy_price"], depot_val_input, limit_pct_input, tax_allowance_input)
        if res:
            results_b.append(res)

    if results_b:
        df_b = pd.DataFrame(results_b)
        display_cols = [
            "Ticker", "Name", "Stückzahl", "Kaufkurs", "Akt. Kurs", 
            "Einstand (€)", "Akt. Wert (€)", "G&V Total", 
            "Fair Value", "Quality", "Opt. Rendite", 
            "Gewicht", "Freie Kap. (€)", "Status"
        ]
        st.dataframe(df_b[display_cols], use_container_width=True)
        
        total_cost = df_b["raw_cost_basis"].sum()
        total_current_val = df_b["raw_current_val"].sum()
        total_pnl_eur = df_b["raw_pnl"].sum()
        total_pnl_pct = ((total_current_val - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
        
        allocated_pct = (total_current_val / depot_val_input) * 100
        cash_left = max(0.0, depot_val_input - total_current_val)
        
        # Euro-Berechnungen für Zielkorridor
        min_target_eur = (target_stock_quote_min / 100.0) * depot_val_input
        max_target_eur = (target_stock_quote_max / 100.0) * depot_val_input
        
        dist_to_min = max(0.0, min_target_eur - total_current_val)
        dist_to_max = max(0.0, max_target_eur - total_current_val)

        st.markdown("---")
        st.markdown("### 📊 Depot-Gesamtübersicht & Performance")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Gesamteinstand Aktien", f"{total_cost:,.2f} €")
        c2.metric("Aktueller Wert Aktien", f"{total_current_val:,.2f} €", f"{allocated_pct:.1f} % Quote")
        c3.metric("Gesamt G&V Aktien", f"{total_pnl_eur:,.2f} €", f"{total_pnl_pct:+.2f} %")
        c4.metric("ETF / Cash / Ungebunden", f"{cash_left:,.2f} €", f"{100 - allocated_pct:.1f} % Freiraum")
        
        st.divider()
        st.markdown(f"#### 🎯 Aktienquoten-Steuerung ({target_stock_quote_min} % – {target_stock_quote_max} % Korridor)")
        
        q_col1, q_col2, q_col3 = st.columns(3)
        q_col1.metric("Bis Untergrenze (10 %)", f"{dist_to_min:,.2f} €", delta="Erreicht" if dist_to_min == 0 else f"Noch {dist_to_min:,.2f} €")
        q_col2.metric("Verbleibender Spielraum bis 20 %", f"{dist_to_max:,.2f} €", delta=f"{dist_to_max:,.2f} € verfügbar", delta_color="normal")
        
        if allocated_pct < target_stock_quote_min:
            q_col3.error(f"Quote zu niedrig: {allocated_pct:.1f}%")
        elif allocated_pct <= target_stock_quote_max:
            q_col3.success(f"🟢 Quote optimal: {allocated_pct:.1f}%")
        else:
            q_col3.warning(f"🔴 Quote überschritten: {allocated_pct:.1f}%")

    else:
        st.info("Keine Aktien im Portfolio.")

# =============================================================
# TAB C: KAUFSIMULATION
# =============================================================
with tab_c:
    st.subheader("🟠 C. Kaufsimulation & Portfolio Fit")
    st.caption("Was passiert mit deinen Quoten, wenn du eine bestimmte Summe investierst?")
    
    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        sim_query = st.text_input("Simulierte Aktie (Name oder Ticker):", value="COCO", key="sim_q").strip()
    with sim_col2:
        sim_amount = st.number_input("Simulierter Kaufwert (€):", min_value=100.0, value=1000.0, step=250.0)
        
    if sim_query and sim_amount > 0:
        sim_ticker = search_ticker(sim_query)
        sim_data = analyze_stock_full(sim_ticker, shares_count=0, buy_price=0, total_portfolio_val=depot_val_input, tax_free_allowance=tax_allowance_input)
        
        if sim_data:
            # Berechnungen Vorher / Nachher
            current_stock_val = sum([x["raw_current_val"] for x in results_b]) if 'results_b' in locals() and results_b else 0.0
            
            quote_before = (current_stock_val / depot_val_input) * 100
            new_stock_val = current_stock_val + sim_amount
            quote_after = (new_stock_val / depot_val_input) * 100
            
            position_weight = (sim_amount / depot_val_input) * 100
            
            max_target_eur = (target_stock_quote_max / 100.0) * depot_val_input
            spielraum_after = max(0.0, max_target_eur - new_stock_val)
            
            st.divider()
            st.markdown(f"### Simulation: Kauf von **{sim_amount:,.2f} €** in `{sim_data['Ticker']}` ({sim_data['Name']})")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Aktienquote vorher", f"{quote_before:.1f} %")
            m2.metric("Aktienquote nach Kauf", f"{quote_after:.1f} %", delta=f"+{quote_after - quote_before:.1f} %")
            m3.metric("Positionsgewicht", f"{position_weight:.1f} %", delta="OK" if position_weight <= limit_pct_input else "Über Limit!", delta_color="normal" if position_weight <= limit_pct_input else "inverse")
            m4.metric("Verbleibender Spielraum (20 %)", f"{spielraum_after:,.2f} €")
            
            # Portfolio-Fit Bewertung
            st.markdown("#### 🎯 Portfolio Fit Bewertung")
            
            fit_checks = []
            if position_weight <= limit_pct_input:
                fit_checks.append("✅ Positionsgröße liegt unter dem 10 % Einzelwert-Limit.")
            else:
                fit_checks.append("❌ Position würde das 10 % Einzelwert-Limit überschreiten!")
                
            if quote_after <= target_stock_quote_max:
                fit_checks.append("✅ Die Gesamte Aktienquote bleibt innerhalb des 20 % Zielkorridors.")
            else:
                fit_checks.append("❌ Die Gesamte Aktienquote würde den 20 % Zielkorridor überschreiten!")
                
            if sim_data["raw_quality"] >= 60:
                fit_checks.append(f"✅ Hohe Qualität (Quality Score: {sim_data['Quality']}).")
            else:
                fit_checks.append(f"⚠️ Mäßige Qualität (Quality Score: {sim_data['Quality']}).")

            for check in fit_checks:
                st.write(check)
        else:
            st.error("Simulations-Aktie konnte nicht geladen werden.")

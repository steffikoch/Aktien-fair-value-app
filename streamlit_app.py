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
# HELPER: BERECHNUNGS-ENGINE (4-SCORE & METRIKEN & SZENARIEN)
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
        fcf = info.get('freeCashflow') or 0
        eps_growth = (info.get('earningsGrowth') or 0.0) * 100
        rev_growth = (info.get('revenueGrowth') or 0.0) * 100
        beta = info.get('beta') or 1.0
        total_cash = info.get('totalCash', 0) or 0
        total_debt = info.get('totalDebt', 0) or 0
        shares_out = info.get('sharesOutstanding', 0) or 0
        eps = info.get('forwardEps') or info.get('trailingEps') or 0.0
        ebitda = info.get('ebitda', 0) or 0
        pe_ratio = info.get('trailingPE') or info.get('forwardPE') or 0.0
        sector = info.get('sector', 'Unbekannt')
        
        net_cash_ps = ((total_cash - total_debt) / shares_out) if shares_out > 0 else 0.0
        medium_term_growth = (eps_growth * 0.6) + (rev_growth * 0.4)

        # 1. Quality Score
        p_score = 15 if net_margin >= 15 else (10 if net_margin >= 5 else (4 if net_margin > 0 else 0))
        p_score += 10 if roe >= 15 else (6 if roe >= 8 else (2 if roe > 0 else 0))
        g_score = 20 if medium_term_growth >= 12.0 else (13 if medium_term_growth >= 5.0 else (7 if medium_term_growth >= 0.0 else 2))
        
        if net_cash_ps > 0: b_score = 20
        else:
            debt_to_ebitda = (total_debt / ebitda) if ebitda > 0 else 99
            b_score = 15 if debt_to_ebitda < 3.0 else (10 if debt_to_ebitda < 5.0 and fcf > 0 else 4)

        c_score = 20 if fcf > 0 else 0
        r_score = 15 if beta < 1.0 else (9 if beta < 1.3 else 3)
        quality_score = min(100, p_score + g_score + b_score + c_score + r_score)

        # 2. Fair Value & Bear/Base/Bull Szenarien
        target_pe_base = min(22.0, max(11.0, 12.0 + (max(0, medium_term_growth) * 0.4)))
        
        def calc_fv(pe_mult):
            vals = []
            if eps > 0: vals.append((eps * pe_mult) + max(0, net_cash_ps))
            if fcf > 0 and shares_out > 0: vals.append(((fcf / shares_out) * pe_mult) + max(0, net_cash_ps))
            return np.mean(vals) if vals else price

        fv_base = calc_fv(target_pe_base)
        fv_bear = calc_fv(target_pe_base * 0.75)
        fv_bull = calc_fv(target_pe_base * 1.25)
        
        mos = ((fv_base - price) / price) * 100 if fv_base > 0 else 0.0
        
        # Confidence Level
        confidence = "Hoch" if quality_score >= 75 and eps > 0 and fcf > 0 else ("Mittel" if quality_score >= 55 else "Niedrig")

        # 3. Netto-Rendite
        raw_div_yield = info.get('dividendYield') or 0.0
        div_yield_gross = raw_div_yield if raw_div_yield > 1.0 else raw_div_yield * 100.0
        
        cap_gain_3y_gross = (((fv_base / price) ** (1 / 3) - 1) * 100) if (price > 0 and fv_base > price) else 0.0
        cap_gain_5y_gross = (((fv_base / price) ** (1 / 5) - 1) * 100) if (price > 0 and fv_base > price) else 0.0
        
        gross_annual_income = (current_position_val * (div_yield_gross / 100.0)) + (current_position_val * (cap_gain_5y_gross / 100.0)) if current_position_val > 0 else (price * (div_yield_gross / 100.0))
        
        TAX_RATE = 0.26375
        if gross_annual_income <= tax_free_allowance:
            net_div = div_yield_gross
            net_cg_3y = cap_gain_3y_gross
            net_cg_5y = cap_gain_5y_gross
        else:
            taxable_ratio = (gross_annual_income - tax_free_allowance) / gross_annual_income if gross_annual_income > 0 else 1.0
            eff_tax = TAX_RATE * taxable_ratio
            net_div = div_yield_gross * (1.0 - eff_tax)
            net_cg_3y = cap_gain_3y_gross * (1.0 - eff_tax)
            net_cg_5y = cap_gain_5y_gross * (1.0 - eff_tax)

        ret_3y_net = net_cg_3y + net_div
        ret_5y_net = net_cg_5y + net_div

        # Kauflimit (z.B. Fair Value abzüglich 10% Sicherheitsmarge)
        buy_limit = fv_base * 0.90

        # 4. Depot-Allokation
        weight_pct = (current_position_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
        max_allowed_val = (max_weight_limit / 100.0) * total_portfolio_val
        remaining_cap_eur = max(0.0, max_allowed_val - current_position_val)

        pnl_str = f"{'+' if pnl_eur >= 0 else ''}{pnl_eur:,.2f} € ({'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%)"

        return {
            "Ticker": symbol,
            "Name": info.get('shortName', symbol),
            "Sector": sector,
            "Stückzahl": f"{shares_count:,.2f}",
            "Kaufkurs": f"{buy_price:.2f} {curr_sym}",
            "Akt. Kurs": f"{price:.2f} {curr_sym}",
            "raw_price": price,
            "Einstand (€)": f"{cost_basis:,.2f} €",
            "Akt. Wert (€)": f"{current_position_val:,.2f} €",
            "G&V Total": pnl_str,
            "Fair Value": f"{fv_base:.2f} {curr_sym}",
            "FV Bear": f"{fv_bear:.2f} {curr_sym}",
            "FV Bull": f"{fv_bull:.2f} {curr_sym}",
            "Confidence": confidence,
            "Puffer": f"{mos:+.1f} %",
            "Quality": f"{quality_score}/100",
            "raw_quality": quality_score,
            "KGV": f"{pe_ratio:.1f}" if pe_ratio > 0 else "-",
            "FCF": f"{fcf / 1e6:,.1f} M. {curr_sym}" if fcf != 0 else "-",
            "Beta": f"{beta:.2f}",
            "Kauflimit": f"{buy_limit:.2f} {curr_sym}",
            "Netto-Rendite 3J": f"{ret_3y_net:.2f} % p.a.",
            "Netto-Rendite 5J": f"{ret_5y_net:.2f} % p.a.",
            "Gewicht": f"{weight_pct:.1f} %",
            "Freie Kap. (€)": f"{remaining_cap_eur:,.2f} €",
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
    "🔵 B. Reales Depot (Bestand & G&V)", 
    "🟠 C. Kaufsimulation (Portfolio Fit)"
])

# =============================================================
# TAB A: EINZELAKTIE (QUICK-CHECK)
# =============================================================
with tab_a:
    st.subheader("🟢 A. Einzelaktien-Analyse")
    st.info("ℹ️ **Hinweis:** Depotdaten werden bei diesem Check **nicht** berücksichtigt. Reines Bewertungstool.")
    
    query_a = st.text_input("Aktie oder Ticker eingeben (z. B. COCO, DTE.DE, AAPL, Münchener Rück):", key="search_a").strip()
    
    if query_a:
        with st.spinner("Analysiere Einzelwert..."):
            resolved_a = search_ticker(query_a)
            res_a = analyze_stock_full(resolved_a, shares_count=0, buy_price=0, total_portfolio_val=depot_val_input, tax_free_allowance=tax_allowance_input)
            
            if res_a:
                st.markdown(f"### {res_a['Name']} (`{res_a['Ticker']}`) – Sector: {res_a['Sector']}")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Aktueller Kurs", res_a["Akt. Kurs"])
                m2.metric("Fair Value (Base)", res_a["Fair Value"], delta=res_a["Puffer"])
                m3.metric("Quality Score", res_a["Quality"])
                m4.metric("Empf. Kauflimit (-10%)", res_a["Kauflimit"])
                
                st.divider()
                st.markdown("#### 🎯 Bewertung & Szenarien")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Bear-Case Fair Value", res_a["FV Bear"])
                c2.metric("Base-Case Fair Value", res_a["Fair Value"])
                c3.metric("Bull-Case Fair Value", res_a["FV Bull"])
                c4.metric("FV Confidence Level", res_a["Confidence"])
                
                st.divider()
                st.markdown("#### 📊 Kennzahlen & Rendite-Erwartung")
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("KGV", res_a["KGV"])
                k2.metric("Free Cashflow", res_a["FCF"])
                k3.metric("Risiko (Beta)", res_a["Beta"])
                k4.metric("Netto-Rendite 3J p.a.", res_a["Netto-Rendite 3J"])
                k5.metric("Netto-Rendite 5J p.a.", res_a["Netto-Rendite 5J"])
            else:
                st.error("Aktie konnte nicht gefunden werden.")

# =============================================================
# TAB B: REALES DEPOT
# =============================================================
with tab_b:
    st.subheader("🔵 B. Reales Depot & Bestandsübersicht")
    st.caption("Verwaltung und Überwachung deiner tatsächlich gehaltenen Positionen.")
    
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
            "Ticker", "Name", "Sector", "Stückzahl", "Kaufkurs", "Akt. Kurs", 
            "Einstand (€)", "Akt. Wert (€)", "G&V Total", 
            "Fair Value", "Quality", "Gewicht", "Freie Kap. (€)"
        ]
        st.dataframe(df_b[display_cols], use_container_width=True)
        
        total_cost = df_b["raw_cost_basis"].sum()
        total_current_val = df_b["raw_current_val"].sum()
        total_pnl_eur = df_b["raw_pnl"].sum()
        total_pnl_pct = ((total_current_val - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
        
        allocated_pct = (total_current_val / depot_val_input) * 100
        cash_left = max(0.0, depot_val_input - total_current_val)
        
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
    st.info("ℹ️ **Hinweis:** Depotdaten werden hier **vollständig** berücksichtigt. Bewertet Auswirkungen auf Quoten und Limits.")
    
    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        sim_query = st.text_input("Simulierte Aktie (Name oder Ticker):", value="COCO", key="sim_q").strip()
    with sim_col2:
        sim_amount = st.number_input("Simulierter Kaufwert (€):", min_value=100.0, value=1000.0, step=250.0)
        
    if sim_query and sim_amount > 0:
        sim_ticker = search_ticker(sim_query)
        sim_data = analyze_stock_full(sim_ticker, shares_count=0, buy_price=0, total_portfolio_val=depot_val_input, tax_free_allowance=tax_allowance_input)
        
        if sim_data:
            current_stock_val = sum([x["raw_current_val"] for x in results_b]) if 'results_b' in locals() and results_b else 0.0
            
            # Prüfen, ob Aktie bereits im Depot ist
            existing_pos_val = 0.0
            if 'results_b' in locals() and results_b:
                for item in results_b:
                    if item["Ticker"] == sim_data["Ticker"]:
                        existing_pos_val = item["raw_current_val"]
                        break

            quote_before = (current_stock_val / depot_val_input) * 100
            new_stock_val = current_stock_val + sim_amount
            quote_after = (new_stock_val / depot_val_input) * 100
            
            new_total_pos_val = existing_pos_val + sim_amount
            new_pos_weight = (new_total_pos_val / depot_val_input) * 100
            
            max_target_eur = (target_stock_quote_max / 100.0) * depot_val_input
            spielraum_quote_after = max(0.0, max_target_eur - new_stock_val)
            
            max_pos_eur = (limit_pct_input / 100.0) * depot_val_input
            spielraum_pos_after = max(0.0, max_pos_eur - new_total_pos_val)
            
            st.divider()
            st.markdown(f"### Simulation: Kauf von **{sim_amount:,.2f} €** in `{sim_data['Ticker']}` ({sim_data['Name']})")
            
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Aktienquote Vorher ➔ Nachher", f"{quote_before:.1f} % ➔ {quote_after:.1f} %")
            s2.metric("Positionsgewicht Nachher", f"{new_pos_weight:.1f} %", delta=f"Limit: {limit_pct_input:.1f}%")
            s3.metric("Verbl. Quoten-Spielraum (20%)", f"{spielraum_quote_after:,.2f} €")
            s4.metric("Verbl. Positions-Spielraum", f"{spielraum_pos_after:,.2f} €")
            
            st.divider()
            st.markdown("#### 🎯 Portfolio Fit & Handlungsempfehlung")
            
            fit_ok = True
            reasons = []
            
            # Quality Check
            if sim_data["raw_quality"] >= 70:
                reasons.append(f"🟢 **Qualität:** Hoch ({sim_data['Quality']})")
            elif sim_data["raw_quality"] >= 50:
                reasons.append(f"🟡 **Qualität:** Mittel ({sim_data['Quality']})")
            else:
                reasons.append(f"🔴 **Qualität:** Schwach ({sim_data['Quality']})")
                fit_ok = False
                
            # Positionslimit Check
            if new_pos_weight <= limit_pct_input:
                reasons.append(f"🟢 **Positionslimit:** Passt ({new_pos_weight:.1f} % / Max {limit_pct_input:.1f} %)")
            else:
                reasons.append(f"🔴 **Positionslimit:** Überschritten ({new_pos_weight:.1f} % > {limit_pct_input:.1f} %)")
                fit_ok = False
                
            # Quotenlimit Check
            if quote_after <= target_stock_quote_max:
                reasons.append(f"🟢 **Gesamte Aktienquote:** Passt ({quote_after:.1f} % / Max {target_stock_quote_max:.1f} %)")
            else:
                reasons.append(f"🔴 **Gesamte Aktienquote:** Überschritten ({quote_after:.1f} % > {target_stock_quote_max:.1f} %)")
                fit_ok = False

            # Gesamtfazit
            if fit_ok:
                st.success("### 🟢 KAUF PASST INS DEPOT")
            elif new_pos_weight > limit_pct_input or quote_after > target_stock_quote_max:
                st.error("### 🔴 KAUF NICHT EMPFOHLEN (Limit-Überschreitung)")
            else:
                st.warning("### 🟡 KAUF GEDROSSELT EMPFOHLEN")

            for r in reasons:
                st.markdown(r)
        else:
            st.error("Simulations-Aktie konnte nicht geladen werden.")

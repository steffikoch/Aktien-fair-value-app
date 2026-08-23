import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="4-Score Depot Engine", layout="wide", page_icon="📈")

st.title("📈 4-Score Depot- & Allokations-Engine (3–5 Jahre Horizont)")
st.caption("Transparente, mehrdimensionale Aktienanalyse & Netto-Renditeprognose")

# =============================================================
# HELPER: TICKER RESOLUTION
# =============================================================
def resolve_ticker_symbol(user_input):
    user_input = user_input.strip()
    if not user_input:
        return None
    
    known_mappings = {
        "DEUTSCHE TELEKOM": "DTE.DE", "TELEKOM": "DTE.DE",
        "LUFTHANSA": "LHA.DE", "DEUTSCHE LUFTHANSA": "LHA.DE",
        "ALLIANZ": "ALV.DE", "BASF": "BAS.DE", "BAYER": "BAYN.DE",
        "BMW": "BMW.DE", "SIEMENS": "SIE.DE", "VOLKSWAGEN": "VOW3.DE",
        "SAP": "SAP.DE", "APPLE": "AAPL", "MICROSOFT": "MSFT",
        "NVIDIA": "NVDA", "AMAZON": "AMZN", "TESLA": "TSLA"
    }
    
    upper_input = user_input.upper()
    if upper_input in known_mappings:
        return known_mappings[upper_input]

    if "." in user_input or (len(user_input) <= 5 and user_input.isalpha()):
        return user_input.upper()
    
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={user_input}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "quotes" in data and len(data["quotes"]) > 0:
                return data["quotes"][0]["symbol"]
    except Exception:
        pass
    
    return user_input.upper()

# =============================================================
# HELPER: ENHANCED 4-SCORE BERECHNUNG & NETTO-RENDITEPROGNOSE
# =============================================================
def analyze_stock_4score(symbol, current_position_val, total_portfolio_val):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
        if not price or price <= 0:
            return None

        curr = info.get('currency', 'EUR')
        curr_sym = "€" if curr == "EUR" else ("$" if curr == "USD" else curr)
        
        # Fundamentaldaten
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
        sector = info.get('sector', 'Unbekannt')
        ebitda = info.get('ebitda', 0) or 0
        
        net_cash_ps = ((total_cash - total_debt) / shares) if shares > 0 else 0.0

        # Mittelfristiger Wachstumstrend (3–5 Jahre Gewichtung)
        medium_term_growth = (eps_growth * 0.6) + (rev_growth * 0.4)

        # -------------------------------------------------------------
        # SCORE 1: QUALITY SCORE (0 - 100 Pkt.)
        # -------------------------------------------------------------
        p_score = 0
        if net_margin >= 15: p_score += 15
        elif net_margin >= 5: p_score += 10
        elif net_margin > 0: p_score += 4
        
        if roe >= 15: p_score += 10
        elif roe >= 8: p_score += 6
        elif roe > 0: p_score += 2

        growth_note = ""
        if medium_term_growth >= 12.0: 
            g_score = 20
        elif medium_term_growth >= 5.0: 
            g_score = 13
        elif medium_term_growth >= 0.0: 
            g_score = 7
            growth_note = "Moderates/Stagnierendes Wachstum dämpft den Score."
        else: 
            g_score = 2
            growth_note = "Rückläufige Kennzahlen führen zu Punktabzug."

        if net_cash_ps > 0:
            b_score = 20
        else:
            debt_to_ebitda = (total_debt / ebitda) if ebitda > 0 else 99
            if debt_to_ebitda < 3.0: b_score = 15
            elif debt_to_ebitda < 5.0 and fcf and fcf > 0: b_score = 10
            else: b_score = 4

        if fcf is None:
            c_score = 10
            fcf_status = "⚪ Keine Daten"
        elif fcf > 0:
            c_score = 20
            fcf_status = "🟢 Positiv"
        elif fcf == 0:
            c_score = 10
            fcf_status = "🟡 Neutral / Schwach"
        else:
            c_score = 0
            fcf_status = "🔴 Negativ"

        if beta is None: r_score = 8
        elif beta < 1.0: r_score = 15
        elif beta < 1.3: r_score = 9
        else: r_score = 3

        quality_score = min(100, p_score + g_score + b_score + c_score + r_score)

        # -------------------------------------------------------------
        # SCORE 2: FAIR-VALUE CONFIDENCE SCORE
        # -------------------------------------------------------------
        conf_score = 100
        if net_margin < 3.0: conf_score -= 35
        elif net_margin < 7.0: conf_score -= 15
        if fcf is None: conf_score -= 15
        elif fcf <= 0: conf_score -= 25
        if quality_score < 45: conf_score -= 20
        if beta and beta > 1.25: conf_score -= 10
        
        conf_score = max(0, min(100, conf_score))
        fv_conf_text = "🟢 HOCH" if conf_score >= 75 else ("🟡 MITTEL" if conf_score >= 45 else "🔴 NIEDRIG")

        # Fair Value Berechnung
        target_pe = min(22.0, max(11.0, 12.0 + (max(0, medium_term_growth) * 0.4)))
        fv_vals = []
        if eps > 0: fv_vals.append((eps * target_pe) + max(0, net_cash_ps))
        if fcf and shares > 0 and fcf > 0: fv_vals.append(((fcf / shares) * target_pe) + max(0, net_cash_ps))
        
        fair_value = np.mean(fv_vals) if fv_vals else price
        mos = ((fair_value - price) / price) * 100 if fair_value > 0 else 0.0

        # -------------------------------------------------------------
        # DIVIDEND YIELD SANITIZATION & RENDITEPROGNOSE
        # -------------------------------------------------------------
        raw_div_yield = info.get('dividendYield') or 0.0
        div_yield_gross = raw_div_yield if raw_div_yield > 1.0 else raw_div_yield * 100.0

        TAX_RATE = 0.26375  # Abgeltungsteuer + Soli (DE)
        net_div_yield = div_yield_gross * (1.0 - TAX_RATE)

        if price > 0 and fair_value > price:
            cap_gain_3y_gross = ((fair_value / price) ** (1 / 3) - 1) * 100
            cap_gain_5y_gross = ((fair_value / price) ** (1 / 5) - 1) * 100
        else:
            cap_gain_3y_gross = 0.0
            cap_gain_5y_gross = 0.0

        net_cap_gain_3y = cap_gain_3y_gross * (1.0 - TAX_RATE)
        net_cap_gain_5y = cap_gain_5y_gross * (1.0 - TAX_RATE)

        # 1. Cash-Flow Modus (Ohne DRIP)
        ret_3y_no_drip = net_cap_gain_3y + net_div_yield
        ret_5y_no_drip = net_cap_gain_5y + net_div_yield

        # 2. Reinvestitions-Modus (Mit DRIP / Compound)
        cagr_3y_dec = net_cap_gain_3y / 100.0
        cagr_5y_dec = net_cap_gain_5y / 100.0
        div_dec = net_div_yield / 100.0

        ret_3y_drip = (((1.0 + cagr_3y_dec) * (1.0 + div_dec)) - 1.0) * 100.0
        ret_5y_drip = (((1.0 + cagr_5y_dec) * (1.0 + div_dec)) - 1.0) * 100.0

        # -------------------------------------------------------------
        # SCORE 3: RISK & CAPITAL EFFICIENCY SCORE
        # -------------------------------------------------------------
        mos_part = min(50, max(0, int((mos + 10) * 1.25)))
        qual_part = int(quality_score * 0.5)
        risk_cap_score = min(100, max(0, mos_part + qual_part))

        # -------------------------------------------------------------
        # SCORE 4: PORTFOLIO FIT & DEPOTKAPAZITÄT (MAXIMALGEWICHT 7.5 %)
        # -------------------------------------------------------------
        weight_pct = (current_position_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
        max_weight_limit = 7.5
        
        remaining_cap_pct = max(0.0, max_weight_limit - weight_pct)
        max_buy_eur = (remaining_cap_pct / 100.0) * total_portfolio_val

        if weight_pct > 10.0:
            fit_score = 0
            pos_status = f"🔴 {weight_pct:.1f}% (⚠️ KEIN NACHKAUF: >10% Hard Limit)"
        elif weight_pct > 7.5:
            fit_score = 30
            pos_status = f"🟠 {weight_pct:.1f}% (⚠️ NACHKAUF-BREMSE: >7.5%)"
        elif weight_pct >= 7.0:
            fit_score = 60
            pos_status = f"🟡 {weight_pct:.1f}% (Nahe Obergrenze 7,5%)"
        elif weight_pct >= 4.0:
            fit_score = 80
            pos_status = f"🟡 {weight_pct:.1f}% (Normale Gewichtung: 4–7%)"
        else:
            fit_score = 100
            pos_status = f"🟢 {weight_pct:.1f}% (Aufstockung möglich: <4%)"

        return {
            "symbol": symbol,
            "name": info.get('shortName', symbol),
            "price": price,
            "curr_sym": curr_sym,
            "fair_value": fair_value,
            "margin_of_safety": mos,
            "quality_score": quality_score,
            "growth_note": growth_note,
            "quality_pillars": {
                "Profitabilität": (p_score, 25),
                "Wachstum (3-5 J.)": (g_score, 20),
                "Bilanz": (b_score, 20),
                "Cashflow": (c_score, 20),
                "Stabilität/Risiko": (r_score, 15)
            },
            "conf_score": conf_score,
            "fv_conf_text": fv_conf_text,
            "risk_cap_score": risk_cap_score,
            "fit_score": fit_score,
            "weight_pct": weight_pct,
            "remaining_cap_pct": remaining_cap_pct,
            "max_buy_eur": max_buy_eur,
            "pos_status": pos_status,
            "net_margin": net_margin,
            "fcf_status": fcf_status,
            "div_yield_gross": div_yield_gross,
            "net_div_yield": net_div_yield,
            "net_cap_gain_3y": net_cap_gain_3y,
            "net_cap_gain_5y": net_cap_gain_5y,
            "ret_3y_no_drip": ret_3y_no_drip,
            "ret_5y_no_drip": ret_5y_no_drip,
            "ret_3y_drip": ret_3y_drip,
            "ret_5y_drip": ret_5y_drip,
            "sector": sector
        }
    except Exception:
        return None

# =============================================================
# EINGABE SIDEBAR
# =============================================================
st.sidebar.header("⚙️ Eingabe & Depot-Kontext")
ticker_input = st.sidebar.text_input("Aktien-Name oder Ticker:", value="Deutsche Telekom").strip()
st.sidebar.markdown("---")
pos_val_input = st.sidebar.number_input("Aktueller Wert im Depot (€):", min_value=0.0, value=710.0, step=50.0)
depot_val_input = st.sidebar.number_input("Gesamtdepot-Wert (€):", min_value=1.0, value=10000.0, step=500.0)

st.sidebar.markdown("---")
st.sidebar.header("🔄 Dividenden-Modell")
drip_mode = st.sidebar.radio(
    "Strategie wählen:",
    ["1. Cash-Flow-Modus (Ausschüttung)", "2. Reinvestitions-Modus (DRIP)"],
    index=0
)
is_drip = "Reinvestitions" in drip_mode

# =============================================================
# HAUPTAUSWERTUNG
# =============================================================
if ticker_input:
    with st.spinner(f"Suche & Analysiere '{ticker_input}'..."):
        resolved_ticker = resolve_ticker_symbol(ticker_input)
        res = analyze_stock_4score(resolved_ticker, pos_val_input, depot_val_input)
        
    if not res:
        st.error(f"Konnte keine Daten für '{ticker_input}' finden.")
    else:
        price = res["price"]
        curr_sym = res["curr_sym"]
        fv = res["fair_value"]
        mos = res["margin_of_safety"]
        q_score = res["quality_score"]
        conf_score = res["conf_score"]
        rc_score = res["risk_cap_score"]
        fit_score = res["fit_score"]
        weight_pct = res["weight_pct"]
        rem_cap = res["remaining_cap_pct"]
        max_eur = res["max_buy_eur"]
        
        # Renditewerte je nach DRIP-Einstellung
        total_3y = res["ret_3y_drip"] if is_drip else res["ret_3y_no_drip"]
        total_5y = res["ret_5y_drip"] if is_drip else res["ret_5y_no_drip"]
        
        limits_active = True
        is_throttled = False
        
        # Signallogik
        if q_score < 40 or res["net_margin"] < 3.0:
            final_action = "🔴 KEIN KAUF (Value Trap: Zu geringe Marge & Qualität)"
            limits_active = False
        elif fit_score <= 30:
            final_action = "🔴 KEIN NACHKAUF (Depotgewicht über Obergrenze 7,5%)"
            limits_active = False
        elif conf_score < 45:
            final_action = "🔴 KEIN KAUF (Fair Value unsicher)"
            limits_active = False
        elif total_5y < 3.0:
            final_action = "🔴 KEIN KAUF (Netto-Rendite unter 3.0% p.a.)"
            limits_active = True
        elif rc_score < 40 or mos < 10:
            final_action = "🟠 ABWARTEN (Sicherheitspuffer zu gering)"
            limits_active = True
        elif q_score >= 65 and mos >= 12:
            if weight_pct >= 7.0:
                final_action = "🟡 NACHKAUF (Gedrosselt: Position nahe Obergrenze 7,5%)"
                is_throttled = True
            else:
                final_action = "🟢 NACHKAUF / POSITION AUFSTOCKEN"
            limits_active = True
        else:
            final_action = "🟡 BEOBACHTEN"
            limits_active = True

        st.subheader(f"{res['name']} ({res['symbol']}) – {price:.2f} {curr_sym}")
        
        if "🔴" in final_action:
            st.error(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")
        elif "🟠" in final_action or "🟡" in final_action:
            st.warning(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")
        else:
            st.success(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")

        # Entscheidungs-Matrix
        st.markdown("#### 🔎 Entscheidungs-Matrix")
        u_cols = st.columns(4)
        with u_cols[0]:
            if weight_pct > 7.5: st.write(f"🔴 **Depotgewicht:** Exzediert ({weight_pct:.1f}%)")
            elif weight_pct >= 7.0: st.write(f"🟡 **Depotgewicht:** Nahe Grenze ({weight_pct:.1f}%)")
            else: st.write(f"🟢 **Depotgewicht:** Im Zielbereich ({weight_pct:.1f}%)")
        with u_cols[1]:
            if mos < 10: st.write(f"🔴 **Puffer:** Zu gering ({mos:+.1f}%)")
            elif mos < 12: st.write(f"🟠 **Puffer:** Moderat ({mos:+.1f}%)")
            else: st.write(f"🟢 **Puffer:** Gut ({mos:+.1f}%)")
        with u_cols[2]:
            q_icon = "🟢" if q_score >= 65 else ("🟡" if q_score >= 45 else "🔴")
            st.write(f"{q_icon} **Quality:** {q_score}/100")
        with u_cols[3]:
            st.write(f"{res['fv_conf_text']} **Model Conf.:** {conf_score}/100")

        st.markdown("---")
        
        # Netto-Renditeprognose
        ret_icon = "🟢" if total_5y >= 5.0 else ("🟡" if total_5y >= 3.0 else "🔴")
        mode_label = "mit DRIP / Reinvestition" if is_drip else "ohne Reinvestition (Cash-Flow)"
        
        st.markdown(f"### {ret_icon} Erwartete Netto-Gesamtrendite p.a. ({mode_label})")
        
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            st.metric(
                label="Horizont 3 Jahre (p.a.)", 
                value=f"{total_3y:.2f} %",
                delta=f"Kurs: {res['net_cap_gain_3y']:.2f}% | Div: {res['net_div_yield']:.2f}%"
            )
        with r_col2:
            st.metric(
                label="Horizont 5 Jahre (p.a.)", 
                value=f"{total_5y:.2f} %",
                delta=f"Kurs: {res['net_cap_gain_5y']:.2f}% | Div: {res['net_div_yield']:.2f}%"
            )

        st.caption(
            "ℹ️ **Berechnungsgrundlage:** 26,375 % Abgeltungsteuer berücksichtigt. "
            f"**Modus:** {mode_label}. "
            f"Brutto-Dividendenrendite: {res['div_yield_gross']:.2f}% → Netto: {res['net_div_yield']:.2f}%."
        )

        st.markdown("---")
        st.subheader("📊 DIE 4 SCORES")
        s1, s2, s3, s4 = st.columns(4)
        
        with s1:
            st.metric("1. Quality Score", f"{q_score} / 100")
            st.caption(f"Nettomarge: {res['net_margin']:.2f}%")
        with s2:
            st.metric("2. Fair Value Conf.", f"{conf_score} / 100", delta=res["fv_conf_text"], delta_color="off")
            st.caption(f"Fair Value: {fv:.2f} {curr_sym} ({mos:+.1f}%)")
        with s3:
            st.metric("3. Risk / Capital Eff.", f"{rc_score} / 100")
            st.caption(f"Free Cashflow: {res['fcf_status']}")
        with s4:
            st.metric("4. Portfolio Fit", f"{fit_score} / 100")
            st.caption(res["pos_status"])

        st.markdown("---")
        st.subheader("🎯 Handlungsmarken & Kaufzonen-Status")
        limit_12 = fv * 0.88
        limit_20 = fv * 0.80

        if not limits_active:
            st.error("⚠️ KAUFLIMITS AUSGESETZT: Qualität zu schwach, Fair Value unsicher oder Depot-Limits erreicht.")
        else:
            if is_throttled:
                st.warning(
                    f"🟡 **AKTUELL IN KAUFZONE – ABER GEDROSSELT**\n\n"
                    f"Der Kurs (`{price:.2f} {curr_sym}`) liegt unter dem 20%-Kauflimit (`{limit_20:.2f} {curr_sym}`). "
                    f"Da das Depotgewicht bereits `{weight_pct:.1f}%` erreicht hat, ist der Kauf auf max. 7,5% Obergrenze gedrosselt."
                )
            elif price <= limit_20:
                st.success(f"🟢 **AKTUELL IN STARKER KAUFZONE (≥ 20% Rabatt)!**\n\n"
                           f"Aktueller Kurs (`{price:.2f} {curr_sym}`) liegt unter dem 20%-Limit (`{limit_20:.2f} {curr_sym}`).")
            elif price <= limit_12:
                st.success(f"🟢 **AKTUELL IN KAUFZONE (≥ 12% Rabatt)!**\n\n"
                           f"Aktueller Kurs (`{price:.2f} {curr_sym}`) liegt unter dem 12%-Limit (`{limit_12:.2f} {curr_sym}`).")
            else:
                st.warning(f"🟡 **KEINE KAUFZONE (Sicherheitspuffer noch nicht erreicht)**\n\n"
                           f"Aktueller Kurs: `{price:.2f} {curr_sym}` | Nächstes Ziel (12% Rabatt): `{limit_12:.2f} {curr_sym}`")

            # Kapazitäts-Berechnung & Limits anzeigen
            c1, c2, c3 = st.columns(3)
            with c1: st.write(f"**1. Kauflimit (12 % Rabatt):** `{limit_12:.2f} {curr_sym}`")
            with c2: st.write(f"**2. Kauflimit (20 % Rabatt):** `{limit_20:.2f} {curr_sym}`")
            with c3: st.write(f"💶 **Max. Nachkauf bis 7,5%-Grenze:** `{max_eur:.2f} {curr_sym}` (Kapazität: `{rem_cap:.1f}%`)")

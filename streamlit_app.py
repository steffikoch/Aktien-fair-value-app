import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="4-Score Depot Engine", layout="wide", page_icon="📈")

st.title("📈 4-Score Depot- & Allokations-Engine (3–5 Jahre Horizont)")
st.caption("Transparente, mehrdimensionale Aktienanalyse & Risikosteuerung")

# =============================================================
# HELPER: TICKER RESOLUTION (NAMEN IN TICKER UMWANDELN)
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
# HELPER: ENHANCED 4-SCORE BERECHNUNG (3-5 JAHRE HORIZONT)
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
        # A) Profitabilität (max 25 Pkt.)
        p_score = 0
        if net_margin >= 15: p_score += 15
        elif net_margin >= 5: p_score += 10
        elif net_margin > 0: p_score += 4
        
        if roe >= 15: p_score += 10
        elif roe >= 8: p_score += 6
        elif roe > 0: p_score += 2

        # B) Mittelfristiges Wachstum - Staffelung (max 20 Pkt.)
        if medium_term_growth >= 12.0: g_score = 20
        elif medium_term_growth >= 5.0: g_score = 13
        elif medium_term_growth >= 0.0: g_score = 7
        else: g_score = 2

        # C) Bilanz & Verschuldung im 3-5-Jahre-Licht (max 20 Pkt.)
        if net_cash_ps > 0:
            b_score = 20
        else:
            debt_to_ebitda = (total_debt / ebitda) if ebitda > 0 else 99
            if debt_to_ebitda < 3.0: b_score = 15
            elif debt_to_ebitda < 5.0 and fcf and fcf > 0: b_score = 10
            else: b_score = 4

        # D) Cashflow (max 20 Pkt.)
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

        # E) Stabilität & Risiko (max 15 Pkt.)
        if beta is None: r_score = 8
        elif beta < 1.0: r_score = 15
        elif beta < 1.3: r_score = 9
        else: r_score = 3

        quality_score = min(100, p_score + g_score + b_score + c_score + r_score)

        # -------------------------------------------------------------
        # SCORE 2: FAIR-VALUE CONFIDENCE SCORE (0 - 100 Pkt.)
        # -------------------------------------------------------------
        conf_score = 100
        if net_margin < 3.0: conf_score -= 35
        elif net_margin < 7.0: conf_score -= 15
        
        if fcf is None: conf_score -= 15
        elif fcf <= 0: conf_score -= 25
        
        if quality_score < 45: conf_score -= 20
        if beta and beta > 1.25: conf_score -= 10
        
        conf_score = max(0, min(100, conf_score))
        
        if conf_score >= 75: fv_conf_text = "🟢 HOCH"
        elif conf_score >= 45: fv_conf_text = "🟡 MITTEL"
        else: fv_conf_text = "🔴 NIEDRIG"

        # Fair Value (auf 3-5-Jahres-KGV-Abzinsung ausgerichtet)
        target_pe = min(22.0, max(11.0, 12.0 + (max(0, medium_term_growth) * 0.4)))
        fv_vals = []
        if eps > 0: fv_vals.append((eps * target_pe) + max(0, net_cash_ps))
        if fcf and shares > 0 and fcf > 0: fv_vals.append(((fcf / shares) * target_pe) + max(0, net_cash_ps))
        
        fair_value = np.mean(fv_vals) if fv_vals else price
        mos = ((fair_value - price) / price) * 100 if fair_value > 0 else 0.0

        # -------------------------------------------------------------
        # SCORE 3: RISK & CAPITAL EFFICIENCY SCORE
        # -------------------------------------------------------------
        mos_part = min(50, max(0, int((mos + 10) * 1.25)))
        qual_part = int(quality_score * 0.5)
        risk_cap_score = min(100, max(0, mos_part + qual_part))

        # -------------------------------------------------------------
        # SCORE 4: PORTFOLIO FIT SCORE (MAXIMALGEWICHT 10 %)
        # -------------------------------------------------------------
        weight_pct = (current_position_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
        
        if weight_pct > 10.0:
            fit_score = 0
            pos_status = f"🔴 {weight_pct:.1f}% (⚠️ KEIN NACHKAUF: >10% Hard Limit)"
        elif weight_pct > 7.5:
            fit_score = 30
            pos_status = f"🟠 {weight_pct:.1f}% (⚠️ NACHKAUF-BREMSE: 7.5–10%)"
        elif weight_pct >= 4.0:
            fit_score = 70
            pos_status = f"🟡 {weight_pct:.1f}% (Normale Gewichtung: 4–7.5%)"
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
            "pos_status": pos_status,
            "net_margin": net_margin,
            "fcf_status": fcf_status,
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
        
        limits_active = True
        
        if q_score < 40 or res["net_margin"] < 3.0:
            final_action = "🔴 KEIN KAUF (Value Trap: Zu geringe Marge & Qualität)"
            limits_active = False
        elif fit_score <= 30:
            final_action = "🔴 KEIN NACHKAUF (Depotgewicht über der Grenze)"
            limits_active = False
        elif conf_score < 45:
            final_action = "🔴 KEIN KAUF (Fair Value unsicher)"
            limits_active = False
        elif rc_score < 40 or mos < 10:
            final_action = "🟠 ABWARTEN (Sicherheitspuffer zu gering)"
            limits_active = True
        elif q_score >= 65 and mos >= 12:
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

        # Ursachen-Synthese Box
        st.markdown("#### 🔎 Entscheidungs-Matrix (Warum dieses Urteil?)")
        u_cols = st.columns(4)
        with u_cols[0]:
            if weight_pct > 7.5:
                st.write(f"🔴 **Hauptgrund:** Depotgewicht hoch ({weight_pct:.1f}%)")
            else:
                st.write(f"🟢 **Depotgewicht:** Im Zielbereich ({weight_pct:.1f}%)")
        with u_cols[1]:
            if mos < 10:
                st.write(f"🔴 **Puffer:** Zu gering ({mos:+.1f}%)")
            elif mos < 12:
                st.write(f"🟠 **Puffer:** Moderat ({mos:+.1f}%)")
            else:
                st.write(f"🟢 **Puffer:** Gut ({mos:+.1f}%)")
        with u_cols[2]:
            q_icon = "🟢" if q_score >= 65 else ("🟡" if q_score >= 45 else "🔴")
            st.write(f"{q_icon} **Quality:** {q_score}/100")
        with u_cols[3]:
            st.write(f"{res['fv_conf_text']} **Model Conf.:** {conf_score}/100")

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
        st.subheader("🔍 Detail-Aufschlüsselung des Quality Scores")
        pil_cols = st.columns(5)
        for idx, (pillar_name, (achieved, max_pts)) in enumerate(res["quality_pillars"].items()):
            ratio = achieved / max_pts
            p_color = "🔴" if ratio < 0.4 else ("🟡" if ratio < 0.7 else "🟢")
            with pil_cols[idx]:
                st.markdown(f"**{pillar_name}**")
                st.write(f"{p_color} **{achieved}** / {max_pts} Pkt.")

        st.markdown("---")
        st.subheader("🎯 Handlungsmarken & Kauflimits")
        limit_12 = fv * 0.88
        limit_20 = fv * 0.80

        if not limits_active:
            st.error("⚠️ KAUFLIMITS AUSGESETZT: Qualität zu schwach, Fair Value unsicher oder Depot-Limits erreicht.")
            st.caption(f"*(Theoretische mathematische Marken: 12% Rabatt = {limit_12:.2f} {curr_sym} | 20% Rabatt = {limit_20:.2f} {curr_sym})*")
        else:
            l1, l2 = st.columns(2)
            with l1: st.success(f"**1. Kauflimit (12 % Rabatt):** `{limit_12:.2f} {curr_sym}`")
            with l2: st.success(f"**2. Kauflimit (20 % Rabatt):** `{limit_20:.2f} {curr_sym}`")

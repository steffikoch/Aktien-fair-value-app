import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="4-Score Depot Engine", layout="wide", page_icon="📈")

st.title("📈 4-Score Depot- & Allokations-Engine")
st.caption("Transparente, mehrdimensionale Aktienanalyse & Risikosteuerung")

# Session State für Portfolio
if "portfolio_data" not in st.session_state:
    st.session_state.portfolio_data = pd.DataFrame([
        {"Ticker": "LHA.DE", "Kaufkurs": 7.50, "Stueckzahl": 200, "Sektor": "Industrials / Aviation"},
        {"Ticker": "AAPL", "Kaufkurs": 175.00, "Stueckzahl": 20, "Sektor": "Technology"},
        {"Ticker": "MSFT", "Kaufkurs": 380.00, "Stueckzahl": 10, "Sektor": "Technology"},
        {"Ticker": "DTE.DE", "Kaufkurs": 22.00, "Stueckzahl": 50, "Sektor": "Telecommunication"}
    ])

# =============================================================
# HELPER: TICKER RESOLUTION (NAMEN IN TICKER UMWANDELN)
# =============================================================
def resolve_ticker_symbol(user_input):
    user_input = user_input.strip()
    if not user_input:
        return None
    
    # Bekannte direkte Zuordnungen für häufige deutsche/internationale Namen
    known_mappings = {
        "DEUTSCHE TELEKOM": "DTE.DE",
        "TELEKOM": "DTE.DE",
        "LUFTHANSA": "LHA.DE",
        "DEUTSCHE LUFTHANSA": "LHA.DE",
        "ALLIANZ": "ALV.DE",
        "BASF": "BAS.DE",
        "BAYER": "BAYN.DE",
        "BMW": "BMW.DE",
        "SIEMENS": "SIE.DE",
        "VOLKSWAGEN": "VOW3.DE",
        "VW": "VOW3.DE",
        "SAP": "SAP.DE",
        "APPLE": "AAPL",
        "MICROSOFT": "MSFT",
        "NVIDIA": "NVDA",
        "AMAZON": "AMZN",
        "TESLA": "TSLA"
    }
    
    upper_input = user_input.upper()
    if upper_input in known_mappings:
        return known_mappings[upper_input]

    # Wenn es bereits wie ein Symbol aussieht (z.B. DTE.DE oder AAPL)
    if "." in user_input or (len(user_input) <= 5 and user_input.isalpha()):
        return user_input.upper()
    
    # Automatische Suche über Yahoo Finance API
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
# HELPER: STABILE 4-SCORE BERECHNUNG
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
        growth = max(0, (info.get('earningsGrowth') or 0.0) * 100)
        beta = info.get('beta')
        total_cash = info.get('totalCash', 0) or 0
        total_debt = info.get('totalDebt', 0) or 0
        shares = info.get('sharesOutstanding', 0) or 0
        eps = info.get('forwardEps') or info.get('trailingEps') or 0.0
        sector = info.get('sector', 'Unbekannt')
        
        # Net Cash per Share
        net_cash_ps = ((total_cash - total_debt) / shares) if shares > 0 else 0.0

        # -------------------------------------------------------------
        # SCORE 1: QUALITY SCORE (0 - 100 Pkt.) mit 5 Säulen
        # -------------------------------------------------------------
        # A) Profitabilität (max 25 Pkt.)
        p_score = 0
        if net_margin >= 15: p_score += 15
        elif net_margin >= 5: p_score += 10
        elif net_margin > 0: p_score += 4
        
        if roe >= 15: p_score += 10
        elif roe >= 8: p_score += 6
        elif roe > 0: p_score += 2

        # B) Wachstum (max 20 Pkt.)
        g_score = min(20, int(growth * 0.8))

        # C) Bilanz & Verschuldung (max 20 Pkt.)
        b_score = 15 if net_cash_ps > 0 else (10 if total_cash > (total_debt * 0.5) else 5)

        # D) Cashflow (max 20 Pkt.) - Differenzierung für N/A!
        if fcf is None:
            c_score = 10  # ⚪ Neutral bei fehlenden Daten (keine künstliche Bestrafung)
            fcf_status = "⚪ Keine Daten"
        elif fcf > 0:
            c_score = 20  # 🟢 Positiv
            fcf_status = "🟢 Positiv"
        elif fcf == 0:
            c_score = 10  # 🟡 Neutral / Schwach
            fcf_status = "🟡 Neutral / Schwach"
        else:
            c_score = 0   # 🔴 Negativ
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
        
        # Marge
        if net_margin < 3.0: conf_score -= 35
        elif net_margin < 7.0: conf_score -= 15
        
        # Cashflow-Datenbasis
        if fcf is None: conf_score -= 15
        elif fcf <= 0: conf_score -= 25
        
        # Basis-Qualität
        if quality_score < 45: conf_score -= 20
        if beta and beta > 1.25: conf_score -= 10
        
        conf_score = max(0, min(100, conf_score))
        
        if conf_score >= 75: fv_conf_text = "🟢 HOCH"
        elif conf_score >= 45: fv_conf_text = "🟡 MITTEL"
        else: fv_conf_text = "🔴 NIEDRIG"

        # Fair Value Berechnung (Stabilisiert)
        target_pe = min(25.0, max(10.0, 10.0 + (growth * 0.3)))
        fv_vals = []
        if eps > 0: fv_vals.append((eps * target_pe) + max(0, net_cash_ps))
        if fcf and shares > 0 and fcf > 0: fv_vals.append(((fcf / shares) * target_pe) + max(0, net_cash_ps))
        
        fair_value = np.mean(fv_vals) if fv_vals else price
        mos = ((fair_value - price) / price) * 100 if fair_value > 0 else 0.0

        # -------------------------------------------------------------
        # SCORE 3: RISK & CAPITAL EFFICIENCY SCORE (0 - 100 Pkt.)
        # -------------------------------------------------------------
        mos_part = min(50, max(0, int((mos + 10) * 1.25)))
        qual_part = int(quality_score * 0.5)
        risk_cap_score = min(100, max(0, mos_part + qual_part))

        # -------------------------------------------------------------
        # SCORE 4: PORTFOLIO FIT SCORE (0 - 100 Pkt.)
        # -------------------------------------------------------------
        weight_pct = (current_position_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
        
        if weight_pct > 8.0:
            fit_score = 0
            pos_status = f"🔴 {weight_pct:.1f}% (⚠️ KEINE NACHKÄUFE: >8%)"
        elif weight_pct > 6.0:
            fit_score = 30
            pos_status = f"🟠 {weight_pct:.1f}% (⚠️ NACHKAUF-BREMSE: 6–8%)"
        elif weight_pct >= 4.0:
            fit_score = 70
            pos_status = f"🟡 {weight_pct:.1f}% (Normale Gewichtung: 4–6%)"
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
                "Wachstum": (g_score, 20),
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
# EINGABE-BEREICH IN DER SIDEBAR
# =============================================================
st.sidebar.header("⚙️ Eingabe & Depot-Kontext")
ticker_input = st.sidebar.text_input("Aktien-Name oder Ticker (z. B. DTE.DE, Deutsche Telekom, AAPL):", value="Deutsche Telekom").strip()

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Positions-Kontext")
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
        st.error(f"Konnte keine Daten für '{ticker_input}' (Kürzel: {resolved_ticker}) abrufen. Bitte überprüfe die Eingabe oder gib das genaue Börsenkürzel an (z. B. DTE.DE für Deutsche Telekom, LHA.DE für Lufthansa, AAPL für Apple).")
    else:
        # Auslesen der Werte
        price = res["price"]
        curr_sym = res["curr_sym"]
        fv = res["fair_value"]
        mos = res["margin_of_safety"]
        q_score = res["quality_score"]
        conf_score = res["conf_score"]
        rc_score = res["risk_cap_score"]
        fit_score = res["fit_score"]
        
        # -------------------------------------------------------------
        # SYNTHESE DES ENDURTEILS
        # -------------------------------------------------------------
        limits_active = True
        
        if q_score < 40 or res["net_margin"] < 3.0:
            final_action = "🔴 KEIN KAUF (Value Trap: Zu geringe Marge & Qualität)"
            limits_active = False
        elif fit_score <= 30:
            final_action = "🔴 KEIN NACHKAUF (Depot-Klumpenrisiko-Bremse aktiv!)"
            limits_active = False
        elif conf_score < 45:
            final_action = "🔴 KEIN KAUF (Fair Value nicht ausreichend vertrauenswürdig)"
            limits_active = False
        elif rc_score < 40 or mos < 10:
            final_action = "🟠 ABWARTEN (Erst bei höherem Sicherheitsrabatt interessant)"
            limits_active = True
        elif q_score >= 70 and mos >= 15:
            final_action = "🟢 NACHKAUF / POSITION AUFSTOCKEN"
            limits_active = True
        else:
            final_action = "🟡 BEOBACHTEN"
            limits_active = True

        # Header & Endurteil Banner
        st.subheader(f"{res['name']} ({res['symbol']}) – {price:.2f} {curr_sym}")
        
        if "🔴" in final_action:
            st.error(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")
        elif "🟠" in final_action or "🟡" in final_action:
            st.warning(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")
        else:
            st.success(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")

        st.markdown("---")
        st.subheader("📊 DIE 4 HOCHTRANSPARENTEN SCORES")

        s1, s2, s3, s4 = st.columns(4)
        
        with s1:
            q_color = "🔴" if q_score < 45 else ("🟡" if q_score < 65 else "🟢")
            st.markdown("### 🏢 Quality")
            st.metric("Quality Score", f"{q_score} / 100", delta=f"Status: {q_color}", delta_color="off")
            st.caption(f"Nettomarge: {res['net_margin']:.2f}%")

        with s2:
            st.markdown("### 💰 Fair Value Conf.")
            st.metric("Confidence Score", f"{conf_score} / 100", delta=f"Status: {res['fv_conf_text']}", delta_color="off")
            st.caption(f"Fair Value: {fv:.2f} {curr_sym} (Puffer: {mos:+.1f}%)")

        with s3:
            rc_color = "🔴" if rc_score < 40 else ("🟡" if rc_score < 65 else "🟢")
            st.markdown("### ⚖️ Risk / Capital")
            st.metric("Capital Eff.", f"{rc_score} / 100", delta=f"Status: {rc_color}", delta_color="off")
            st.caption(f"Cashflow: {res['fcf_status']}")

        with s4:
            fit_color = "🔴" if fit_score <= 30 else ("🟡" if fit_score < 70 else "🟢")
            st.markdown("### 💼 Portfolio Fit")
            st.metric("Fit Score", f"{fit_score} / 100", delta=f"Status: {fit_color}", delta_color="off")
            st.caption(res["pos_status"])

        st.markdown("---")

        # -------------------------------------------------------------
        # TRANSPARENZ-BOX: QUALITY SCORE IN 5 SÄULEN
        # -------------------------------------------------------------
        st.subheader("🔍 Detail-Aufschlüsselung des Quality Scores")
        
        pil_cols = st.columns(5)
        for idx, (pillar_name, (achieved, max_pts)) in enumerate(res["quality_pillars"].items()):
            ratio = achieved / max_pts
            p_color = "🔴" if ratio < 0.4 else ("🟡" if ratio < 0.7 else "🟢")
            with pil_cols[idx]:
                st.markdown(f"**{pillar_name}**")
                st.write(f"{p_color} **{achieved}** / {max_pts} Pkt.")

        st.markdown("---")

        # -------------------------------------------------------------
        # HANDLUNGSMARKEN & KAUFLIMITS
        # -------------------------------------------------------------
        st.subheader("🎯 Handlungsmarken & Kauflimits")
        
        limit_15 = fv * 0.85
        limit_25 = fv * 0.75

        if not limits_active:
            st.error("⚠️ KAUFLIMITS AUSGESETZT: Qualität zu schwach, Fair Value unsicher oder Depot-Limits erreicht.")
            st.caption(f"*(Theoretische mathematische Marken ohne Kaufempfehlung: 15% Rabatt = {limit_15:.2f} {curr_sym} | 25% Rabatt = {limit_25:.2f} {curr_sym})*")
        else:
            l1, l2 = st.columns(2)
            with l1:
                st.success(f"**1. Kauflimit (15 % Rabatt):** `{limit_15:.2f} {curr_sym}`")
            with l2:
                st.success(f"**2. Kauflimit (25 % Rabatt):** `{limit_25:.2f} {curr_sym}`")

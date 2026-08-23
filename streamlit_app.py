import streamlit as st
import yfinance as ticker_data

# =============================================================
# SEITEN-KONFIGURATION
# =============================================================
st.set_page_config(
    page_title="Depot-Strategie & Bewertungs-Engine",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Depot-Strategie & Aktien-Bewertungs-Engine")
st.caption("Qualitätsprüfung, Fair-Value-Vertrauen, Risikomanagement und Depot-Synthese")

# =============================================================
# SIDEBAR: DEPOT- & AKTIEN-EINGABE
# =============================================================
st.sidebar.header("⚙️ Eingabe & Depot-Kontext")

ticker_symbol = st.sidebar.text_input("Aktien-Ticker (z. B. LHA.DE, AAPL, MSFT)", value="LHA.DE").upper()

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Deine Depot-Daten")
current_position_val = st.sidebar.number_input("Wert deiner Position in dieser Aktie (€)", min_value=0.0, value=710.0, step=50.0)
total_portfolio_val = st.sidebar.number_input("Gesamtwert deines Depots (€)", min_value=1.0, value=10000.0, step=500.0)

# Depot-Gewichtung berechnen
weight_pct = (current_position_val / total_portfolio_val) * 100

# =============================================================
# BERECHNUNGS-FUNKTIONEN
# =============================================================
@st.cache_data(ttl=3600)
def fetch_and_analyze_stock(symbol):
    stock = ticker_data.Ticker(symbol)
    info = stock.info
    
    # Fundamental-Daten abrufen (mit Fallbacks)
    current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0.0
    currency = info.get('currency', 'EUR')
    curr_sym = "€" if currency == "EUR" else ("$" if currency == "USD" else currency)
    
    # Finanzkennzahlen
    net_margin = (info.get('profitMargins') or 0.0) * 100
    fcf = info.get('freeCashflow') or 0
    beta = info.get('beta') or 1.0
    roe = (info.get('returnOnEquity') or 0.0) * 100
    
    # ---------------------------------------------------------
    # 1. QUALITY SCORE BERECHNUNG (0-100)
    # ---------------------------------------------------------
    q_score = 50 # Basiswert
    
    if net_margin > 15: q_score += 20
    elif net_margin > 8: q_score += 10
    elif net_margin < 3: q_score -= 20
    
    if roe > 15: q_score += 15
    elif roe < 5: q_score -= 15
    
    if fcf > 0: q_score += 15
    else: q_score -= 20
    
    q_score = max(0, min(100, q_score))
    
    # ---------------------------------------------------------
    # 2. FAIR VALUE BERECHNUNG (Vereinfachtes DCF/Multi-Modell)
    # ---------------------------------------------------------
    target_price = info.get('targetMeanPrice') or current_price
    pe_ratio = info.get('trailingPE') or 15.0
    eps = info.get('trailingEps') or 0.0
    
    # Rechnerischer Fair Value als Kombination aus Analystenziel und KGV-Ansatz
    fair_value = target_price if target_price > 0 else (eps * 12.0)
    if fair_value <= 0:
        fair_value = current_price
        
    margin_of_safety = ((fair_value - current_price) / fair_value) * 100 if fair_value > 0 else 0
    
    # ---------------------------------------------------------
    # 3. FAIR-VALUE-VERTRAUENSGRAD (CONFIDENCE)
    # ---------------------------------------------------------
    conf_score = 100
    
    if net_margin < 5.0:
        conf_score -= 35  # Zykliker / Marge zu dünn
    if fcf <= 0:
        conf_score -= 25  # Kein echter Cashflow
    if q_score < 50:
        conf_score -= 20  # Schwache Gesamtqualität
    if beta > 1.2:
        conf_score -= 10  # Hohe Markt-Volatilität
        
    if conf_score >= 75:
        fv_confidence = "🟢 HOCH"
    elif conf_score >= 45:
        fv_confidence = "🟡 MITTEL"
    else:
        fv_confidence = "🔴 NIEDRIG"
        
    # Kapital-Effizienz Score
    cap_eff = max(0, min(100, int(roe * 3.5)))
    
    return {
        'symbol': symbol,
        'name': info.get('shortName', symbol),
        'price': current_price,
        'curr_sym': curr_sym,
        'margin_pct': net_margin,
        'fcf': fcf,
        'q_score': q_score,
        'fair_value': fair_value,
        'margin_of_safety': margin_of_safety,
        'fv_confidence': fv_confidence,
        'conf_score': conf_score,
        'cap_eff': cap_eff,
        'sector': info.get('sector', 'Unbekannt')
    }

# =============================================================
# HAUPTPROGRAMM / AUSWERTUNG
# =============================================================
if ticker_symbol:
    with st.spinner("Analysiere Bilanzen & Depot-Kontext..."):
        res = fetch_and_analyze_stock(ticker_symbol)
        
    quality_score = res['q_score']
    fair_value = res['fair_value']
    current_price = res['price']
    curr_sym = res['curr_sym']
    margin_of_safety = res['margin_of_safety']
    cap_eff = res['cap_eff']
    
    # ---------------------------------------------------------
    # DECISION ENGINE: REGELWERK
    # ---------------------------------------------------------
    
    # Ebene 4: Positions-Einstufung
    if weight_pct > 8.0:
        weight_status = f"🔴 {weight_pct:.1f}% (⚠️ KEINE NACHKÄUFE: Position > 8%)"
        pos_blocked = True
    elif weight_pct > 6.0:
        weight_status = f"🟠 {weight_pct:.1f}% (⚠️ NACHKAUF-BREMSE: Position 6–8%)"
        pos_blocked = True
    elif weight_pct >= 4.0:
        weight_status = f"🟡 {weight_pct:.1f}% (Normale Gewichtung 4–6%)"
        pos_blocked = False
    else:
        weight_status = f"🟢 {weight_pct:.1f}% (Aufstockung möglich < 4%)"
        pos_blocked = False

    sector_blocked = False # Platzhalter für Branchen-Klumpenrisiko
    
    # Synthese des Endurteils (4-Ebenen-Check)
    if quality_score < 45 or res['margin_pct'] < 3.0:
        final_action = "🔴 KEIN KAUF (Value Trap: Zu geringe Marge & Qualität)"
        limits_active = False
    elif pos_blocked or sector_blocked:
        final_action = "🔴 KEIN NACHKAUF (Klumpenrisiko-Bremse aktiv!)"
        limits_active = False
    elif "🔴 NIEDRIG" in res['fv_confidence']:
        final_action = "🔴 KEIN KAUF (Fair Value nicht ausreichend vertrauenswürdig)"
        limits_active = False
    elif cap_eff < 40 or margin_of_safety < 10:
        limit_15_val = fair_value * 0.85
        final_action = f"🟠 ABWARTEN (Nachkauflimit erst ab {limit_15_val:.2f} {curr_sym})"
        limits_active = True
    elif quality_score >= 75 and margin_of_safety >= 15:
        final_action = "🟢 NACHKAUF / POSITION AUFSTOCKEN"
        limits_active = True
    else:
        final_action = "🟡 BEOBACHTEN"
        limits_active = True

    # Kauflimit-Marken berechnen
    limit_15 = fair_value * 0.85
    limit_25 = fair_value * 0.75

    # ---------------------------------------------------------
    # OBERFLÄCHEN-AUSGABE (STYLING & METRIKEN)
    # ---------------------------------------------------------
    st.subheader(f"{res['name']} ({res['symbol']}) – {current_price:.2f} {curr_sym}")
    
    # ENDGÜLTIGES URTEIL BANNER
    if "🔴" in final_action:
        st.error(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")
    elif "🟠" in final_action or "🟡" in final_action:
        st.warning(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")
    else:
        st.success(f"### 🎯 ENDGÜLTIGES DEPOT-URTEIL: {final_action}")

    st.markdown("---")

    # 4-EBENEN TABELLE
    st.subheader("📋 4-Ebenen-Analyse im Detail")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**1️⃣ Ebene: Qualität**")
        q_color = "🔴" if quality_score < 45 else ("🟠" if quality_score < 65 else "🟢")
        st.metric("Quality Score", f"{quality_score}/100", delta_color="normal")
        st.write(f"Status: {q_color}")
        st.caption(f"Nettomarge: {res['margin_pct']:.2f}%")

    with col2:
        st.markdown("**2️⃣ Ebene: Bewertung**")
        st.metric("Fair Value", f"{fair_value:.2f} {curr_sym}")
        st.write(f"Vertrauensgrad: {res['fv_confidence']}")
        st.caption(f"Rechnerischer Puffer: {margin_of_safety:.1f}%")

    with col3:
        st.markdown("**3️⃣ Ebene: Risiko**")
        eff_color = "🔴" if cap_eff < 40 else ("🟠" if cap_eff < 65 else "🟢")
        st.metric("Kapital-Effizienz", f"{cap_eff}/100")
        st.write(f"Status: {eff_color}")
        st.caption(f"FCF: {'Positive' if res['fcf'] > 0 else 'Negativ/Schwach'}")

    with col4:
        st.markdown("**4️⃣ Ebene: Depot**")
        st.metric("Depot-Anteil", f"{weight_pct:.1f}%")
        st.write(weight_status)
        st.caption(f"Sektor: {res['sector']}")

    st.markdown("---")

    # HANDLUNGSMARKEN & KAUFLIMITS
    st.subheader("🎯 Handlungsmarken & Kauflimits")

    if not limits_active:
        st.error("⚠️ KAUFLIMITS AUSGESETZT: Qualität zu schwach, Fair Value unsicher oder Depot-Limits erreicht.")
        st.caption(f"*(Theoretische mathematische Marken ohne Kaufempfehlung: 15% Rabatt = {limit_15:.2f} {curr_sym} | 25% Rabatt = {limit_25:.2f} {curr_sym})*")
    else:
        l1, l2 = st.columns(2)
        with l1:
            st.success(f"**1. Kauflimit (15 % Rabatt):** `{limit_15:.2f} {curr_sym}`")
        with l2:
            st.success(f"**2. Kauflimit (25 % Rabatt):** `{limit_25:.2f} {curr_sym}`")

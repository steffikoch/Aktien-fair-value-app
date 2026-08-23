import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page Config
st.set_page_config(page_title="Aktien & Portfolio-Allokations-Engine", layout="wide")

st.title("📊 Risiko, Fair-Value & Depot-Allokations-Engine")

tab1, tab2, tab3 = st.tabs(["🔍 Einzelanalyse & Depot-Check", "📋 Watchlist & Kauflimits", "💼 Mein Depot (Portfolio-Kontext)"])

# Default-Depot im Session State
if "portfolio_data" not in st.session_state:
    st.session_state.portfolio_data = pd.DataFrame([
        {"Ticker": "COCO", "Kaufkurs": 54.50, "Stueckzahl": 50, "Sektor": "Consumer / Beverages"},
        {"Ticker": "AAPL", "Kaufkurs": 175.00, "Stueckzahl": 20, "Sektor": "Technology"},
        {"Ticker": "MSFT", "Kaufkurs": 380.00, "Stueckzahl": 10, "Sektor": "Technology"},
        {"Ticker": "TOST", "Kaufkurs": 22.00, "Stueckzahl": 100, "Sektor": "Technology / SaaS"},
        {"Ticker": "PG", "Kaufkurs": 145.00, "Stueckzahl": 15, "Sektor": "Consumer Staples"},
        {"Ticker": "LHA.DE", "Kaufkurs": 7.50, "Stueckzahl": 200, "Sektor": "Industrials / Aviation"}
    ])

# ==========================================
# HELPER FUNCTION: TICKER-ANALYSE & FILTER
# ==========================================
def analyze_single_ticker(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price or np.isnan(price):
            return None
        
        curr = info.get("currency", "USD")
        curr_sym = "€" if curr == "EUR" else "$"
        eps = info.get("forwardEps") or info.get("trailingEps")
        fcf = info.get("freeCashflow")
        shares = info.get("sharesOutstanding")
        growth = max(0, (info.get("earningsGrowth", 0) or 0) * 100)
        margins = info.get("profitMargins", 0) or 0
        sector = info.get("sector", "Unbekannt")
        beta = info.get("beta")
        ev_ebitda = info.get("enterpriseToEbitda")
        
        # 🚨 FIX 1: Dividendenrendite abfangen / plausibilisieren (>20% = Datenfehler/Sonderdiv)
        raw_div_yield = (info.get("dividendYield", 0) or 0) * 100
        if raw_div_yield > 20.0:
            div_yield_clean = None 
        else:
            div_yield_clean = raw_div_yield

        # Net Cash
        total_cash = info.get("totalCash", 0) or 0
        total_debt = info.get("totalDebt", 0) or 0
        net_cash_ps = 0.0
        if shares and shares > 0 and (total_cash - total_debt) > 0:
            net_cash_ps = (total_cash - total_debt) / shares
        
        # Fair Value Modell (KGV & FCF)
        target_pe = min(30.0, max(12.0, 12.0 + (growth * 0.4)))
        vals = []
        if eps and eps > 0:
            vals.append((eps * target_pe) + net_cash_ps)
        if fcf and shares and fcf > 0 and shares > 0:
            vals.append(((fcf / shares) * target_pe) + net_cash_ps)
        
        if vals:
            fv = np.mean(vals)
            mos = ((fv - price) / price) * 100
        else:
            fv, mos = price, 0.0

        # Quality Score (0 - 100)
        score_growth = min(20, max(0, int(growth * 0.8)))
        score_margin = min(25, max(0, int(margins * 100 * 1.5))) # Starke Gewichtung der Marge
        score_cash = 20 if net_cash_ps > 0 else 5
        score_balance = 20 if (ev_ebitda and ev_ebitda < 15) else 5
        score_risk = 15 if (beta and beta < 1.0) else (10 if beta and beta < 1.4 else 0)
        
        quality_score = min(100, score_growth + score_margin + score_cash + score_balance + score_risk)

        # 🎯 FIX 2: Vertrauensgrad des Fair Values bestimmen
        confidence_points = 100
        if margins < 0.05: confidence_points -= 35       # Nettomarge < 5% = zyklisch & instabil
        if not fcf or fcf <= 0: confidence_points -= 25    # Kein freier Cashflow
        if quality_score < 50: confidence_points -= 20     # Schwacher Quality Score
        if beta and beta > 1.2: confidence_points -= 10
        
        if confidence_points >= 75:
            fv_confidence = "🟢 HOCH (Stabile Bilanz & Cashflows)"
        elif confidence_points >= 45:
            fv_confidence = "🟡 MITTEL (Zyklisch / schwankende Gewinne)"
        else:
            fv_confidence = "🔴 NIEDRIG (Achtung: Value-Trap-Risiko / Dünne Marge!)"

        # 💰 Kapital-Effizienz Score (0 - 100)
        mos_factor = min(50, max(0, int((mos + 10) * 1.25)))
        quality_factor = int(quality_score * 0.5)
        capital_efficiency = min(100, max(0, mos_factor + quality_factor))

        return {
            "ticker": ticker_symbol,
            "info": info,
            "price": price,
            "currency_symbol": curr_sym,
            "fair_value": fv,
            "margin_of_safety": mos,
            "quality_score": quality_score,
            "capital_efficiency": capital_efficiency,
            "fv_confidence": fv_confidence,
            "div_yield": div_yield_clean,
            "net_cash_ps": net_cash_ps,
            "sector": sector,
            "margin_pct": margins * 100
        }
    except Exception:
        return None

# ==========================================
# TAB 1: EINZELANALYSE & DEPOT-CHECK
# ==========================================
with tab1:
    st.subheader("4-Ebenen-Analyse: Unternehmen ➔ Bewertung ➔ Risiko ➔ Depot")
    
    user_query = st.text_input("Gib Ticker oder Firmennamen ein:", value="LHA.DE", placeholder="z. B. LHA.DE, COCO, AAPL...")
    ticker_input = user_query.strip().upper()
    
    analyze_btn = st.button("4-Ebenen-Check ausführen", type="primary")

    if analyze_btn and ticker_input:
        with st.spinner(f"Analysiere {ticker_input} über alle 4 Ebenen..."):
            res = analyze_single_ticker(ticker_input)
            
            if not res:
                st.error("Keine gültigen Kursdaten für diesen Ticker gefunden.")
            else:
                price = res["price"]
                curr_sym = res["currency_symbol"]
                base_case = res["fair_value"]
                margin_of_safety = res["margin_of_safety"]
                quality_score = res["quality_score"]
                cap_eff = res["capital_efficiency"]
                info = res["info"]
                
                limit_15 = base_case * 0.85
                limit_25 = base_case * 0.75

                # -------------------------------------------------------------
                # EBENE 1 & 2: UNTERNEHMEN & BEWERTUNG
                # -------------------------------------------------------------
                st.markdown("---")
                st.header(f"1. Ebene: Unternehmen & Bewertung ({info.get('shortName', ticker_input)})")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Aktueller Kurs", f"{price:.2f} {curr_sym}")
                c2.metric("Qualitäts-Fair-Value", f"{base_case:.2f} {curr_sym}")
                c3.metric("Sicherheitspuffer", f"{margin_of_safety:+.1f} %")
                c4.metric("Quality Score", f"{quality_score} / 100 Pkt.")

                st.write(f"**Vertrauensgrad des Fair Values:** {res['fv_confidence']}")
                
                if res['div_yield'] is None:
                    st.caption("⚠️ *Dividendenrendite ausgeblendet (Auffällige Rohdaten / Sonderdividende >20%)*")
                else:
                    st.write(f"**Dividendenrendite:** {res['div_yield']:.2f} %")

                # 🚨 FIX 3: Value-Trap-Schutz im isolierten Urteil
                if quality_score < 45 or res['margin_pct'] < 3.0:
                    stock_judgment = "🔴 VALUE TRAP / HOCHES RISIKO (Schwache Marge & Qualität – Rechnerischer Puffer trügerisch!)"
                elif margin_of_safety >= 20 and quality_score >= 75:
                    stock_judgment = "🟢 KAUFEN (Attraktiver Rabatt bei hoher Qualität)"
                elif margin_of_safety >= 15 and quality_score >= 55:
                    stock_judgment = "🟡 SPEKULATIVER VALUE (Guter Puffer, mittlere Qualität)"
                elif margin_of_safety >= 0:
                    stock_judgment = "🟠 ABWARTEN (Fair bewertet / erst bei Rücksetzer interessant)"
                else:
                    stock_judgment = "🔴 VERKAUFEN / ÜBERBEWERTET"

                st.info(f"**Isoliertes Aktien-Urteil:** {stock_judgment}")

                # -------------------------------------------------------------
                # EBENE 3: KAPITAL-EFFIZIENZ & RISIKO
                # -------------------------------------------------------------
                st.markdown("---")
                st.header("2. Ebene: Risiko & 💰 Kapital-Effizienz")

                ce1, ce2 = st.columns(2)
                
                if cap_eff >= 80 and quality_score >= 60:
                    eff_text = "🟢 Top Kapital-Einsatz (Hoher Rabatt + Hohe Qualität)"
                elif cap_eff >= 60 and quality_score >= 50:
                    eff_text = "🟡 Attraktiv (Gutes Chance/Risiko-Profil)"
                elif cap_eff >= 30:
                    eff_text = "🟠 Beobachten (Geld vorerst zurückhalten)"
                else:
                    eff_text = "🔴 Attraktivität gering (Geringe Qualität oder unzureichende Marge)"

                ce1.metric("Kapital-Effizienz Score", f"{cap_eff} / 100 Pkt.", delta=eff_text, delta_color="off")
                ce2.write(f"**Nettomarge:** {res['margin_pct']:.2f} %")
                ce2.write(f"**Net Cash Bonus:** +{res['net_cash_ps']:.2f} {curr_sym} / Aktie")
                ce2.write(f"**Sektor:** {res['sector']}")

                # -------------------------------------------------------------
                # EBENE 4: DEPOT-KONTEXT & ALLOKATION
                # -------------------------------------------------------------
                st.markdown("---")
                st.header("3. Ebene: 💼 Depot-Kontext & Allokation (Das endgültige Signal)")

                port_df = st.session_state.portfolio_data.copy()
                
                existing_pos = port_df[port_df["Ticker"] == ticker_input]
                has_position = not existing_pos.empty
                
                total_portfolio_val = 0.0
                sector_weights = {}
                
                for idx, r in port_df.iterrows():
                    p_ticker = str(r["Ticker"]).strip().upper()
                    p_qty = r["Stueckzahl"]
                    p_res = analyze_single_ticker(p_ticker)
                    if p_res:
                        pos_val = p_res["price"] * p_qty
                        total_portfolio_val += pos_val
                        sec = r.get("Sektor", p_res.get("sector", "Sonstige"))
                        sector_weights[sec] = sector_weights.get(sec, 0.0) + pos_val

                # Positionsgewicht & Sektoranteil
                if has_position:
                    pos_qty = existing_pos.iloc[0]["Stueckzahl"]
                    buy_price = existing_pos.iloc[0]["Kaufkurs"]
                    pos_val = price * pos_qty
                    weight_pct = (pos_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
                else:
                    weight_pct = 0.0

                pos_blocked = weight_pct > 6.0
                act_sector = res.get("sector", "Unbekannt")
                sector_val = sector_weights.get(act_sector, 0.0)
                sector_pct = (sector_val / total_portfolio_val * 100) if total_portfolio_val > 0 else 0.0
                sector_blocked = sector_pct > 25.0

                # Statusmeldungen
                weight_status = f"🔴 {weight_pct:.1f}% (⚠️ NACHKAUF-BREMSE AKTIV: Position > 6%)" if pos_blocked else f"🟢 {weight_pct:.1f}% (Im Solllimit < 6%)"
                sector_status = f"🔴 {act_sector} ({sector_pct:.1f}% - ⚠️ NACHKAUF-BREMSE AKTIV: Sektor > 25%)" if sector_blocked else f"🟢 {act_sector} ({sector_pct:.1f}% im Depot)"

                # Synthese: Endgültige Depot-Empfehlung
                if quality_score < 45 or res['margin_pct'] < 3.0:
                    final_action = "🔴 KEIN KAUF (Value Trap Risk: Zu geringe Marge & Qualität)"
                elif pos_blocked or sector_blocked:
                    final_action = "🔴 KEIN NACHKAUF (Klumpenrisiko-Bremse aktiv!)"
                elif cap_eff < 40 or margin_of_safety < 10:
                    final_action = f"🟠 ABWARTEN (Nachkauflimit erst ab {limit_15:.2f} {curr_sym})"
                elif quality_score >= 75 and margin_of_safety >= 15:
                    final_action = "🟢 NACHKAUF / POSITION AUFSTOCKEN"
                else:
                    final_action = "🟡 BEOBACHTEN"

                depot_matrix = pd.DataFrame({
                    "Ebene / Kriterium": [
                        "1. Aktie & Qualität",
                        "2. Fair-Value-Vertrauen",
                        "3. 💰 Kapital-Effizienz",
                        "4. Positionsgewicht (>6% Bremse)",
                        "5. Sektoranteil (>25% Bremse)",
                        "🎯 ENDGÜLTIGES DEPOT-URTEIL"
                    ],
                    "Ergebnis": [
                        f"{'🟢' if quality_score >= 75 else ('🟡' if quality_score >= 50 else '🔴')} Score {quality_score}/100",
                        res['fv_confidence'],
                        f"{'🟢' if cap_eff >= 60 else '🟠'} Score {cap_eff}/100",
                        weight_status,
                        sector_status,
                        f"**{final_action}**"
                    ]
                })
                st.table(depot_matrix)

                st.subheader("🎯 Handlungsmarken für den Kauf")
                st.write(f"- **1. Kauflimit (15 % Rabatt):** `{limit_15:.2f} {curr_sym}`")
                st.write(f"- **2. Kauflimit (25 % Rabatt):** `{limit_25:.2f} {curr_sym}`")

# ==========================================
# TAB 2: WATCHLIST
# ==========================================
with tab2:
    st.subheader("📋 Watchlist & Kauflimits")
    watchlist_input = st.text_input("Ticker-Liste:", value="COCO, LHA.DE, AAPL, MSFT, TOST")
    
    if st.button("Watchlist vergleichen"):
        tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
        results = []
        for t in tickers:
            r = analyze_single_ticker(t)
            if r:
                results.append({
                    "Ticker": t,
                    f"Kurs ({r['currency_symbol']})": round(r['price'], 2),
                    f"Fair Value ({r['currency_symbol']})": round(r['fair_value'], 2),
                    "Puffer (%)": f"{r['margin_of_safety']:+.1f} %",
                    "Quality": f"{r['quality_score']}/100",
                    "Kapital-Effizienz": f"{r['capital_efficiency']}/100",
                    "Vertrauensgrad": r['fv_confidence']
                })
        st.table(pd.DataFrame(results))

# ==========================================
# TAB 3: MEIN DEPOT (PORTFOLIO-KONTEXT)
# ==========================================
with tab3:
    st.subheader("💼 Portfolio-Verwaltung (~15 Aktien)")
    
    uploaded_file = st.file_uploader("📂 Depot aus CSV laden (optional)", type=["csv"])
    if uploaded_file is not None:
        st.session_state.portfolio_data = pd.read_csv(uploaded_file)

    edited_df = st.data_editor(
        st.session_state.portfolio_data,
        num_rows="dynamic",
        use_container_width=True
    )
    st.session_state.portfolio_data = edited_df

    if st.button("Gesamtes Portfolio auswerten", type="primary"):
        with st.spinner("Analysiere Gesamtdepot..."):
            port_summary = []
            for idx, r in edited_df.iterrows():
                t = str(r.get("Ticker", "")).strip().upper()
                p_res = analyze_single_ticker(t)
                if p_res:
                    qty = int(r.get("Stueckzahl", 0))
                    val = p_res["price"] * qty
                    port_summary.append({
                        "Ticker": t,
                        "Stück": qty,
                        "Kaufkurs": r.get("Kaufkurs"),
                        f"Akt. Kurs ({p_res['currency_symbol']})": round(p_res['price'], 2),
                        f"Wert ({p_res['currency_symbol']})": round(val, 2),
                        "Quality": f"{p_res['quality_score']}/100",
                        "Kapital-Effizienz": f"{p_res['capital_efficiency']}/100",
                        "Fair Value Puffer": f"{p_res['margin_of_safety']:+.1f} %",
                        "Vertrauen": p_res['fv_confidence'],
                        "Sektor": r.get("Sektor", p_res.get("sector"))
                    })
            st.table(pd.DataFrame(port_summary))

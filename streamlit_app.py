import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page Config
st.set_page_config(page_title="Aktien Fair-Value & Depot App", layout="wide")

st.title("📊 Risiko, Fair-Value & Depot Analysator")

tab1, tab2, tab3 = st.tabs(["🔍 Einzelanalyse", "📋 Watchlist & Kauflimits", "💼 Depot-Abgleich"])

# ==========================================
# TAB 1: EINZELANALYSE
# ==========================================
with tab1:
    st.subheader("Aktie auswählen")
    
    user_query = st.text_input("Gib Ticker oder Firmennamen ein:", placeholder="z. B. Luf, Toast, Coco, Apple...")
    ticker_input = user_query.strip()
    
    if len(user_query) >= 3:
        try:
            search_results = yf.Search(user_query, max_results=5).quotes
            if search_results:
                options = {
                    item['symbol']: f"{item['symbol']} - {item.get('shortname', item.get('longname', 'Unbekannt'))}" 
                    for item in search_results if 'symbol' in item
                }
                if options:
                    selected_ticker = st.selectbox(
                        "Gefundene Aktien (auswählen):", 
                        options=list(options.keys()), 
                        format_func=lambda x: options[x]
                    )
                    if selected_ticker:
                        ticker_input = selected_ticker
        except Exception:
            pass

    analyze_btn = st.button("Aktie analysieren", type="primary")

    if analyze_btn and ticker_input:
        with st.spinner(f"Lade Daten für {ticker_input}..."):
            try:
                stock = yf.Ticker(ticker_input)
                info = stock.info
                
                current_price = info.get("currentPrice") or info.get("regularMarketPrice")
                currency = info.get("currency", "USD")
                currency_symbol = "€" if currency == "EUR" else "$"
                
                if current_price is None or np.isnan(current_price):
                    st.error("Keine gültigen Kursdaten für diesen Ticker gefunden.")
                else:
                    eps = info.get("trailingEps")
                    forward_eps = info.get("forwardEps")
                    fcf = info.get("freeCashflow")
                    shares = info.get("sharesOutstanding")
                    pe_ratio = info.get("trailingPE")
                    pb_ratio = info.get("priceToBook")
                    beta = info.get("beta")
                    profit_margins = info.get("profitMargins", 0) or 0
                    ev_ebitda = info.get("enterpriseToEbitda")
                    dividend_yield = info.get("dividendYield", 0) or 0
                    earnings_growth = info.get("earningsGrowth", 0) or 0
                    
                    # 1. Net Cash per Share
                    total_cash = info.get("totalCash", 0) or 0
                    total_debt = info.get("totalDebt", 0) or 0
                    net_cash_per_share = 0.0
                    if shares and shares > 0:
                        net_cash = total_cash - total_debt
                        if net_cash > 0:
                            net_cash_per_share = net_cash / shares

                    # 2. Fundamentale Ziel-KGVs & Entkoppelte Szenario-Annahmen
                    growth_rate = max(0, earnings_growth * 100)
                    target_pe_base = min(30.0, max(15.0, 15.0 + (growth_rate * 0.4)))
                    target_pe_bear = max(12.0, target_pe_base * 0.75)
                    target_pe_bull = min(38.0, target_pe_base * 1.25)
                    
                    # 3. Modelle Berechnen (Base Case)
                    eval_eps = forward_eps if (forward_eps and forward_eps > 0) else eps
                    
                    dcf_val, kgv_val, fcf_val = None, None, None
                    
                    if eval_eps and eval_eps > 0:
                        kgv_val = (eval_eps * target_pe_base) + net_cash_per_share
                        dcf_val = (eval_eps * (target_pe_base * 0.9)) + net_cash_per_share
                    
                    if fcf and shares and fcf > 0 and shares > 0:
                        fcf_per_share = fcf / shares
                        fcf_val = (fcf_per_share * target_pe_base) + net_cash_per_share
                    
                    # 4. Qualitätsgewichteter Fair Value (Base Case)
                    weights = []
                    vals = []
                    if dcf_val:
                        vals.append(dcf_val); weights.append(1.0)
                    if kgv_val:
                        vals.append(kgv_val); weights.append(1.0)
                    if fcf_val:
                        fcf_weight = 1.5 if profit_margins > 0.10 else 1.0
                        vals.append(fcf_val); weights.append(fcf_weight)
                    
                    if vals:
                        base_case = np.average(vals, weights=weights)
                        
                        bear_eps = (eval_eps * 0.85) if eval_eps else 0
                        bull_eps = (eval_eps * 1.15) if eval_eps else 0
                        
                        if eval_eps and eval_eps > 0:
                            bear_case = (bear_eps * target_pe_bear) + net_cash_per_share
                            best_case = (bull_eps * target_pe_bull) + net_cash_per_share
                        else:
                            bear_case = base_case * 0.75
                            best_case = base_case * 1.35
                        
                        margin_of_safety = ((base_case - current_price) / current_price) * 100
                    else:
                        base_case, bear_case, best_case = current_price, current_price, current_price
                        margin_of_safety = 0.0

                    # 5. Quality Score
                    score_growth = min(20, max(0, int(growth_rate * 0.8)))
                    score_margin = min(20, max(0, int(profit_margins * 100 * 1.2)))
                    score_cash = 20 if net_cash_per_share > 0 else 5
                    score_balance = 20 if (ev_ebitda and ev_ebitda < 20) else 10
                    score_risk = 20 if (beta and beta < 1.0) else (10 if beta and beta < 1.5 else 5)
                    
                    quality_score = min(100, score_growth + score_margin + score_cash + score_balance + score_risk)

                    # Kauflimits Vorberechnen
                    limit_15 = base_case * 0.85 if vals else 0.0

                    # Ergebnisse anzeigen
                    st.markdown("---")
                    st.header(f"Ergebnis für {info.get('shortName', ticker_input)}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Aktueller Kurs", f"{current_price:.2f} {currency_symbol}")
                    
                    if vals and kgv_val and kgv_val > 0:
                        safety_discount_pct = ((kgv_val - base_case) / kgv_val) * 100
                        col2.metric(
                            "Qualitäts-Fair-Value", 
                            f"{base_case:.2f} {currency_symbol}",
                            help=f"Inkl. ca. {safety_discount_pct:.1f}% Sicherheitsabschlag gegenüber dem reinen KGV-Wert ({kgv_val:.2f} {currency_symbol}) durch Einbezug von DCF & FCF."
                        )
                    else:
                        col2.metric("Qualitäts-Fair-Value", f"{base_case:.2f} {currency_symbol}" if vals else "N/A")
                        
                    col3.metric("Sicherheitspuffer", f"{margin_of_safety:.1f} %" if vals else "0.0 %")
                    col4.metric("Quality Score", f"{quality_score} / 100 Pkt.")

                    # Urteils-Matrix
                    st.subheader("📢 Gesamturteil")
                    if not vals:
                        st.info("Urteil: **NEUTRAL / UNRENTABEL** (Keine ausreichenden Gewinne/FCF vorhanden)")
                    elif margin_of_safety > 30:
                        st.success(f"🟢 **STARKER KAUF** | Hohe Sicherheitsmarge ({margin_of_safety:.1f}%) & Quality Score {quality_score}/100")
                    elif margin_of_safety >= 20:
                        st.success(f"🟢 **KAUFEN** | Guter Sicherheitspuffer ({margin_of_safety:.1f}%) & Quality Score {quality_score}/100")
                    elif margin_of_safety >= 10:
                        st.warning(f"🟡 **BEOBACHTEN** | Moderater Sicherheitspuffer ({margin_of_safety:.1f}%)")
                    elif margin_of_safety >= 0:
                        st.warning(f"🟠 **ABWARTEN** | Fair bewertet (+{margin_of_safety:.1f}% Puffer). Erst bei Abgaben einsteigen.")
                    else:
                        st.error(f"🔴 **VERKAUFEN / ÜBERBEWERTET** | Kurs liegt {abs(margin_of_safety):.1f}% über dem Fair Value.")

                    # Dynamischer "Warum dieses Urteil?"-Erklärungsblock
                    if vals:
                        downside_bear_val = ((bear_case - current_price) / current_price) * 100
                        pe_str = f"{pe_ratio:.1f}x" if pe_ratio else "N/A"
                        
                        with st.expander("💡 Warum dieses Urteil? (Schnell-Analyse)", expanded=True):
                            st.markdown(f"""
                            * **Qualität:** {'🟢' if quality_score >= 80 else ('🟡' if quality_score >= 70 else '🔴')} Quality Score **{quality_score}/100**
                            * **Bewertung:** {'🟢' if margin_of_safety >= 20 else ('🟠' if margin_of_safety >= 0 else '🔴')} Fair-Value-Puffer **+{margin_of_safety:.1f}%**
                            * **Bear-Risiko:** {'🔴' if downside_bear_val < -20 else '🟡'} **{downside_bear_val:.1f}%**
                            * **KGV-Niveau:** {'🔴' if pe_ratio and pe_ratio > 30 else '🟢'} **{pe_str}** {'(Anspruchsvoll)' if pe_ratio and pe_ratio > 30 else ''}
                            * **Net Cash:** {'🟢' if net_cash_per_share > 0 else '⚪'} **+{net_cash_per_share:.2f} {currency_symbol} / Aktie**
                            * **Kauflimits:** {'🟢 Voll aktiv' if quality_score >= 80 else ('🟡 Aktiv (Reduzierte Dosis)' if quality_score >= 70 else '🔴 Ausgesetzt')}
                            
                            **Fazit:**  
                            {"Hochwertiges Unternehmen, aber aktuell kein ausreichender Sicherheitsabstand." if margin_of_safety < 10 and quality_score >= 70 else "Gute Einstiegsgelegenheit mit adäquatem Sicherheitspuffer."}
                            """)

                    if net_cash_per_share > 0:
                        st.caption(f"💡 Enthält einen Net-Cash-Bonus von +{net_cash_per_share:.2f} {currency_symbol} je Aktie.")

                    # Chance / Risiko Profile (RRR Base vs Bull) mit Tooltips
                    if vals and current_price > 0:
                        st.subheader("⚖️ Chance / Risiko-Profil")
                        upside_base = ((base_case - current_price) / current_price) * 100
                        downside_bear = ((bear_case - current_price) / current_price) * 100
                        upside_bull = ((best_case - current_price) / current_price) * 100
                        
                        abs_bear = abs(downside_bear) if downside_bear != 0 else 1.0
                        rrr_base = upside_base / abs_bear if upside_base > 0 else 0.0
                        rrr_bull = upside_bull / abs_bear if upside_bull > 0 else 0.0

                        cr1, cr2, cr3, cr4, cr5 = st.columns(5)
                        cr1.metric("Bear Downside", f"{downside_bear:+.1f} %", delta_color="inverse")
                        cr2.metric("Fair Value Upside", f"{upside_base:+.1f} %")
                        cr3.metric("Bull Upside", f"{upside_bull:+.1f} %")
                        
                        cr4.metric(
                            "RRR (Base Case)", 
                            f"{rrr_base:.2f}x", 
                            help="Berechnung: Fair Value Upside / Bear Downside. Zeigt das Chance/Risiko-Verhältnis im realistischen Szenario. Ein Wert unter 1.0x bedeutet, dass das Rückschlagsrisiko den Fair-Value-Puffer übersteigt."
                        )
                        cr5.metric(
                            "RRR (Bull Case)", 
                            f"{rrr_bull:.2f}x", 
                            help="Berechnung: Bull Case Upside / Bear Downside. Zeigt das maximale Potenzial, wenn sowohl EPS-Wachstum als auch Multiple-Expansion eintreffen."
                        )

                    # Kauflimit-Rechner
                    if vals:
                        st.subheader("🎯 Kauflimit-Rechner (Staffeln aus Fair Value)")
                        limit_10 = base_case * 0.90
                        limit_20 = base_case * 0.80
                        limit_25 = base_case * 0.75
                        limit_30 = base_case * 0.70

                        limits_df = pd.DataFrame({
                            "Sicherheitsmarge": ["10 % (Beobachten)", "15 % (1. Staffel)", "20 % (2. Staffel)", "25 % (Starke Kaufzone)", "30 % (Sehr starker Kauf)"],
                            f"Zielkurs ({currency_symbol})": [f"{limit_10:.2f}", f"{limit_15:.2f}", f"{limit_20:.2f}", f"{limit_25:.2f}", f"{limit_30:.2f}"],
                            "Abstand vom aktuellen Kurs": [
                                f"{((limit_10 - current_price) / current_price) * 100:+.1f} %",
                                f"{((limit_15 - current_price) / current_price) * 100:+.1f} %",
                                f"{((limit_20 - current_price) / current_price) * 100:+.1f} %",
                                f"{((limit_25 - current_price) / current_price) * 100:+.1f} %",
                                f"{((limit_30 - current_price) / current_price) * 100:+.1f} %"
                            ]
                        })
                        st.table(limits_df)
                        
                        if quality_score >= 80:
                            st.success("🟢 **Quality Rule:** Kauflimits sind VOLL AKTIV (Starkes Qualitätsunternehmen).")
                        elif quality_score >= 70:
                            st.warning("🟡 **Quality Rule:** Kauflimits sind AKTIV, jedoch wird eine REDUZIERTE POSITIONSGRÖSSE empfohlen.")
                        else:
                            st.error("🔴 **Quality Rule:** Kauflimits AUSGESETZT! (Quality Score < 70). Erst fundamentale Erholung abwarten.")

                    # Szenarien Details & Treiber (Mathematisch transparent getrennt)
                    st.subheader("📌 Fundamentale Szenarien & Treiber")
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Bear-Case (Konservativ)", f"{bear_case:.2f} {currency_symbol}")
                    sc2.metric("Qualitäts-Base-Case", f"{base_case:.2f} {currency_symbol}")
                    sc3.metric("Best-Case (Optimistisch)", f"{best_case:.2f} {currency_symbol}")

                    if eval_eps:
                        kgv_base_pure = (eval_eps * target_pe_base) + net_cash_per_share
                        
                        drivers_df = pd.DataFrame({
                            "Szenario": ["Bear-Case", "Reines KGV-Modell", "Qualitäts-Base-Case (Ziel, inkl. Sicherheitsabschlag)", "Bull-Case"],
                            f"EPS-Annahme ({currency_symbol})": [f"{bear_eps:.2f}", f"{eval_eps:.2f}", f"{eval_eps:.2f}", f"{bull_eps:.2f}"],
                            "Ziel-KGV": [f"{target_pe_bear:.1f}x", f"{target_pe_base:.1f}x", f"{target_pe_base:.1f}x (Gewichtet)", f"{target_pe_bull:.1f}x"],
                            f"Net Cash / Aktie": [f"+{net_cash_per_share:.2f} {currency_symbol}"] * 4,
                            f"Errechneter Wert": [f"{bear_case:.2f} {currency_symbol}", f"{kgv_base_pure:.2f} {currency_symbol}", f"{base_case:.2f} {currency_symbol}", f"{best_case:.2f} {currency_symbol}"]
                        })
                        st.table(drivers_df)
                        st.caption("ℹ️ **Hinweis zur Abweichung:** Der *Qualitäts-Base-Case* kombiniert KGV-, DCF- und FCF-Modelle. Das *Reine KGV-Modell* zeigt den theoretischen Einzelwert ohne den konservativen Sicherheitsabschlag der anderen Modelle.")

                    # Modell-Details
                    st.subheader("📐 Modell-Details")
                    st.write(f"- **DCF/Gewinn-Modell:** {f'{dcf_val:.2f} {currency_symbol}' if dcf_val else 'N/A'}")
                    st.write(f"- **KGV-Modell (Ziel-KGV {target_pe_base:.1f}):** {f'{kgv_val:.2f} {currency_symbol}' if kgv_val else 'N/A'}")
                    st.write(f"- **FCF-Modell (Höher gewichtet bei Marge > 10%):** {f'{fcf_val:.2f} {currency_symbol}' if fcf_val else 'N/A'}")

                    # Risikocheck & Qualität
                    st.subheader("📊 Risikocheck & Qualität")
                    rc1, rc2, rc3 = st.columns(3)
                    
                    beta_str = f"{beta:.2f}" if beta else "N/A"
                    margin_str = f"{profit_margins * 100:.1f} %" if profit_margins else "N/A"
                    pe_str = f"{pe_ratio:.1f}" if pe_ratio else "N/A"
                    pb_str = f"{pb_ratio:.1f}" if pb_ratio else "N/A"
                    ev_str = f"{ev_ebitda:.1f}" if ev_ebitda else "N/A"
                    div_str = f"{dividend_yield * 100:.2f} %"
                    
                    rc1.write(f"**Beta (Schwankung):** {beta_str}")
                    rc1.write(f"**Nettomarge:** {margin_str}")
                    rc2.write(f"**KGV:** {pe_str} | **KBV:** {pb_str}")
                    rc2.write(f"**EV/EBITDA:** {ev_str}")
                    rc3.write(f"**Dividendenrendite:** {div_str}")

            except Exception as e:
                st.error(f"Fehler bei der Datenabfrage: {str(e)}")

# ==========================================
# TAB 2: WATCHLIST, KAUFLIMITS & EXPORT
# ==========================================
with tab2:
    st.subheader("📋 Mehrere Aktien im Vergleich & Export")
    st.write("Gib mehrere Ticker ein (kommagetrennt), um Fair Value, Quality Score und Kauflimits zu vergleichen und als CSV zu exportieren.")
    
    watchlist_input = st.text_input("Ticker-Liste:", value="COCO, AAPL, MSFT, TOST")
    calc_watchlist_btn = st.button("Watchlist berechnen", type="primary")

    if calc_watchlist_btn and watchlist_input:
        tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
        
        results = []
        with st.spinner("Berechne Watchlist-Daten..."):
            for t in tickers:
                try:
                    s = yf.Ticker(t)
                    i = s.info
                    price = i.get("currentPrice") or i.get("regularMarketPrice")
                    if not price or np.isnan(price):
                        continue
                    
                    curr = i.get("currency", "USD")
                    curr_sym = "€" if curr == "EUR" else "$"
                    eps = i.get("forwardEps") or i.get("trailingEps")
                    fcf = i.get("freeCashflow")
                    shares = i.get("sharesOutstanding")
                    growth = max(0, (i.get("earningsGrowth", 0) or 0) * 100)
                    margins = i.get("profitMargins", 0) or 0
                    
                    # Net Cash
                    total_cash = i.get("totalCash", 0) or 0
                    total_debt = i.get("totalDebt", 0) or 0
                    net_cash_ps = 0.0
                    if shares and shares > 0 and (total_cash - total_debt) > 0:
                        net_cash_ps = (total_cash - total_debt) / shares
                    
                    # Fair Value Modell
                    target_pe = min(30.0, max(15.0, 15.0 + (growth * 0.4)))
                    vals = []
                    if eps and eps > 0:
                        vals.append((eps * target_pe) + net_cash_ps)
                    if fcf and shares and fcf > 0 and shares > 0:
                        vals.append(((fcf / shares) * target_pe) + net_cash_ps)
                    
                    if vals:
                        fv = np.mean(vals)
                        mos = ((fv - price) / price) * 100
                        limit_15 = fv * 0.85
                        limit_25 = fv * 0.75
                    else:
                        fv, mos, limit_15, limit_25 = price, 0.0, price, price

                    # Quality Score
                    score = min(100, int(growth * 0.8) + int(margins * 120) + (20 if net_cash_ps > 0 else 5) + 20)

                    # Signal
                    if score < 70:
                        signal = "🔴 Ausgesetzt (Score <70)"
                    elif mos >= 20:
                        signal = "🟢 Kaufzone"
                    elif mos >= 0:
                        signal = "🟠 Abwarten"
                    else:
                        signal = "🔴 Überbewertet"

                    results.append({
                        "Ticker": t,
                        f"Aktueller Kurs ({curr_sym})": round(price, 2),
                        f"Fair Value ({curr_sym})": round(fv, 2),
                        "Puffer (%)": f"{mos:+.1f} %",
                        "Quality Score": f"{score}/100",
                        f"1. Limit (15%) ({curr_sym})": round(limit_15, 2),
                        f"2. Limit (25%) ({curr_sym})": round(limit_25, 2),
                        "Signal": signal
                    })
                except Exception:
                    pass
        
        if results:
            df_results = pd.DataFrame(results)
            st.table(df_results)
            
            # CSV Export
            csv_data = df_results.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Watchlist als CSV herunterladen",
                data=csv_data,
                file_name="aktien_watchlist_analysator.csv",
                mime="text/csv",
                type="secondary"
            )
        else:
            st.warning("Keine Daten für die angegebenen Ticker gefunden.")

# ==========================================
# TAB 3: DEPOT-ABGLEICH (CA. 15 AKTIEN)
# ==========================================
with tab3:
    st.subheader("💼 Portfolio-Abgleich mit deinen Kaufkursen & Kauflimits")
    st.write("Verwalte dein Depot (~15 Aktien) und vergleiche deine Kaufkurse direkt mit dem aktuellen Fair Value und den Nachkauflimits.")

    # Beispiel-Standard-Depot
    default_portfolio = pd.DataFrame([
        {"Ticker": "COCO", "Kaufkurs": 54.50, "Stueckzahl": 50},
        {"Ticker": "AAPL", "Kaufkurs": 175.00, "Stueckzahl": 20},
        {"Ticker": "MSFT", "Kaufkurs": 380.00, "Stueckzahl": 10},
        {"Ticker": "TOST", "Kaufkurs": 22.00, "Stueckzahl": 100}
    ])

    uploaded_file = st.file_content = st.file_uploader("📥 Eigenes Depot hochladen (CSV)", type=["csv"])
    if uploaded_file is not None:
        try:
            portfolio_df = pd.read_csv(uploaded_file)
            st.success("Depot erfolgreich geladen!")
        except Exception:
            st.error("Fehler beim Lesen der CSV. Bitte Format prüfen (Spalten: Ticker, Kaufkurs, Stueckzahl).")
            portfolio_df = default_portfolio
    else:
        portfolio_df = default_portfolio

    st.markdown("#### ✏️ Depot bearbeiten")
    edited_portfolio = st.data_editor(
        portfolio_df, 
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker (z. B. COCO)"),
            "Kaufkurs": st.column_config.NumberColumn("Kaufkurs", format="%.2f"),
            "Stueckzahl": st.column_config.NumberColumn("Stückzahl", format="%d")
        }
    )

    calc_portfolio_btn = st.button("Depot jetzt analysieren", type="primary")

    if calc_portfolio_btn and not edited_portfolio.empty:
        port_results = []
        with st.spinner("Lade Live-Daten für dein Depot..."):
            for idx, row in edited_portfolio.iterrows():
                t = str(row.get("Ticker", "")).strip().upper()
                buy_price = float(row.get("Kaufkurs", 0) or 0)
                qty = int(row.get("Stueckzahl", 0) or 0)
                
                if not t:
                    continue
                
                try:
                    s = yf.Ticker(t)
                    i = s.info
                    price = i.get("currentPrice") or i.get("regularMarketPrice")
                    if not price or np.isnan(price):
                        continue
                    
                    curr = i.get("currency", "USD")
                    curr_sym = "€" if curr == "EUR" else "$"
                    eps = i.get("forwardEps") or i.get("trailingEps")
                    fcf = i.get("freeCashflow")
                    shares = i.get("sharesOutstanding")
                    growth = max(0, (i.get("earningsGrowth", 0) or 0) * 100)
                    margins = i.get("profitMargins", 0) or 0
                    
                    # Net Cash
                    total_cash = i.get("totalCash", 0) or 0
                    total_debt = i.get("totalDebt", 0) or 0
                    net_cash_ps = 0.0
                    if shares and shares > 0 and (total_cash - total_debt) > 0:
                        net_cash_ps = (total_cash - total_debt) / shares
                    
                    # Fair Value Modell
                    target_pe = min(30.0, max(15.0, 15.0 + (growth * 0.4)))
                    vals = []
                    if eps and eps > 0:
                        vals.append((eps * target_pe) + net_cash_ps)
                    if fcf and shares and fcf > 0 and shares > 0:
                        vals.append(((fcf / shares) * target_pe) + net_cash_ps)
                    
                    if vals:
                        fv = np.mean(vals)
                        limit_15 = fv * 0.85
                        limit_25 = fv * 0.75
                    else:
                        fv, limit_15, limit_25 = price, price, price

                    # Quality Score
                    score = min(100, int(growth * 0.8) + int(margins * 120) + (20 if net_cash_ps > 0 else 5) + 20)

                    # Performance
                    perf_pct = ((price - buy_price) / buy_price) * 100 if buy_price > 0 else 0.0
                    position_value = price * qty
                    
                    # Handlungssignal
                    if score < 70:
                        action = "🔴 Schwache Qualität (Score <70) -> Halten / Aussteigen prüfen"
                    elif price <= limit_25:
                        action = "🟢 **STARKES NACHKAUFLIMIT REACHED (25%)**"
                    elif price <= limit_15:
                        action = "🟢 **1. NACHKAUFLIMIT REACHED (15%)**"
                    elif perf_pct > 50 and price > (fv * 1.2):
                        action = "🟠 Stark gelaufen (>20% über Fair Value) -> Gewinne sichern?"
                    else:
                        action = "⚪ Halten (Kein Nachkaufsignal)"

                    port_results.append({
                        "Ticker": t,
                        "Stück": qty,
                        f"Kaufkurs ({curr_sym})": round(buy_price, 2),
                        f"Akt. Kurs ({curr_sym})": round(price, 2),
                        "Performance (%)": f"{perf_pct:+.1f} %",
                        f"Wert ({curr_sym})": round(position_value, 2),
                        f"Fair Value ({curr_sym})": round(fv, 2),
                        "Quality": f"{score}/100",
                        f"Nachkauf-Limit (15%) ({curr_sym})": round(limit_15, 2),
                        "Handlungssignal": action
                    })
                except Exception:
                    pass

        if port_results:
            df_port_res = pd.DataFrame(port_results)
            st.markdown("### 📊 Auswertung deines Portfolios")
            st.table(df_port_res)
            
            # Export des Portfolios
            csv_port = edited_portfolio.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Depot-Konfiguration als CSV speichern",
                data=csv_port,
                file_name="mein_depot_aktien.csv",
                mime="text/csv"
            )
        else:
            st.warning("Keine Live-Daten für dein Portfolio gefunden.")

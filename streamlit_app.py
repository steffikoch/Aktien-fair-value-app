import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page Config
st.set_page_config(page_title="Aktien Fair-Value App", layout="wide")

st.title("📊 Risiko & Fair-Value Analysator")

tab1, tab2 = st.tabs(["🔍 Einzelanalyse", "📋 Watchlist & Kauflimits"])

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

                    # 2. Moderatere KGV-Staffelung (Bear: 25 / Base: 30 / Bull: 35)
                    growth_rate = max(0, earnings_growth * 100)
                    target_pe_base = min(30.0, max(15.0, 15.0 + (growth_rate * 0.4)))
                    target_pe_bear = max(12.0, target_pe_base * 0.80)
                    target_pe_bull = min(38.0, target_pe_base * 1.20)
                    
                    # 3. Modelle Berechnen
                    eval_eps = forward_eps if (forward_eps and forward_eps > 0) else eps
                    
                    dcf_val, kgv_val, fcf_val = None, None, None
                    
                    if eval_eps and eval_eps > 0:
                        kgv_val = (eval_eps * target_pe_base) + net_cash_per_share
                        dcf_val = (eval_eps * (target_pe_base * 0.9)) + net_cash_per_share
                    
                    if fcf and shares and fcf > 0 and shares > 0:
                        fcf_per_share = fcf / shares
                        fcf_val = (fcf_per_share * target_pe_base) + net_cash_per_share
                    
                    # 4. Qualitätsgewichteter Fair Value
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
                        
                        bear_eps_val = (eval_eps * target_pe_bear) + net_cash_per_share if eval_eps else base_case * 0.8
                        bull_eps_val = (eval_eps * target_pe_bull) + net_cash_per_share if eval_eps else base_case * 1.2
                        
                        bear_case = min(bear_eps_val, base_case * 0.85)
                        best_case = max(bull_eps_val, base_case * 1.15)
                        
                        margin_of_safety = ((base_case - current_price) / current_price) * 100
                    else:
                        base_case, bear_case, best_case = current_price, current_price, current_price
                        margin_of_safety = 0.0

                    # Ergebnisse anzeigen
                    st.markdown("---")
                    st.header(f"Ergebnis für {info.get('shortName', ticker_input)}")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Aktueller Kurs", f"{current_price:.2f} {currency_symbol}")
                    col2.metric("Qualitätsbereinigter Fair Value", f"{base_case:.2f} {currency_symbol}" if vals else "N/A")
                    col3.metric("Sicherheitspuffer", f"{margin_of_safety:.1f} %" if vals else "0.0 %")
                    
                    # Exakte Ampel-Logik
                    if not vals:
                        st.info("Urteil: **NEUTRAL / UNRENTABEL** (Keine ausreichenden Gewinne/FCF vorhanden)")
                    elif margin_of_safety > 30:
                        st.success(f"Urteil: 🟢 **STARKER KAUF** (Sicherheitspuffer > 30%)")
                    elif margin_of_safety >= 20:
                        st.success(f"Urteil: 🟢 **KAUFEN** (Sicherheitspuffer 20–30%)")
                    elif margin_of_safety >= 10:
                        st.warning(f"Urteil: 🟡 **BEOBACHTEN** (Sicherheitspuffer 10–20%)")
                    elif margin_of_safety >= 0:
                        st.warning(f"Urteil: 🟠 **ABWARTEN** (Sicherheitspuffer 0–10%)")
                    else:
                        st.error(f"Urteil: 🔴 **VERKAUFEN** (Sicherheitspuffer < 0%)")

                    if net_cash_per_share > 0:
                        st.caption(f"💡 Enthält einen Net-Cash-Bonus von +{net_cash_per_share:.2f} {currency_symbol} je Aktie.")

                    # Kauflimit-Rechner
                    if vals:
                        st.subheader("🎯 Kauflimit-Rechner (Staffeln & Limits)")
                        limit_10 = base_case * 0.90
                        limit_15 = base_case * 0.85
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

                    # Szenarien
                    st.subheader("Szenarien")
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Bear-Case (Konservativ)", f"{bear_case:.2f} {currency_symbol}" if vals else "N/A")
                    sc2.metric("Base-Case (Realistisch)", f"{base_case:.2f} {currency_symbol}" if vals else "N/A")
                    sc3.metric("Best-Case (Optimistisch)", f"{best_case:.2f} {currency_symbol}" if vals else "N/A")

                    # Einzelne Modelle Detail
                    st.subheader("Modell-Details")
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

with tab2:
    st.write("Hier kannst du deine Kauflimits verwalten.")

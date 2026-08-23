import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page Config
st.set_page_config(page_title="Aktien Fair-Value App", layout="wide")

st.title("📊 Risiko & Fair-Value Analysator")

# Tabs / Menü
tab1, tab2 = st.tabs(["🔍 Einzelanalyse", "📋 Watchlist & Kauflimits"])

with tab1:
    st.subheader("Aktie auswählen")
    
    # Live-Suche / Ticker-Eingabe
    user_query = st.text_input("Gib Ticker oder Firmennamen ein:", placeholder="z. B. Luf, Toast, Apple...")
    
    ticker_input = user_query.strip()
    
    # Erst ab 3 Buchstaben wird die Live-Suche von Yahoo aktiv
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
                
                # Prüfen ob Kursdaten vorhanden sind
                current_price = info.get("currentPrice") or info.get("regularMarketPrice")
                
                if current_price is None or np.isnan(current_price):
                    st.error("Keine gültigen Kursdaten für diesen Ticker gefunden.")
                else:
                    eps = info.get("trailingEps")
                    fcf = info.get("freeCashflow")
                    shares = info.get("sharesOutstanding")
                    pe_ratio = info.get("trailingPE")
                    pb_ratio = info.get("priceToBook")
                    beta = info.get("beta")
                    profit_margins = info.get("profitMargins")
                    ev_ebitda = info.get("enterpriseToEbitda")
                    dividend_yield = info.get("dividendYield", 0) or 0
                    
                    # 1. DCF Modell
                    dcf_val = None
                    if eps and eps > 0:
                        dcf_val = eps * 18.9  # Vereinfachtes KGV/DCF Multiplikator-Modell
                    
                    # 2. KGV Modell
                    kgv_val = None
                    if eps and eps > 0:
                        kgv_val = eps * 20.0
                        
                    # 3. FCF Modell
                    fcf_val = None
                    if fcf and shares and fcf > 0 and shares > 0:
                        fcf_per_share = fcf / shares
                        fcf_val = fcf_per_share * 15.0
                    
                    # Fair Values berechnen (Base, Bear, Best)
                    valid_models = [v for v in [dcf_val, kgv_val, fcf_val] if v is not None]
                    
                    if valid_models:
                        base_case = sum(valid_models) / len(valid_models)
                        bear_case = base_case * 0.95
                        best_case = base_case * 1.05
                        margin_of_safety = ((base_case - current_price) / current_price) * 100
                    else:
                        # Fallback für unrentable / neue Unternehmen ohne positive Erträge
                        base_case = current_price
                        bear_case = current_price
                        best_case = current_price
                        margin_of_safety = 0.0

                    # Ergebnisse anzeigen
                    st.markdown("---")
                    st.header(f"Ergebnis für {info.get('shortName', ticker_input)}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Aktueller Kurs", f"{current_price:.2f} $")
                    col2.metric("Base-Case Fair Value", f"{base_case:.2f} $" if valid_models else "N/A")
                    col3.metric("Sicherheitspuffer", f"{margin_of_safety:.1f} %" if valid_models else "0.0 %")
                    
                    # Urteil
                    if not valid_models:
                        urteil = "NEUTRAL / UNRENTABEL"
                        st.info(f"Urteil: **{urteil}** (Keine ausreichenden Gewinne/FCF für Fair-Value-Berechnung)")
                    elif margin_of_safety >= 15:
                        urteil = "KAUFEN"
                        st.success(f"Urteil: 🟢 **{urteil}**")
                    elif margin_of_safety >= -10:
                        urteil = "HALTEN"
                        st.warning(f"Urteil: 🟠 **{urteil}**")
                    else:
                        urteil = "VERKAUFEN"
                        st.error(f"Urteil: 🔴 **{urteil}**")

                    # Szenarien
                    st.subheader("Szenarien (Base Case)")
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Bear-Case (Konservativ)", f"{bear_case:.2f} $" if valid_models else "N/A")
                    sc2.metric("Base-Case (Realistisch)", f"{base_case:.2f} $" if valid_models else "N/A")
                    sc3.metric("Best-Case (Optimistisch)", f"{best_case:.2f} $" if valid_models else "N/A")

                    # Einzelne Modelle Detail
                    st.subheader("Modell-Details")
                    st.write(f"- **DCF-Modell:** {f'{dcf_val:.2f} $' if dcf_val else 'N/A'}")
                    st.write(f"- **KGV-Modell:** {f'{kgv_val:.2f} $' if kgv_val else 'N/A'}")
                    st.write(f"- **FCF-Modell:** {f'{fcf_val:.2f} $' if fcf_val else 'N/A'}")

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

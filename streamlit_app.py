import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Fair Value Aktienanalyse", page_icon="📈", layout="wide")

st.title("📈 Fair Value Aktienanalyse")
st.caption("Prototyp – automatische Aktienanalyse mit anpassbaren Bewertungsannahmen")

ticker = st.text_input("Aktie / Ticker", "ALV.DE").upper().strip()

c1, c2, c3 = st.columns(3)
with c1:
    discount = st.number_input("Diskontsatz (%)", min_value=0.0, max_value=1.0, value=0.10, step=0.01, format="%.2f")

with c2:
    terminal_growth = st.number_input("Langfristiges Wachstum", 0.00, 0.04, 0.02, 0.005, format="%.1f%%")
with c3:
    target_pe = st.number_input("Ziel-KGV", 8.0, 20.0, 13.0, 0.5)

if st.button("🔄 Aktie analysieren", type="primary"):
    try:
        t = yf.Ticker(ticker)
        info = t.info

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        eps = info.get("trailingEps")
        shares = info.get("sharesOutstanding")
        name = info.get("longName", ticker)

        if price is None or eps is None:
            st.error("Für diesen Ticker konnten nicht genügend Daten abgerufen werden.")
            st.stop()

        # Einfache 5-Jahres-EPS-Prognose als Prototyp.
        growth_rates = [0.06, 0.05, 0.05, 0.04, 0.03]
        eps_forecast = []
        x = float(eps)
        for g in growth_rates:
            x *= 1 + g
            eps_forecast.append(x)

        # EPS-basierter Terminalwert + abgezinste EPS
        pv_eps = sum(e / (1 + discount)**(i+1) for i, e in enumerate(eps_forecast))
        terminal_eps = eps_forecast[-1] * (1 + terminal_growth)
        terminal_value = terminal_eps / (discount - terminal_growth)
        pv_terminal = terminal_value / (1 + discount)**5
        fair_eps_model = pv_eps + pv_terminal

        # KGV-Modell
        fair_pe = eps_forecast[-1] * target_pe

        # Gewichtung
        fair_value = 0.6 * fair_eps_model + 0.4 * fair_pe
        upside = fair_value / price - 1
        margin_price = fair_value * 0.85

        if price < margin_price:
            verdict = "🟢 KAUFEN"
        elif price < fair_value:
            verdict = "🟡 BEOBACHTEN"
        else:
            verdict = "🔴 ZU TEUER"

        st.subheader(name)

        a,b,c,d = st.columns(4)
        a.metric("Aktueller Kurs", f"{price:,.2f} €")
        b.metric("Fair Value", f"{fair_value:,.2f} €")
        c.metric("Potenzial", f"{upside:+.1%}")
        d.metric("Urteil", verdict)

        st.divider()

        st.subheader("Bewertung")
        left, right = st.columns(2)
        with left:
            st.write(f"**EPS aktuell:** {eps:.2f} €")
            st.write(f"**Fair Value EPS-Modell:** {fair_eps_model:.2f} €")
            st.write(f"**Fair Value KGV-Modell:** {fair_pe:.2f} €")
        with right:
            st.write(f"**15-%-Sicherheitsmarge:** {margin_price:.2f} €")
            st.write(f"**Diskontsatz:** {discount:.1%}")
            st.write(f"**Langfristiges Wachstum:** {terminal_growth:.1%}")

        st.subheader("EPS-Prognose")
        st.line_chart({"EPS": eps_forecast}, x_label="Prognosejahr", y_label="€")

        st.info("Hinweis: Dies ist ein Prototyp und keine Anlageberatung. Finanzdaten können unvollständig oder verzögert sein; die Bewertungsannahmen sollten vor einer Anlageentscheidung geprüft werden.")

    except Exception as e:
        st.error(f"Fehler beim Abrufen der Aktie: {e}")

st.divider()
st.caption("Version 1 – als nächstes können wir Versicherer wie Allianz mit einem speziellen Modell behandeln und danach beliebige Aktien automatisch analysieren.")

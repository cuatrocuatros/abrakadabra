import streamlit as st
import pandas as pd
import utils.data_fetcher as df_utils
import utils.charts as chart_utils
import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Professional Investment Dashboard", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; width: 250px; }
    [data-testid="stMetricValue"] { font-family: 'Inter', sans-serif; font-weight: 600; color: #00F0FF; }
    h1, h2, h3 { font-family: 'Outfit', sans-serif; color: #E6EDF3; }
    /* Botones blancos, diseño oscuro */
    div.stButton > button:first-child { background-color: #FFFFFF; color: #000000; border-radius: 4px; border: none; font-weight: bold; }
    div.stButton > button:hover { background-color: #E0E0E0; border: none; color: black; }
    /* Fix para evitar que los títulos de métricas se corten */
    div[data-testid="stMetric"] p { white-space: nowrap; overflow: visible; text-overflow: clip; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Professional Investment Dashboard")
st.caption(f"Last Market Refresh: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except:
    st.error("⚠️ FRED_API_KEY not found in secrets. Please configure it in .streamlit/secrets.toml")
    FRED_API_KEY = None
    
try:
    FMP_API_KEY = st.secrets["FMP_API_KEY"]
except:
    FMP_API_KEY = None
    
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    GOOGLE_API_KEY = None

import utils.yf_fundamentals as yf_utils

# Strict Portfolio Tickers (No "Discovery" assets here, they belong in the Scanner)
tickers = [
    "GOOG", "TSLA", "YOU", "IONQ", "JOBY", "CLSK", "SDGR",
    "ETH", "SOL", "LINK", "TAO", "ONDO", "XRP"
]

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header("Navegación")
    page = st.radio("Ir a:", ["Net Worth & Portfolio", "Market Control", "Company Deep-Dive"], index=0)
    st.divider()
    st.header("Settings")
    st.info("Auto-refresh enabled via Browser (F5)")
    st.divider()
    st.caption("v7.0 - Intelligence Hub Beta")

# ==========================================
# PAGE 1: MARKET CONTROL (The Original Dashboard)
# ==========================================
if page == "Market Control":
    # --- 1. Top Level KPIs ---
    kpi1, kpi2, kpi3 = st.columns(3)

    yf_tickers = []
    for t in tickers:
        if t == "TAO": yf_tickers.append("TAO22974-USD") 
        elif t == "RENDER": yf_tickers.append("RENDER-USD")
        elif t.upper() in ["TAO", "RENDER", "FET", "SOL", "ETH", "XRP", "LINK", "ONDO"]: 
            # Safety check for crypto symbols if not covered above
             if t not in ["TAO", "RENDER"]: # Avoid double add
                 yf_tickers.append(f"{t}-USD")
        else: yf_tickers.append(t)

    # Main Data Fetch
    with st.spinner("Analyzing Portfolio & Trajectories..."):
        port_df, history_df, sp500_change, trajectory_df = df_utils.get_portfolio_data(yf_tickers)

    # Calculate Alpha
    beating_sp500_count = 0
    if not port_df.empty:
        beating_sp500_count = len(port_df[port_df['Change_Pct'] > sp500_change])
        alpha_pct = (beating_sp500_count / len(port_df)) * 100

    with kpi3:
        st.metric("Daily Alpha (24h Window)", f"{alpha_pct:.0f}% Beating", delta=f"SP500: {sp500_change:.2f}%")
    with kpi1:
        hr = df_utils.get_hashrate()
        st.metric("BTC Network Health", f"{hr:,.0f} TH/s", delta="Hashrate")
    with kpi2:
        fg_val, fg_class = df_utils.get_fear_and_greed()
        st.metric("Fear & Greed Index", f"{fg_val}", delta=fg_class)

    st.divider()

    # --- 2. Global Macro Context ---
    st.subheader("1. Global Macro Context")

    # 1. Weekly Liquidity (The big one) - NEEDS FRED
    if FRED_API_KEY:
        macro_df = df_utils.get_macro_liquidity(FRED_API_KEY)
        if not macro_df.empty: 
            st.plotly_chart(chart_utils.create_liquidity_chart(macro_df), use_container_width=True)
            st.caption("ℹ️ **Net Liquidity vs Bitcoin**: Muestra la liquidez global del sistema. Liquidez ↑ = Viento a favor para el precio de BTC.")
    else:
        st.warning("⚠️ FRED API Key missing. Liquidity Data unavailable.")
    
    # 2. Daily High Frequency
    d1, d2, d3 = st.columns(3)
    
    with d1:
        if FRED_API_KEY:
            yc_df = df_utils.get_yield_curve(FRED_API_KEY)
            if not yc_df.empty:
                st.plotly_chart(chart_utils.create_generic_line_chart(yc_df, "Yield Curve (10Y-2Y)", "Yield_Curve", color="#FF00FF", period="daily"), use_container_width=True)
                st.caption("ℹ️ **Yield Curve**: Predictor de recesión. Si baja de 0 (invertida), avisa de problemas económicos serios.")
    
    with d2:
        if FRED_API_KEY:
            dxy_df = df_utils.get_dxy(FRED_API_KEY)
            if not dxy_df.empty:
                st.plotly_chart(chart_utils.create_generic_line_chart(dxy_df, "DXY Dollar Index", "DXY", color="#00FF00", period="daily"), use_container_width=True)
                st.caption("ℹ️ **DXY**: Fuerza del dólar. Dólar ↑ = Activos ↓. Es el principal enemigo del Bitcoin.")
                
    with d3:
        # INDEPENDENT of FRED (Uses Yahoo Finance)
        bg_df = df_utils.get_btc_gold_ratio()
        if not bg_df.empty: 
            st.plotly_chart(chart_utils.create_btc_gold_chart(bg_df), use_container_width=True)
            st.caption("ℹ️ **BTC/Gold Ratio**: Mide la fuerza de BTC frente al Oro. Si sube, el mercado prefiere riesgo (Risk-on).")
            
    if FRED_API_KEY:
        # 3. Weekly Stress & TGA
        d4, d5 = st.columns(2)
        with d4:
            stress_df = df_utils.get_stress_index(FRED_API_KEY)
            if not stress_df.empty:
                st.plotly_chart(chart_utils.create_generic_line_chart(stress_df, "St. Louis Fed Stress Index", "Stress_Index", color="#FF3333", period="weekly"), use_container_width=True)
                st.caption("ℹ️ **Stress Index**: Termómetro del miedo. >0 indica estrés financiero o crisis inminente.")
        with d5:
            tga_df = df_utils.get_tga(FRED_API_KEY)
            if not tga_df.empty:
                 st.plotly_chart(chart_utils.create_generic_line_chart(tga_df, "Treasury General Account (TGA)", "TGA", color="#FFA500", period="weekly_tga"), use_container_width=True)
                 st.caption("ℹ️ **TGA**: Cuenta del gobierno. TGA ↓ = El gobierno gasta e inyecta liquidez al sistema.")

        # 4. Daily Liquidity Indicators (RRP & Breakeven)
        d6, d7 = st.columns(2)
        with d6:
            rrp_df = df_utils.get_reverse_repo(FRED_API_KEY)
            if not rrp_df.empty:
                st.plotly_chart(chart_utils.create_generic_line_chart(rrp_df, "Reverse Repo (RRP)", "RRP", color="#00FFFF", period="daily_rrp"), use_container_width=True)
                st.caption("ℹ️ **Reverse Repo (RRP)**: Dinero aparcado en el banco central. RRP ↓ = Dinero fluyendo al mercado.")
        with d7:
            break_df = df_utils.get_breakeven_inflation(FRED_API_KEY)
            if not break_df.empty:
                st.plotly_chart(chart_utils.create_generic_line_chart(break_df, "10Y Breakeven Inflation", "Breakeven_10Y", color="#FF00FF", period="daily_break"), use_container_width=True)
                st.caption("ℹ️ **10Y Breakeven**: Expectativa de inflación. Si sube, el mercado busca refugio en Oro y BTC.")

        # 5. Monthly Econ
        m1, m2, m3 = st.columns(3)
        ind_df = df_utils.get_industrial_data(FRED_API_KEY)
        m2_df_data = df_utils.get_m2_supply(FRED_API_KEY)
        
        with m1:
            if not ind_df.empty: 
                st.plotly_chart(chart_utils.create_philly_chart(ind_df), use_container_width=True)
                st.caption("ℹ️ **Philly Fed**: Salud industrial. >0 expansión, <0 contracción. Anticipa giros en el ciclo económico.")
        with m2:
             if not ind_df.empty: 
                 st.plotly_chart(chart_utils.create_ind_prod_chart(ind_df), use_container_width=True)
                 st.caption("ℹ️ **Ind. Production**: El motor real de la economía. Crecimiento sostenido = Economía fuerte.")
        with m3:
             if not m2_df_data.empty: 
                 st.plotly_chart(chart_utils.create_m2_chart(m2_df_data), use_container_width=True)
                 st.caption("ℹ️ **M2 Money Supply**: Cantidad de dólares en circulación. Es el combustible de los activos a largo plazo.")

    st.divider()

    # --- 3. Portfolio Analysis ---
    st.subheader("2. Portfolio Analysis & Signals")

    if not port_df.empty:
        port_df['Extra Info'] = ""
        port_df['Theme'] = "Other"
        
        theme_map = {
            "IREN": "Miners", "CLSK": "Miners", "CIFR": "Miners", "CORZ": "Miners",
            "JOBY": "eVTOL", "ACHR": "eVTOL", "EVEX": "eVTOL", "EVTL": "eVTOL",
            "IONQ": "Quantum", "QBTS": "Quantum",
            "TSLA": "IA/BigTech", "GOOG": "IA/BigTech",
            "RXRX": "Biotech", "SDGR": "Biotech",
            "TAO": "IA Crypto", "TAO1-USD": "IA Crypto", "TAO22974-USD": "IA Crypto", "RENDER": "IA Crypto", "RENDER-USD": "IA Crypto", "FET": "IA Crypto", "FET-USD": "IA Crypto",
            "SOL": "Crypto L1", "SOL-USD": "Crypto L1", "ETH": "Crypto L1", "ETH-USD": "Crypto L1", "XRP": "Crypto L1", "XRP-USD": "Crypto L1",
            "LINK": "Crypto DeFi", "LINK-USD": "Crypto DeFi",
            "ONDO": "Crypto DeFi", "ONDO-USD": "Crypto DeFi",
            "YOU": "Cybersecurity"
        }

        miners = ["IREN", "CLSK", "CIFR", "CORZ"]
        evtols = ["JOBY", "ACHR", "EVEX", "EVTL"]
        rsi_vol_group = [
            "IONQ", "QBTS", "TSLA", "GOOG", "RXRX", "SDGR", "YOU",
            "TAO22974-USD", "RENDER-USD", "FET-USD", "SOL-USD", "ETH-USD", "XRP-USD", "LINK-USD"
        ]
        
        for index, row in port_df.iterrows():
            ticker = row['Ticker']
            clean_ticker = ticker.replace("-USD", "").replace("TAO1", "TAO").replace("TAO22974", "TAO")
            port_df.at[index, 'Theme'] = theme_map.get(ticker, theme_map.get(clean_ticker, "Other"))
            
            rsi = row.get('RSI', 50)
            vol_ratio = row.get('Vol_Ratio', 1.0)
            
            signal = ""
            if rsi < 35 and vol_ratio > 1.2:
                signal = " 🔥 ACCUMULATION"
            elif rsi > 70:
                signal = " ⚠️ OVERBOUGHT"
            
            info_text = ""
            try:
                if clean_ticker in miners:
                     global_hashrate = hr 
                     hr_txt = f"{global_hashrate:,.0f}T" if global_hashrate else "?"
                     info_text = f"Hash: {hr_txt} | RSI: {rsi:.1f}"
                elif clean_ticker in evtols:
                    dist = row.get('Dist_52w', 0)
                    info_text = f"Dist 52wH: {dist:.1f}%"
                elif ticker in rsi_vol_group or clean_ticker in rsi_vol_group:
                    info_text = f"RSI: {rsi:.1f} | Vol: {vol_ratio:.1f}x"
                elif "ONDO" in ticker or clean_ticker == "ONDO":
                    slug_map = {"ONDO": "ondo-finance"}
                    slug = slug_map.get(clean_ticker, None)
                    if slug:
                        tvl = df_utils.get_defi_tvl(slug)
                        if isinstance(tvl, list): tvl = tvl[-1] if len(tvl)>0 else 0
                        val_str = f"${float(tvl):,.0f}" if tvl else "N/A"
                        info_text = f"TVL: {val_str}"
                    else:
                        info_text = f"RSI: {rsi:.1f}"
                else:
                    info_text = f"RSI: {rsi:.1f}"
                
                port_df.at[index, 'Extra Info'] = info_text + signal
            except Exception as e:
                port_df.at[index, 'Extra Info'] = "Data Error"

        def highlight_rsi(row):
            rsi_val = row.get('RSI', 50)
            if rsi_val > 65: return ['color: #FF4B4B; font-weight: bold;'] * len(row)
            elif rsi_val < 35: return ['color: #00CC96; font-weight: bold;'] * len(row)
            return [''] * len(row)

        styled_df = port_df[['Ticker', 'Price', 'Change_Pct', 'Extra Info', 'RSI']].style.apply(highlight_rsi, axis=1)
        styled_df = styled_df.format({"Price": "${:,.2f}", "Change_Pct": "{:,.2f}%", "RSI": "{:.1f}"})
        st.dataframe(styled_df, column_order=["Ticker", "Price", "Change_Pct", "Extra Info"], use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("3. Deep Dive Analysis")
        
        tab1, tab2 = st.tabs(["🔥 Discovery Map (Trajectories)", "🧩 Correlation Matrix"])
        
        with tab1:
            if not trajectory_df.empty:
                trajectory_df['Theme'] = trajectory_df['Ticker'].apply(lambda x: port_df.loc[port_df['Ticker']==x, 'Theme'].iloc[0] if not port_df.loc[port_df['Ticker']==x].empty else "Other")
                trajectory_df = trajectory_df.sort_values(by=['Ticker', 'Days_Ago'], ascending=[True, False]) # T-3 -> T-0
                
                fig = go.Figure()
                
                # Trails
                line_fig = px.line(
                     trajectory_df, x="RSI", y="Rel_Strength_14d", color="Theme", line_group="Ticker",
                     hover_name="Ticker", color_discrete_sequence=px.colors.qualitative.Bold
                )
                line_fig.update_traces(line=dict(width=1), opacity=0.3)
                for trace in line_fig.data: fig.add_trace(trace)

                # Heads
                t0_df = trajectory_df[trajectory_df['Days_Ago'] == 0]
                scatter_fig = px.scatter(
                    t0_df, x="RSI", y="Rel_Strength_14d", size="Vol_Ratio", color="Theme",
                    hover_name="Ticker", color_discrete_sequence=px.colors.qualitative.Bold
                )
                for trace in scatter_fig.data:
                    trace.marker.sizeref = 2. * max(t0_df['Vol_Ratio']) / (20.**2) 
                    trace.marker.sizemin = 4
                    fig.add_trace(trace)
                    
                fig.update_layout(
                    title="Asset Trajectories (Trailing 4 Days)",
                    xaxis_title="RSI (14d)", yaxis_title="Rel. Strength vs SP500 (14d)",
                    template="plotly_dark", height=600, showlegend=True
                )
                fig.add_vline(x=30, line_dash="dash", line_color="green", opacity=0.5)
                fig.add_vline(x=70, line_dash="dash", line_color="red", opacity=0.5)
                fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("ℹ️ Nota: La posición de las burbujas refleja el rendimiento relativo acumulado de los últimos 14 días.")
                
            else:
                st.warning("Not enough data for trajectories.")
            
        with tab2:
            if not history_df.empty:
                corr_matrix = history_df.tail(30).corr()
                fig_corr = px.imshow(
                    corr_matrix, text_auto=True, aspect="auto", color_continuous_scale="RdBu_r",
                    title="30-Day Correlation Matrix"
                )
                fig_corr.update_layout(template="plotly_dark", height=800)
                st.plotly_chart(fig_corr, use_container_width=True)

    else:
        st.error("Failed to load portfolio data.")

    # --- 4. ALPHA SCANNER (NEW MODULE) ---
    st.divider()
    st.header("🚀 Radar de Prospección: Nuevas S-Curves")

    @st.cache_data(ttl=3600*4) # Cache for 4 hours
    def run_alpha_scanner(existing_tickers):
        return df_utils.scan_potential_alphas(existing_tickers)

    # Execute Scanner
    with st.spinner("Escaneando Oportunidades de Reversión (RSI < 40)..."):
        alpha_df = run_alpha_scanner(yf_tickers)

    if not alpha_df.empty:
        st.success(f"Detectadas {len(alpha_df)} Oportunidades 'Reversal' (RSI < 40 + Momentum Norte)")
        
        # Scatter for Alphas
        fig_alpha = px.scatter(
            alpha_df,
            x="RSI",
            y="Rel_Strength_14d",
            size="Vol_Avg",
            hover_name="Ticker",
            color="Rel_Strength_14d", # Color by strength
            color_continuous_scale="Viridis",
            title="Detecciones Reversal (S-Curve Bottom Fishing)",
            labels={"Rel_Strength_14d": "Fuerza Relativa vs SP500", "Vol_Avg": "Volumen Promedio"},
            template="plotly_dark",
            height=500
        )
        fig_alpha.add_vline(x=50, line_dash="dash", line_color="white", opacity=0.3)
        
        st.plotly_chart(fig_alpha, use_container_width=True)
        
        # Optional Dataframe
        st.dataframe(alpha_df.sort_values(by="Rel_Strength_14d", ascending=False), use_container_width=True)
    else:
        st.info("El Radar no ha detectado Reversiones hoy.")

# ==========================================
# PAGE 3: COMPANY DEEP-DIVE (Fundamental)
# ==========================================
elif page == "Company Deep-Dive":
    st.header("🔬 Company Deep-Dive")
    st.caption("Módulo de Análisis Fundamental conectado a Yahoo Finance (Fallback).")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.write("### Quick Access (Bookmarks)")
        # Dynamically generate buttons from requested unified portfolio equities
        equities = ['GOOG', 'TSLA', 'YOU', 'IONQ', 'JOBY', 'CLSK', 'SDGR']
        
        # Display up to 15 equities in a 5-column layout
        display_equities = equities[:15]
        num_cols = 5
        for i in range(0, len(display_equities), num_cols):
            cols = st.columns(num_cols)
            for j, eq in enumerate(display_equities[i:i+num_cols]):
                with cols[j]:
                    if st.button(eq, key=f"btn_{eq}", use_container_width=True):
                        st.session_state.fmp_ticker = eq

        default_ticker = st.session_state.get("fmp_ticker", "TSLA")
        ticker_input = st.text_input("Ticker Symbol (Manual Search)", value=default_ticker).upper()
        
        st.write("### Statement Period")
        # Statement Period toggle for fundamentals (Annual vs Quarterly YoY vs Quarterly QoQ)
        period_mode = st.radio("Select Period:", ["Annual", "Quarterly (YoY)", "Quarterly (QoQ)"], horizontal=True, label_visibility="collapsed")
                
        if ticker_input:
            with st.spinner(f"Accediendo a estados financieros (Yahoo Finance) de {ticker_input}..."):
                analysis = yf_utils.analyze_company(ticker_input, period=period_mode)
                
            if analysis is None or analysis['df'].empty:
                st.error("No se encontraron suficientes datos fundamentales para este Ticker.")
            else:
                df = analysis['df']
                latest = analysis['latest']
                
                # Filter df based on timeframe to affect charts visual logic
                df_filtered = df.copy()
                
                st.divider()
                st.subheader(f"Fundamentals Snapshot: {ticker_input} ({latest['date']})")
                
                ol_val = latest.get('Operating_Leverage')
                prev_ol_val = latest.get('Prev_Operating_Leverage')
                lr_val = latest.get('Liquidity_Ratio')
                prev_lr_val = latest.get('Prev_Liquidity_Ratio')
                eq_val = latest.get('Earnings_Quality')
                prev_eq_val = latest.get('Prev_Earnings_Quality')
                
                rev_val = latest.get('Revenue')
                prev_rev_val = latest.get('Prev_Revenue')
                ni_val = latest.get('Net_Income')
                prev_ni_val = latest.get('Prev_Net_Income')
                
                rev_chg = latest.get('Revenue_Change')
                ni_chg = latest.get('Net_Income_Change')

                def format_currency(val):
                    if pd.isna(val) or val is None:
                        return "N/A"
                    if abs(val) >= 1e9:
                        return f"${val/1e9:.2f}B"
                    if abs(val) >= 1e6:
                        return f"${val/1e6:.2f}M"
                    if abs(val) >= 1e3:
                        return f"${val/1e3:.2f}K"
                    return f"${val:.2f}"
                    
                def format_ratio(val):
                    if pd.isna(val) or val is None:
                        return "N/A"
                    return f"{val:.2f}x"
                
                def get_growth_str(curr, prev):
                    if pd.isna(curr) or pd.isna(prev) or prev == 0 or prev is None or curr is None:
                        return None
                    growth = (curr - prev) / abs(prev)
                    return f"{growth * 100:.1f}%"
                    
                prev_label = "Prev. Year" if period_mode == "Annual" else ("Prev. Quarter YoY" if period_mode == "Quarterly (YoY)" else "Prev. Quarter QoQ")
                
                ol_color = "🟢 Strong" if pd.notna(ol_val) and ol_val > 1 else "🔴 Review"
                lr_color = "🟢 Safe" if pd.notna(lr_val) and lr_val > 1 else "🔴 Risk"
                eq_color = "🟢 High" if pd.notna(eq_val) and eq_val > 1 else "🔴 Low"
                
                k1, k2, k3 = st.columns(3)
                with k1:
                    vol_gr = get_growth_str(ol_val, prev_ol_val)
                    st.metric("The Trend Check (Op. Leverage)", format_ratio(ol_val), delta=vol_gr)
                    st.caption(f"{prev_label}: {format_ratio(prev_ol_val)} | State: {ol_color}")
                    if pd.notna(ol_val):
                        if ol_val > 1:
                            st.caption("Vas por buen camino: Ganas más dinero gastando lo mismo o menos.")
                        else:
                            st.caption("Alerta: Los gastos suben más rápido que las ventas o el negocio se está achicando.")
                    with st.expander("¿Qué significa esto?"):
                         st.write("Mide la eficiencia. Si es positivo y alto, la empresa gana más dinero sin subir tanto sus costes. Si es negativo (ej. -109x), significa que los costes se han disparado o los ingresos han colapsado.")
                with k2:
                    lr_gr = get_growth_str(lr_val, prev_lr_val)
                    st.metric("The Survival Check (Liquidity)", format_ratio(lr_val), delta=lr_gr)
                    st.caption(f"{prev_label}: {format_ratio(prev_lr_val)} | State: {lr_color}")
                    if pd.notna(lr_val):
                        if lr_val > 1.5:
                            st.caption("Colchón seguro: Hay dinero de sobra en el banco para pagar todas las deudas de este año.")
                        elif lr_val < 1:
                            st.caption("Cuidado: Si no entra dinero pronto, la empresa tendrá problemas para pagar sus facturas.")
                    with st.expander("¿Qué significa esto?"):
                         st.write("Es el escudo anti-quiebra. Mide cuántas veces puede pagar la empresa sus deudas a corto plazo con el dinero que tiene en el banco hoy. Menos de 1x es peligroso.")
                with k3:
                    eq_gr = get_growth_str(eq_val, prev_eq_val)
                    st.metric("The Reality Check (Profit Quality)", format_ratio(eq_val), delta=eq_gr)
                    st.caption(f"{prev_label}: {format_ratio(prev_eq_val)} | State: {eq_color}")
                    if pd.notna(eq_val):
                        if eq_val > 1:
                            st.caption("Calidad total: El beneficio que dicen tener es dinero de verdad entrando en la caja.")
                        elif 0 <= eq_val <= 1:
                            st.caption("Verdad a medias: Dicen tener beneficios, pero el dinero real en el banco es menor.")
                        else:
                            st.caption("⚠️ Trampa: Reportan beneficios en el papel, pero en la realidad están perdiendo dinero.")
                    with st.expander("¿Qué significa esto?"):
                         st.write("El detector de humo contable. Compara el Beneficio Neto (lo que dice el papel) con el Free Cash Flow (el dinero real en la caja). Si es muy bajo, los beneficios reportados no son dinero real.")

                # Add Magnitude / Growth Metrics
                st.markdown("### 📈 Magnitude / Growth")
                g1, g2 = st.columns(2)
                with g1:
                    rev_delta = f"{rev_chg * 100:.2f}%" if pd.notna(rev_chg) else None
                    st.metric("Revenue (Absolute)", format_currency(rev_val), delta=rev_delta)
                    st.caption(f"{prev_label}: {format_currency(prev_rev_val)}")
                    st.caption("Es el dinero total que ha entrado por ventas. Si es positivo, el negocio se expande.")
                with g2:
                    ni_delta = f"{ni_chg * 100:.2f}%" if pd.notna(ni_chg) else None
                    st.metric("Net Income (Absolute)", format_currency(ni_val), delta=ni_delta)
                    st.caption(f"{prev_label}: {format_currency(prev_ni_val)}")
                    st.caption("Es lo que queda de las ventas tras pagar todos los gastos. Es el beneficio puro.")

                # Charts
                st.markdown("### 📊 Evolución Histórica")
                
                tab_ol, tab_lr, tab_eq = st.tabs(["Trend (Op. Leverage)", "Survival (Liquidity)", "Reality (Earnings Quality)"])
                
                with tab_ol:
                     if not df_filtered.empty and 'Operating_Leverage' in df_filtered.columns:
                         fig_ol = px.line(df_filtered, x='date', y='Operating_Leverage', markers=True)
                         fig_ol.add_hline(y=1, line_dash="dash", line_color="green", opacity=0.5)
                         fig_ol.update_layout(template="plotly_dark", height=400)
                         st.plotly_chart(fig_ol, use_container_width=True)
                with tab_lr:
                     if not df_filtered.empty and 'Liquidity_Ratio' in df_filtered.columns:
                         fig_lr = px.line(df_filtered, x='date', y='Liquidity_Ratio', markers=True)
                         fig_lr.add_hline(y=1, line_dash="dash", line_color="green", opacity=0.5)
                         fig_lr.update_layout(template="plotly_dark", height=400)
                         st.plotly_chart(fig_lr, use_container_width=True)
                with tab_eq:
                     if not df_filtered.empty and 'Earnings_Quality' in df_filtered.columns:
                         fig_eq = px.line(df_filtered, x='date', y='Earnings_Quality', markers=True)
                         fig_eq.add_hline(y=1, line_dash="dash", line_color="green", opacity=0.5)
                         fig_eq.update_layout(template="plotly_dark", height=400)
                         st.plotly_chart(fig_eq, use_container_width=True)

# ==========================================
# PAGE 4: NET WORTH & PORTFOLIO (New)
# ==========================================
elif page == "Net Worth & Portfolio":
    st.header("💎 Net Worth & Portfolio")
    st.caption("Visual command center for Stocks & Crypto. (Live)")

    try:
        TRADING212_KEY = st.secrets.get("TRADING212_API_KEY", "")
        TRADING212_SECRET = st.secrets.get("TRADING212_API_SECRET", "")
    except:
        TRADING212_KEY = ""
        TRADING212_SECRET = ""
        
    with st.spinner("Fetching Portfolio Data..."):
        # Fetch Data
        t212_data = df_utils.get_trading212_portfolio(TRADING212_KEY, TRADING212_SECRET)
        crypto_data = df_utils.get_crypto_balances(st.secrets if hasattr(st, 'secrets') else {})
        
        # Calculate Totals
        stocks_total_eur = t212_data.get("total_equity_eur", 0)
        stocks_total_usd = t212_data.get("total_equity_usd", 0)
        
        liquid_crypto_eur = crypto_data.get("total_liquid_eur", 0)
        staked_crypto_eur = crypto_data.get("total_staked_eur", 0)
        crypto_total_eur = liquid_crypto_eur + staked_crypto_eur
        
        liquid_crypto_usd = crypto_data.get("total_liquid_usd", 0)
        staked_crypto_usd = crypto_data.get("total_staked_usd", 0)
        crypto_total_usd = liquid_crypto_usd + staked_crypto_usd
        
        net_worth_eur = stocks_total_eur + crypto_total_eur
        net_worth_usd = stocks_total_usd + crypto_total_usd
        
    # --- HERO SECTION ---
    st.markdown("<br>", unsafe_allow_html=True)
    hero_col1, hero_col2, hero_col3 = st.columns([1,1,1])
    
    def metric_card(title, eur_val, usd_val):
        return f'''
        <div style="background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border-left: 4px solid #00F0FF;">
            <p style="color: #A0A0A0; font-size: 14px; margin-bottom: 5px; font-weight: bold;">{title}</p>
            <h2 style="margin: 0; color: #FFFFFF; font-size: 28px;">€{eur_val:,.2f} <sup style="color: #AAAAAA; font-size: 0.5em; font-weight: normal;">${usd_val:,.2f}</sup></h2>
        </div>
        '''
    
    with hero_col1:
        st.markdown(metric_card("Total Net Worth", net_worth_eur, net_worth_usd), unsafe_allow_html=True)
    with hero_col2:
        st.markdown(metric_card("Stocks (Trading 212)", stocks_total_eur, stocks_total_usd), unsafe_allow_html=True)
    with hero_col3:
        st.markdown(metric_card("Crypto (Liquid + Staked)", crypto_total_eur, crypto_total_usd), unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    
    # --- CHARTS SECTION ---
    st.subheader("📊 Portfolio Overview")
    
    chart_col1, chart_col2 = st.columns([1, 2])
    
    with chart_col1:
        # Donut Chart
        labels = ['Stocks', 'Liquid Crypto', 'Staked Crypto']
        values = [stocks_total_eur, liquid_crypto_eur, staked_crypto_eur]
        
        fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6, marker_colors=['#00F0FF', '#FF00FF', '#00FF00'])])
        fig_donut.update_layout(
            title_text="Asset Allocation",
            template="plotly_dark",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=50, b=0, l=0, r=0)
        )
        st.plotly_chart(fig_donut, use_container_width=True)
        
    with chart_col2:
        # Line Chart for Historical Growth
        # Generate mock data for history based on today
        import numpy as np
        dates = pd.date_range(end=datetime.datetime.today(), periods=365)
        np.random.seed(42)
        random_walk = np.random.normal(loc=0.0005, scale=0.01, size=365)
        cumulative_returns = np.cumprod(1 + random_walk)
        mock_historical = cumulative_returns * (net_worth_eur / cumulative_returns[-1]) # Scale to end at current NW
        
        hist_df = pd.DataFrame({'Date': dates, 'Net Worth': mock_historical})
        
        time_filter = st.radio("Timeframe:", ["1W", "1M", "YTD", "1Y"], horizontal=True, index=3)
        
        if time_filter == "1W": hist_df_filtered = hist_df.tail(7)
        elif time_filter == "1M": hist_df_filtered = hist_df.tail(30)
        elif time_filter == "YTD": 
             start_of_year = datetime.datetime(datetime.datetime.today().year, 1, 1)
             hist_df_filtered = hist_df[hist_df['Date'] >= start_of_year]
        else: hist_df_filtered = hist_df
        
        fig_line = px.line(hist_df_filtered, x='Date', y='Net Worth')
        fig_line.update_traces(line_color='#00F0FF', fill='tozeroy', fillcolor='rgba(0, 240, 255, 0.1)')
        fig_line.update_layout(
            title="Crecimiento Simulable (Último Año)",
            template="plotly_dark",
            margin=dict(t=50, b=0, l=0, r=0),
            yaxis_title=None,
            xaxis_title=None
        )
        st.plotly_chart(fig_line, use_container_width=True)
        
    st.divider()
    
    # --- BREAKDOWN SECTION ---
    st.subheader("🔐 Crypto Breakdown (Liquid vs Staked)")
    
    col_liquid, col_staked = st.columns(2)
    
    with col_liquid:
        st.markdown(f"#### 💧 Liquid / Cold Wallet (€{liquid_crypto_eur:,.2f})")
        liquid_df = pd.DataFrame(crypto_data.get("liquid", []))
        if not liquid_df.empty:
            # Reorder explicitly for aesthetics
            liquid_df = liquid_df[["asset", "balance", "value_eur", "value_usd"]]
            styled_liq = liquid_df.style.format({"balance": "{:,.4f}", "value_eur": "€{:,.2f}", "value_usd": "${:,.2f}"})
            st.dataframe(styled_liq, hide_index=True, use_container_width=True)
            
    with col_staked:
        st.markdown(f"#### 🥩 Staked (€{staked_crypto_eur:,.2f})")
        staked_df = pd.DataFrame(crypto_data.get("staked", []))
        if not staked_df.empty:
            staked_df = staked_df[["asset", "balance", "value_eur", "value_usd"]]
            styled_stk = staked_df.style.format({"balance": "{:,.4f}", "value_eur": "€{:,.2f}", "value_usd": "${:,.2f}"})
            st.dataframe(styled_stk, hide_index=True, use_container_width=True)
            
    st.divider()
    st.subheader("📈 Stocks Breakdown (Trading 212)")
    stocks_df = pd.DataFrame(t212_data.get("positions", []))
    if not stocks_df.empty:
         def highlight_profit(val):
             if pd.isna(val): return ''
             try:
                 val_float = float(val)
                 color = '#00FF00' if val_float > 0 else '#FF0000'
                 return f'color: {color}; font-weight: bold;'
             except:
                 return ''
             
         stocks_df = stocks_df[["ticker", "value_eur", "value_usd", "profit_eur", "profit_usd"]]
         styled_stk212 = stocks_df.style.format({
             "value_eur": "€{:,.2f}", "value_usd": "${:,.2f}",
             "profit_eur": "€{:,.2f}", "profit_usd": "${:,.2f}"
         }).applymap(highlight_profit, subset=["profit_eur", "profit_usd"])
         st.dataframe(styled_stk212, hide_index=True, use_container_width=True)



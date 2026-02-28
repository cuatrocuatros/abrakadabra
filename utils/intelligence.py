import feedparser
import pandas as pd
import datetime
import random
import google.generativeai as genai
import streamlit as st

def get_crypto_news():
    """
    Fetches latest Crypto news from Cointelegraph ES (Spanish).
    """
    news = []
    try:
        # Cointelegraph en Español RSS
        feed = feedparser.parse("https://es.cointelegraph.com/rss")
        for entry in feed.entries[:10]:
            news.append({
                "Source": "Cointelegraph ES",
                "Title": entry.title,
                "Link": entry.link,
                "Published": entry.published if 'published' in entry else "Reciente"
            })
    except Exception as e:
        print(f"Error fetching Cointelegraph ES: {e}")
    return news

def get_macro_news():
    """
    Fetches Macro/Finance news from Investing.com ES (Spanish).
    """
    news = []
    try:
        # Investing.com Noticias Generales en Español
        feed = feedparser.parse("https://es.investing.com/rss/news_25.rss") 
        for entry in feed.entries[:10]:
            news.append({
                "Source": "Investing ES",
                "Title": entry.title,
                "Link": entry.link,
                "Published": entry.published if 'published' in entry else "Reciente"
            })
    except Exception as e:
         print(f"Error fetching Investing ES: {e}")
    return news

def get_curated_headlines():
    """
    Aggregates news and simulates curation for impact.
    """
    crypto = get_crypto_news()
    macro = get_macro_news()
    
    # Interleave them for a mixed feed
    combined = []
    max_len = max(len(crypto), len(macro))
    for i in range(max_len):
        if i < len(macro): combined.append(macro[i])
        if i < len(crypto): combined.append(crypto[i])
        
    return combined[:20] 

def analyze_sentiment(ticker):
    """
    Simulates AI Sentiment Analysis for a specific ticker.
    """
    # Placeholder Logic: Random but deterministic per run
    score = random.randint(30, 80) 
    
    # Slight biases for demo realism based on ticker types
    if "BTC" in ticker or "TAO" in ticker: score += 5
    
    if score > 60: return "Bullish", "color: #00CC96" # Green
    elif score < 40: return "Bearish", "color: #FF4B4B" # Red
    else: return "Neutral", "color: #FFA500" # Orange

@st.cache_data(ttl=3600*24, show_spinner=False)
def get_ai_macro_panorama(tga_df, rrp_df, dxy_df, yc_df):
    """
    Ingiere los datos históricos (Pandas DataFrames) de las métricas macro y solicita 
    a Gemini 2.5 Flash que analice las trayectorias para emitir un veredicto de liquidez.
    """
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return "⚠️ Entorno macroeconómico temporalmente inaccesible (Falta API Key de Gemini)."
        
    if not api_key:
        return "⚠️ Entorno macroeconómico temporalmente inaccesible (Falta API Key de Gemini)."
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Prepare Data strings
        tga_str = tga_df.tail(4).to_string(index=False) if tga_df is not None and not tga_df.empty else "No data"
        rrp_str = rrp_df.tail(5).to_string(index=False) if rrp_df is not None and not rrp_df.empty else "No data"
        dxy_str = dxy_df.tail(5).to_string(index=False) if dxy_df is not None and not dxy_df.empty else "No data"
        yc_str = yc_df.tail(5).to_string(index=False) if yc_df is not None and not yc_df.empty else "No data"
        
        prompt = f"""
        Actúa como un Director de Macroeconomía Cuantitativa.
        A continuación tienes los últimos datos históricos de los 4 grandes pilares de la liquidez del mercado.
        Analiza SU TENDENCIA TEMPORAL ACTIVA y dime qué panorama dibujan estas métricas en conjunto sobre el "Risk-On" o "Risk-Off" del mercado.
        
        Datos Históricos (últimos días/semanas):
        1. Cuenta General del Tesoro (TGA, en Billones $):
        {tga_str}
        
        2. Reverse Repo de la Fed (RRP, en Billones $):
        {rrp_str}
        
        3. Índice Dólar (DXY):
        {dxy_str}
        
        4. Spread de Curva de Tipos (10Y-2Y, pct):
        {yc_str}
        
        Instrucciones:
        1. Responde en Español.
        2. SÉ ALTAMENTE CONCISO (Máximo 2 o 3 párrafos).
        3. No repitas los números tabla por tabla. Explica hacia dónde se mueven (¿Sube la liquidez del RRP o se drena? ¿Sube el TGA y ahoga el mercado?).
        4. Termina SIEMPRE el análisis con un veredicto final en negrita: ¿Entorno de Viento a favor (Bullish Liquidity) o Viento en contra (Bearish Liquidity)?
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"\n[ERROR CRÍTICO GEMINI AI - MACRO PANORAMA] {str(e)}\n")
        return "⚠️ No se pudo cargar el análisis Macro Panorama en este momento."

@st.cache_data(ttl=3600*24, show_spinner=False)
def get_llm_analysis(metrics_dict):
    """
    Sintetiza un resumen AI dinámico utilizando Gemini 1.5 Pro.
    Si falla o no hay API Key, usa el fallback estático.
    """
    ticker = metrics_dict.get("Ticker", "Unknown")
    
    # Extract values for the fallback and the prompt
    op_leverage = metrics_dict.get("Trend_Check_Op_Leverage")
    liquidity = metrics_dict.get("Survival_Check_Liquidity")
    eq = metrics_dict.get("Reality_Check_Earnings_Quality")
    rev_growth = metrics_dict.get("Revenue_Growth")
    ni_growth = metrics_dict.get("Net_Income_Growth")
    period = metrics_dict.get("Period_Mode", "Annual")
    
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        api_key = None
        
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Period-specific context injection
            period_context = ""
            if period == "Annual":
                period_context = "Alerta de Enfoque: Estás analizando el periodo Anual. ATENCIÓN: El 'Crecimiento' (Growth) compara este ÚLTIMO AÑO completo con respecto al AÑO ANTERIOR completo. Evalúa el panorama a largo plazo."
            elif period == "Quarterly (YoY)":
                period_context = "Alerta de Enfoque: Estás leyendo datos Trimestrales (Year-over-Year). ATENCIÓN: El 'Crecimiento' (Growth) compara el trimestre actual con el MISMO TRIMESTRE exacto del AÑO PASADO."
            elif period == "Quarterly (QoQ)":
                period_context = "Alerta de Enfoque: Estás leyendo datos Trimestrales (Quarter-over-Quarter). ATENCIÓN: El 'Crecimiento' (Growth) compara el trimestre actual con el TRIMESTRE INMEDIATAMENTE ANTERIOR."
            
            prompt = f"""
            Actúa como un Analista Senior de Hedge Fund. Estás evaluando a {ticker}.
            Analiza estos KPIs fundamentales (Periodo evaluado: {period}) y explica al usuario qué significan para la salud de la empresa.
            
            {period_context}
            
            KPIs Extraídos:
            - The Trend (Operating Leverage): {f"{op_leverage:.2f}x" if pd.notna(op_leverage) else "N/A"}
            - The Survival (Liquidity Ratio): {f"{liquidity:.2f}x" if pd.notna(liquidity) else "N/A"}
            - The Reality (Earnings Quality [FCF/Net Income]): {f"{eq:.2f}x" if pd.notna(eq) else "N/A"}
            - Revenue Growth: {f"{rev_growth*100:.2f}%" if pd.notna(rev_growth) else "N/A"}
            - Net Income Growth: {f"{ni_growth*100:.2f}%" if pd.notna(ni_growth) else "N/A"}
            
            Instrucciones Clave:
            1. SÉ MUY CONCISO Y BREVE (MÁXIMO 1 o 2 párrafos cortos). Sé directo, analítico y profesional.
            2. Evalúa los datos teniendo en cuenta la temporalidad estricta mencionada arriba (Annual, YoY o QoQ).
            3. Menciona anomalías entre beneficio y caja libre (The Reality). Si es muy bajo, señala posible 'humo contable'.
            4. Relaciona el crecimiento de ventas (Revenue Growth) con la eficiencia (Operating Leverage).
            5. Responde íntegramente en Español.
            """
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"\n[ERROR CRÍTICO GEMINI AI] Hubo un problema conectando con google-generativeai:\n{str(e)}\n")
            pass # Fall through to static fallback
    else:
        print("\n[ERROR CRÍTICO GEMINI AI] No se ha detectado ninguna GOOGLE_API_KEY. Verifica tu archivo .streamlit/secrets.toml\n")
            
    # --- STATIC FALLBACK (if no key or API error) ---
    summary = f"**⚠️ Análisis Estático de Respaldo ({ticker}):** *(Falta GOOGLE_API_KEY o error de IA. Revisa la consola)*\n\n"
    
    # Trend Analysis
    if pd.isna(op_leverage):
         summary += "🔹 **The Trend**: Datos insuficientes para Operating Leverage.\n"
    elif op_leverage > 1:
         summary += "✅ ***The Trend* (Apalancamiento Operativo):** Muy fuerte (>1x). Crecimiento altamente eficiente.\n"
    elif op_leverage > 0:
         summary += "⚠️ ***The Trend* (Apalancamiento Operativo):** Positivo pero comprimido.\n"
    else:
         summary += "🔴 ***The Trend* (Apalancamiento Operativo):** Alerta Negativa. Gastos operativos crecen más rápido que ingresos.\n"
         
    # Survival Analysis
    if pd.isna(liquidity):
        summary += "🔹 **The Survival**: Datos de liquidez no disponibles.\n"
    elif liquidity > 1.5:
        summary += "✅ ***The Survival* (Liquidez Inmediata):** Escudo de Hierro (>1.5x).\n"
    elif liquidity > 1:
        summary += "🔸 ***The Survival* (Liquidez Inmediata):** Ajustada. \n"
    else:
        summary += "🔴 ***The Survival* (Liquidez Inmediata):** Peligro Crítico (<1x).\n"
        
    # Reality Analysis
    if pd.isna(eq):
        summary += "🔹 **The Reality**: Calidad de ganancias no calculable.\n"
    elif eq > 1:
        summary += "✅ ***The Reality* (Calidad del Beneficio):** Transparente (>1x). El beneficio contable es dinero líquido real.\n"
    elif eq > 0.7:
        summary += "🔸 ***The Reality* (Calidad del Beneficio):** Aceptable.\n"
    else:
        summary += "🔴 ***The Reality* (Calidad del Beneficio):** Banderita Roja (<0.7x). Beneficios contables no respaldados íntegramente por flujo de caja líquido.\n"
        
    # Growth Info
    summary += f"\n📊 **Growth ({period})**: Rev: {f'{rev_growth*100:.1f}%' if pd.notna(rev_growth) else 'N/A'} | Net Inc: {f'{ni_growth*100:.1f}%' if pd.notna(ni_growth) else 'N/A'}"
    
    return summary


@st.cache_data(ttl=3600*24, show_spinner=False)
def get_vision_2036_thesis(df_history, ticker, period_mode):
    """
    Genera una tesis de inversión de DCA a largo plazo (Visión 2036) basada en 
    el histórico de fundamentales y contexto de noticias simulado.
    """
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return "⚠️ Visión 2036 temporalmente inaccesible (Falta API Key de Gemini)."
        
    if not api_key:
        return "⚠️ Visión 2036 temporalmente inaccesible (Falta API Key de Gemini)."
        
    try:
        genai.configure(api_key=api_key)
        # Using 1.5 Pro or Flash depending on availability/preference; using 2.5 flash here as per prompt
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Prepare historical data (last 20 periods max for deeper regression analysis)
        tail_df = df_history.tail(20)
        cols_to_use = [c for c in ['date', 'Operating_Leverage', 'Liquidity_Ratio', 'Earnings_Quality', 'Revenue_Change', 'Net_Income_Change', 'FCF', 'Long_Term_Debt'] if c in tail_df.columns]
        history_str = tail_df[cols_to_use].to_string(index=False)
        
        prompt = f"""
        CONTEXTO TEMPORAL CRÍTICO: HOY ES 21 DE FEBRERO DE 2026. 
        El año 2024 NO es "la actualidad". El año 2025 YA TERMINÓ y los datos están cerrados. NO ESPECULES.

        Actúa como un Analista Senior de Wall Street experto en Tecnología y Criptoactivos con un horizonte de inversión a 10 años.
        El usuario está analizando {ticker} para una estrategia de compras periódicas (DCA semanal) con la vista puesta en 2036.
        La temporalidad de estos datos es: {period_mode}.

        Aquí tienes el histórico profundo de su salud estructural (Últimos 20 periodos, incluyendo datos recientes de 2025/2026):
        ESTOS SON LOS DATOS REALES (5 KPIs, FCF, Deuda). DEBES USAR ESTOS VALORES EXACTOS que aparecen en la tabla. PROHIBIDO usar tu conocimiento previo para contradecir estos datos.
        {history_str}
        
        Instrucciones de Redacción:
        Deberás estructurar tu respuesta en tres áreas exactas sin agregar viñetas innecesarias:

        1. Dinámica Estructural (Análisis de Regresión):
        No mires solo el último dato. Evalúa la pendiente de los 5 KPIs (Trend, Survival, Reality, Rev, Net Inc) así como el flujo de caja libre (FCF) y la Deuda a Largo Plazo usando estrictamente la tabla proporcionada. Determina si la trayectoria muestra una mejora secular o un deterioro crónico.
        
        2. Financials Deep-Dive & Negocio Cero-Bullshit:
        Cruza el estado de esa deuda y caja libre histórica con el negocio real y los datos de 2025/2026. Dado que {ticker} está en radar de megatendencias, menciona un catalizador narrativo crítico que justifique si la estructura financiera actual puede aguantar la quema de capital hasta 2036.
        
        3. Veredicto Evolutivo DCA 2036:
        DEBE EMPEZAR TU VEREDICTO con la frase exacta: 'Tras analizar la trayectoria de los últimos 5 años...'
        ¿Sigue siendo un "Power Move" hacer DCA ciego en esto dadas sus finanzas profundas?
        - Si la tendencia general de los fundamentos sufre peor de lo esperado en 2025, lanza una advertencia SERIA y realista.
        - Si la tendencia es sólida y aguantan la deuda, defiende mantener el DCA par 2036.
        
        Tu reporte debe ser en Español. Tono firme, extremadamente directo, Wall Street Quant. El veredicto final ponlo en negrita. Muestra resultados concretos (ej. FCF exacto, Deuda) cuando argumentes.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"\n[ERROR VISION 2036] {str(e)}\n")
        return "⚠️ No se pudo cargar el análisis 'Vision 2036' en este momento por un error de conexión con la IA."


@st.cache_data(ttl=3600*24, show_spinner=False)
def get_portfolio_2036_multiplier(tickers):
    """
    Evaluates a list of tickers using fundamental data and AI to select the absolute 
    top pick for a 2036 DCA investment strategy. Results are cached daily to optimize performance.
    All internal logic comments in English.
    """
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        return "⚠️ Portfolio Analysis: Requires GOOGLE_API_KEY."
        
    if not api_key:
        return "⚠️ Portfolio Analysis: Requires GOOGLE_API_KEY to run Gemini Flash."
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # We need to import yf_utils here to avoid circular imports if any, 
        # or assuming it is available. It is cleaner to import at function level.
        import utils.yf_fundamentals as yf_utils
        
        # Collect extended historical tracking for all 15 tickers
        fund_data = []
        
        # Columns mapped for the AI to understand trends
        cols_to_keep = ['date', 'Operating_Leverage', 'Liquidity_Ratio', 'Earnings_Quality', 'Revenue_Change', 'Net_Income_Change', 'FCF', 'Long_Term_Debt']
        
        for t in tickers:
            ticker_data_str = f"\n--- TICKER: {t} ---\n"
            
            # 1. Fetch Annual (Last 5 Years)
            analysis_a = yf_utils.analyze_company(t, period="Annual")
            if analysis_a and analysis_a['df'] is not None and not analysis_a['df'].empty:
                df_a = analysis_a['df'].tail(5)
                df_a_filtered = df_a[[c for c in cols_to_keep if c in df_a.columns]]
                ticker_data_str += "HISTÓRICO ANUAL (Últimos 5 años fiscales):\n" + df_a_filtered.to_string(index=False) + "\n"
            else:
                ticker_data_str += "HISTÓRICO ANUAL: No disponible.\n"
                
            # 2. Fetch Quarterly (Last 20 Quarters)
            analysis_q = yf_utils.analyze_company(t, period="Quarterly (YoY)")
            if analysis_q and analysis_q['df'] is not None and not analysis_q['df'].empty:
                df_q = analysis_q['df'].tail(20)
                df_q_filtered = df_q[[c for c in cols_to_keep if c in df_q.columns]]
                ticker_data_str += "HISTÓRICO TRIMESTRAL (Últimos 20 trimestres):\n" + df_q_filtered.to_string(index=False) + "\n"
            else:
                ticker_data_str += "HISTÓRICO TRIMESTRAL: No disponible.\n"
                
            fund_data.append(ticker_data_str)
                
        # Join data into a single text block
        fund_str = "".join(fund_data)
        
        prompt = f"""
        CONTEXTO TEMPORAL CRÍTICO: HOY ES 21 DE FEBRERO DE 2026. 
        El año 2024 NO es "la actualidad". El año 2025 YA TERMINÓ y los datos de Q3 y Q4 de 2025 están cerrados y disponibles en la tabla de abajo. NO ESPECULES.

        Actúa como un Director de Estrategia de Inversión Tecnológica Institucional.
        El usuario requiere construir el mejor portafolio para una estrategia de DCA (Dollar Cost Averaging) sistemática e ininterrumpida de aquí a 2036 manejando la consistencia y el alto riesgo.
        
        A continuación tienes el historial financiero profundo de cada una: los últimos 5 años fiscales (incluyendo 2025) y hasta los últimos 20 trimestres (incluyendo Q1 a Q4 de 2025). 
        ESTOS SON LOS DATOS REALES (5 KPIs: Trend Check, Survival Check, Reality Check, etc., junto con FCF y Deuda a Largo Plazo). 
        DEBES USAR ESTOS VALORES EXACTOS (ej. el multiplicador exacto de FCF, el nivel exacto de deuda, el valor de Trend Check) que aparecen en la tabla. PROHIBIDO usar tu conocimiento previo para contradecir estos datos.
        
        Datos Financieros:
        {fund_str}
        
        Instrucciones Obligatorias:
        1. Veredicto Evolutivo (OBLIGATORIO): Empieza tu reporte exactamente con esta frase: 'Tras analizar la trayectoria de los últimos 5 años cerrados...'
        2. Estructura Top 10 + Tiering: Vuelve a generar el ranking basándote RIGUROSAMENTE en los datos reales de 2025 y 2026 provistos en la tabla. Si una empresa tiene ingresos cayendo o métricas deteriorándose en 2025, eso debe pesar más que cualquier narrativa histórica.
           - Tier 1 (Core): Puestos 1-3. Pilares de estabilidad. Sugiere un % de Asignación.
           - Tier 2 (Estratégico): Puestos 4-10. Crecimiento con mayor riesgo.
           - Vigilancia Crítica: Breve mención a las 5 restantes y la razón cruda por la que no entran basándose en sus datos recientes.
        3. Evidencia Numérica Obligatoria (Q1-Q4 2025): AL LADO DE CADA TICKER en el Top 10, DEBES mostrar un resumen concreto de los resultados de los últimos 4 trimestres (Q1-Q4 2025) extraídos directamente de la tabla (ej. FCF de cada trimestre, Trend Check, Deuda). USA LOS NÚMEROS EXACTOS DE LA TABLA.
        4. Cálculo de Multipliers (Potencial de Explosión): Junto al nombre de cada una en el Top 10, añade una etiqueta explícita de 'Potencial Multiplier 2036' (ej. 2x, 5x, 10x+ o 100x). Justifica este cálculo con análisis prospectivo.
        5. Análisis de 'Patrón Ten-Bagger' (Moonshots): Dentro del Tier 2, para aquellas empresas ultra-disruptivas que aún queman caja, compara explícitamente sus métricas actuales de crecimiento (Trend Check) con los estados financieros formativos de colosos históricos.
        6. Sé directo, brutal, Wall Street Quant tone. Tu reporte es un dictamen institucional. Tu respuesta DEBE ser 100% en Español puro, sin viñetas sobrantes cuando redactes texto.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"\n[ERROR PORTFOLIO MULTIPLIER 2036] {str(e)}\n")
        return "⚠️ No se pudo generar \"The 2036 Multiplier\" en este momento por un fallo en la IA."




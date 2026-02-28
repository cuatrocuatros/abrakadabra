import pandas as pd
import yfinance as yf
from fredapi import Fred
import requests
import datetime
import streamlit as st

@st.cache_data(ttl=3600)
def get_macro_liquidity(api_key):
    """
    Calculates Net Liquidity = WALCL - (WDTGAL + RRPONTSYD * 1000)
    Returns a DataFrame with Net Liquidity and BTC Price.
    """
    try:
        fred = Fred(api_key=api_key)
        
        # Fetch Data
        walcl = fred.get_series('WALCL')  # Total Assets (Millions)
        wdtgal = fred.get_series('WDTGAL') # Treasury General Account (Millions)
        rrp = fred.get_series('RRPONTSYD') # Reverse Repo (Billions)
        
        # Align dates
        df = pd.DataFrame({'WALCL': walcl, 'WDTGAL': wdtgal, 'RRP': rrp})
        df = df.interpolate(method='linear') 
        df = df.dropna()
        
        # Formula: Net Liq = WALCL - (WDTGAL + RRP * 1000)
        df['Net_Liquidity_Millions'] = df['WALCL'] - (df['WDTGAL'] + df['RRP'] * 1000)
        df['Net_Liquidity_Billions'] = df['Net_Liquidity_Millions'] / 1000
        
        # Get BTC Price
        btc = yf.download('BTC-USD', start=df.index.min(), end=None, progress=False)
        if not btc.empty:
            if isinstance(btc.columns, pd.MultiIndex):
                # Flatten or select 'Close' level
                try:
                    btc_closes = btc['Close']
                except:
                    btc_closes = btc.xs('Close', level=0, axis=1) # Fallback
            else:
                 btc_closes = btc['Close']
            
            # Resample to match frequency if needed, but simple join works on index
            df = df.join(btc_closes, how='inner')
            df = df.rename(columns={'Close': 'BTC_Price'})
            if 'BTC-USD' in df.columns:
                 df = df.rename(columns={'BTC-USD': 'BTC_Price'})
            
        return df
    except Exception as e:
        print(f"Error fetching macro data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_m2_supply(api_key):
    """
    Fetches M2 Money Supply (WM2NS) and calculates % Change from Year Ago.
    """
    try:
        fred = Fred(api_key=api_key)
        m2 = fred.get_series('WM2NS')
        df = pd.DataFrame({'M2': m2})
        df = df.dropna()
        
        # Calculate % Change from Year Ago (52 weeks roughly)
        df['M2_YoY'] = df['M2'].pct_change(periods=52) * 100
        return df.dropna()
    except Exception as e:
        print(f"Error fetching M2 data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_industrial_data(api_key):
    """
    Fetches Philly Fed Manufacturing Index and Industrial Production.
    """
    try:
        fred = Fred(api_key=api_key)
        philly = fred.get_series('GACDFSA066MSFRBPHI')
        ind_prod = fred.get_series('IPGMFN')
        
        df = pd.DataFrame({'Philly_Fed': philly, 'Industrial_Production': ind_prod})
        df = df.dropna()
        return df
    except Exception as e:
        print(f"Error fetching industrial data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_btc_gold_ratio():
    """
    Fetches BTC and Gold (GC=F) prices to calculate the Ratio.
    """
    try:
        data = yf.download(['BTC-USD', 'GC=F'], period="max", progress=False)
        if not data.empty:
            try:
                closes = data['Close']
            except:
                return pd.DataFrame()
                
            if isinstance(closes.columns, pd.MultiIndex):
                closes.columns = closes.columns.get_level_values(0)
            
            if 'BTC-USD' in closes.columns and 'GC=F' in closes.columns:
                 df = closes[['BTC-USD', 'GC=F']].copy()
                 df = df.dropna()
                 df['Ratio'] = df['BTC-USD'] / df['GC=F']
                 return df
        
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching BTC/Gold: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_fred_generic(api_key, series_id, col_name):
    try:
        fred = Fred(api_key=api_key)
        s = fred.get_series(series_id)
        df = pd.DataFrame({col_name: s})
        return df.dropna()
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return pd.DataFrame()

def get_yield_curve(api_key):
    return get_fred_generic(api_key, 'T10Y2Y', 'Yield_Curve')

def get_dxy(api_key):
    return get_fred_generic(api_key, 'DTWEXBGS', 'DXY')

def get_stress_index(api_key):
    return get_fred_generic(api_key, 'STLFSI4', 'Stress_Index')

def get_reverse_repo(api_key):
    """
    Reverse Repo (Daily). RRPONTSYD.
    """
    return get_fred_generic(api_key, 'RRPONTSYD', 'RRP')

def get_tga(api_key):
    """
    Treasury General Account (Weekly). WTREGEN.
    """
    return get_fred_generic(api_key, 'WTREGEN', 'TGA')

def get_breakeven_inflation(api_key):
    """
    10-Year Breakeven Inflation Rate (Daily). T10YIE.
    """
    return get_fred_generic(api_key, 'T10YIE', 'Breakeven_10Y')

@st.cache_data(ttl=3600)
def get_fear_and_greed():
    """
    Fetches Fear & Greed Index from Alternative.me
    """
    url = "https://api.alternative.me/fng/"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and len(data['data']) > 0:
                item = data['data'][0]
                return item['value'], item['value_classification']
    except Exception as e:
        pass
    return 50, "Neutral"

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_portfolio_data(tickers):
    """
    Fetches metrics for list of tickers.
    Returns:
       summary_df: For table (latest T-0)
       history_df: For correlation (closes)
       sp500_change: For Alpha KPI
       trajectory_df: For Scatter Trails (T-0 to T-3 for each asset)
    """
    data_summary = []
    trajectory_data = [] # List of dicts
    history_closes = pd.DataFrame()
    
    try:
        all_tickers = tickers + ["^GSPC"]
        tik_str = " ".join(all_tickers)
        
        # Fetch 6mo to ensure enough history for RSI and Trails
        df = yf.download(tik_str, period="6mo", group_by='ticker', progress=False)
        
        # SP500 Data for Benchmarking
        sp500_full = pd.DataFrame()
        sp500_change = 0.0
        try:
            sp500_full = df["^GSPC"].copy().dropna(how='all')
            if not sp500_full.empty:
                sp500_curr = sp500_full['Close'].iloc[-1]
                sp500_prev = sp500_full['Close'].iloc[-2]
                sp500_change = ((sp500_curr - sp500_prev) / sp500_prev) * 100
        except: pass
            
        for ticker in tickers:
            try:
                # Extract ticker data
                if len(all_tickers) > 1:
                    try:
                        t_data = df[ticker].copy()
                    except KeyError:
                        continue
                else:
                    t_data = df.copy()
                
                t_data = t_data.dropna(how='all')
                if t_data.empty or 'Close' not in t_data.columns:
                    continue

                # Close History for Correlation
                history_closes[ticker] = t_data['Close']
                
                # --- CALCULATE FULL SERIES METRICS FIRST ---
                closes = t_data['Close']
                rsi_series = calculate_rsi(closes)
                
                # Rel Strength
                asset_ret_14d = closes.pct_change(14) * 100
                sp500_aligned = sp500_full['Close'].reindex(t_data.index).ffill()
                sp500_ret_14d = sp500_aligned.pct_change(14) * 100
                rel_strength_series = asset_ret_14d - sp500_ret_14d
                
                # Vol Ratio
                vol_avg = t_data['Volume'].rolling(30).mean()
                vol_ratio_series = t_data['Volume'] / vol_avg
                
                # 52w Dist
                high_val = t_data['High'].max()
                dist_series = ((closes - high_val) / high_val) * 100
                
                # --- LATEST SUMMARY (T-0) ---
                idx_0 = -1
                data_summary.append({
                    'Ticker': ticker,
                    'Price': closes.iloc[idx_0],
                    'Change_Pct': closes.pct_change().iloc[idx_0] * 100,
                    'RSI': rsi_series.iloc[idx_0],
                    'Dist_52w': dist_series.iloc[idx_0],
                    'Vol_Ratio': vol_ratio_series.iloc[idx_0],
                    'Rel_Strength_14d': rel_strength_series.iloc[idx_0]
                })
                
                # --- TRAJECTORY DATA (T-0 to T-3) ---
                days_to_fetch = 4
                if len(t_data) >= days_to_fetch:
                    for i in range(days_to_fetch):
                         pos = -1 - i
                         trajectory_data.append({
                             'Ticker': ticker,
                             'Date': t_data.index[pos],
                             'Days_Ago': i,
                             'RSI': rsi_series.iloc[pos],
                             'Rel_Strength_14d': rel_strength_series.iloc[pos],
                             'Vol_Ratio': vol_ratio_series.iloc[pos]
                         })

            except Exception as e:
                pass
                
    except Exception as e:
        print(f"Error fetching portfolio batch: {e}")
        
    return pd.DataFrame(data_summary), history_closes, sp500_change, pd.DataFrame(trajectory_data)

def get_defi_tvl(token_slug):
    """
    Fetches TVL from DeFiLlama.
    """
    url = f"https://api.llama.fi/protocol/{token_slug}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            tvl_series = data.get('tvl', [])
            if tvl_series:
                 return tvl_series[-1]['totalLiquidityUSD']
    except:
        pass
    return 0

def get_hashrate():
    """
    Fetches Bitcoin Hashrate (using a public source if available, else placeholder).
    """
    try:
        resp = requests.get("https://api.blockchain.info/charts/hash-rate?timespan=1days&format=json")
        if resp.status_code == 200:
            data = resp.json()
            if 'values' in data and len(data['values']) > 0:
                return data['values'][-1]['y']
    except:
        pass
    return 0

# --- ALPHA SCANNER FUNCTIONS ---

def get_nasdaq_100_tickers():
    """
    Scrapes NASDAQ 100 tickers from Wikipedia.
    """
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        # Usually the 5th table contains the components
        # We look for a table with 'Ticker' or 'Symbol'
        for table in tables:
            if 'Ticker' in table.columns:
                return table['Ticker'].tolist()
            elif 'Symbol' in table.columns:
                return table['Symbol'].tolist()
        return []
    except Exception as e:
        print(f"Error fetching NASDAQ 100: {e}")
        return []

def scan_potential_alphas(existing_tickers):
    """
    Scans NASDAQ 100 for 'Reversal' Opportunities.
    Criteria (S-Curve Reversion):
    1. RSI < 40 (Oversold / Beaten Down)
    2. Rising Relative Strength (North/North-West Momentum)
    """
    candidates = []
    try:
        nasdaq_tickers = get_nasdaq_100_tickers()
        
        # Filter existing (TAO will be in portfolio now, so excluded)
        to_scan = [t for t in nasdaq_tickers if t not in existing_tickers and f"{t}-USD" not in existing_tickers]
        
        # Limit to 100
        to_scan = list(set(to_scan)) 
        
        scan_tickers = to_scan + ["^GSPC"]
        tik_str = " ".join(scan_tickers)
        
        # We need short term history for reversal (1mo is enough)
        df = yf.download(tik_str, period="3mo", group_by='ticker', progress=False)
        
        # SP500 
        sp500_full = pd.DataFrame()
        try:
             sp500_full = df["^GSPC"].copy().dropna(how='all')
        except: pass
            
        for ticker in to_scan:
            try:
                if len(scan_tickers) > 1:
                    try: t_data = df[ticker].copy()
                    except: continue
                else:
                    t_data = df.copy()
                
                t_data = t_data.dropna(how='all')
                if len(t_data) < 20: continue
                
                closes = t_data['Close']
                volume = t_data['Volume']
                
                # RSI
                rsi_series = calculate_rsi(closes)
                if len(rsi_series) < 5: continue
                
                rsi_now = rsi_series.iloc[-1]
                rsi_prev = rsi_series.iloc[-5] # T-4
                
                # Rel Strength
                try:
                    asset_ret_14d = closes.pct_change(14) * 100
                    sp500_aligned = sp500_full['Close'].reindex(t_data.index).ffill()
                    sp500_ret_14d = sp500_aligned.pct_change(14) * 100
                    rel_strength_series = asset_ret_14d - sp500_ret_14d
                    
                    rs_now = rel_strength_series.iloc[-1]
                    rs_prev = rel_strength_series.iloc[-5]
                except:
                    continue
                
                # FILTER: Reversal
                # 1. RSI < 40
                # 2. RS Improving (North)
                
                if rsi_now < 40 and rs_now > rs_prev:
                    candidates.append({
                        'Ticker': ticker,
                        'RSI': rsi_now,
                        'Rel_Strength_14d': rs_now,
                        'Vol_Avg': volume.tail(5).mean(),
                        'Price': closes.iloc[-1],
                        'Momentum': "North" if rsi_now > rsi_prev else "North-West"
                    })
                    
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Error scanning alphas: {e}")
        
    return pd.DataFrame(candidates)

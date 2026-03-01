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

# --- NET WORTH PORTFOLIO FETCHERS ---

import base64

def get_trading212_portfolio(api_key, api_secret=None):
    """
    Fetches the portfolio from Trading 212 API using Basic Auth base64 encoding.
    """
    if not api_key:
        return {"total_equity": 0, "cash": 0, "positions": []}
        
    # As per Trading 212 Docs, auth is Basic <base64(key:secret)>
    # If no secret provided, we'll try the old direct bearer just in case, but assume basic auth.
    if api_secret:
        cred_str = f"{api_key}:{api_secret}"
        encoded_cred = base64.b64encode(cred_str.encode('utf-8')).decode('utf-8')
        auth_header = f"Basic {encoded_cred}"
    else:
        auth_header = api_key # Fallback if user only provided one string in legacy format
    
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }
    result = {"total_equity_usd": 0, "total_equity_eur": 0, "cash_usd": 0, "cash_eur": 0, "positions": []}
    
    # Let's try LIVE first, then DEMO if 401/404
    base_urls = ["https://live.trading212.com", "https://demo.trading212.com"]
    success = False
    
    # Pre-fetch EUR/USD strictly to convert total account values (assuming account is in EUR)
    eur_usd_rate = 1.08 # Safe fallback
    try:
        eur_usd_data = yf.download("EURUSD=X", period="1d", progress=False)
        eur_usd_rate = float(eur_usd_data['Close'].iloc[-1])
    except Exception as e:
        print(f"EUR/USD Fetch Error: {e}")
        
    for base in base_urls:
        try:
            # Cash/Equity endpoint
            cash_url = f"{base}/api/v0/equity/account/cash"
            cash_resp = requests.get(cash_url, headers=headers, timeout=10)
            
            if cash_resp.status_code == 200:
                success = True
                data = cash_resp.json()
                # Assuming T212 totals are in EUR based on account.
                result["total_equity_eur"] = data.get("total", 0)
                result["total_equity_usd"] = data.get("total", 0) * eur_usd_rate
                result["cash_eur"] = data.get("free", 0)
                result["cash_usd"] = data.get("free", 0) * eur_usd_rate
                
                # If cash successful, do Positions endpoint on same base URL
                pos_url = f"{base}/api/v0/equity/portfolio"
                pos_resp = requests.get(pos_url, headers=headers, timeout=10)
                if pos_resp.status_code == 200:
                    for p in pos_resp.json():
                        qty = p.get("quantity", 0)
                        price = p.get("currentPrice", 0)
                        
                        raw_ticker = p.get("ticker", "")
                        clean_ticker = raw_ticker.split("_")[0] if raw_ticker else ""
                        
                        # Fix common SPAC legacy tickers in T212 portfolio
                        if clean_ticker == "DMYI": clean_ticker = "IONQ"
                        if clean_ticker == "RTP": clean_ticker = "JOBY"
                        
                        result["positions"].append({
                            "ticker": clean_ticker,
                            "value_usd": qty * price, # US stocks return currentPrice in USD
                            "value_eur": (qty * price) / eur_usd_rate if eur_usd_rate else qty * price,
                            "profit_eur": p.get("ppl", 0), # ppl is returned in account currency (EUR)
                            "profit_usd": p.get("ppl", 0) * eur_usd_rate
                        })
                else:
                    st.sidebar.error(f"T212 Port Error {pos_resp.status_code} ({base}): {pos_resp.text}")
                
                break # Stop trying URLs if one succeeded
            else:
                 # It failed, we'll loop to the next Dem/Live environment
                 pass
                 
        except Exception as e:
            st.sidebar.error(f"T212 Exception: {e}")
            break
            
    if not success and cash_resp:
         # If all failed, show the last error
         st.sidebar.error(f"T212 Cash Error failed on all endpoints. Last error {cash_resp.status_code}: {cash_resp.text}")
         
    return result

def get_crypto_balances(_secrets):
    """
    Fetches Crypto balances dynamically using public RPCs/Explorers.
    """
    result = {
        "liquid": [],
        "staked": [],
        "total_liquid_usd": 0.0,
        "total_staked_usd": 0.0,
        "total_liquid_eur": 0.0,
        "total_staked_eur": 0.0
    }
    
    eur_usd_rate = 1.08 # Safe fallback
    try:
        eur_usd_data = yf.download("EURUSD=X", period="1d", progress=False)
        eur_usd_rate = float(eur_usd_data['Close'].iloc[-1])
    except: pass
    
    # Configure robust session for public APIs like Solana that frequently timeout
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[ 500, 502, 503, 504 ])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    # 1. Prices (using yfinance as fallback for USD value)
    prices = {}
    try:
        tickers = ["ETH-USD", "SOL-USD", "LINK-USD", "TAO22974-USD", "ONDO-USD", "XRP-USD"]
        df = yf.download(tickers, period="1d", progress=False)
        
        # Helper to safely extract scalar prices from yfinance df
        def get_price(tik):
            try:
                col = df['Close'][tik]
                return float(col.iloc[-1])
            except:
                return 0.0
                
        prices['ETH'] = get_price("ETH-USD")
        prices['SOL'] = get_price("SOL-USD")
        prices['LINK'] = get_price("LINK-USD")
        prices['TAO'] = get_price("TAO22974-USD")
        prices['ONDO'] = get_price("ONDO-USD")
        prices['XRP'] = get_price("XRP-USD")
    except Exception as e:
        print(f"Crypto price fetch error: {e}")

    def add_balance(category, asset, balance):
        if balance > 0:
            val_usd = balance * prices.get(asset, 0)
            val_eur = val_usd / eur_usd_rate
            
            result[category].append({
                "asset": asset,
                "balance": balance,
                "value_usd": val_usd,
                "value_eur": val_eur
            })
            if category == "liquid":
                result["total_liquid_usd"] += val_usd
                result["total_liquid_eur"] += val_eur
            else:
                result["total_staked_usd"] += val_usd
                result["total_staked_eur"] += val_eur

    # --- ETHEREUM (Liquid) ---
    eth_addr = _secrets.get("LEDGER_ETH_ADDRESS", "")
    if eth_addr:
        try:
            url = f"https://api.ethplorer.io/getAddressInfo/{eth_addr}?apiKey=freekey"
            res = requests.get(url, timeout=10).json()
            if "ETH" in res:
                add_balance("liquid", "ETH", res["ETH"].get("balance", 0))
            if "tokens" in res:
                for t in res["tokens"]:
                    sym = t.get("tokenInfo", {}).get("symbol", "").upper()
                    if sym in ["LINK", "ONDO", "TAO"]: # TAO might be wTAO
                        decimals = int(t.get("tokenInfo", {}).get("decimals", 18))
                        bal = int(t.get("balance", 0)) / (10**decimals)
                        add_balance("liquid", sym, bal)
        except Exception as e:
            print(f"Ethplorer error: {e}")

    # --- SOLANA (Liquid + Staked) ---
    sol_addr = _secrets.get("LEDGER_SOL_ADDRESS", "")
    if sol_addr:
        try:
            # 1. Native SOL (Liquid)
            payload = {"jsonrpc":"2.0", "id":1, "method":"getBalance", "params":[sol_addr]}
            res = session.post("https://api.mainnet-beta.solana.com", json=payload, timeout=10).json()
            lamports = res.get("result", {}).get("value", 0)
            if lamports:
                add_balance("liquid", "SOL", lamports / 1e9)
                
            # 2. SPL Tokens (Staked SOL / mSOL)
            # Marinade staked SOL token mint: mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqkVmF8n
            token_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    sol_addr,
                    {"mint": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqkVmF8n"},
                    {"encoding": "jsonParsed"}
                ]
            }
            tok_res_raw = session.post("https://api.mainnet-beta.solana.com", json=token_payload, timeout=10)
            if tok_res_raw.status_code == 200:
                tok_res = tok_res_raw.json()
                accounts = tok_res.get("result", {}).get("value", [])
                
                for acc in accounts:
                    info = acc.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                    # Marinade Staked SOL matches the filtered request
                    amount_str = info.get("tokenAmount", {}).get("uiAmountString", "0")
                    add_balance("staked", "SOL", float(amount_str))
            else:
                st.sidebar.error(f"Solana Token Error: {tok_res_raw.text}")
                    
        except Exception as e:
            st.sidebar.error(f"Solana Exception: {e}")

    # --- XRP (Liquid) ---
    xrp_addr = _secrets.get("LEDGER_XRP_ADDRESS", "")
    if xrp_addr:
        try:
            payload = {"method": "account_info", "params": [{"account": xrp_addr, "strict": True}]}
            res = session.post("https://s1.ripple.com:51234/", json=payload, timeout=10).json()
            drops = res.get("result", {}).get("account_data", {}).get("Balance", "0")
            if drops:
                add_balance("liquid", "XRP", int(drops) / 1e6)
        except Exception as e:
            print(f"XRP error: {e}")
            
    # --- STAKED ---
    # For Staked ETH, typically held as stETH or in a smart contract. 
    # Best effort via ethplorer (checking if the user provided the stETH contract as their staked address)
    stk_eth = _secrets.get("STAKED_ETH_ADDRESS", "")
    if stk_eth:
         try:
            res = requests.get(f"https://api.ethplorer.io/getAddressInfo/{stk_eth}?apiKey=freekey", timeout=10).json()
            for t in res.get("tokens", []):
                sym = t.get("tokenInfo", {}).get("symbol", "").upper()
                if "ETH" in sym or "STETH" in sym:
                    decimals = int(t.get("tokenInfo", {}).get("decimals", 18))
                    bal = int(t.get("balance", 0)) / (10**decimals)
                    add_balance("staked", "ETH", bal)
         except: pass
         
    # For Native Staked SOL (e.g. Marinade Native Stake accounts or Stake Authority PDA)
    stk_sol = _secrets.get("STAKED_SOL_ADDRESS", "")
    if stk_sol:
        try:
            # Check if it's an Authority Address with multiple Stake Accounts
            STAKE_PROGRAM_ID = 'Stake11111111111111111111111111111111111111'
            payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getProgramAccounts',
                'params': [
                    STAKE_PROGRAM_ID,
                    {
                        'encoding': 'jsonParsed',
                        'filters': [{'memcmp': {'offset': 44, 'bytes': stk_sol}}]
                    }
                ]
            }
            res = session.post("https://api.mainnet-beta.solana.com", json=payload, timeout=15).json()
            accounts = res.get("result", [])
            total_lamports = 0
            for acc in accounts:
                total_lamports += acc.get("account", {}).get("lamports", 0)
                
            if total_lamports > 0:
                add_balance("staked", "SOL", total_lamports / 1e9)
            else:
                # Fallback to check if the address itself is a single native stake account (direct balance)
                payload_bal = {"jsonrpc":"2.0", "id":2, "method":"getBalance", "params":[stk_sol]}
                res_bal = session.post("https://api.mainnet-beta.solana.com", json=payload_bal, timeout=10).json()
                lamports_bal = res_bal.get("result", {}).get("value", 0)
                if lamports_bal > 0:
                     add_balance("staked", "SOL", lamports_bal / 1e9)
                     
        except Exception as e:
            # Suppress noisy timeouts as it's common for public solana RPCs if partial balance loaded
            if "Max retries exceeded" not in str(e) and "timeout" not in str(e).lower():
                st.sidebar.error(f"Solana Staked Exception: {e}")

    # --- BITTENSOR (TAO) Liquid & Staked ---
    tao_addr = _secrets.get("LEDGER_TAO_ADDRESS", "")
    tao_api_key = _secrets.get("TAOSTATS_API_KEY", "")
    if tao_addr:
        if not tao_api_key:
            st.sidebar.warning("Native TAO tracking requires a Taostats API Key. Check setup instructions.")
        else:
            try:
                # Based on Taostats API docs for Account bounds
                tao_headers = {"Authorization": tao_api_key}
                
                # We will fetch Get Account latest data from Taostats 
                tao_res = session.get(f"https://api.taostats.io/api/account/latest/v1?address={tao_addr}", headers=tao_headers, timeout=10)
                if tao_res.status_code == 200:
                    data = tao_res.json()
                    if "data" in data and len(data["data"]) > 0:
                        account_info = data["data"][0]
                        # Balances from Taostats are returned in RAO (1e-9 TAO)
                        l_bal = float(account_info.get("balance_free", 0)) / 1e9
                        s_bal = float(account_info.get("balance_staked", 0)) / 1e9
                        
                        if l_bal > 0: add_balance("liquid", "TAO", l_bal)
                        if s_bal > 0: add_balance("staked", "TAO", s_bal)
                elif tao_res.status_code == 404:
                     # Account might be new or unindexed
                     pass
                else:
                    st.sidebar.error(f"Taostats API Error: {tao_res.status_code} - {tao_res.text}")
            except Exception as e:
                 print(f"TAO fetch exception: {e}")

    return result

import requests
import streamlit as st
import base64
import pandas as pd
from datetime import datetime

class Trading212API:
    def __init__(self, api_key: str, api_secret: str):
        self.base_url = "https://live.trading212.com"
        
        credentials_string = f"{api_key}:{api_secret}"
        encoded_credentials = base64.b64encode(credentials_string.encode('utf-8')).decode('utf-8')
        auth_header = f"Basic {encoded_credentials}"
        self.headers = {"Authorization": auth_header}
        
    def get_portfolio(self):
        """Fetch current portfolio status (equity, invested, etc)"""
        url = f"{self.base_url}/api/v0/equity/portfolio"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_account_cash(self):
        url = f"{self.base_url}/api/v0/equity/account/cash"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None

    def get_all_transactions(self):
        """
        Paginates through all transactions (deposits, withdrawals, etc)
        to calculate total invested amount.
        Uses a local JSON cache to prevent hitting the 6 requests/minute rate limit.
        Only fetches new pages until it overlaps with the cached transactions.
        """
        import os
        import json
        import urllib.parse
        import time
        
        cache_file = ".t212_cache.json"
        
        cached_txs = []
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    cached_txs = json.load(f)
            except:
                pass
                
        cached_refs = {tx.get('reference') for tx in cached_txs if tx.get('reference')}
        
        base_url_tx = f"{self.base_url}/api/v0/equity/history/transactions"
        url = base_url_tx
        params = {'limit': 50}
        
        new_transactions = []
        max_pages = 200 # High enough for ~10000 transactions, safe for rate limits
        page_count = 0
        
        last_items = []
        fallback_index = -2
        overlap_found = False
        
        while page_count < max_pages and not overlap_found:
            page_count += 1
            print(f"Fetching T212 transactions page {page_count}...")
            
            resp = requests.get(url, headers=self.headers, params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('items', [])
                
                for item in items:
                    ref = item.get('reference')
                    if ref and ref in cached_refs:
                        overlap_found = True
                        break
                    new_transactions.append(item)
                    
                last_items = items
                fallback_index = -2
                
                if overlap_found:
                    break
                
                next_page_str = data.get('nextPagePath')
                if not next_page_str:
                    break # No more pages
                
                # Just append it to avoid any double-encoding bugs with the time + character!
                url = f"{base_url_tx}?{next_page_str}"
                params = None # Wipe params since the query is inside url
                            
            elif resp.status_code == 429:
                print("T212 API limits reached, sleeping for 11.0s...")
                time.sleep(11.0)
                page_count -= 1 # Retry same page
                continue
                
            elif resp.status_code == 404:
                # The cursor transaction might have been deleted from their database!
                # Try to use an older item on the previous page as the cursor
                if last_items and abs(fallback_index) <= len(last_items):
                    fallback_item = last_items[fallback_index]
                    ref = fallback_item.get('reference')
                    dtime = fallback_item.get('dateTime')
                    
                    if ref and dtime:
                        import urllib.parse
                        encoded_time = urllib.parse.quote(dtime)
                        url = f"{base_url_tx}?limit=50&cursor={ref}&time={encoded_time}"
                        params = None
                        fallback_index -= 1
                        page_count -= 1 # retry this page index
                        continue
                
                print(f"Failed to fetch transactions. 404 and no fallbacks left.")
                break
                
            else:
                print(f"Failed to fetch transactions. Status: {resp.status_code}")
                try: print(resp.json())
                except: pass
                break
                
        if new_transactions:
            print(f"Adding {len(new_transactions)} new transactions to T212 cache.")
            merged_txs = new_transactions + cached_txs
            # Ensure no duplicates just in case
            seen = set()
            unique_txs = []
            for tx in merged_txs:
                ref = tx.get('reference')
                if ref not in seen:
                    unique_txs.append(tx)
                    if ref: seen.add(ref)
            
            unique_txs.sort(key=lambda x: x.get('dateTime', ''), reverse=True)
            
            try:
                with open(cache_file, "w") as f:
                    json.dump(unique_txs, f, indent=2)
            except Exception as e:
                print("Could not write cache", e)
            return unique_txs
            
        return cached_txs

    def calculate_dca_history(self):
        """
        Returns a DataFrame with the cumulative invested amount (DCA) over time.
        We look for 'DEPOSIT' and 'WITHDRAWAL' type transactions.
        """
        txs = self.get_all_transactions()
        if not txs:
            return pd.DataFrame()
            
        # Parse into DataFrame
        df = pd.DataFrame(txs)
        
        # Filter for deposits and withdrawals
        # T212 uses 'DEPOSIT' and 'WITHDRAW'
        df = df[df['type'].isin(['DEPOSIT', 'WITHDRAW'])].copy()
        
        # Convert amounts. Withdrawals should be negative
        df['amount'] = df['amount'].astype(float)
        df.loc[df['type'] == 'WITHDRAW', 'amount'] = -df['amount']
        
        # Sort by date
        df['dateTime'] = pd.to_datetime(df['dateTime'])
        df = df.sort_values('dateTime')
        
        # Calculate cumulative DCA
        df['cumulative_dca'] = df['amount'].cumsum()
        
        # Set datetime as index and resample to daily for smoother charts
        df.set_index('dateTime', inplace=True)
        # Resample to daily, forward fill missing days so the staircase is flat
        daily_dca = df[['cumulative_dca']].resample('D').last().ffill()
        
        # We might have days before the first deposit, fill them with 0 if any
        daily_dca = daily_dca.fillna(0)
        
        return daily_dca

    def get_total_invested(self) -> float:
        """Returns the true historical Net Deposits (Total Deposits - Total Withdrawals)"""
        # We must use history sum, as cash_data['invested'] is only the cost basis of active positions
        df = self.calculate_dca_history()
        if df.empty:
            return 0.0
        return float(df['cumulative_dca'].iloc[-1])
        
    def get_portfolio_equity(self) -> float:
        """Helper to quickly get the total equity value of the portfolio"""
        cash_data = self.get_account_cash()
        port_data = self.get_portfolio()
        
        equity = 0.0
        if cash_data:
            equity += cash_data.get('total', 0.0)
            
        if port_data:
            # sum of all current positions
            for position in port_data:
                equity += position.get('quantity', 0) * position.get('currentPrice', 0)
                
        return equity

def get_t212_client():
    if "TRADING212_API_KEY" in st.secrets and "TRADING212_API_SECRET" in st.secrets:
        key = st.secrets["TRADING212_API_KEY"]
        secret = st.secrets["TRADING212_API_SECRET"]
        return Trading212API(key, secret)
    return None

import requests
import time
import streamlit as st

@st.cache_data(ttl=3600)
def get_eth_dca(address, api_key):
    """Fetches total incoming ETH and ERC20 tokens to the address using Etherscan API"""
    if not address or not api_key:
        return {}
        
    dca_totals = {}
    
    # Need to query for native ETH transfers and ERC20 token transfers
    try:
        # 1. Native ETH txs
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=10000&sort=asc&apikey={api_key}"
        res = requests.get(url, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "1":
                for tx in data.get("result", []):
                    if tx.get("to", "").lower() == address.lower() and tx.get("isError") == "0":
                        val = float(tx.get("value", 0)) / 1e18
                        dca_totals["ETH"] = dca_totals.get("ETH", 0.0) + val
                        
        # 2. ERC-20 Token Transfers
        url2 = f"https://api.etherscan.io/api?module=account&action=tokentx&address={address}&startblock=0&endblock=99999999&page=1&offset=10000&sort=asc&apikey={api_key}"
        res2 = requests.get(url2, timeout=10)
        if res2.status_code == 200:
            data2 = res2.json()
            if data2.get("status") == "1":
                for tx in data2.get("result", []):
                    if tx.get("to", "").lower() == address.lower():
                        sym = tx.get("tokenSymbol", "").upper()
                        if sym in ["LINK", "ONDO", "TAO", "WTAO"]:
                            decimals = int(tx.get("tokenDecimal", 18))
                            val = float(tx.get("value", 0)) / (10**decimals)
                            name = "TAO" if sym == "WTAO" else sym
                            dca_totals[name] = dca_totals.get(name, 0.0) + val
                            
    except Exception as e:
        print(f"Error fetching ETH DCA: {e}")
        
    return dca_totals

@st.cache_data(ttl=3600)
def get_sol_dca(address):
    """Fetches total incoming SOL to the address using Solana RPC with pagination"""
    if not address:
        return {}
        
    RPC_URL = "https://api.mainnet-beta.solana.com"
    total_sol = 0.0
    
    try:
        last_signature = None
        has_more = True
        
        while has_more:
            # 1. Get recent signatures
            payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getSignaturesForAddress",
                "params": [address, {"limit": 1000}]
            }
            if last_signature:
                payload["params"][1]["before"] = last_signature
                
            res = requests.post(RPC_URL, json=payload, timeout=10)
            if res.status_code != 200:
                break
                
            sigs_data = res.json()
            signatures = [s["signature"] for s in sigs_data.get("result", [])]
            
            if not signatures:
                break
                
            last_signature = signatures[-1]
            if len(signatures) < 1000:
                has_more = False
            
            # 2. Get transaction details in batches
            batch_payload = []
            for i, sig in enumerate(signatures):
                batch_payload.append({
                    "jsonrpc": "2.0", "id": i,
                    "method": "getTransaction",
                    "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
                })
            
            # Split into smaller chunks to avoid RPC payload size limits
            chunk_size = 50
            for i in range(0, len(batch_payload), chunk_size):
                chunk = batch_payload[i:i+chunk_size]
                retries = 3
                while retries > 0:
                    try:
                        tx_res = requests.post(RPC_URL, json=chunk, timeout=15)
                        if tx_res.status_code == 200:
                            for tx_data in tx_res.json():
                                res_obj = tx_data.get("result")
                                if res_obj and res_obj.get("meta"):
                                    meta = res_obj["meta"]
                                    if meta.get("err") is None: # Only successful txs
                                        pre_bals = meta.get("preBalances", [])
                                        post_bals = meta.get("postBalances", [])
                                        
                                        # Find user's index in account keys
                                        account_keys = res_obj.get("transaction", {}).get("message", {}).get("accountKeys", [])
                                        user_idx = -1
                                        for idx, key in enumerate(account_keys):
                                            if isinstance(key, dict) and key.get("pubkey") == address:
                                                user_idx = idx
                                                break
                                            elif isinstance(key, str) and key == address:
                                                user_idx = idx
                                                break
                                                
                                        if user_idx >= 0 and user_idx < len(pre_bals) and user_idx < len(post_bals):
                                            delta = post_bals[user_idx] - pre_bals[user_idx]
                                            if delta > 0: # Only incoming transfers 
                                                # We apply a small heuristic to ignore tiny rent-exemption spam
                                                if delta > 10000: 
                                                    total_sol += (delta / 1e9)
                            break # Success, exit retry loop
                        elif tx_res.status_code == 429:
                            time.sleep(2)
                            retries -= 1
                        else:
                            break
                    except Exception as e:
                        time.sleep(2)
                        retries -= 1
                        if retries == 0:
                            print(f"Solana chunk error: {e}")
                    
    except Exception as e:
        print(f"Error fetching SOL DCA: {e}")
        
    if total_sol > 0:
        return {"SOL": total_sol}
    return {}

@st.cache_data(ttl=3600)
def get_tao_dca(address, api_key):
    """Fetches total incoming TAO to the address using Taostats API with pagination"""
    if not address or not api_key:
        return {}
        
    headers = {"Authorization": api_key}
    total_tao = 0.0
    
    try:
        page = 1
        while page <= 50:
            url = f"https://api.taostats.io/api/transfer/v1?address={address}&limit=100&page={page}"
            res = requests.get(url, headers=headers, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                transfers = data.get("data", [])
                if not transfers:
                    break # No more data
                    
                for tx in transfers:
                    to_addr = tx.get("to", {}).get("ss58", "")
                    if to_addr == address:
                        val = float(tx.get("amount", "0")) / 1e9
                        total_tao += val
                
                # Check pagination bounds
                pagination = data.get("pagination", {})
                if page >= pagination.get("pages", 1):
                    break
                    
                page += 1
            else:
                break
                
        if total_tao > 0:
            return {"TAO": total_tao}
            
    except Exception as e:
        print(f"Error fetching TAO DCA: {e}")
        
    return {}

def get_crypto_dca_totals(secrets):
    """
    Fetches the total incoming amount (DCA) for each supported crypto.
    Returns a dictionary of amounts e.g. { 'ETH': 1.5, 'SOL': 100, 'TAO': 50, 'LINK': 500 }
    """
    dca_totals = {}
    
    def merge_dict(d):
        for k, v in d.items():
            name = k
            if name == 'WTAO': name = 'TAO' # normalize wrapped TAO on ETH if it exists
            dca_totals[name] = dca_totals.get(name, 0.0) + v

    # ETH (and ERC20s)
    eth_addr = secrets.get("LEDGER_ETH_ADDRESS", "")
    eth_key = secrets.get("ETHERSCAN_API_KEY", "")
    if eth_addr and eth_key:
        merge_dict(get_eth_dca(eth_addr, eth_key))
        
    # SOL
    sol_addr = secrets.get("LEDGER_SOL_ADDRESS", "")
    if sol_addr:
        merge_dict(get_sol_dca(sol_addr))
        
    # TAO
    tao_addr = secrets.get("LEDGER_TAO_ADDRESS", "")
    tao_key = secrets.get("TAOSTATS_API_KEY", "")
    if tao_addr and tao_key:
        merge_dict(get_tao_dca(tao_addr, tao_key))
        
    return dca_totals

import pandas as pd
import streamlit as st
import yfinance as yf

@st.cache_data(ttl=3600*24)
def analyze_company(ticker, period="Annual"):
    """
    Fetches Fundamental data via Yahoo Finance to calculate:
    1. Trend Check (Operating Leverage)
    2. Survival Check (Liquidity)
    3. Reality Check (Quality of Earnings)
    
    Supports "Annual" and "Quarterly (YoY)" periods.
    """
    try:
        t = yf.Ticker(ticker)
        
        # Yahoo Finance returns DataFrames where columns are Dates
        if period in ["Quarterly (YoY)", "Quarterly (QoQ)"]:
            is_df = t.quarterly_income_stmt
            bs_df = t.quarterly_balance_sheet
            cf_df = t.quarterly_cashflow
        else:
            is_df = t.income_stmt
            bs_df = t.balance_sheet
            cf_df = t.cashflow
        
        # If the financials don't exist for the ticker, yf often returns an empty dataframe or None
        if is_df is None or bs_df is None or cf_df is None or is_df.empty or bs_df.empty or cf_df.empty:
            st.error(f"⚠️ No se encontraron suficientes estados financieros anuales en Yahoo Finance para {ticker}.")
            return None
            
        # Transpose so Dates are rows
        is_df = is_df.T
        bs_df = bs_df.T
        cf_df = cf_df.T
        
        # Merge on Date index
        df = is_df.join(bs_df, how='inner', rsuffix='_bs')
        df = df.join(cf_df, how='inner', rsuffix='_cf')
        
        if df.empty:
            return None
            
        df = df.sort_index(ascending=True) # Sort oldest to newest
        df = df.reset_index().rename(columns={'index': 'date'})
        
        # =========================================================
        # 1. Trend & Growth Checks: Operating Leverage & Growth %
        # =========================================================
        rev_col = 'Total Revenue' if 'Total Revenue' in df.columns else 'Operating Revenue'
        op_inc_col = 'Operating Income' if 'Operating Income' in df.columns else 'EBIT'
        ni_col = 'Net Income'
        
        # Initialize changes to None
        df['Revenue_Change'] = None
        df['Operating_Income_Change'] = None
        df['Net_Income_Change'] = None
        df['Operating_Leverage'] = None

        if rev_col in df.columns and op_inc_col in df.columns:
            def calc_abs_growth(series, periods=1):
                """Calculates (Current - Past) / abs(Past) to handle negative base numbers correctly."""
                past = series.shift(periods)
                return (series - past) / past.abs()

            if period == "Quarterly (YoY)":
                if len(df) < 5:
                    st.warning(f"⚠️ No hay suficiente histórico trimestral para {ticker} (se requieren al menos 5 trimestres para YoY).")
                else:
                    df['Revenue_Change'] = calc_abs_growth(df[rev_col], 4)
                    df['Operating_Income_Change'] = calc_abs_growth(df[op_inc_col], 4)
                    if ni_col in df.columns: df['Net_Income_Change'] = calc_abs_growth(df[ni_col], 4)
            elif period == "Quarterly (QoQ)":
                if len(df) < 2:
                    st.warning(f"⚠️ No hay suficiente histórico trimestral para {ticker} (se requieren al menos 2 trimestres para QoQ).")
                else:
                    df['Revenue_Change'] = calc_abs_growth(df[rev_col], 1)
                    df['Operating_Income_Change'] = calc_abs_growth(df[op_inc_col], 1)
                    if ni_col in df.columns: df['Net_Income_Change'] = calc_abs_growth(df[ni_col], 1)
            else:
                df['Revenue_Change'] = calc_abs_growth(df[rev_col], 1)
                df['Operating_Income_Change'] = calc_abs_growth(df[op_inc_col], 1)
                if ni_col in df.columns: df['Net_Income_Change'] = calc_abs_growth(df[ni_col], 1)
                
            def calc_leverage(rev_chg, op_chg):
                if pd.isna(rev_chg) or pd.isna(op_chg) or rev_chg == 0: return None
                return op_chg / rev_chg
                
            df['Operating_Leverage'] = df.apply(lambda row: calc_leverage(row['Revenue_Change'], row['Operating_Income_Change']), axis=1)
            
        # =========================================================
        # 2. Survival Check: Liquidity Ratio
        # (Cash + ST Inv) / Current Liab
        # =========================================================
        # Try primary keys, fallback to alternatives
        cash_col = 'Cash And Cash Equivalents'
        st_inv_col = 'Other Short Term Investments'
        curr_liab_col = 'Current Liabilities'
        
        cash = df[cash_col] if cash_col in df.columns else df.get('Cash Financial', pd.Series([0]*len(df)))
        st_inv = df[st_inv_col] if st_inv_col in df.columns else pd.Series([0]*len(df))
        curr_liab = df[curr_liab_col] if curr_liab_col in df.columns else df.get('Total Liabilities Net Minority Interest', pd.Series([1]*len(df)))
        
        try:
            df['Liquidity_Ratio'] = (cash.fillna(0) + st_inv.fillna(0)) / curr_liab
        except:
            df['Liquidity_Ratio'] = None
            
        # =========================================================
        # 3. Reality Check: Earnings Quality
        # FCF / Net Income
        # =========================================================
        fcf_col = 'Free Cash Flow'
        ni_col = 'Net Income'
        
        if fcf_col in df.columns and ni_col in df.columns:
            def calc_quality(fcf, ni):
                if pd.isna(fcf) or pd.isna(ni) or ni == 0: return None
                return fcf / ni
            df['Earnings_Quality'] = df.apply(lambda row: calc_quality(row[fcf_col], row[ni_col]), axis=1)
            df['FCF'] = df[fcf_col]
        else:
            df['Earnings_Quality'] = None
            df['FCF'] = None
            
        # Long Term Debt extraction
        if 'Long Term Debt' in df.columns:
            df['Long_Term_Debt'] = df['Long Term Debt']
        elif 'Total Debt' in df.columns:
            df['Long_Term_Debt'] = df['Total Debt']
        else:
            df['Long_Term_Debt'] = None
            
        latest = df.iloc[-1]
        date_str = latest['date'].strftime('%Y-%m-%d') if pd.notna(latest['date']) else "Latest"
        
        # Calculate shift periods for previous values
        shift_periods = 4 if period == "Quarterly (YoY)" else 1
        
        # Helper to get shifted value
        def get_prev(col):
            if col in df.columns and len(df) > shift_periods:
                return df[col].shift(shift_periods).iloc[-1]
            return None

        return {
            'df': df,
            'latest': {
                'date': date_str,
                'Operating_Leverage': latest.get('Operating_Leverage', None),
                'Prev_Operating_Leverage': get_prev('Operating_Leverage'),
                'Liquidity_Ratio': latest.get('Liquidity_Ratio', None),
                'Prev_Liquidity_Ratio': get_prev('Liquidity_Ratio'),
                'Earnings_Quality': latest.get('Earnings_Quality', None),
                'Prev_Earnings_Quality': get_prev('Earnings_Quality'),
                'Revenue_Change': latest.get('Revenue_Change', None),
                'Net_Income_Change': latest.get('Net_Income_Change', None),
                'Revenue': latest.get(rev_col, None) if rev_col in df.columns else None,
                'Prev_Revenue': get_prev(rev_col) if rev_col in df.columns else None,
                'Net_Income': latest.get(ni_col, None) if ni_col in df.columns else None,
                'Prev_Net_Income': get_prev(ni_col) if ni_col in df.columns else None
            }
        }
    except Exception as e:
        st.error(f"Error procesando fundamentales para {ticker} en Yahoo Finance: {e}")
        return None

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

def add_range_selector(fig, period="daily"):
    """
    Adds range selector buttons with SPECIFIC order (Left to Right):
    Order: Histórico, 1 Year, 6 Months, 1 Month.
    """
    
    buttons = []
    default_range_days = None # None means 'History' / Auto-range
    
    # Common Buttons
    btn_hist = dict(step="all", label="Histórico")
    btn_1y = dict(count=1, label="1Y", step="year", stepmode="backward")
    btn_6m = dict(count=6, label="6M", step="month", stepmode="backward")
    btn_1m = dict(count=1, label="1M", step="month", stepmode="backward")
    btn_5y = dict(count=5, label="5Y", step="year", stepmode="backward") # Useful for long macro
    
    if period == "daily" or period == "daily_hist":
        # Yield, DXY, BTC/Gold
        # Default: Hist. Options: Hist, 1Y, 6M, 1M
        buttons = [btn_hist, btn_1y, btn_6m, btn_1m]
        default_range_days = None # All/Auto

    elif period == "weekly":
        # Liquidity, Stress
        # Default: 1Y. Options: Hist, 5Y, 1Y, 6M
        buttons = [btn_hist, btn_5y, btn_1y, btn_6m]
        default_range_days = 365 
        
    elif period == "monthly" or period == "monthly_hist":
        # Ind Prod, M2, Philly
        # Default: Hist. Options: Hist, 5Y, 1Y
        buttons = [btn_hist, btn_5y, btn_1y]
        default_range_days = None # All/Auto
        
    elif period == "daily_rrp" or period == "daily_break":
        # Reverse Repo & Breakeven
        # Request: 5 años, 1 año (y Historico)
        # Previous: 1W, 1M, Hist
        buttons = [btn_hist, btn_5y, btn_1y]
        default_range_days = None
        
    elif period == "weekly_tga":
        # TGA
        # Request: 6M, Histórico.
        buttons = [btn_hist, btn_6m]
        default_range_days = None 
    
    fig.update_xaxes(
        rangeslider_visible=False,
        rangeselector=dict(
            buttons=buttons,
            bgcolor="white",
            activecolor="#00F0FF",
            font=dict(color="black") 
        )
    )
    
    # Set default range View
    if default_range_days is not None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=default_range_days)
        fig.update_xaxes(range=[start_date, end_date])
    else:
        fig.update_xaxes(autorange=True)
        
    return fig

def create_liquidity_chart(df):
    """
    Creates a dual-axis chart for Net Liquidity and BTC Price.
    Frequency: WEEKLY -> Period 'weekly' (1Y Default)
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Net Liquidity Trace
    fig.add_trace(
        go.Scatter(x=df.index, y=df['Net_Liquidity_Billions'], name="Net Liquidity (Billions)",
                   line=dict(color='#00F0FF', width=2)),
        secondary_y=False,
    )

    # BTC Price Trace
    fig.add_trace(
        go.Scatter(x=df.index, y=df['BTC_Price'], name="BTC Price",
                   line=dict(color='#FF9900', width=2)),
        secondary_y=True,
    )

    fig.update_layout(
        title_text="Net Liquidity vs Bitcoin",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="Net Liquidity (B$)", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text="BTC Price ($)", secondary_y=True, showgrid=False)

    fig = add_range_selector(fig, period="weekly")
    return fig

def create_industrial_chart(df):
    """
    Combined Chart. Frequency: MONTHLY -> Period 'monthly' (Hist Default)
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        subplot_titles=("Philly Fed Manufacturing Index", "Industrial Production"))

    colors = ['#00CC66' if val > 0 else '#FF3333' for val in df['Philly_Fed']]
    
    fig.add_trace(
        go.Bar(x=df.index, y=df['Philly_Fed'], name="Philly Fed", marker_color=colors),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['Industrial_Production'], name="Industrial Production",
                   line=dict(color='#A0A0A0')),
        row=2, col=1
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=500,
        showlegend=False
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="white", row=1, col=1)

    fig = add_range_selector(fig, period="monthly")
    return fig

def create_philly_chart(df):
    """
    Creates a simple Bar chart for Philly Fed. Frequency: MONTHLY -> Period 'monthly' (Hist Default)
    """
    fig = go.Figure()
    colors = ['#00CC66' if val > 0 else '#FF3333' for val in df['Philly_Fed']]
    
    fig.add_trace(go.Bar(x=df.index, y=df['Philly_Fed'], name="Philly Fed", marker_color=colors))
    
    fig.update_layout(
        title_text="Philly Fed Index",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300,
        showlegend=False
    )
    fig.add_hline(y=0, line_dash="dash", line_color="white")
    
    fig = add_range_selector(fig, period="monthly")
    return fig

def create_ind_prod_chart(df):
    """
    Creates a Line chart for Industrial Production. Frequency: MONTHLY -> Period 'monthly' (Hist Default)
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Industrial_Production'], name="Ind Prod",
                   line=dict(color='#A0A0A0')))
    
    fig.update_layout(
        title_text="Industrial Production",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        height=300,
        showlegend=False
    )
    
    fig = add_range_selector(fig, period="monthly")
    return fig


def create_m2_chart(df):
    """
    Creates a Line chart for M2 Money Supply YoY %. Frequency: MONTHLY -> Period 'monthly' (Hist Default)
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['M2_YoY'], name="M2 YoY %",
                             line=dict(color='#00FF00', width=2)))
    
    fig.update_layout(
        title_text="M2 Money Supply (YoY %)",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        height=300,
        showlegend=False
    )
    
    fig = add_range_selector(fig, period="monthly")
    return fig

def create_btc_gold_chart(df):
    """
    Creates a Line chart for BTC/Gold Ratio. Frequency: DAILY -> Period 'daily' (Hist Default)
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Ratio'], name="BTC/Gold Ratio",
                             line=dict(color='#FFD700', width=2)))
    
    fig.update_layout(
        title_text="BTC / Gold Ratio",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    
    fig = add_range_selector(fig, period="daily")
    return fig

def create_generic_line_chart(df, title, y_col, color='#00F0FF', period="daily"):
    """
    Generic Line Chart for single series.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[y_col], name=title,
                             line=dict(color=color, width=2)))
    
    fig.update_layout(
        title_text=title,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        height=300,
        showlegend=False
    )
    
    fig = add_range_selector(fig, period=period)
    return fig

def create_dca_staircase_chart(dca_df, current_equity, expected_total=None):
    """
    Creates a staircase chart representing the cumulative invested capital (DCA).
    Also plots a point/line for the current equity value to compare.
    If expected_total is provided and the DCA history doesn't reach it (due to API limits),
    we draw a flat line indicating the true known invested amount.
    """
    fig = go.Figure()
    
    # If we have an expected total that is higher than the last point in our history
    # it means our history is truncated.
    draw_expected = False
    if expected_total is not None and not dca_df.empty:
        last_dca_val = dca_df['cumulative_dca'].iloc[-1]
        if abs(expected_total - last_dca_val) > 1.0: # Delta > 1 euro
            draw_expected = True

    # The DCA line (Staircase)
    if draw_expected:
        # Just use a single flat line for the known total invested instead of the broken slope
        start_date = dca_df.index[0]
        end_date = dca_df.index[-1]
        fig.add_trace(go.Scatter(
            x=[start_date, end_date], 
            y=[expected_total, expected_total], 
            name="True Capital Invertido (DCA)",
            line=dict(color='#A0A0A0', width=2),
            fill='tozeroy', 
            fillcolor='rgba(160, 160, 160, 0.1)'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=dca_df.index, 
            y=dca_df['cumulative_dca'], 
            name="Capital Invertido (DCA)",
            line=dict(color='#A0A0A0', width=2, shape='hv'), # 'hv' = Horizontal, then Vertical (Staircase)
            fill='tozeroy', 
            fillcolor='rgba(160, 160, 160, 0.1)'
        ))
    
    # Current Equity Point (or just horizontal line from start to end)
    # We'll add a simple horizontal dashed line showing current value
    # so the user can see if the staircase is above or below water
    if not dca_df.empty:
        start_date = dca_df.index[0]
        end_date = dca_df.index[-1]
        
        fig.add_trace(go.Scatter(
            x=[start_date, end_date],
            y=[current_equity, current_equity],
            name="Valor Actual",
            mode="lines",
            line=dict(color='#00F0FF', width=2, dash='dash')
        ))

    fig.update_layout(
         # Empty title for layout integration
         template="plotly_dark",
         paper_bgcolor='rgba(0,0,0,0)',
         height=400,
         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # We will use the same add_range_selector since DCA is essentially "daily" history
    fig = add_range_selector(fig, period="daily")
    return fig

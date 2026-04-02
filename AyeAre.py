# src/ui/app.py
import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

from src.core.engine import ArbitrageEngine
from src.utils.logger import setup_logger

# Page configuration
st.set_page_config(
    page_title="MEV Arbitrage Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'engine' not in st.session_state:
    st.session_state.engine = ArbitrageEngine()
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'opportunities' not in st.session_state:
    st.session_state.opportunities = []

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #00ff88, #00b8ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 1rem;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/your-repo/logo.png", width=200)
    st.markdown("## 🤖 Bot Controls")
    
    # Bot control buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start Bot", use_container_width=True):
            st.session_state.bot_running = True
            st.success("Bot started!")
    with col2:
        if st.button("⏹️ Stop Bot", use_container_width=True):
            st.session_state.bot_running = False
            st.warning("Bot stopped!")
    
    st.markdown("---")
    
    # Configuration
    st.markdown("## ⚙️ Configuration")
    flash_loan_amount = st.number_input(
        "Flash Loan Amount (WETH)",
        min_value=1.0,
        max_value=5000.0,
        value=1500.0,
        step=100.0
    )
    
    min_profit = st.number_input(
        "Minimum Profit (ETH)",
        min_value=0.01,
        max_value=10.0,
        value=0.05,
        step=0.01,
        format="%.2f"
    )
    
    slippage = st.slider(
        "Slippage Tolerance (%)",
        min_value=0.1,
        max_value=5.0,
        value=0.5,
        step=0.1
    )
    
    st.markdown("---")
    
    # Statistics display
    st.markdown("## 📊 Quick Stats")
    stats = st.session_state.engine.get_statistics()
    
    st.metric("💰 Total Profit", f"{stats['total_profit']:.4f} ETH")
    st.metric("📈 Total Trades", stats['total_trades'])
    st.metric("💹 Daily Profit", f"{stats['daily_profit']:.4f} ETH")
    st.metric("⭐ Avg Profit/Trade", f"{stats['avg_profit']:.4f} ETH")

# Main content
st.markdown('<div class="main-header">🤖 MEV Arbitrage Bot Dashboard</div>', unsafe_allow_html=True)

# Real-time metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("ETH Price", "$3,200", delta="+1.2%", delta_color="normal")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("WBTC Price", "$60,000", delta="+0.8%", delta_color="normal")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    current_gas = st.session_state.engine.w3.eth.gas_price / 1e9
    st.metric("Gas Price", f"{current_gas:.1f} Gwei", delta="-2.3%")
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    status = "🟢 Active" if st.session_state.bot_running else "🔴 Stopped"
    st.metric("Bot Status", status)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💰 Execute", "📈 History", "⚙️ Settings"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Real-time Price Chart")
        
        # Create price chart
        fig = go.Figure()
        
        # Add price traces
        fig.add_trace(go.Scatter(
            x=list(range(100)),
            y=[3200 + i*2 for i in range(100)],
            mode='lines',
            name='WETH',
            line=dict(color='#00ff88', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=list(range(100)),
            y=[60000 + i*10 for i in range(100)],
            mode='lines',
            name='WBTC',
            line=dict(color='#00b8ff', width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title="Token Prices (Last 100 blocks)",
            xaxis_title="Block",
            yaxis_title="WETH Price (USD)",
            yaxis2=dict(
                title="WBTC Price (USD)",
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            template='plotly_dark'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Opportunities table
        st.subheader("Current Opportunities")
        opportunities = st.session_state.engine.find_opportunities()
        
        if opportunities:
            df = pd.DataFrame(opportunities)
            st.dataframe(
                df[['type', 'expected_profit', 'curve_rate', 'balancer_rate']],
                use_container_width=True
            )
        else:
            st.info("No arbitrage opportunities found at this moment")
    
    with col2:
        st.subheader("Market Metrics")
        
        # Arbitrage spread gauge
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = 0.8,
            title = {'text': "Arbitrage Spread (%)"},
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [None, 2]},
                'bar': {'color': "#00ff88"},
                'steps': [
                    {'range': [0, 0.5], 'color': "lightgray"},
                    {'range': [0.5, 1], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0.5
                }
            }
        ))
        
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent trades
        st.subheader("Recent Trades")
        recent_trades = st.session_state.engine.get_trade_history(5)
        if not recent_trades.empty:
            st.dataframe(
                recent_trades[['time', 'profit', 'gas_used']],
                use_container_width=True
            )

with tab2:
    st.subheader("Manual Arbitrage Execution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        execute_amount = st.number_input(
            "Amount to Flash Loan (WETH)",
            min_value=0.1,
            value=flash_loan_amount,
            step=10.0,
            key="execute_amount"
        )
        
        execute_min_profit = st.number_input(
            "Minimum Profit Required (ETH)",
            min_value=0.01,
            value=min_profit,
            step=0.01,
            key="execute_min_profit"
        )
    
    with col2:
        st.info("""
        ⚠️ **Risk Warning**
        - Ensure sufficient gas funds
        - Check market conditions
        - Monitor for MEV competition
        """)
    
    if st.button("🚀 Execute Arbitrage Now", type="primary", use_container_width=True):
        with st.spinner("Executing flash loan arbitrage..."):
            # Run async execution
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                st.session_state.engine.execute_arbitrage(execute_amount, execute_min_profit)
            )
            
            if result['success']:
                st.success(f"✅ Arbitrage successful! Profit: {result['profit']:.4f} ETH")
                st.json({
                    'Transaction Hash': result['tx_hash'],
                    'Profit': f"{result['profit']:.4f} ETH",
                    'Gas Used': result['gas_used'],
                    'Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # Refresh stats
                st.rerun()
            else:
                st.error(f"❌ Arbitrage failed: {result.get('error', 'Unknown error')}")

with tab3:
    st.subheader("Trade History")
    
    # Date filter
    col1, col2 = st.columns(2)
    with col1:
        days = st.selectbox("Time Range", [7, 14, 30, 90], index=0)
    with col2:
        st.write("")  # Placeholder
    
    # Load trade history
    trades_df = st.session_state.engine.get_trade_history(limit=1000)
    
    if not trades_df.empty:
        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days)
        trades_df['time'] = pd.to_datetime(trades_df['time'])
        filtered_df = trades_df[trades_df['time'] >= cutoff_date]
        
        # Profit chart
        fig = px.line(
            filtered_df,
            x='time',
            y='profit',
            title='Profit Over Time',
            labels={'profit': 'Profit (ETH)', 'time': 'Time'}
        )
        fig.update_layout(template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)
        
        # Trade table
        st.dataframe(
            filtered_df,
            use_container_width=True,
            column_config={
                "time": "Time",
                "profit": st.column_config.NumberColumn("Profit (ETH)", format="%.4f"),
                "gas_used": "Gas Used",
                "gas_price": st.column_config.NumberColumn("Gas Price (Gwei)", format="%.1f"),
                "tx_hash": "Transaction Hash"
            }
        )
        
        # Export button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Trade History (CSV)",
            data=csv,
            file_name=f"trade_history_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No trades executed yet")

with tab4:
    st.subheader("Bot Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Risk Parameters")
        max_position = st.number_input("Max Position Size (ETH)", min_value=100, max_value=10000, value=1500)
        max_slippage = st.number_input("Max Slippage (%)", min_value=0.1, max_value=10.0, value=1.0)
        min_liquidity = st.number_input("Min Pool Liquidity (ETH)", min_value=1000, max_value=1000000, value=100000)
        
        st.markdown("#### Gas Settings")
        max_gas_price = st.number_input("Max Gas Price (Gwei)", min_value=10, max_value=1000, value=200)
        gas_multiplier = st.slider("Gas Price Multiplier", 1.0, 2.0, 1.2, 0.1)
    
    with col2:
        st.markdown("#### Notification Settings")
        email_notifications = st.checkbox("Email Notifications")
        if email_notifications:
            email = st.text_input("Email Address")
        
        telegram_notifications = st.checkbox("Telegram Notifications")
        if telegram_notifications:
            telegram_bot = st.text_input("Telegram Bot Token", type="password")
            telegram_chat = st.text_input("Telegram Chat ID")
        
        st.markdown("#### Auto-Execution")
        auto_execute = st.checkbox("Enable Auto-Execution")
        if auto_execute:
            check_interval = st.number_input("Check Interval (seconds)", min_value=1, max_value=60, value=5)
    
    if st.button("💾 Save Settings", type="primary"):
        st.success("Settings saved successfully!")
        # Save settings to database or file

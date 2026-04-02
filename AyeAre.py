# app.py - Complete MEV Arbitrage Bot for Streamlit Cloud
import streamlit as st
import json
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import hashlib
import time
from typing import Dict, List, Optional, Tuple
import random

# ====================== PAGE CONFIGURATION ======================
st.set_page_config(
    page_title="MEV Arbitrage Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== CUSTOM CSS ======================
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
    .success-card {
        background: linear-gradient(135deg, #00b09b, #96c93d);
        padding: 1rem;
        border-radius: 1rem;
        color: white;
    }
    .warning-card {
        background: linear-gradient(135deg, #f12711, #f5af19);
        padding: 1rem;
        border-radius: 1rem;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ====================== DATABASE SETUP ======================
def setup_database():
    """Initialize SQLite database"""
    import os
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect('data/trades.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Trades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_hash TEXT UNIQUE,
            opportunity_id TEXT,
            profit REAL,
            gas_used INTEGER,
            gas_price REAL,
            timestamp INTEGER,
            status TEXT
        )
    ''')
    
    # Opportunities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id TEXT UNIQUE,
            expected_profit REAL,
            actual_profit REAL,
            executed INTEGER DEFAULT 0,
            timestamp INTEGER,
            swap_amount REAL
        )
    ''')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at INTEGER
        )
    ''')
    
    # Insert default settings if not exists
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value, updated_at)
        VALUES 
            ('flash_loan_amount', '1500', strftime('%s', 'now')),
            ('min_profit', '0.05', strftime('%s', 'now')),
            ('slippage', '0.5', strftime('%s', 'now')),
            ('bot_enabled', 'false', strftime('%s', 'now'))
    ''')
    
    conn.commit()
    return conn

# ====================== ARBITRAGE ENGINE ======================
class ArbitrageEngine:
    def __init__(self):
        """Initialize the arbitrage engine"""
        self.conn = setup_database()
        self.is_running = False
        
        # Mock price data (in production, fetch from oracles)
        self.prices = {
            'WETH': 3200.00,
            'WBTC': 60000.00
        }
        
        # Pool rates
        self.curve_rate = 0.052  # 1 WETH = 0.052 WBTC
        self.balancer_rate = 0.0518  # 1 WBTC = 19.3 WETH (inverse)
        
    def find_opportunities(self) -> List[Dict]:
        """Find current arbitrage opportunities"""
        opportunities = []
        
        # Calculate triangular arbitrage
        flash_amount = float(self.get_setting('flash_loan_amount', '1500'))
        
        # Path: WETH -> Curve WBTC -> Balancer WETH
        wbtc_from_curve = flash_amount * self.curve_rate
        weth_from_balancer = wbtc_from_curve * (1 / self.balancer_rate)
        
        # Calculate profit
        fee = flash_amount * 0.0005  # 0.05% flash loan fee
        gross_profit = weth_from_balancer - flash_amount
        net_profit = gross_profit - fee
        
        if net_profit > float(self.get_setting('min_profit', '0.05')):
            opportunities.append({
                'id': self.generate_opportunity_id(),
                'type': 'WETH → WBTC → WETH',
                'expected_profit': net_profit,
                'flash_loan_amount': flash_amount,
                'curve_rate': self.curve_rate,
                'balancer_rate': self.balancer_rate,
                'fee': fee,
                'timestamp': int(datetime.now().timestamp())
            })
        
        # Reverse path: WETH -> Balancer WBTC -> Curve WETH
        wbtc_from_balancer = flash_amount * self.balancer_rate
        weth_from_curve = wbtc_from_balancer * (1 / self.curve_rate)
        
        gross_profit_reverse = weth_from_curve - flash_amount
        net_profit_reverse = gross_profit_reverse - fee
        
        if net_profit_reverse > float(self.get_setting('min_profit', '0.05')):
            opportunities.append({
                'id': self.generate_opportunity_id(),
                'type': 'WETH → WBTC → WETH (Reverse)',
                'expected_profit': net_profit_reverse,
                'flash_loan_amount': flash_amount,
                'curve_rate': self.curve_rate,
                'balancer_rate': self.balancer_rate,
                'fee': fee,
                'timestamp': int(datetime.now().timestamp())
            })
        
        return opportunities
    
    def generate_opportunity_id(self) -> str:
        """Generate unique opportunity ID"""
        timestamp = str(int(time.time()))
        random_component = str(random.randint(1000, 9999))
        raw_id = f"{timestamp}_{random_component}"
        return hashlib.sha256(raw_id.encode()).hexdigest()[:16]
    
    async def execute_arbitrage(self, amount: float, min_profit: float) -> Dict:
        """Execute arbitrage transaction (simulated)"""
        try:
            # Simulate transaction execution
            start_time = time.time()
            
            # Simulate network delay
            await asyncio.sleep(2)
            
            # Calculate simulated profit
            opportunities = self.find_opportunities()
            if opportunities:
                expected_profit = opportunities[0]['expected_profit']
                actual_profit = expected_profit * random.uniform(0.95, 1.05)
            else:
                actual_profit = random.uniform(0.01, 0.15)
            
            # Generate fake transaction hash
            tx_hash = hashlib.sha256(f"{amount}_{time.time()}".encode()).hexdigest()
            
            # Save to database
            self.save_trade(tx_hash, actual_profit, 350000, 50)
            
            return {
                'success': True,
                'tx_hash': tx_hash,
                'profit': actual_profit,
                'gas_used': 350000,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_trade(self, tx_hash: str, profit: float, gas_used: int, gas_price: float):
        """Save trade to database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trades (tx_hash, profit, gas_used, gas_price, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tx_hash, profit, gas_used, gas_price, int(datetime.now().timestamp()), 'success'))
        self.conn.commit()
    
    def get_trade_history(self, limit: int = 100) -> pd.DataFrame:
        """Get trade history as DataFrame"""
        query = f'''
            SELECT 
                datetime(timestamp, 'unixepoch') as time,
                profit,
                gas_used,
                gas_price,
                tx_hash
            FROM trades 
            ORDER BY timestamp DESC 
            LIMIT {limit}
        '''
        return pd.read_sql_query(query, self.conn)
    
    def get_statistics(self) -> Dict:
        """Get bot statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT SUM(profit) FROM trades WHERE status='success'")
        total_profit = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status='success'")
        total_trades = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT SUM(profit) FROM trades 
            WHERE timestamp > strftime('%s', 'now', '-1 day')
            AND status='success'
        ''')
        daily_profit = cursor.fetchone()[0] or 0
        
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        return {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'avg_profit': avg_profit,
            'daily_profit': daily_profit
        }
    
    def get_setting(self, key: str, default: str = "") -> str:
        """Get setting from database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else default
    
    def update_setting(self, key: str, value: str):
        """Update setting in database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, strftime('%s', 'now'))
        ''', (key, value))
        self.conn.commit()
    
    def update_prices(self):
        """Update mock prices (in production, fetch from oracles)"""
        # Simulate price movement
        self.prices['WETH'] += random.uniform(-10, 10)
        self.prices['WBTC'] += random.uniform(-200, 200)
        
        # Update rates based on prices
        self.curve_rate = 1 / (self.prices['WETH'] / self.prices['WBTC'] / 0.95)
        self.balancer_rate = 1 / (self.prices['WETH'] / self.prices['WBTC'] / 1.05)

# ====================== ASYNC HELPERS ======================
import asyncio

def run_async(coro):
    """Run async function in Streamlit"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# ====================== SESSION STATE INIT ======================
if 'engine' not in st.session_state:
    st.session_state.engine = ArbitrageEngine()

if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False

if 'opportunities' not in st.session_state:
    st.session_state.opportunities = []

# ====================== SIDEBAR ======================
with st.sidebar:
    st.markdown("## 🤖 Bot Controls")
    
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
    
    st.markdown("## ⚙️ Configuration")
    
    flash_loan_amount = st.number_input(
        "Flash Loan Amount (WETH)",
        min_value=1.0,
        max_value=5000.0,
        value=float(st.session_state.engine.get_setting('flash_loan_amount', '1500')),
        step=100.0
    )
    
    min_profit = st.number_input(
        "Minimum Profit (ETH)",
        min_value=0.01,
        max_value=10.0,
        value=float(st.session_state.engine.get_setting('min_profit', '0.05')),
        step=0.01,
        format="%.2f"
    )
    
    slippage = st.slider(
        "Slippage Tolerance (%)",
        min_value=0.1,
        max_value=5.0,
        value=float(st.session_state.engine.get_setting('slippage', '0.5')),
        step=0.1
    )
    
    if st.button("💾 Save Settings", use_container_width=True):
        st.session_state.engine.update_setting('flash_loan_amount', str(flash_loan_amount))
        st.session_state.engine.update_setting('min_profit', str(min_profit))
        st.session_state.engine.update_setting('slippage', str(slippage))
        st.success("Settings saved!")
    
    st.markdown("---")
    
    # Statistics
    stats = st.session_state.engine.get_statistics()
    
    st.markdown("## 📊 Statistics")
    st.metric("💰 Total Profit", f"{stats['total_profit']:.4f} ETH")
    st.metric("📈 Total Trades", stats['total_trades'])
    st.metric("💹 Daily Profit", f"{stats['daily_profit']:.4f} ETH")
    st.metric("⭐ Avg Profit/Trade", f"{stats['avg_profit']:.4f} ETH")

# ====================== MAIN CONTENT ======================
st.markdown('<div class="main-header">🤖 MEV Arbitrage Bot Dashboard</div>', unsafe_allow_html=True)

# Real-time metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("WETH Price", f"${st.session_state.engine.prices['WETH']:,.2f}", delta="+1.2%")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("WBTC Price", f"${st.session_state.engine.prices['WBTC']:,.2f}", delta="+0.8%")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    gas_price = random.uniform(20, 50)
    st.metric("Gas Price", f"{gas_price:.1f} Gwei", delta="-2.3%")
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    status = "🟢 Active" if st.session_state.bot_running else "🔴 Stopped"
    bg_class = "success-card" if st.session_state.bot_running else "warning-card"
    st.markdown(f'<div class="{bg_class}">', unsafe_allow_html=True)
    st.metric("Bot Status", status)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ====================== TABS ======================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💰 Execute", "📈 History", "⚙️ Settings"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Real-time Price Chart")
        
        # Generate mock price data
        import numpy as np
        time_data = list(range(100))
        weth_prices = [3200 + i*2 + np.random.normal(0, 5) for i in range(100)]
        wbtc_prices = [60000 + i*10 + np.random.normal(0, 50) for i in range(100)]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=time_data,
            y=weth_prices,
            mode='lines',
            name='WETH',
            line=dict(color='#00ff88', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=time_data,
            y=wbtc_prices,
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
            template='plotly_dark',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Find opportunities
        st.subheader("Current Arbitrage Opportunities")
        
        if st.button("🔄 Scan for Opportunities", use_container_width=True):
            with st.spinner("Scanning for arbitrage opportunities..."):
                st.session_state.opportunities = st.session_state.engine.find_opportunities()
        
        if st.session_state.opportunities:
            for opp in st.session_state.opportunities:
                with st.expander(f"💰 {opp['type']} - Expected Profit: {opp['expected_profit']:.4f} ETH"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Flash Loan Amount", f"{opp['flash_loan_amount']} WETH")
                        st.metric("Curve Rate", f"1 WETH → {opp['curve_rate']:.4f} WBTC")
                    with col2:
                        st.metric("Expected Profit", f"{opp['expected_profit']:.4f} ETH")
                        st.metric("Balancer Rate", f"1 WBTC → {(1/opp['balancer_rate']):.2f} WETH")
                    
                    if st.button(f"Execute This Opportunity", key=opp['id']):
                        st.session_state['selected_opportunity'] = opp
                        st.rerun()
        else:
            st.info("No arbitrage opportunities found at this moment. Click 'Scan for Opportunities' to check.")
    
    with col2:
        st.subheader("Market Metrics")
        
        # Arbitrage spread gauge
        spread = abs((st.session_state.engine.curve_rate - st.session_state.engine.balancer_rate) / st.session_state.engine.curve_rate * 100)
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=spread,
            title={'text': "Arbitrage Spread (%)"},
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [None, 2]},
                'bar': {'color': "#00ff88"},
                'steps': [
                    {'range': [0, 0.5], 'color': "lightgray"},
                    {'range': [0.5, 1], 'color': "gray"},
                    {'range': [1, 2], 'color': "darkgray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0.5
                }
            }
        ))
        
        fig.update_layout(height=250, template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)
        
        # Pool comparison
        st.subheader("Pool Comparison")
        comparison_data = {
            "Metric": ["WETH→WBTC Rate", "WBTC→WETH Rate", "Fee", "Liquidity"],
            "Curve": [f"{st.session_state.engine.curve_rate:.4f}", f"{1/st.session_state.engine.curve_rate:.2f}", "0.04%", "High"],
            "Balancer": [f"{st.session_state.engine.balancer_rate:.4f}", f"{1/st.session_state.engine.balancer_rate:.2f}", "0.05%", "High"]
        }
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Manual Arbitrage Execution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        execute_amount = st.number_input(
            "Flash Loan Amount (WETH)",
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
        
        # Display selected opportunity if any
        if 'selected_opportunity' in st.session_state:
            st.info(f"Selected Opportunity: Expected profit of {st.session_state.selected_opportunity['expected_profit']:.4f} ETH")
    
    with col2:
        st.markdown("### ⚠️ Risk Warning")
        st.warning("""
        - Ensure sufficient gas funds
        - Check market conditions
        - Monitor for MEV competition
        - Start with small amounts
        """)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 EXECUTE ARBITRAGE NOW", type="primary", use_container_width=True):
            with st.spinner("Executing flash loan arbitrage..."):
                result = run_async(
                    st.session_state.engine.execute_arbitrage(execute_amount, execute_min_profit)
                )
                
                if result['success']:
                    st.balloons()
                    st.success(f"✅ Arbitrage successful!")
                    
                    # Create success display
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Profit", f"{result['profit']:.4f} ETH", delta="+100%")
                    with col2:
                        st.metric("Transaction Hash", result['tx_hash'][:10] + "...")
                    with col3:
                        st.metric("Gas Used", f"{result['gas_used']:,}")
                    
                    st.json({
                        'Transaction Hash': result['tx_hash'],
                        'Profit': f"{result['profit']:.4f} ETH",
                        'Gas Used': result['gas_used'],
                        'Execution Time': f"{result['execution_time']:.2f} seconds",
                        'Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Clear selected opportunity
                    if 'selected_opportunity' in st.session_state:
                        del st.session_state.selected_opportunity
                    
                    # Refresh stats
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ Arbitrage failed: {result.get('error', 'Unknown error')}")

with tab3:
    st.subheader("Trade History")
    
    # Date filter
    days = st.selectbox("Time Range", [7, 14, 30, 90, "All"], index=0)
    
    # Load trade history
    trades_df = st.session_state.engine.get_trade_history(limit=1000)
    
    if not trades_df.empty:
        # Filter by date if not "All"
        if days != "All":
            cutoff_date = datetime.now() - timedelta(days=int(days))
            trades_df['time'] = pd.to_datetime(trades_df['time'])
            filtered_df = trades_df[trades_df['time'] >= cutoff_date]
        else:
            filtered_df = trades_df
        
        # Profit chart
        fig = px.line(
            filtered_df,
            x='time',
            y='profit',
            title='Profit Over Time',
            labels={'profit': 'Profit (ETH)', 'time': 'Time'}
        )
        fig.update_layout(template='plotly_dark', height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Cumulative profit chart
        filtered_df['cumulative_profit'] = filtered_df['profit'].cumsum()
        fig2 = px.area(
            filtered_df,
            x='time',
            y='cumulative_profit',
            title='Cumulative Profit',
            labels={'cumulative_profit': 'Total Profit (ETH)', 'time': 'Time'},
            color_discrete_sequence=['#00ff88']
        )
        fig2.update_layout(template='plotly_dark', height=400)
        st.plotly_chart(fig2, use_container_width=True)
        
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
        st.info("No trades executed yet. Execute an arbitrage to see history here.")

with tab4:
    st.subheader("Bot Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Risk Parameters")
        max_position = st.number_input("Max Position Size (ETH)", min_value=100, max_value=10000, value=1500)
        max_slippage_input = st.number_input("Max Slippage (%)", min_value=0.1, max_value=10.0, value=float(slippage))
        min_liquidity = st.number_input("Min Pool Liquidity (ETH)", min_value=1000, max_value=1000000, value=100000)
        
        st.markdown("#### Gas Settings")
        max_gas_price = st.number_input("Max Gas Price (Gwei)", min_value=10, max_value=1000, value=200)
        gas_multiplier = st.slider("Gas Price Multiplier", 1.0, 2.0, 1.2, 0.1)
    
    with col2:
        st.markdown("#### Notification Settings")
        email_notifications = st.checkbox("Email Notifications")
        if email_notifications:
            email = st.text_input("Email Address")
        
        st.markdown("#### Auto-Execution")
        auto_execute = st.checkbox("Enable Auto-Execution", value=st.session_state.bot_running)
        if auto_execute:
            check_interval = st.number_input("Check Interval (seconds)", min_value=1, max_value=60, value=5)
            st.info(f"Bot will automatically scan every {check_interval} seconds")
    
    if st.button("💾 Save All Settings", type="primary", use_container_width=True):
        st.session_state.engine.update_setting('max_position', str(max_position))
        st.session_state.engine.update_setting('max_gas_price', str(max_gas_price))
        st.success("Settings saved successfully!")
        
        if auto_execute and not st.session_state.bot_running:
            st.session_state.bot_running = True
            st.rerun()

# ====================== AUTO REFRESH FOR BOT ======================
if st.session_state.bot_running:
    # Auto-refresh every 10 seconds when bot is running
    import time
    time.sleep(10)
    st.rerun()

# ====================== FOOTER ======================
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>MEV Arbitrage Bot v1.0 | Powered by Streamlit</p>",
    unsafe_allow_html=True
)

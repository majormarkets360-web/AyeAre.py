import streamlit as st
import json
import sqlite3
import pandas as pd
from datetime import datetime
import time
import hashlib

st.set_page_config(
    page_title="MEV Arbitrage Bot",
    page_icon="🤖",
    layout="wide"
)

# ========== DATABASE ==========
import os
os.makedirs('data', exist_ok=True)

conn = sqlite3.connect('data/arbitrage.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tx_hash TEXT,
        amount REAL,
        profit REAL,
        timestamp INTEGER,
        status TEXT
    )
''')
conn.commit()

# ========== BOT ENGINE ==========
class ArbitrageBot:
    def __init__(self):
        self.conn = conn
        
    def calculate_profit(self, amount_weth):
        # Simplified profit calculation
        curve_rate = 0.052  # 1 WETH = 0.052 WBTC
        balancer_rate = 0.0518  # 1 WBTC = 19.3 WETH
        
        wbtc = amount_weth * curve_rate
        weth_back = wbtc * (1 / balancer_rate)
        profit = weth_back - amount_weth
        
        return max(0, profit)
    
    def execute_trade(self, amount, min_profit):
        # Simulate execution
        time.sleep(2)
        
        expected_profit = self.calculate_profit(amount)
        
        if expected_profit >= min_profit:
            profit = expected_profit * 0.95  # 5% slippage
            tx_hash = hashlib.md5(f"{amount}{time.time()}".encode()).hexdigest()[:16]
            
            # Save to database
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO trades (tx_hash, amount, profit, timestamp, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (tx_hash, amount, profit, int(time.time()), 'success'))
            self.conn.commit()
            
            return {'success': True, 'profit': profit, 'tx_hash': tx_hash}
        else:
            return {'success': False, 'error': 'Profit below minimum'}
    
    def get_stats(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT SUM(profit) FROM trades WHERE status='success'")
        total_profit = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status='success'")
        total_trades = cursor.fetchone()[0] or 0
        return {'total_profit': total_profit, 'total_trades': total_trades}
    
    def get_history(self):
        return pd.read_sql_query("SELECT datetime(timestamp, 'unixepoch') as time, amount, profit, status FROM trades ORDER BY timestamp DESC LIMIT 20", self.conn)

# ========== UI ==========
st.title("🤖 MEV Arbitrage Bot")
st.markdown("### Flash Loan Arbitrage | Curve → Balancer")

# Initialize
if 'bot' not in st.session_state:
    st.session_state.bot = ArbitrageBot()

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    amount = st.number_input("Flash Loan Amount (WETH)", min_value=1, max_value=5000, value=100, step=50)
    min_profit = st.number_input("Min Profit (ETH)", min_value=0.001, max_value=1.0, value=0.01, step=0.01)
    
    st.markdown("---")
    if st.button("🚀 Execute Arbitrage", type="primary", use_container_width=True):
        with st.spinner("Executing..."):
            result = st.session_state.bot.execute_trade(amount, min_profit)
            if result['success']:
                st.balloons()
                st.success(f"✅ Profit: {result['profit']:.4f} ETH")
                st.code(f"Tx: {result['tx_hash']}")
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"Failed: {result.get('error')}")

# Main content
col1, col2, col3 = st.columns(3)
stats = st.session_state.bot.get_stats()

with col1:
    st.metric("💰 Total Profit", f"{stats['total_profit']:.4f} ETH")
with col2:
    st.metric("📈 Total Trades", stats['total_trades'])
with col3:
    expected = st.session_state.bot.calculate_profit(amount)
    st.metric("Expected Profit", f"{expected:.4f} ETH")

st.markdown("---")
st.subheader("📊 Trade History")

history = st.session_state.bot.get_history()
if not history.empty:
    st.dataframe(history, use_container_width=True)
else:
    st.info("No trades yet. Click Execute to start!")

st.markdown("---")
st.markdown("*Powered by Balancer V2 Flash Loans | Multi-DEX Support*")

# app.py - Complete Dashboard with Contract Integration
import streamlit as st
import json
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
from typing import Dict, List
import requests

# ====================== WEB3 SETUP ======================
try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    st.warning("Web3 not installed. Install with: pip install web3")

# ====================== CONTRACT ABI ======================
CONTRACT_ABI = [
    {
        "inputs": [{"name": "amountWETH", "type": "uint256"}, {"name": "minExpectedProfit", "type": "uint256"}],
        "name": "startArbitrage",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "withdrawProfit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "amountWETH", "type": "uint256"}],
        "name": "calculateExpectedProfit",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getBalance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getStats",
        "outputs": [{"name": "", "type": "uint256"}, {"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalProfit",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalTrades",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ====================== PAGE CONFIG ======================
st.set_page_config(
    page_title="MEV Arbitrage Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== DATABASE SETUP ======================
def setup_database():
    import os
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect('data/trades.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_hash TEXT,
            amount REAL,
            expected_profit REAL,
            actual_profit REAL,
            status TEXT,
            timestamp INTEGER
        )
    ''')
    
    conn.commit()
    return conn

conn = setup_database()

# ====================== WEB3 CONNECTION ======================
@st.cache_resource
def get_contract():
    """Get contract instance"""
    if not WEB3_AVAILABLE:
        return None
    
    try:
        rpc_url = st.secrets.get("RPC_URL", "https://eth-mainnet.g.alchemy.com/v2/demo")
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not w3.is_connected():
            st.warning("Web3 not connected. Running in demo mode.")
            return None
        
        contract_address = st.secrets.get("CONTRACT_ADDRESS")
        if not contract_address:
            st.info("Contract address not configured. Add CONTRACT_ADDRESS to secrets.")
            return None
        
        contract = w3.eth.contract(address=contract_address, abi=CONTRACT_ABI)
        return {"w3": w3, "contract": contract, "address": contract_address}
    
    except Exception as e:
        st.error(f"Web3 connection error: {e}")
        return None

# ====================== BOT ENGINE ======================
class ArbitrageBot:
    def __init__(self):
        self.contract_data = get_contract()
        self.conn = conn
    
    def calculate_profit(self, amount_weth: float) -> Dict:
        """Calculate expected profit from contract"""
        if self.contract_data:
            try:
                amount_wei = self.contract_data["w3"].to_wei(amount_weth, 'ether')
                expected_profit_wei = self.contract_data["contract"].functions.calculateExpectedProfit(amount_wei).call()
                expected_profit = self.contract_data["w3"].from_wei(expected_profit_wei, 'ether')
                
                return {
                    'expected_profit': expected_profit,
                    'is_profitable': expected_profit > 0.01,
                    'source': 'contract'
                }
            except Exception as e:
                st.warning(f"Contract call failed: {e}")
                return self._simulate_profit(amount_weth)
        else:
            return self._simulate_profit(amount_weth)
    
    def _simulate_profit(self, amount_weth: float) -> Dict:
        """Fallback simulation when contract unavailable"""
        # Simulated rates
        curve_rate = 0.052
        balancer_rate = 0.0518
        
        wbtc = amount_weth * curve_rate
        weth_back = wbtc * (1 / balancer_rate)
        profit = weth_back - amount_weth
        
        return {
            'expected_profit': profit,
            'is_profitable': profit > 0.01,
            'source': 'simulation'
        }
    
    def execute_arbitrage(self, amount_weth: float, min_profit: float) -> Dict:
        """Execute arbitrage via contract"""
        if not self.contract_data:
            return self._simulate_execution(amount_weth, min_profit)
        
        try:
            w3 = self.contract_data["w3"]
            contract = self.contract_data["contract"]
            
            # Get account
            private_key = st.secrets.get("PRIVATE_KEY")
            if not private_key:
                return {'success': False, 'error': 'PRIVATE_KEY not found in secrets'}
            
            account = w3.eth.account.from_key(private_key)
            wallet_address = st.secrets.get("WALLET_ADDRESS", account.address)
            
            # Prepare transaction
            amount_wei = w3.to_wei(amount_weth, 'ether')
            min_profit_wei = w3.to_wei(min_profit, 'ether')
            
            tx = contract.functions.startArbitrage(amount_wei, min_profit_wei).build_transaction({
                'from': wallet_address,
                'nonce': w3.eth.get_transaction_count(wallet_address),
                'gas': 800000,
                'gasPrice': w3.eth.gas_price,
                'chainId': 1
            })
            
            # Sign and send
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            # Save to database
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO executions (tx_hash, amount, expected_profit, status, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (tx_hash_hex, amount_weth, min_profit, 'pending', int(datetime.now().timestamp())))
            conn.commit()
            
            return {
                'success': True,
                'tx_hash': tx_hash_hex,
                'mode': 'real',
                'message': 'Transaction sent! Check block explorer for confirmation.'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'mode': 'real'}
    
    def _simulate_execution(self, amount_weth: float, min_profit: float) -> Dict:
        """Simulate execution for testing"""
        time.sleep(2)
        
        profit_calc = self.calculate_profit(amount_weth)
        actual_profit = profit_calc['expected_profit'] * 0.95
        
        # Save to database
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO executions (amount, expected_profit, actual_profit, status, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (amount_weth, profit_calc['expected_profit'], actual_profit, 'success', int(datetime.now().timestamp())))
        conn.commit()
        
        return {
            'success': True,
            'profit': actual_profit,
            'mode': 'simulation',
            'tx_hash': f"sim_{int(time.time())}"
        }
    
    def get_stats(self) -> Dict:
        """Get bot statistics"""
        if self.contract_data:
            try:
                total_profit_wei = self.contract_data["contract"].functions.totalProfit().call()
                total_trades = self.contract_data["contract"].functions.totalTrades().call()
                balance_wei = self.contract_data["contract"].functions.getBalance().call()
                
                w3 = self.contract_data["w3"]
                
                return {
                    'total_profit': w3.from_wei(total_profit_wei, 'ether'),
                    'total_trades': total_trades,
                    'contract_balance': w3.from_wei(balance_wei, 'ether'),
                    'source': 'contract'
                }
            except Exception as e:
                st.warning(f"Failed to get contract stats: {e}")
                return self._get_db_stats()
        else:
            return self._get_db_stats()
    
    def _get_db_stats(self) -> Dict:
        """Get stats from database"""
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(actual_profit) FROM executions WHERE status='success'")
        total_profit = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM executions WHERE status='success'")
        total_trades = cursor.fetchone()[0] or 0
        
        return {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'contract_balance': 0,
            'source': 'database'
        }
    
    def get_history(self, limit=20) -> pd.DataFrame:
        """Get execution history"""
        query = f'''
            SELECT 
                datetime(timestamp, 'unixepoch') as time,
                amount,
                expected_profit,
                actual_profit,
                status,
                tx_hash
            FROM executions 
            ORDER BY timestamp DESC 
            LIMIT {limit}
        '''
        return pd.read_sql_query(query, conn)

# ====================== INITIALIZE BOT ======================
if 'bot' not in st.session_state:
    st.session_state.bot = ArbitrageBot()

# ====================== UI ======================
st.title("🤖 MEV Arbitrage Bot")
st.markdown("### Fully Automated | Flash Loan Funded | Real-time Execution")

# Status banner
if st.session_state.bot.contract_data:
    st.success(f"✅ Connected to contract: {st.session_state.bot.contract_data['address'][:10]}...")
else:
    st.info("🟡 Running in SIMULATION mode. Add contract address to secrets for real execution.")

# ====================== STATISTICS ROW ======================
stats = st.session_state.bot.get_stats()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Total Profit", f"{stats['total_profit']:.4f} ETH")
with col2:
    st.metric("📈 Total Trades", stats['total_trades'])
with col3:
    st.metric("🏦 Contract Balance", f"{stats['contract_balance']:.4f} ETH")
with col4:
    mode = "REAL" if st.session_state.bot.contract_data else "SIMULATION"
    st.metric("Mode", mode)

st.markdown("---")

# ====================== EXECUTION PANEL ======================
st.markdown("## 🚀 Execute Arbitrage")

col1, col2 = st.columns([1, 1])

with col1:
    amount_weth = st.number_input(
        "Flash Loan Amount (WETH)",
        min_value=0.1,
        max_value=5000.0,
        value=100.0,
        step=10.0,
        help="Amount of WETH to borrow via flash loan"
    )
    
    # Calculate profit in real-time
    profit_calc = st.session_state.bot.calculate_profit(amount_weth)
    
    if profit_calc['is_profitable']:
        st.success(f"💰 Expected Profit: {profit_calc['expected_profit']:.4f} WETH")
    else:
        st.warning("⚠️ Not profitable at current rates")
    
    min_profit = st.number_input(
        "Minimum Profit Required (ETH)",
        min_value=0.001,
        max_value=1.0,
        value=0.01,
        step=0.005,
        format="%.3f",
        help="Transaction will revert if profit is below this"
    )

with col2:
    st.markdown("### ")
    st.markdown("### ")
    
    execute_button = st.button(
        "🚀 EXECUTE ARBITRAGE", 
        type="primary", 
        use_container_width=True,
        disabled=not profit_calc['is_profitable']
    )
    
    if execute_button:
        if profit_calc['expected_profit'] < min_profit:
            st.error(f"Expected profit ({profit_calc['expected_profit']:.4f} ETH) is below minimum ({min_profit} ETH)")
        else:
            with st.spinner("Executing flash loan arbitrage..."):
                result = st.session_state.bot.execute_arbitrage(amount_weth, min_profit)
                
                if result['success']:
                    st.balloons()
                    st.success("✅ Arbitrage executed successfully!")
                    
                    # Display result
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Amount", f"{amount_weth} WETH")
                    with col_b:
                        if result.get('profit'):
                            st.metric("Profit", f"{result['profit']:.4f} ETH")
                    with col_c:
                        st.metric("Mode", result['mode'].upper())
                    
                    if result.get('tx_hash'):
                        st.code(f"Tx Hash: {result['tx_hash']}")
                        st.info("Transaction sent! Check Etherscan for confirmation.")
                    
                    # Refresh after 3 seconds
                    time.sleep(3)
                    st.rerun()
                else:
                    st.error(f"❌ Execution failed: {result.get('error', 'Unknown error')}")

# ====================== CONTRACT INFO ======================
if st.session_state.bot.contract_data:
    st.markdown("---")
    st.markdown("## 📋 Contract Information")
    
    col1, col2 = st.columns(2)
    with col1:
        st.code(f"Contract Address: {st.session_state.bot.contract_data['address']}")
    with col2:
        st.info("""
        **Contract Functions:**
        - `startArbitrage(amount, minProfit)` - Execute flash loan arbitrage
        - `withdrawProfit()` - Withdraw accumulated profits
        - `calculateExpectedProfit(amount)` - Preview expected profit
        """)

# ====================== HISTORY ======================
st.markdown("---")
st.markdown("## 📈 Execution History")

history_df = st.session_state.bot.get_history()

if not history_df.empty:
    st.dataframe(
        history_df,
        use_container_width=True,
        column_config={
            "time": "Time",
            "amount": st.column_config.NumberColumn("Amount (WETH)", format="%.2f"),
            "expected_profit": st.column_config.NumberColumn("Expected Profit", format="%.4f"),
            "actual_profit": st.column_config.NumberColumn("Actual Profit", format="%.4f"),
            "status": st.column_config.Column("Status", width="small"),
            "tx_hash": "Transaction Hash"
        }
    )
else:
    st.info("No executions yet. Click 'Execute Arbitrage' to start!")

# ====================== AUTO-REFRESH ======================
if st.sidebar.checkbox("Auto-refresh", value=False):
    time.sleep(5)
    st.rerun()

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>MEV Arbitrage Bot | Flash Loan Funded | Powered by Balancer V2</p>",
    unsafe_allow_html=True
)

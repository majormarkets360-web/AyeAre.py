# src/core/engine.py
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from web3 import Web3
from web3.middleware import geth_poa_middleware
import streamlit as st
import sqlite3
import pandas as pd

from src.exchanges.balancer import BalancerExchange
from src.exchanges.curve import CurveExchange
from src.utils.web3_utils import Web3Utils
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class ArbitrageEngine:
    def __init__(self):
        """Initialize the arbitrage engine"""
        self.w3 = Web3(Web3.WebsocketProvider(st.secrets["WSS_URL"]))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Initialize exchanges
        self.balancer = BalancerExchange(self.w3)
        self.curve = CurveExchange(self.w3)
        self.web3_utils = Web3Utils(self.w3)
        
        # Load contract
        self.load_contract()
        
        # Database setup
        self.setup_database()
        
        # Bot state
        self.is_running = False
        self.current_task = None
        
    def load_contract(self):
        """Load the arbitrage contract"""
        import json
        with open('contracts/abi/AutoArbitrageBot.json', 'r') as f:
            abi = json.load(f)
        
        self.contract = self.w3.eth.contract(
            address=st.secrets["CONTRACT_ADDRESS"],
            abi=abi
        )
    
    def setup_database(self):
        """Setup SQLite database for trade history"""
        self.conn = sqlite3.connect('data/trades.db', check_same_thread=False)
        cursor = self.conn.cursor()
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT UNIQUE,
                expected_profit REAL,
                actual_profit REAL,
                executed INTEGER,
                timestamp INTEGER
            )
        ''')
        self.conn.commit()
    
    def find_opportunities(self) -> List[Dict]:
        """Find current arbitrage opportunities"""
        opportunities = []
        
        try:
            # Get prices from both pools
            curve_price = self.curve.get_price(1, 0)  # WETH -> WBTC
            balancer_price = self.balancer.get_price(
                st.secrets["WBTC_ADDRESS"],
                st.secrets["WETH_ADDRESS"]
            )
            
            # Calculate arbitrage
            flash_loan_amount = float(st.secrets["FLASH_LOAN_AMOUNT"])
            expected_wbtc = curve_price * flash_loan_amount
            expected_weth = balancer_price * expected_wbtc
            
            # Calculate profit
            fee = flash_loan_amount * 0.0005  # 0.05% flash loan fee
            profit = expected_weth - flash_loan_amount - fee
            
            if profit > float(st.secrets["MIN_PROFIT"]):
                opportunities.append({
                    'type': 'WETH->WBTC->WETH',
                    'expected_profit': profit,
                    'flash_loan_amount': flash_loan_amount,
                    'curve_rate': curve_price,
                    'balancer_rate': balancer_price,
                    'timestamp': int(datetime.now().timestamp())
                })
            
        except Exception as e:
            logger.error(f"Error finding opportunities: {e}")
        
        return opportunities
    
    async def execute_arbitrage(self, amount_weth: float, min_profit: float) -> Dict:
        """Execute arbitrage transaction"""
        try:
            # Prepare transaction
            amount_wei = self.web3_utils.to_wei(amount_weth)
            min_profit_wei = self.web3_utils.to_wei(min_profit)
            deadline = int(datetime.now().timestamp()) + 300
            
            # Build transaction
            tx = await self.contract.functions.executeArbitrage(
                self.web3_utils.string_to_bytes32(f"opp_{datetime.now().timestamp()}"),
                b'',  # swap_data
                min_profit_wei,
                deadline
            ).build_transaction({
                'from': st.secrets["WALLET_ADDRESS"],
                'nonce': self.w3.eth.get_transaction_count(st.secrets["WALLET_ADDRESS"]),
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': 1
            })
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx, 
                st.secrets["PRIVATE_KEY"]
            )
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt['status'] == 1:
                # Calculate actual profit
                profit = await self.calculate_profit(tx_hash.hex())
                
                # Save to database
                self.save_trade(tx_hash.hex(), profit, receipt['gasUsed'])
                
                return {
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'profit': profit,
                    'gas_used': receipt['gasUsed']
                }
            else:
                return {
                    'success': False,
                    'error': 'Transaction failed'
                }
                
        except Exception as e:
            logger.error(f"Execution error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def calculate_profit(self, tx_hash: str) -> float:
        """Calculate actual profit from transaction"""
        # Get balance before and after
        balance_before = self.contract.functions.getBalance().call()
        
        # Wait for transaction to settle
        await asyncio.sleep(5)
        
        balance_after = self.contract.functions.getBalance().call()
        profit_wei = balance_after - balance_before
        
        return self.web3_utils.from_wei(profit_wei)
    
    def save_trade(self, tx_hash: str, profit: float, gas_used: int):
        """Save trade to database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trades (tx_hash, profit, gas_used, gas_price, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            tx_hash, 
            profit, 
            gas_used,
            float(self.w3.eth.gas_price) / 1e9,
            int(datetime.now().timestamp()),
            'success'
        ))
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
        
        # Total profit
        cursor.execute("SELECT SUM(profit) FROM trades WHERE status='success'")
        total_profit = cursor.fetchone()[0] or 0
        
        # Total trades
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status='success'")
        total_trades = cursor.fetchone()[0] or 0
        
        # Average profit
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        # Last 24h profit
        cursor.execute('''
            SELECT SUM(profit) FROM trades 
            WHERE timestamp > strftime('%s', 'now', '-1 day')
            AND status='success'
        ''')
        daily_profit = cursor.fetchone()[0] or 0
        
        return {
            'total_profit': total_profit,
            'total_trades': total_trades,
            'avg_profit': avg_profit,
            'daily_profit': daily_profit
        }

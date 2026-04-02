# scripts/setup_database.py
import sqlite3
import os

def setup_database():
    """Initialize the database with all required tables"""
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect('data/trades.db')
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
            status TEXT,
            error_message TEXT
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
            pools_used TEXT,
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
    
    # Insert default settings
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value, updated_at)
        VALUES 
            ('flash_loan_amount', '1500', strftime('%s', 'now')),
            ('min_profit', '0.05', strftime('%s', 'now')),
            ('slippage', '0.5', strftime('%s', 'now')),
            ('bot_enabled', 'false', strftime('%s', 'now'))
    ''')
    
    # Performance metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            metric_name TEXT,
            metric_value REAL
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("Database setup complete!")

if __name__ == "__main__":
    setup_database()

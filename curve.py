# src/exchanges/curve.py
from web3 import Web3
import json

class CurveExchange:
    def __init__(self, w3: Web3):
        self.w3 = w3
        
        # Curve tricrypto2 pool
        self.pool_address = "0x7F86Bf177DAd5Fc4F2e6E6b3bcAdA3ed2B0E38a5"
        
        # Load ABI
        with open('contracts/abi/curve_pool.json', 'r') as f:
            self.abi = json.load(f)
        
        self.contract = self.w3.eth.contract(
            address=self.pool_address,
            abi=self.abi
        )
    
    def get_price(self, from_index: int, to_index: int, amount: int = 10**18) -> float:
        """Get price from Curve pool"""
        try:
            # Get expected output
            expected = self.contract.functions.get_dy(
                from_index,
                to_index,
                amount
            ).call()
            
            # Convert based on decimals
            if to_index == 0:  # WBTC (8 decimals)
                return expected / 10**8
            else:  # WETH (18 decimals)
                return expected / 10**18
                
        except Exception as e:
            print(f"Error getting Curve price: {e}")
            return 0

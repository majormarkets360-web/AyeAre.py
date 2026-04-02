# scripts/deploy_contract.py
from web3 import Web3
import json
import os
from dotenv import load_dotenv

load_dotenv()

def deploy_contract():
    """Deploy the AutoArbitrageBot contract"""
    
    # Connect to Ethereum
    w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
    
    # Load account
    account = w3.eth.account.from_key(os.getenv("PRIVATE_KEY"))
    
    # Load contract bytecode and ABI
    with open('contracts/AutoArbitrageBot.sol', 'r') as f:
        contract_source = f.read()
    
    # Compile contract (simplified - use solc in production)
    # For this example, assume we have compiled bytecode
    
    bytecode = "0x..."  # Your compiled bytecode
    abi = json.loads('[...]')  # Your contract ABI
    
    # Deploy contract
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Build transaction
    transaction = contract.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': w3.eth.gas_price,
        'chainId': 1
    })
    
    # Sign transaction
    signed_txn = account.sign_transaction(transaction)
    
    # Send transaction
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    
    print(f"Deployment transaction sent: {tx_hash.hex()}")
    
    # Wait for deployment
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt['contractAddress']
    
    print(f"Contract deployed at: {contract_address}")
    
    # Save address to .env
    with open('.env', 'a') as f:
        f.write(f"\nCONTRACT_ADDRESS={contract_address}")
    
    return contract_address

if __name__ == "__main__":
    deploy_contract()

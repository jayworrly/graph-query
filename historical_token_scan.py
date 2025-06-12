from web3 import Web3
from datetime import datetime
import psycopg2
from web3.middleware import geth_poa_middleware
import time
import logging
import os
from dotenv import load_dotenv
import random
from multiprocessing import Pool, cpu_count

# Load environment variables
load_dotenv()

# Configuration
TARGET_ADDRESS = '0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e'
RPC_ENDPOINTS = [
    'https://api.avax.network/ext/bc/C/rpc',
    'https://avalanche.public-rpc.com',
    'https://rpc.ankr.com/avalanche',
    'https://avalanche-c-chain.publicnode.com'
]

# ABIs
TOKEN_CREATED_EVENT_ABI = [{
    "anonymous": False,
    "inputs": [
        {"indexed": False, "internalType": "uint256", "name": "tokenId", "type": "uint256"},
        {"components": [
            {"internalType": "uint128", "name": "curveScaler", "type": "uint128"},
            {"internalType": "uint16", "name": "a", "type": "uint16"},
            {"internalType": "uint8", "name": "b", "type": "uint8"},
            {"internalType": "bool", "name": "lpDeployed", "type": "bool"},
            {"internalType": "uint8", "name": "lpPercentage", "type": "uint8"},
            {"internalType": "uint8", "name": "salePercentage", "type": "uint8"},
            {"internalType": "uint8", "name": "creatorFeeBasisPoints", "type": "uint8"},
            {"internalType": "address", "name": "creatorAddress", "type": "address"},
            {"internalType": "address", "name": "pairAddress", "type": "address"},
            {"internalType": "address", "name": "tokenContractAddress", "type": "address"}
        ], "indexed": False, "internalType": "struct TokenManager.TokenParameters", "name": "params", "type": "tuple"},
        {"indexed": False, "internalType": "uint256", "name": "tokenSupply", "type": "uint256"}
    ],
    "name": "TokenCreated", "type": "event"
}]

TOKEN_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

PAIR_ABI = [{
    "anonymous": False,
    "inputs": [
        {"indexed": True, "internalType": "address", "name": "sender", "type": "address"},
        {"indexed": False, "internalType": "uint256", "name": "amount0", "type": "uint256"},
        {"indexed": False, "internalType": "uint256", "name": "amount1", "type": "uint256"}
    ],
    "name": "Sync", "type": "event"
}]

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.FileHandler('historical_scan.log'), logging.StreamHandler()])

class TokenScanner:
    def __init__(self):
        self.w3 = self._get_web3()
        self.event_signature = self.w3.keccak(text="TokenCreated(uint256,(uint128,uint16,uint8,bool,uint8,uint8,uint8,address,address,address),uint256)").hex()
        
    def _get_web3(self):
        """Get Web3 instance with random RPC endpoint"""
        for endpoint in random.sample(RPC_ENDPOINTS, len(RPC_ENDPOINTS)):
            try:
                w3 = Web3(Web3.HTTPProvider(endpoint))
                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                if w3.is_connected():
                    return w3
            except:
                continue
        raise Exception("Failed to connect to any RPC endpoint")
    
    def _get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(
                dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT')
            )
        except:
            return None
    
    def _get_token_details(self, token_address):
        """Get token name, symbol, decimals, and supply"""
        try:
            contract = self.w3.eth.contract(address=token_address, abi=TOKEN_ABI)
            return {
                'name': contract.functions.name().call(),
                'symbol': contract.functions.symbol().call(),
                'decimals': contract.functions.decimals().call(),
                'total_supply': contract.functions.totalSupply().call()
            }
        except:
            return {'name': 'Unknown', 'symbol': 'UNKNOWN', 'decimals': 0, 'total_supply': 0}
    
    def _save_deployment(self, conn, data):
        """Save deployment data to database"""
        with conn.cursor() as cur:
            try:
                # Insert deployment
                cur.execute("""
                    INSERT INTO token_deployments (
                        deployer_address, token_address, transaction_hash, block_number,
                        timestamp, deployer_wallet, token_name, token_symbol,
                        decimals, total_supply, deployment_value
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_hash) DO NOTHING
                """, tuple(data.values()))
                
                # Update deployer stats
                cur.execute("""
                    INSERT INTO deployer_wallets (wallet_address, first_seen_at, total_deployments, last_deployment_at)
                    VALUES (%s, %s, 1, %s)
                    ON CONFLICT (wallet_address) DO UPDATE
                    SET total_deployments = deployer_wallets.total_deployments + 1,
                        last_deployment_at = EXCLUDED.last_deployment_at
                """, (data['deployer_wallet'], data['timestamp'], data['timestamp']))
                
                conn.commit()
                return True
            except:
                conn.rollback()
                return False
    
    def _manage_scan_progress(self, block_number=None):
        """Get or update last processed block"""
        conn = self._get_db_connection()
        if not conn:
            return 63418307 if block_number is None else False
            
        with conn.cursor() as cur:
            try:
                # Create table if not exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS scan_progress (
                        id SERIAL PRIMARY KEY,
                        last_block_scanned BIGINT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                if block_number is None:  # Get last block
                    cur.execute("SELECT last_block_scanned FROM scan_progress ORDER BY id DESC LIMIT 1")
                    result = cur.fetchone()
                    if not result:
                        cur.execute("INSERT INTO scan_progress (last_block_scanned) VALUES (%s)", (63418307,))
                        conn.commit()
                        return 63418307
                    return result[0]
                else:  # Update last block
                    cur.execute("""
                        UPDATE scan_progress 
                        SET last_block_scanned = %s, last_updated = CURRENT_TIMESTAMP 
                        WHERE id = (SELECT id FROM scan_progress ORDER BY id DESC LIMIT 1)
                    """, (block_number,))
                    conn.commit()
                    return True
            except:
                return 63418307 if block_number is None else False
            finally:
                conn.close()
    
    def _get_pair_creation_time(self, pair_address):
        """Get pair creation time by finding first Sync event"""
        try:
            contract = self.w3.eth.contract(address=Web3.to_checksum_address(pair_address), abi=PAIR_ABI)
            current_block = self.w3.eth.block_number
            start_block = max(current_block - 2102400, 0)  # ~1 year ago
            
            # Search in chunks
            chunk_size = 2000
            for chunk_start in range(start_block, current_block + 1, chunk_size):
                chunk_end = min(chunk_start + chunk_size, current_block)
                try:
                    sync_events = contract.events.Sync.get_logs(fromBlock=chunk_start, toBlock=chunk_end)
                    if sync_events:
                        block = self.w3.eth.get_block(sync_events[0]['blockNumber'])
                        return datetime.fromtimestamp(block['timestamp'])
                    time.sleep(0.5)  # Rate limiting
                except:
                    time.sleep(2)
                    continue
            return None
        except:
            return None
    
    def scan_events(self, start_block, end_block, batch_size=1000):
        """Scan for TokenCreated events and save to database"""
        conn = self._get_db_connection()
        if not conn:
            return
            
        try:
            logging.info(f"Scanning blocks {start_block} to {end_block}")
            
            for current_block in range(start_block, end_block + 1, batch_size):
                batch_end = min(current_block + batch_size - 1, end_block)
                
                try:
                    logs = self.w3.eth.get_logs({
                        'fromBlock': current_block,
                        'toBlock': batch_end,
                        'address': TARGET_ADDRESS,
                        'topics': [self.event_signature]
                    })
                    
                    logging.info(f"Found {len(logs)} events in blocks {current_block}-{batch_end}")
                    
                    for log in logs:
                        try:
                            # Decode event
                            contract = self.w3.eth.contract(abi=TOKEN_CREATED_EVENT_ABI)
                            event = contract.events.TokenCreated().process_log(log)
                            
                            # Extract data
                            tx = self.w3.eth.get_transaction(log['transactionHash'])
                            params = event['args']['params']
                            token_details = self._get_token_details(params['tokenContractAddress'])
                            
                            deployment_data = {
                                'deployer_address': TARGET_ADDRESS,
                                'token_address': params['tokenContractAddress'],
                                'transaction_hash': log['transactionHash'].hex(),
                                'block_number': log['blockNumber'],
                                'timestamp': datetime.fromtimestamp(self.w3.eth.get_block(log['blockNumber']).timestamp),
                                'deployer_wallet': tx['from'],
                                'token_name': token_details['name'],
                                'token_symbol': token_details['symbol'],
                                'decimals': token_details['decimals'],
                                'total_supply': event['args']['tokenSupply'],
                                'deployment_value': float(self.w3.from_wei(tx['value'], 'ether'))
                            }
                            
                            if self._save_deployment(conn, deployment_data):
                                logging.info(f"Saved: {token_details['symbol']} at {params['tokenContractAddress']}")
                            
                            time.sleep(0.1)
                        except:
                            continue
                            
                except:
                    continue
                    
                # Update progress
                progress = ((current_block - start_block) / (end_block - start_block + 1)) * 100
                logging.info(f"Progress: {progress:.1f}%")
                
        finally:
            conn.close()
    
    def process_bonded_token(self, token_data):
        """Process a single bonded token for creation time"""
        token_address, token_name, token_symbol, pair_address = token_data
        time.sleep(random.uniform(1, 2))  # Rate limiting
        
        creation_time = self._get_pair_creation_time(pair_address)
        return {
            'token_address': token_address,
            'creation_time': creation_time,
            'success': creation_time is not None
        }
    
    def update_bonded_tokens(self):
        """Update bonded timestamps for all bonded tokens"""
        conn = self._get_db_connection()
        if not conn:
            return
            
        try:
            with conn.cursor() as cur:
                # Get bonded tokens
                cur.execute("""
                    SELECT token_address, token_name, token_symbol, pair_address
                    FROM token_deployments
                    WHERE lp_deployed = TRUE 
                    AND pair_address IS NOT NULL
                    AND pair_address != '0x0000000000000000000000000000000000000000'
                """)
                tokens = cur.fetchall()
                
                if not tokens:
                    logging.info("No bonded tokens to process")
                    return
                
                logging.info(f"Processing {len(tokens)} bonded tokens")
                
                # Process in parallel
                with Pool(min(cpu_count() // 2, 4)) as pool:
                    results = pool.map(self.process_bonded_token, tokens)
                
                # Update database
                for result in results:
                    if result['success']:
                        cur.execute("""
                            UPDATE token_deployments
                            SET bonded_at = %s
                            WHERE token_address = %s
                        """, (result['creation_time'], result['token_address']))
                        conn.commit()
                        logging.info(f"Updated bonded timestamp for {result['token_address']}")
                        
        except:
            pass
        finally:
            conn.close()
    
    def run_continuous_scan(self):
        """Main continuous scanning loop"""
        start_block = self._manage_scan_progress()
        logging.info(f"Starting continuous scan from block {start_block}")
        
        while True:
            try:
                # Refresh connection
                self.w3 = self._get_web3()
                current_tip = self.w3.eth.block_number
                
                if current_tip >= start_block:
                    self.scan_events(start_block, current_tip)
                    self._manage_scan_progress(current_tip)
                    start_block = current_tip + 1
                    logging.info(f"Scan complete. Next start block: {start_block}")
                else:
                    logging.info("No new blocks. Waiting...")
                
                time.sleep(60)
                
            except:
                time.sleep(30)

def main():
    """Main entry point"""
    scanner = TokenScanner()
    
    # Uncomment to update bonded token timestamps
    # scanner.update_bonded_tokens()
    
    # Run continuous scan
    scanner.run_continuous_scan()

if __name__ == "__main__":
    main()
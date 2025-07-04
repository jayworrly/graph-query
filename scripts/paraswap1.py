#!/usr/bin/env python3
"""
PARASWAP-FIRST APPROACH - FIXED TO GET REAL USERS
Instead of scanning 88k tokens, scan ParaSwap directly and filter for Arena tokens!
This version gets the actual transaction initiator (user) instead of liquidity pool contracts.
"""

import os
import json
import requests
import pandas as pd
from tqdm import tqdm
import psycopg2
import time
from dotenv import load_dotenv
import logging
from datetime import datetime
from collections import defaultdict

# Load environment variables
load_dotenv()
ANKR_API_KEY = os.getenv('ANKR_API_KEY')
ALCHEMY_URL = os.getenv('ALCHEMY_URL')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# RPC endpoints
RPC_ENDPOINTS = []
if ANKR_API_KEY:
    RPC_ENDPOINTS.append(f"https://rpc.ankr.com/avalanche/{ANKR_API_KEY}")
if ALCHEMY_URL:
    RPC_ENDPOINTS.append(ALCHEMY_URL)

RPC_ENDPOINTS.extend([
    "https://api.avax.network/ext/bc/C/rpc",
    "https://avalanche-c-chain.publicnode.com",
    "https://rpc.ankr.com/avalanche"
])

# Constants
TRANSFER_EVENT_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
PARASWAP_ADDRESS = "0x6a000f20005980200259b80c5102003040001068"

# Configuration
START_BLOCK = 61473123
BLOCK_CHUNK_SIZE = 2000
REQUEST_DELAY = 0.1
TIMEOUT_SECONDS = 30

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('paraswap_fixed_scan.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AvaxRPCClient:
    def __init__(self, rpc_url):
        self.rpc_url = rpc_url
        self.session = requests.Session()
        self.request_id = 1
    
    def _make_request(self, method, params):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }
        self.request_id += 1
        
        try:
            response = self.session.post(self.rpc_url, json=payload, timeout=TIMEOUT_SECONDS)
            result = response.json()
            
            if "error" in result:
                raise Exception(f"RPC Error: {result['error']}")
            
            return result["result"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network Error: {e}")
    
    def get_block_number(self):
        result = self._make_request("eth_blockNumber", [])
        return int(result, 16)
    
    def get_logs(self, from_block, to_block, address=None, topics=None):
        params = {
            "fromBlock": from_block,
            "toBlock": to_block
        }
        
        if address:
            params["address"] = address
        if topics:
            params["topics"] = topics
        
        return self._make_request("eth_getLogs", [params])

    def get_transaction(self, tx_hash):
        """Return full transaction object for a given hash"""
        return self._make_request("eth_getTransactionByHash", [tx_hash])

    def get_code(self, address, block_identifier="latest"):
        """Return contract bytecode at an address – empty string means EOA"""
        return self._make_request("eth_getCode", [address, block_identifier])

def find_best_rpc():
    """Find the fastest working RPC"""
    for rpc_url in RPC_ENDPOINTS:
        try:
            client = AvaxRPCClient(rpc_url)
            block_num = client.get_block_number()
            logger.info(f"Using RPC: {rpc_url} (block: {block_num})")
            return client, block_num
        except Exception as e:
            logger.error(f"RPC {rpc_url} failed: {e}")
    
    raise Exception("No working RPC found!")

def load_arena_token_set():
    """Load Arena tokens into a set for fast lookup"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        query = "SELECT DISTINCT token_address FROM token_deployments WHERE token_address IS NOT NULL;"
        
        arena_tokens = set()
        with conn.cursor() as cursor:
            cursor.execute(query)
            for row in cursor.fetchall():
                token_addr = str(row[0]).lower().strip()
                if not token_addr.startswith('0x'):
                    token_addr = '0x' + token_addr
                if len(token_addr) == 42:
                    arena_tokens.add(token_addr.lower())
        
        conn.close()
        logger.info(f"Loaded {len(arena_tokens)} Arena token addresses for filtering")
        return arena_tokens
        
    except Exception as e:
        logger.error(f"Error loading Arena tokens: {e}")
        return set()

def is_contract(rpc_client, address):
    """Determine whether an address is a smart-contract (has non-empty code)."""
    try:
        code = rpc_client.get_code(address)
        return code not in ("0x", "0x0", None, "")
    except Exception:
        return False

def get_all_paraswap_transfers(rpc_client, start_block, end_block, arena_tokens):
    """Get ALL transfers to/from ParaSwap, then filter for Arena tokens and get real users"""
    
    logger.info("🎯 PARASWAP-FIRST STRATEGY (FIXED)")
    logger.info("Getting Arena token transfers via ParaSwap and identifying real users...")
    
    arena_paraswap_logs = []
    tx_cache = {}  # Cache transaction data to avoid duplicate RPC calls
    
    # Calculate block chunks
    total_blocks = end_block - start_block
    block_chunks = []
    current_start = start_block
    
    while current_start < end_block:
        current_end = min(current_start + BLOCK_CHUNK_SIZE, end_block)
        block_chunks.append((current_start, current_end))
        current_start = current_end
    
    logger.info(f"Scanning {len(block_chunks)} block chunks for ParaSwap activity...")
    
    for i, (chunk_start, chunk_end) in enumerate(tqdm(block_chunks, desc="Scanning ParaSwap")):
        try:
            from_block_hex = hex(chunk_start)
            to_block_hex = hex(chunk_end)
            
            # Get ALL transfer events involving ParaSwap
            logs = rpc_client.get_logs(
                from_block=from_block_hex,
                to_block=to_block_hex,
                topics=[
                    TRANSFER_EVENT_SIG,
                    None,  # from (any address)
                    None,  # to (any address) 
                ]
            )
            
            # Filter for logs where ParaSwap is involved AND it's an Arena token
            for log in logs:
                try:
                    topics = log.get('topics', [])
                    if len(topics) >= 3:
                        from_addr = "0x" + topics[1][-40:]
                        to_addr = "0x" + topics[2][-40:]
                        token_address = log.get('address', '').lower()
                        
                        # Check if ParaSwap is involved AND it's an Arena token
                        if ((from_addr.lower() == PARASWAP_ADDRESS.lower() or 
                             to_addr.lower() == PARASWAP_ADDRESS.lower()) and
                            token_address in arena_tokens):
                            
                            # Add transaction hash to the log for later processing
                            log['tx_hash'] = log['transactionHash']
                            arena_paraswap_logs.append(log)
                            
                except Exception as e:
                    logger.warning(f"Error parsing log: {e}")
                    continue
            
            if i % 10 == 0 and arena_paraswap_logs:
                logger.info(f"Progress: {i+1}/{len(block_chunks)} chunks, "
                          f"{len(arena_paraswap_logs)} Arena transfers found")
            
            time.sleep(REQUEST_DELAY)
            
        except Exception as e:
            logger.error(f"Error in chunk {chunk_start}-{chunk_end}: {e}")
            time.sleep(REQUEST_DELAY * 2)
    
    logger.info(f"🎉 SCAN COMPLETE!")
    logger.info(f"Arena token transfers via ParaSwap: {len(arena_paraswap_logs)}")
    
    return arena_paraswap_logs

def process_transactions_and_get_users(rpc_client, arena_paraswap_logs):
    """Process transactions to get real users (transaction initiators)"""
    
    logger.info("🔍 IDENTIFYING REAL USERS...")
    logger.info("Getting transaction data to find who actually initiated each swap...")
    
    # Group logs by transaction hash to process efficiently
    logs_by_tx = defaultdict(list)
    for log in arena_paraswap_logs:
        logs_by_tx[log['transactionHash']].append(log)
    
    user_transactions = []
    tx_cache = {}
    
    for tx_hash, logs in tqdm(logs_by_tx.items(), desc="Processing transactions"):
        try:
            # Get transaction data (cached to avoid duplicate calls)
            if tx_hash not in tx_cache:
                tx_data = rpc_client.get_transaction(tx_hash)
                tx_cache[tx_hash] = tx_data
                time.sleep(REQUEST_DELAY)
            else:
                tx_data = tx_cache[tx_hash]
            
            if not tx_data:
                continue
            
            # The 'from' field in transaction data is the actual user who initiated the transaction
            real_user = tx_data.get('from', '').lower()
            
            # Process each log in this transaction
            for log in logs:
                try:
                    topics = log['topics']
                    from_addr = "0x" + topics[1][-40:]
                    to_addr = "0x" + topics[2][-40:]
                    token_address = log['address'].lower()
                    
                    # Determine if it's a buy or sell based on ParaSwap involvement
                    if from_addr.lower() == PARASWAP_ADDRESS.lower():
                        # ParaSwap is sending tokens (user is buying)
                        label = 'BUY'
                        counterparty = to_addr.lower()
                    elif to_addr.lower() == PARASWAP_ADDRESS.lower():
                        # ParaSwap is receiving tokens (user is selling)
                        label = 'SELL'
                        counterparty = from_addr.lower()
                    else:
                        # This shouldn't happen based on our filtering, but handle it
                        continue
                    
                    amount_hex = log.get('data', '0x')
                    amount = int(amount_hex, 16) if amount_hex and amount_hex != '0x' else 0
                    
                    user_transactions.append({
                        "block_number": int(log['blockNumber'], 16),
                        "tx_hash": tx_hash,
                        "token_address": token_address,
                        "real_user": real_user,  # This is the actual user who initiated the transaction
                        "counterparty": counterparty,  # This might be a pool contract or intermediate
                        "from_address": from_addr.lower(),
                        "to_address": to_addr.lower(),
                        "amount": amount,
                        "label": label
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing log in tx {tx_hash}: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Error getting transaction data for {tx_hash}: {e}")
            continue
    
    logger.info(f"✅ Processed {len(logs_by_tx)} transactions")
    logger.info(f"✅ Found {len(user_transactions)} user interactions")
    
    return user_transactions

def analyze_user_results(user_transactions):
    """Analyze the user transaction results"""
    
    logger.info("📊 ANALYZING USER RESULTS...")
    
    if not user_transactions:
        logger.info("No user transactions found")
        return
    
    df = pd.DataFrame(user_transactions)
    
    # Analysis
    unique_users = df['real_user'].nunique()
    unique_tokens = df['token_address'].nunique()
    buy_count = len(df[df['label'] == 'BUY'])
    sell_count = len(df[df['label'] == 'SELL'])
    
    logger.info(f"User Analysis:")
    logger.info(f"- Total user transactions: {len(df)}")
    logger.info(f"- Unique users: {unique_users}")
    logger.info(f"- Unique Arena tokens: {unique_tokens}")
    logger.info(f"- BUY transactions: {buy_count}")
    logger.info(f"- SELL transactions: {sell_count}")
    
    # Top users by transaction count
    top_users = df['real_user'].value_counts().head(10)
    logger.info(f"\n🔥 Most active users:")
    for user, count in top_users.items():
        logger.info(f"  {user}: {count} transactions")
    
    # Top tokens by transaction count
    top_tokens = df['token_address'].value_counts().head(10)
    logger.info(f"\n🎯 Most traded Arena tokens:")
    for token, count in top_tokens.items():
        logger.info(f"  {token}: {count} transactions")
    
    return df

def save_user_results(df):
    """Save user results to CSV and database"""
    
    if df is None or len(df) == 0:
        logger.info("No user transactions to save")
        return
    
    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"arena_paraswap_users_{timestamp}.csv"
    df.to_csv(filename, index=False)
    logger.info(f"✅ User results saved to {filename}")
    
    # Try to upload to database
    try:
        upload_user_data_to_database(df)
    except Exception as e:
        logger.error(f"Database upload failed: {e}")
    
    return df

def upload_user_data_to_database(df):
    """Upload user results to PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            # Create table for user transactions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS paraswap_arena_users (
                    id SERIAL PRIMARY KEY,
                    block_number BIGINT,
                    tx_hash VARCHAR(66),
                    token_address VARCHAR(66),
                    real_user VARCHAR(66),
                    counterparty VARCHAR(66),
                    from_address VARCHAR(66),
                    to_address VARCHAR(66),
                    amount NUMERIC(78, 0),
                    label VARCHAR(16),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_users_token ON paraswap_arena_users(token_address);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_users_user ON paraswap_arena_users(real_user);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_users_label ON paraswap_arena_users(label);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_users_block ON paraswap_arena_users(block_number);')
            
            # Insert data
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO paraswap_arena_users 
                    (block_number, tx_hash, token_address, real_user, counterparty, from_address, to_address, amount, label)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', (
                    row['block_number'], row['tx_hash'], row['token_address'],
                    row['real_user'], row['counterparty'], row['from_address'], 
                    row['to_address'], row['amount'], row['label']
                ))
            
            conn.commit()
        
        conn.close()
        logger.info(f"✅ Uploaded {len(df)} user records to database")
        
    except Exception as e:
        logger.error(f"Database upload error: {e}")

if __name__ == "__main__":
    logger.info("🎯 PARASWAP-FIRST ARENA TOKEN SCANNER (FIXED)")
    logger.info("=" * 60)
    logger.info("Strategy: Scan ParaSwap for Arena tokens, then get REAL USERS")
    logger.info("This identifies actual transaction initiators, not pool contracts!")
    
    # Setup
    rpc_client, latest_block = find_best_rpc()
    arena_tokens = load_arena_token_set()
    
    if not arena_tokens:
        logger.error("Failed to load Arena tokens!")
        exit(1)
    
    # Calculate scope
    total_blocks = latest_block - START_BLOCK
    num_chunks = (total_blocks + BLOCK_CHUNK_SIZE - 1) // BLOCK_CHUNK_SIZE
    estimated_minutes = (num_chunks * REQUEST_DELAY) / 60
    
    logger.info(f"📋 Scan Configuration:")
    logger.info(f"   Block range: {START_BLOCK} to {latest_block} ({total_blocks:,} blocks)")
    logger.info(f"   Block chunks: {num_chunks} ({BLOCK_CHUNK_SIZE} blocks each)")
    logger.info(f"   Arena tokens loaded: {len(arena_tokens):,}")
    logger.info(f"   Estimated time: {estimated_minutes:.1f} minutes")
    
    # Confirmation
    response = input(f"\n🚀 Scan ParaSwap for Arena token users? (y/N): ")
    if response.lower() != 'y':
        logger.info("Cancelled by user.")
        exit(0)
    
    # Run the scan
    start_time = time.time()
    
    # Step 1: Get all Arena token transfers via ParaSwap
    arena_paraswap_logs = get_all_paraswap_transfers(
        rpc_client, START_BLOCK, latest_block, arena_tokens
    )
    
    if not arena_paraswap_logs:
        logger.info("No Arena token transfers found via ParaSwap")
        exit(0)
    
    # Step 2: Process transactions to identify real users
    user_transactions = process_transactions_and_get_users(
        rpc_client, arena_paraswap_logs
    )
    
    # Step 3: Analyze and save results
    df = analyze_user_results(user_transactions)
    save_user_results(df)
    
    end_time = time.time()
    runtime_minutes = (end_time - start_time) / 60
    
    logger.info(f"\n🎉 SCAN COMPLETED!")
    logger.info(f"   Runtime: {runtime_minutes:.1f} minutes")
    logger.info(f"   Real users found: {df['real_user'].nunique() if df is not None else 0}")
    logger.info(f"   Total user transactions: {len(df) if df is not None else 0}")
    
    if df is not None and len(df) > 0:
        logger.info(f"\n🎯 SUCCESS! Found real users trading Arena tokens on ParaSwap!")
    else:
        logger.info("\n💡 No user transactions found in this block range.")
        logger.info("   Try expanding the block range or checking recent activity.")
#!/usr/bin/env python3
"""
INCREMENTAL PARASWAP SCANNER
Resumes from the last scanned block to keep data updated efficiently.
No more 9-hour full rescans!
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
FALLBACK_START_BLOCK = 61473123  # Only used if no data exists
BLOCK_CHUNK_SIZE = 2000
REQUEST_DELAY = 0.1
TIMEOUT_SECONDS = 30

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('paraswap_incremental.log', encoding='utf-8'),
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
        return self._make_request("eth_getTransactionByHash", [tx_hash])

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

def get_last_scanned_block():
    """Get the highest block number we've already scanned"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'paraswap_arena_users'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.info("ParaSwap table doesn't exist yet - starting from scratch")
                conn.close()
                return FALLBACK_START_BLOCK
            
            # Get the highest block number
            cursor.execute("""
                SELECT MAX(block_number) 
                FROM paraswap_arena_users;
            """)
            result = cursor.fetchone()
            max_block = result[0] if result[0] is not None else FALLBACK_START_BLOCK
            
            # Get some stats
            cursor.execute("SELECT COUNT(*) FROM paraswap_arena_users;")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT real_user) FROM paraswap_arena_users;")
            unique_users = cursor.fetchone()[0]
            
        conn.close()
        
        logger.info(f"📊 Current ParaSwap Database Status:")
        logger.info(f"   Last scanned block: {max_block:,}")
        logger.info(f"   Total transactions: {total_records:,}")
        logger.info(f"   Unique users: {unique_users:,}")
        
        return max_block
        
    except Exception as e:
        logger.error(f"Error checking last scanned block: {e}")
        logger.info(f"Falling back to start block: {FALLBACK_START_BLOCK}")
        return FALLBACK_START_BLOCK

def create_scanning_checkpoint(block_number):
    """Save a checkpoint of our scanning progress"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            # Create checkpoint table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS paraswap_scan_checkpoints (
                    id SERIAL PRIMARY KEY,
                    scan_type VARCHAR(50),
                    last_block BIGINT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_transactions BIGINT,
                    unique_users BIGINT
                );
            ''')
            
            # Get current stats
            cursor.execute("SELECT COUNT(*) FROM paraswap_arena_users;")
            total_tx = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT real_user) FROM paraswap_arena_users;")
            unique_users = cursor.fetchone()[0]
            
            # Upsert checkpoint
            cursor.execute('''
                INSERT INTO paraswap_scan_checkpoints 
                (scan_type, last_block, total_transactions, unique_users)
                VALUES ('incremental', %s, %s, %s)
                ON CONFLICT (scan_type) DO UPDATE SET
                    last_block = EXCLUDED.last_block,
                    last_updated = CURRENT_TIMESTAMP,
                    total_transactions = EXCLUDED.total_transactions,
                    unique_users = EXCLUDED.unique_users
            ''', (block_number, total_tx, unique_users))
            
            # Add unique constraint if it doesn't exist
            cursor.execute('''
                DO $$ 
                BEGIN
                    ALTER TABLE paraswap_scan_checkpoints 
                    ADD CONSTRAINT unique_scan_type UNIQUE (scan_type);
                EXCEPTION
                    WHEN duplicate_table THEN NULL;
                END $$;
            ''')
            
            conn.commit()
        
        conn.close()
        logger.info(f"✅ Checkpoint saved at block {block_number:,}")
        
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")

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

def scan_incremental_blocks(rpc_client, start_block, end_block, arena_tokens):
    """Scan only new blocks since last update"""
    
    if start_block >= end_block:
        logger.info("✅ Already up to date! No new blocks to scan.")
        return []
    
    blocks_to_scan = end_block - start_block
    logger.info(f"🔄 INCREMENTAL SCAN")
    logger.info(f"Scanning {blocks_to_scan:,} new blocks ({start_block:,} to {end_block:,})")
    
    arena_paraswap_logs = []
    
    # Calculate block chunks
    block_chunks = []
    current_start = start_block
    
    while current_start < end_block:
        current_end = min(current_start + BLOCK_CHUNK_SIZE, end_block)
        block_chunks.append((current_start, current_end))
        current_start = current_end
    
    logger.info(f"Processing {len(block_chunks)} block chunks...")
    
    for i, (chunk_start, chunk_end) in enumerate(tqdm(block_chunks, desc="Scanning new blocks")):
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
            
            # Filter for Arena tokens involving ParaSwap
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
                            
                            log['tx_hash'] = log['transactionHash']
                            arena_paraswap_logs.append(log)
                            
                except Exception as e:
                    logger.warning(f"Error parsing log: {e}")
                    continue
            
            # Save checkpoint every 50 chunks
            if (i + 1) % 50 == 0:
                create_scanning_checkpoint(chunk_end)
                logger.info(f"Progress: {i+1}/{len(block_chunks)} chunks, "
                          f"{len(arena_paraswap_logs)} new transfers found")
            
            time.sleep(REQUEST_DELAY)
            
        except Exception as e:
            logger.error(f"Error in chunk {chunk_start}-{chunk_end}: {e}")
            time.sleep(REQUEST_DELAY * 2)
    
    logger.info(f"🎉 INCREMENTAL SCAN COMPLETE!")
    logger.info(f"Found {len(arena_paraswap_logs)} new Arena token transfers via ParaSwap")
    
    return arena_paraswap_logs

def process_transactions_and_get_users(rpc_client, arena_paraswap_logs):
    """Process transactions to get real users (same as before)"""
    
    if not arena_paraswap_logs:
        logger.info("No new transactions to process")
        return []
    
    logger.info("🔍 PROCESSING NEW TRANSACTIONS...")
    
    # Group logs by transaction hash
    logs_by_tx = defaultdict(list)
    for log in arena_paraswap_logs:
        logs_by_tx[log['transactionHash']].append(log)
    
    user_transactions = []
    tx_cache = {}
    
    for tx_hash, logs in tqdm(logs_by_tx.items(), desc="Processing new transactions"):
        try:
            # Get transaction data
            if tx_hash not in tx_cache:
                tx_data = rpc_client.get_transaction(tx_hash)
                tx_cache[tx_hash] = tx_data
                time.sleep(REQUEST_DELAY)
            else:
                tx_data = tx_cache[tx_hash]
            
            if not tx_data:
                continue
            
            real_user = tx_data.get('from', '').lower()
            
            # Process each log in this transaction
            for log in logs:
                try:
                    topics = log['topics']
                    from_addr = "0x" + topics[1][-40:]
                    to_addr = "0x" + topics[2][-40:]
                    token_address = log['address'].lower()
                    
                    # Determine buy/sell
                    if from_addr.lower() == PARASWAP_ADDRESS.lower():
                        label = 'BUY'
                        counterparty = to_addr.lower()
                    elif to_addr.lower() == PARASWAP_ADDRESS.lower():
                        label = 'SELL'
                        counterparty = from_addr.lower()
                    else:
                        continue
                    
                    amount_hex = log.get('data', '0x')
                    amount = int(amount_hex, 16) if amount_hex and amount_hex != '0x' else 0
                    
                    user_transactions.append({
                        "block_number": int(log['blockNumber'], 16),
                        "tx_hash": tx_hash,
                        "token_address": token_address,
                        "real_user": real_user,
                        "counterparty": counterparty,
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
    
    logger.info(f"✅ Processed {len(logs_by_tx)} new transactions")
    logger.info(f"✅ Found {len(user_transactions)} new user interactions")
    
    return user_transactions

def upload_new_data_to_database(user_transactions):
    """Upload only new transactions to database"""
    
    if not user_transactions:
        logger.info("No new data to upload")
        return
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            # Ensure table exists (in case this is first run)
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
            
            # Create indexes if they don't exist
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_users_token ON paraswap_arena_users(token_address);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_users_user ON paraswap_arena_users(real_user);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_users_label ON paraswap_arena_users(label);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_users_block ON paraswap_arena_users(block_number);')
            
            # Insert new data
            new_records = 0
            for transaction in user_transactions:
                cursor.execute('''
                    INSERT INTO paraswap_arena_users 
                    (block_number, tx_hash, token_address, real_user, counterparty, from_address, to_address, amount, label)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                ''', (
                    transaction['block_number'], transaction['tx_hash'], transaction['token_address'],
                    transaction['real_user'], transaction['counterparty'], transaction['from_address'], 
                    transaction['to_address'], transaction['amount'], transaction['label']
                ))
                
                if cursor.rowcount > 0:
                    new_records += 1
            
            conn.commit()
        
        conn.close()
        logger.info(f"✅ Uploaded {new_records} new records to database")
        
    except Exception as e:
        logger.error(f"Database upload error: {e}")

if __name__ == "__main__":
    logger.info("🔄 INCREMENTAL PARASWAP SCANNER")
    logger.info("=" * 60)
    logger.info("Efficiently updating ParaSwap data from last scanned position")
    
    # Setup
    rpc_client, latest_block = find_best_rpc()
    arena_tokens = load_arena_token_set()
    
    if not arena_tokens:
        logger.error("Failed to load Arena tokens!")
        exit(1)
    
    # Get starting position
    start_block = get_last_scanned_block() + 1  # Start from next block
    
    # Calculate scope
    blocks_to_scan = latest_block - start_block
    
    if blocks_to_scan <= 0:
        logger.info("✅ ParaSwap data is already up to date!")
        exit(0)
    
    num_chunks = (blocks_to_scan + BLOCK_CHUNK_SIZE - 1) // BLOCK_CHUNK_SIZE
    estimated_minutes = (num_chunks * REQUEST_DELAY) / 60
    
    logger.info(f"📋 Incremental Scan Configuration:")
    logger.info(f"   Start block: {start_block:,}")
    logger.info(f"   Latest block: {latest_block:,}")
    logger.info(f"   Blocks to scan: {blocks_to_scan:,}")
    logger.info(f"   Estimated time: {estimated_minutes:.1f} minutes")
    
    # Confirmation for large scans
    if blocks_to_scan > 10000:
        response = input(f"\n🚀 Scan {blocks_to_scan:,} new blocks? (y/N): ")
        if response.lower() != 'y':
            logger.info("Cancelled by user.")
            exit(0)
    
    # Run incremental scan
    start_time = time.time()
    
    # Step 1: Scan only new blocks
    arena_paraswap_logs = scan_incremental_blocks(
        rpc_client, start_block, latest_block, arena_tokens
    )
    
    # Step 2: Process new transactions
    user_transactions = process_transactions_and_get_users(
        rpc_client, arena_paraswap_logs
    )
    
    # Step 3: Upload to database
    upload_new_data_to_database(user_transactions)
    
    # Step 4: Save final checkpoint
    create_scanning_checkpoint(latest_block)
    
    end_time = time.time()
    runtime_minutes = (end_time - start_time) / 60
    
    logger.info(f"\n🎉 INCREMENTAL SCAN COMPLETED!")
    logger.info(f"   Runtime: {runtime_minutes:.1f} minutes")
    logger.info(f"   Blocks scanned: {blocks_to_scan:,}")
    logger.info(f"   New transactions: {len(user_transactions)}")
    logger.info(f"   Database updated to block: {latest_block:,}")
    
    if len(user_transactions) > 0:
        logger.info(f"\n✅ Found {len(user_transactions)} new ParaSwap transactions!")
    else:
        logger.info("\n💡 No new ParaSwap activity found in scanned blocks.")
        
    logger.info(f"\n📅 Next run will start from block {latest_block + 1:,}")
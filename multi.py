import json
import time
from web3 import Web3
from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

load_dotenv()

# Setup logging with thread safety
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - [Thread-%(thread)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PARASWAP_CONTRACTS = {
    "AugustusSwapper": "0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57",
    "AugustusV6": "0x6A000F20005980200259B80c5102003040001068",
    "TokenTransferProxy": "0x216B4B4Ba9F3e719726886d34a177484278Bfcae"
}

# Get API keys from environment
ANKR_API_KEY = os.getenv("ANKR_API_KEY", "")
ALCHEMY_URL = os.getenv("ALCHEMY_URL", "")

# Build RPC endpoints with API keys
def build_rpc_endpoints():
    endpoints = [
        "https://api.avax.network/ext/bc/C/rpc",                    # Official Avalanche
        "https://ava-mainnet.public.blastapi.io/ext/bc/C/rpc",     # Blast public
        "https://avalanche-c-chain.publicnode.com",                # PublicNode
    ]
    
    # Add Ankr endpoint if API key is available
    if ANKR_API_KEY:
        endpoints.append(f"https://rpc.ankr.com/avalanche/{ANKR_API_KEY}")
        logger.info(f"✅ Using Ankr API key - added premium endpoint")
    
    # Add Alchemy endpoint if URL is available
    if ALCHEMY_URL:
        endpoints.append(ALCHEMY_URL)
        logger.info(f"✅ Using Alchemy URL - added premium endpoint")
    
    if not ANKR_API_KEY and not ALCHEMY_URL:
        logger.info("ℹ️ No premium API keys found - using public RPCs only")
    
    return endpoints

# Get RPC endpoints
RPC_ENDPOINTS = build_rpc_endpoints()

# PostgreSQL connection
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Scanning configuration  
START_BLOCK = 61561219
NUM_THREADS = len(RPC_ENDPOINTS)  # Match number of available RPCs
BLOCKS_PER_BATCH = 500

@dataclass
class TradeEvent:
    tx_hash: str
    block_number: int
    timestamp: int
    user_address: str
    token_in_symbol: str
    token_out_symbol: str
    amount_in: float
    amount_out: float
    trade_type: str

class SimpleWorker:
    def __init__(self, worker_id: int, rpc_url: str, target_tokens: Set[str]):
        self.worker_id = worker_id
        self.rpc_url = rpc_url
        self.target_tokens = target_tokens
        self.trades_found = 0
        self.blocks_processed = 0
        self.errors = 0
        
        # Setup Web3 with retries
        self.setup_web3()
        
        # Convert contract addresses to lowercase
        self.paraswap_addresses = [addr.lower() for addr in PARASWAP_CONTRACTS.values()]
        
        # Transfer event topic hash
        self.transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex()
        
        # PostgreSQL connection params
        self.connection_params = {
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
            "user": DB_USER,
            "password": DB_PASSWORD
        }
        
        logger.info(f"Worker {worker_id} initialized with {rpc_url}")
    
    def setup_web3(self):
        """Setup Web3 connection with error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={'timeout': 60}))
                self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                
                # Test connection
                current_block = self.w3.eth.block_number
                logger.info(f"Worker {self.worker_id}: Connected to {self.rpc_url}, current block: {current_block:,}")
                return
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id}: Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)
    
    def get_connection(self):
        """Get PostgreSQL connection with error handling"""
        try:
            return psycopg2.connect(**self.connection_params)
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Database connection failed: {e}")
            raise
    
    def is_paraswap_transaction(self, tx) -> bool:
        """Quick check if transaction is to ParaSwap"""
        return tx.to and tx.to.lower() in self.paraswap_addresses
    
    def has_target_tokens(self, block_num: int, tx_hash: str) -> bool:
        """Quick check if transaction involves target tokens"""
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            
            # Check transfer events for target tokens
            for log in receipt.logs:
                if (len(log.topics) >= 3 and 
                    log.topics[0].hex() == self.transfer_topic and
                    log.address.lower() in self.target_tokens):
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Worker {self.worker_id}: Error checking target tokens in {tx_hash}: {e}")
            return False
    
    def save_simple_trade(self, trade_data: Dict):
        """Save trade with enhanced error handling and verification"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert trade
            cursor.execute('''
                INSERT INTO target_token_trades 
                (tx_hash, block_number, timestamp, user_address, token_in_symbol, token_out_symbol,
                 amount_in, amount_out, trade_type, contract_used, is_target_token_in, is_target_token_out)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash) DO NOTHING
            ''', (
                trade_data['tx_hash'],
                trade_data['block_number'],
                trade_data['timestamp'],
                trade_data['user_address'],
                trade_data['token_in_symbol'],
                trade_data['token_out_symbol'],
                trade_data['amount_in'],
                trade_data['amount_out'],
                trade_data['trade_type'],
                "ParaSwap",
                True,  # is_target_token_in
                True   # is_target_token_out
            ))
            
            # Verify the insert worked
            if cursor.rowcount > 0:
                logger.info(f"💾 Worker {self.worker_id}: Successfully saved trade {trade_data['tx_hash'][:10]}...")
            else:
                logger.debug(f"Worker {self.worker_id}: Trade {trade_data['tx_hash'][:10]}... already exists (duplicate)")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error saving trade {trade_data.get('tx_hash', 'unknown')}: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
    
    def process_block_range(self, start_block: int, end_block: int) -> Dict:
        """Process blocks with heavy error handling"""
        logger.info(f"Worker {self.worker_id}: Processing blocks {start_block:,} to {end_block:,}")
        
        for block_num in range(start_block, end_block + 1):
            try:
                # Get block with transactions
                block = self.w3.eth.get_block(block_num, full_transactions=True)
                
                # Skip empty blocks
                if len(block.transactions) == 0:
                    self.blocks_processed += 1
                    continue
                
                # Check each transaction
                for tx in block.transactions:
                    try:
                        # Quick ParaSwap check
                        if not self.is_paraswap_transaction(tx):
                            continue
                        
                        # Quick target token check
                        if not self.has_target_tokens(block_num, tx.hash.hex()):
                            continue
                        
                        # Found a target trade!
                        trade_data = {
                            'tx_hash': tx.hash.hex(),
                            'block_number': block_num,
                            'timestamp': block.timestamp,
                            'user_address': tx['from'],
                            'token_in_symbol': 'UNKNOWN',  # Simplified
                            'token_out_symbol': 'TARGET',  # Simplified
                            'amount_in': 0.0,
                            'amount_out': 0.0,
                            'trade_type': 'SWAP'
                        }
                        
                        self.save_simple_trade(trade_data)
                        self.trades_found += 1
                        
                        logger.info(f"🎯 Worker {self.worker_id}: Found trade in block {block_num} - {tx.hash.hex()}")
                        
                    except Exception as e:
                        logger.debug(f"Worker {self.worker_id}: Error processing tx {tx.hash.hex()}: {e}")
                        continue
                
                self.blocks_processed += 1
                
                # Progress update every 100 blocks
                if self.blocks_processed % 100 == 0:
                    logger.info(f"⚡ Worker {self.worker_id}: {self.blocks_processed} blocks, {self.trades_found} trades, {self.errors} errors")
                
            except Exception as e:
                self.errors += 1
                logger.error(f"Worker {self.worker_id}: Error processing block {block_num}: {e}")
                
                # If too many errors, take a break
                if self.errors > 10:
                    logger.warning(f"Worker {self.worker_id}: Too many errors, sleeping...")
                    time.sleep(5)
                    self.errors = 0
                
                continue
        
        logger.info(f"✅ Worker {self.worker_id}: Completed! {self.blocks_processed} blocks, {self.trades_found} trades")
        
        return {
            "worker_id": self.worker_id,
            "blocks_processed": self.blocks_processed,
            "trades_found": self.trades_found,
            "errors": self.errors
        }

class SimpleMultiScanner:
    def __init__(self):
        self.target_tokens = self.load_target_tokens()
        self.setup_tables()
        
        logger.info(f"✅ Scanner initialized with {len(self.target_tokens)} target tokens")
    
    def load_target_tokens(self) -> Set[str]:
        """Load target tokens"""
        target_tokens = set()
        
        try:
            connection_params = {
                "host": DB_HOST,
                "port": DB_PORT,
                "database": DB_NAME,
                "user": DB_USER,
                "password": DB_PASSWORD
            }
            
            conn = psycopg2.connect(**connection_params)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Simple query - just get tokens that have bonding activity
            query = """
            SELECT DISTINCT td.token_address
            FROM token_deployments td
            INNER JOIN bonding_events be ON td.id = be.token_address 
            WHERE td.token_address IS NOT NULL 
            LIMIT 1000
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for row in rows:
                address = row['token_address']
                if address and address.startswith('0x'):
                    target_tokens.add(address.lower())
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            
        return target_tokens
    
    def setup_tables(self):
        """Setup output tables"""
        try:
            connection_params = {
                "host": DB_HOST,
                "port": DB_PORT,
                "database": DB_NAME,
                "user": DB_USER,
                "password": DB_PASSWORD
            }
            
            conn = psycopg2.connect(**connection_params)
            cursor = conn.cursor()
            
            # Simple table structure
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS target_token_trades (
                    id SERIAL PRIMARY KEY,
                    tx_hash VARCHAR(66) UNIQUE,
                    block_number BIGINT,
                    timestamp BIGINT,
                    user_address VARCHAR(42),
                    token_in_symbol VARCHAR(20),
                    token_out_symbol VARCHAR(20),
                    amount_in DECIMAL(36,18),
                    amount_out DECIMAL(36,18),
                    trade_type VARCHAR(10),
                    contract_used VARCHAR(50),
                    is_target_token_in BOOLEAN,
                    is_target_token_out BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Tables ready")
            
        except Exception as e:
            logger.error(f"Error setting up tables: {e}")
    
    def scan_parallel(self, start_block: int, end_block: int):
        """Simple parallel scanning"""
        
        total_blocks = end_block - start_block + 1
        blocks_per_worker = total_blocks // NUM_THREADS
        
        logger.info(f"🚀 Starting simple parallel scan")
        logger.info(f"📊 Total blocks: {total_blocks:,}")
        logger.info(f"⚡ Workers: {NUM_THREADS}")
        logger.info(f"📦 Blocks per worker: {blocks_per_worker:,}")
        
        # Create work assignments
        work_assignments = []
        current_start = start_block
        
        for i in range(NUM_THREADS):
            if i == NUM_THREADS - 1:
                worker_end = end_block
            else:
                worker_end = current_start + blocks_per_worker - 1
            
            work_assignments.append((current_start, worker_end, RPC_ENDPOINTS[i % len(RPC_ENDPOINTS)]))
            logger.info(f"Worker {i}: blocks {current_start:,} to {worker_end:,} via {RPC_ENDPOINTS[i % len(RPC_ENDPOINTS)]}")
            current_start = worker_end + 1
        
        # Start workers
        start_time = time.time()
        total_trades = 0
        total_blocks = 0
        
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = []
            
            for i, (range_start, range_end, rpc_url) in enumerate(work_assignments):
                worker = SimpleWorker(i, rpc_url, self.target_tokens)
                future = executor.submit(worker.process_block_range, range_start, range_end)
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    result = future.result()
                    total_trades += result['trades_found']
                    total_blocks += result['blocks_processed']
                    
                    logger.info(f"✅ Worker {result['worker_id']} done: {result['blocks_processed']:,} blocks, {result['trades_found']} trades")
                    
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
                    logger.error(traceback.format_exc())
        
        duration = time.time() - start_time
        
        logger.info(f"🎉 Scan complete!")
        logger.info(f"⏱️  Duration: {duration:.1f}s ({duration/60:.1f} min)")
        logger.info(f"📊 Blocks: {total_blocks:,}")
        logger.info(f"🎯 Trades: {total_trades}")
        logger.info(f"⚡ Speed: {total_blocks/duration:.1f} blocks/sec")
        
        # Verify database entries
        self.verify_database_entries()
    
    def verify_database_entries(self):
        """Verify that trades were actually saved to database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Count total trades in database
            cursor.execute("SELECT COUNT(*) FROM target_token_trades")
            total_count = cursor.fetchone()[0]
            
            # Get recent trades
            cursor.execute("""
                SELECT tx_hash, block_number, token_in_symbol, token_out_symbol, trade_type, created_at
                FROM target_token_trades 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent_trades = cursor.fetchall()
            
            conn.close()
            
            logger.info(f"📊 DATABASE VERIFICATION:")
            logger.info(f"   Total trades in database: {total_count:,}")
            
            if recent_trades:
                logger.info(f"   Recent trades:")
                for trade in recent_trades:
                    tx_hash, block_num, token_in, token_out, trade_type, created = trade
                    logger.info(f"     {trade_type}: {token_in} → {token_out} (Block {block_num:,}) [{tx_hash[:10]}...]")
            else:
                logger.warning("   ⚠️ No trades found in database!")
                
        except Exception as e:
            logger.error(f"Error verifying database: {e}")

def main():
    print("=" * 60)
    print("SIMPLE MULTI-THREADED SCANNER")
    print("=" * 60)
    
    try:
        scanner = SimpleMultiScanner()
        
        if not scanner.target_tokens:
            print("❌ No target tokens loaded")
            return
        
        current_block = Web3(Web3.HTTPProvider(RPC_ENDPOINTS[0])).eth.block_number
        
        start = input(f"Start block (default {START_BLOCK:,}): ").strip()
        start_block = int(start) if start else START_BLOCK
        
        end = input(f"End block (default current {current_block:,}): ").strip()
        end_block = int(end) if end else current_block
        
        print(f"\n🚀 Configuration:")
        print(f"   Tokens: {len(scanner.target_tokens):,}")
        print(f"   Blocks: {start_block:,} to {end_block:,}")
        print(f"   Workers: {NUM_THREADS}")
        
        scanner.scan_parallel(start_block, end_block)
        
    except Exception as e:
        logger.error(f"Main error: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
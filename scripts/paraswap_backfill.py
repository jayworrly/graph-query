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

# Enhanced logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - [Thread-%(thread)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Paraswap contract addresses
PARASWAP_CONTRACTS = {
    "AugustusSwapper": "0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57",
    "AugustusV6": "0x6A000F20005980200259B80c5102003040001068",
    "TokenTransferProxy": "0x216B4B4Ba9F3e719726886d34a177484278Bfcae"
}

# Multi-RPC configuration for better performance
def build_rpc_endpoints():
    endpoints = [
        "https://api.avax.network/ext/bc/C/rpc",
        "https://ava-mainnet.public.blastapi.io/ext/bc/C/rpc",
        "https://avalanche-c-chain.publicnode.com",
    ]
    
    # Add premium endpoints if available
    ankr_key = os.getenv("ANKR_API_KEY")
    alchemy_url = os.getenv("ALCHEMY_URL")
    
    if ankr_key:
        endpoints.append(f"https://rpc.ankr.com/avalanche/{ankr_key}")
    if alchemy_url:
        endpoints.append(alchemy_url)
    
    return endpoints

RPC_ENDPOINTS = build_rpc_endpoints()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD", "")
}

# Scanning configuration optimized for speed
OPTIMAL_BATCH_SIZE = 2000  # Larger batches for efficiency
NUM_WORKERS = min(len(RPC_ENDPOINTS), 8)  # Cap workers
RATE_LIMIT_PER_WORKER = 10  # Requests per second per worker

@dataclass
class ParaswapTradeData:
    tx_hash: str
    block_number: int
    timestamp: int
    uuid: str
    initiator: str
    beneficiary: str
    partner: str
    src_token: str
    dest_token: str
    src_amount: float
    received_amount: float
    expected_amount: float
    fee_percent: float
    trade_type: str
    is_arena_involved: bool
    arena_token: str = None
    avax_value: float = 0.0

class SmartParaswapWorker:
    def __init__(self, worker_id: int, rpc_url: str, target_tokens: Set[str]):
        self.worker_id = worker_id
        self.rpc_url = rpc_url
        self.target_tokens = {addr.lower() for addr in target_tokens}
        self.processed_blocks = 0
        self.trades_found = 0
        self.request_count = 0
        self.last_rate_reset = time.time()
        
        # Major tokens to filter out
        self.major_tokens = {
            "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7",  # WAVAX
            "0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7",  # USDt
            "0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664",  # USDC.e
            "0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e",  # USDC
        }
        
        # Setup Web3 and Paraswap contract
        self.setup_web3()
        self.setup_contracts()
        
        # PostgreSQL connection
        self.db_config = DB_CONFIG.copy()
        
        logger.info(f"Worker {worker_id} initialized: {len(target_tokens)} target tokens")

    def setup_web3(self):
        """Setup Web3 with connection pooling"""
        self.w3 = Web3(Web3.HTTPProvider(
            self.rpc_url, 
            request_kwargs={'timeout': 30, 'pool_connections': 20, 'pool_maxsize': 20}
        ))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        # Verify connection
        current_block = self.w3.eth.block_number
        logger.info(f"Worker {self.worker_id}: Connected to {self.rpc_url}, block: {current_block:,}")

    def setup_contracts(self):
        """Setup Paraswap contract interfaces"""
        # Load Paraswap ABI
        abi_path = os.path.join(os.path.dirname(__file__), "..", "arena-tracker", "abis", "ParaswapAggregator.json")
        with open(abi_path, 'r') as f:
            self.paraswap_abi = json.load(f)
        
        # Create contract instances for each Paraswap address
        self.paraswap_contracts = {}
        for name, address in PARASWAP_CONTRACTS.items():
            self.paraswap_contracts[name] = self.w3.eth.contract(
                address=Web3.toChecksumAddress(address),
                abi=self.paraswap_abi
            )
        
        # Event signatures
        self.swapped_signature = Web3.keccak(text="Swapped(bytes16,address,uint256,address,address,address,address,uint256,uint256,uint256)").hex()
        self.bought_signature = Web3.keccak(text="Bought(bytes16,address,uint256,address,address,address,address,uint256,uint256,uint256)").hex()
        self.sold_signature = Web3.keccak(text="Sold(bytes16,address,uint256,address,address,address,address,uint256,uint256,uint256)").hex()

    def rate_limit(self):
        """Smart rate limiting"""
        self.request_count += 1
        
        # Reset counter every second
        now = time.time()
        if now - self.last_rate_reset >= 1.0:
            self.request_count = 0
            self.last_rate_reset = now
        
        # If approaching limit, sleep briefly
        if self.request_count >= RATE_LIMIT_PER_WORKER:
            sleep_time = 1.0 - (now - self.last_rate_reset)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def get_database_connection(self):
        """Get database connection with error handling"""
        return psycopg2.connect(**self.db_config)

    def is_arena_token(self, token_address: str) -> bool:
        """Check if token is an Arena token"""
        addr = token_address.lower()
        
        # Skip major tokens
        if addr in self.major_tokens:
            return False
        
        # Check against our target tokens
        return addr in self.target_tokens

    def process_paraswap_event(self, log, block_timestamp: int) -> Optional[ParaswapTradeData]:
        """Process a single Paraswap event log"""
        try:
            # Determine event type
            topic0 = log['topics'][0].hex()
            
            if topic0 == self.swapped_signature:
                event_type = "SWAPPED"
            elif topic0 == self.bought_signature:
                event_type = "BOUGHT"
            elif topic0 == self.sold_signature:
                event_type = "SOLD"
            else:
                return None
            
            # Decode event data (simplified - you might want to use contract.events.decode_log)
            # For now, we'll extract what we can from the raw log
            
            # Basic extraction (you'd want proper ABI decoding here)
            tx_hash = log['transactionHash'].hex()
            block_number = log['blockNumber']
            
            # This is a simplified version - in production you'd decode the full event
            trade_data = ParaswapTradeData(
                tx_hash=tx_hash,
                block_number=block_number,
                timestamp=block_timestamp,
                uuid="", # Would extract from decoded event
                initiator="", # Would extract from decoded event  
                beneficiary="", # Would extract from decoded event
                partner="", # Would extract from decoded event
                src_token="", # Would extract from decoded event
                dest_token="", # Would extract from decoded event
                src_amount=0.0, # Would extract from decoded event
                received_amount=0.0, # Would extract from decoded event
                expected_amount=0.0, # Would extract from decoded event
                fee_percent=0.0, # Would extract from decoded event
                trade_type=event_type,
                is_arena_involved=False, # Would determine after decoding
                arena_token=None,
                avax_value=0.0
            )
            
            return trade_data
            
        except Exception as e:
            logger.debug(f"Worker {self.worker_id}: Error processing event: {e}")
            return None

    def process_block_batch(self, start_block: int, end_block: int) -> List[ParaswapTradeData]:
        """Process a batch of blocks efficiently"""
        trades = []
        
        logger.info(f"Worker {self.worker_id}: Processing blocks {start_block:,} to {end_block:,}")
        
        for block_num in range(start_block, end_block + 1):
            try:
                self.rate_limit()
                
                # Get block with minimal data needed
                block = self.w3.eth.get_block(block_num, full_transactions=False)
                block_timestamp = block.timestamp
                
                # Get logs for all Paraswap contracts in this block
                for contract_name, contract_address in PARASWAP_CONTRACTS.items():
                    try:
                        self.rate_limit()
                        
                        logs = self.w3.eth.get_logs({
                            'fromBlock': block_num,
                            'toBlock': block_num,
                            'address': contract_address,
                            'topics': [
                                [self.swapped_signature, self.bought_signature, self.sold_signature]
                            ]
                        })
                        
                        # Process each log
                        for log in logs:
                            trade_data = self.process_paraswap_event(log, block_timestamp)
                            if trade_data and trade_data.is_arena_involved:
                                trades.append(trade_data)
                                self.trades_found += 1
                                
                    except Exception as e:
                        logger.debug(f"Worker {self.worker_id}: Error getting logs for {contract_name}: {e}")
                        continue
                
                self.processed_blocks += 1
                
                # Progress update
                if self.processed_blocks % 500 == 0:
                    logger.info(f"Worker {self.worker_id}: {self.processed_blocks} blocks, {self.trades_found} trades")
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id}: Error processing block {block_num}: {e}")
                continue
        
        return trades

    def save_trades_batch(self, trades: List[ParaswapTradeData]):
        """Save multiple trades efficiently"""
        if not trades:
            return
        
        try:
            conn = self.get_database_connection()
            cursor = conn.cursor()
            
            # Prepare batch insert
            trade_values = []
            for trade in trades:
                trade_values.append((
                    trade.tx_hash,
                    trade.block_number,
                    trade.timestamp,
                    trade.uuid,
                    trade.initiator,
                    trade.beneficiary,
                    trade.src_token,
                    trade.dest_token,
                    trade.src_amount,
                    trade.received_amount,
                    trade.trade_type,
                    trade.is_arena_involved,
                    trade.arena_token,
                    trade.avax_value
                ))
            
            # Batch insert with conflict handling
            cursor.executemany('''
                INSERT INTO paraswap_trades_historical 
                (tx_hash, block_number, timestamp, uuid, initiator, beneficiary,
                 src_token, dest_token, src_amount, received_amount, trade_type,
                 is_arena_involved, arena_token, avax_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash) DO NOTHING
            ''', trade_values)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Worker {self.worker_id}: Saved {len(trades)} trades to database")
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Error saving trades: {e}")

class SmartParaswapBackfiller:
    def __init__(self):
        self.target_tokens = self.load_arena_tokens()
        self.setup_database()
        
        logger.info(f"✅ Backfiller initialized with {len(self.target_tokens)} Arena tokens")

    def load_arena_tokens(self) -> Set[str]:
        """Load Arena tokens from database"""
        tokens = set()
        
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Get all Arena tokens from token_deployments
            cursor.execute("""
                SELECT DISTINCT token_address 
                FROM token_deployments 
                WHERE token_address IS NOT NULL
            """)
            
            for row in cursor.fetchall():
                tokens.add(row[0].lower())
            
            conn.close()
            logger.info(f"Loaded {len(tokens)} Arena tokens")
            
        except Exception as e:
            logger.error(f"Error loading Arena tokens: {e}")
        
        return tokens

    def setup_database(self):
        """Setup database tables for historical data"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Create historical Paraswap trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS paraswap_trades_historical (
                    id SERIAL PRIMARY KEY,
                    tx_hash VARCHAR(66) UNIQUE NOT NULL,
                    block_number BIGINT NOT NULL,
                    timestamp BIGINT NOT NULL,
                    uuid VARCHAR(34),
                    initiator VARCHAR(42),
                    beneficiary VARCHAR(42),
                    src_token VARCHAR(42),
                    dest_token VARCHAR(42),
                    src_amount DECIMAL(36,18),
                    received_amount DECIMAL(36,18),
                    trade_type VARCHAR(10),
                    is_arena_involved BOOLEAN DEFAULT FALSE,
                    arena_token VARCHAR(42),
                    avax_value DECIMAL(36,18),
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    INDEX idx_block_number (block_number),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_arena_token (arena_token),
                    INDEX idx_is_arena_involved (is_arena_involved)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Database tables ready")
            
        except Exception as e:
            logger.error(f"Error setting up database: {e}")

    def get_scan_range(self) -> tuple:
        """Determine optimal scan range"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Get the earliest bonding event block
            cursor.execute("""
                SELECT MIN(block_number) as start_block, MAX(block_number) as end_block
                FROM bonding_events 
                WHERE block_number IS NOT NULL
            """)
            
            result = cursor.fetchone()
            start_block = result[0] if result[0] else 61473123  # Fallback to factory deployment
            
            # Get current blockchain block
            w3 = Web3(Web3.HTTPProvider(RPC_ENDPOINTS[0]))
            current_block = w3.eth.block_number
            
            conn.close()
            
            logger.info(f"📊 Scan range: {start_block:,} to {current_block:,} ({current_block - start_block:,} blocks)")
            
            return start_block, current_block
            
        except Exception as e:
            logger.error(f"Error determining scan range: {e}")
            return 61473123, 0  # Fallback

    def run_parallel_backfill(self, start_block: int = None, end_block: int = None):
        """Run the parallel backfill process"""
        if start_block is None or end_block is None:
            start_block, end_block = self.get_scan_range()
        
        total_blocks = end_block - start_block + 1
        blocks_per_worker = total_blocks // NUM_WORKERS
        
        logger.info(f"🚀 Starting smart Paraswap backfill")
        logger.info(f"📊 Total blocks: {total_blocks:,}")
        logger.info(f"⚡ Workers: {NUM_WORKERS}")
        logger.info(f"📦 Blocks per worker: {blocks_per_worker:,}")
        
        # Create work assignments
        assignments = []
        current_start = start_block
        
        for i in range(NUM_WORKERS):
            worker_end = min(current_start + blocks_per_worker - 1, end_block)
            rpc_url = RPC_ENDPOINTS[i % len(RPC_ENDPOINTS)]
            assignments.append((current_start, worker_end, rpc_url))
            current_start = worker_end + 1
        
        # Run workers
        start_time = time.time()
        total_trades = 0
        
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = []
            
            for i, (range_start, range_end, rpc_url) in enumerate(assignments):
                worker = SmartParaswapWorker(i, rpc_url, self.target_tokens)
                future = executor.submit(worker.process_block_batch, range_start, range_end)
                futures.append((future, worker))
            
            # Collect results
            for future, worker in futures:
                try:
                    trades = future.result()
                    worker.save_trades_batch(trades)
                    total_trades += len(trades)
                    
                    logger.info(f"✅ Worker {worker.worker_id}: {worker.processed_blocks:,} blocks, {len(trades)} trades")
                    
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
        
        duration = time.time() - start_time
        
        logger.info(f"🎉 Backfill complete!")
        logger.info(f"⏱️  Duration: {duration:.1f}s ({duration/60:.1f} min)")
        logger.info(f"🎯 Total trades found: {total_trades}")
        logger.info(f"⚡ Speed: {total_blocks/duration:.1f} blocks/sec")

def main():
    """Main entry point"""
    backfiller = SmartParaswapBackfiller()
    
    # Run backfill for recent blocks (you can adjust this)
    current_time = int(time.time())
    one_week_ago = current_time - (7 * 24 * 60 * 60)
    
    # You could make this more sophisticated to only backfill missing data
    backfiller.run_parallel_backfill()

if __name__ == "__main__":
    main() 
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

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ANKR_RPC_URL = os.getenv("ANKR_RPC_URL")
PARASWAP_CONTRACTS = {
    "AugustusSwapper": "0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57",
    "AugustusV6": "0x6A000F20005980200259B80c5102003040001068",
    "TokenTransferProxy": "0x216B4B4Ba9F3e719726886d34a177484278Bfcae"
}

# PostgreSQL connection from .env
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Historical scan configuration
START_BLOCK = 61561219
BATCH_SIZE = 2000  # Smaller batches for rate limiting
RPC_RATE_LIMIT = 1800  # Max requests per batch to stay under 2048 limit
REQUESTS_PER_BLOCK = 2  # Avg requests: get_block + get_transaction_receipt per tx

@dataclass
class TokenInfo:
    address: str
    symbol: str
    decimals: int
    name: str

@dataclass
class TradeEvent:
    tx_hash: str
    block_number: int
    timestamp: int
    user_address: str
    token_in: TokenInfo
    token_out: TokenInfo
    amount_in: float
    amount_out: float
    trade_type: str
    usd_value: float = 0.0
    gas_used: int = 0
    contract_used: str = ""

class AutoPostgresScanner:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(ANKR_RPC_URL))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self.token_cache = {}
        
        # Rate limiting tracking
        self.request_count = 0
        self.batch_start_time = time.time()
        
        # Setup PostgreSQL connection
        self.connection_params = {
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
            "user": DB_USER,
            "password": DB_PASSWORD
        }
        
        # Test connection
        self.test_connection()
        
        # Load target tokens automatically
        self.target_tokens = self.auto_load_tokens()
        logger.info(f"✅ Loaded {len(self.target_tokens)} target tokens automatically")
        
        # Convert contract addresses to lowercase for comparison
        self.paraswap_addresses = [addr.lower() for addr in PARASWAP_CONTRACTS.values()]
        
        # Transfer event topic hash
        self.transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex()
        
        # Setup output tables with unique names to avoid conflicts
        self.setup_output_tables()
        
        logger.info(f"Connected to Avalanche: {self.w3.is_connected()}")
        logger.info(f"⚡ Rate limiting: {RPC_RATE_LIMIT} requests per batch")
        
    def test_connection(self):
        """Test PostgreSQL connection"""
        try:
            conn = psycopg2.connect(**self.connection_params)
            conn.close()
            logger.info(f"✅ PostgreSQL connection successful: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise
    
    def track_rpc_request(self):
        """Track RPC requests for rate limiting"""
        self.request_count += 1
        
        # If we're approaching the limit, pause briefly
        if self.request_count >= RPC_RATE_LIMIT:
            elapsed = time.time() - self.batch_start_time
            if elapsed < 60:  # If we hit limit in under 60 seconds, wait
                sleep_time = 60 - elapsed + 1  # Wait until next minute + buffer
                logger.info(f"⏸️ Rate limit approached ({self.request_count} requests), sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
            
            # Reset counters
            self.request_count = 0
            self.batch_start_time = time.time()
    
    def get_block_with_rate_limit(self, block_number: int, full_transactions: bool = True):
        """Get block with rate limiting"""
        self.track_rpc_request()
        return self.w3.eth.get_block(block_number, full_transactions=full_transactions)
    
    def get_transaction_with_rate_limit(self, tx_hash: str):
        """Get transaction with rate limiting"""
        self.track_rpc_request()
        return self.w3.eth.get_transaction(tx_hash)
    
    def get_transaction_receipt_with_rate_limit(self, tx_hash: str):
        """Get transaction receipt with rate limiting"""
        self.track_rpc_request()
        return self.w3.eth.get_transaction_receipt(tx_hash)
    
    def get_block_timestamp_with_rate_limit(self, block_number: int):
        """Get block timestamp with rate limiting"""
        self.track_rpc_request()
        return self.w3.eth.get_block(block_number).timestamp
        """Get a new PostgreSQL connection"""
    def get_connection(self):
        """Get a new PostgreSQL connection"""
        return psycopg2.connect(**self.connection_params)
    
    def auto_load_tokens(self) -> Set[str]:
        """Automatically load tokens from token_deployments table"""
        target_tokens = set()
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Automatically use the most likely query
            query = "SELECT token_address FROM token_deployments WHERE token_address IS NOT NULL"
            
            logger.info(f"Loading tokens using: {query}")
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for row in rows:
                address = row['token_address']
                if address and isinstance(address, str) and address.startswith('0x') and len(address) == 42:
                    target_tokens.add(address.lower())
            
            conn.close()
            logger.info(f"Successfully loaded {len(target_tokens)} tokens from token_deployments")
            
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            
        return target_tokens
    
    def setup_output_tables(self):
        """Initialize PostgreSQL tables for filtered trades (with unique names)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Create target_token_trades table (unique name to avoid conflicts)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS target_token_trades (
                    id SERIAL PRIMARY KEY,
                    tx_hash VARCHAR(66) UNIQUE,
                    block_number BIGINT,
                    timestamp BIGINT,
                    user_address VARCHAR(42),
                    token_in_address VARCHAR(42),
                    token_in_symbol VARCHAR(20),
                    token_out_address VARCHAR(42),
                    token_out_symbol VARCHAR(20),
                    amount_in DECIMAL(36,18),
                    amount_out DECIMAL(36,18),
                    trade_type VARCHAR(10),
                    usd_value DECIMAL(18,2),
                    gas_used INTEGER,
                    contract_used VARCHAR(50),
                    is_target_token_in BOOLEAN,
                    is_target_token_out BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create target_scan_progress table (unique name)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS target_scan_progress (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    last_scanned_block BIGINT,
                    total_blocks_scanned INTEGER DEFAULT 0,
                    total_trades_found INTEGER DEFAULT 0,
                    target_token_trades INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT single_row_target CHECK (id = 1)
                )
            ''')
            
            # Initialize progress if not exists
            cursor.execute('SELECT COUNT(*) FROM target_scan_progress')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO target_scan_progress (id, last_scanned_block, total_blocks_scanned, total_trades_found, target_token_trades)
                    VALUES (1, %s, 0, 0, 0)
                ''', (START_BLOCK - 1,))
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_target_block_number ON target_token_trades(block_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_target_token_in ON target_token_trades(token_in_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_target_token_out ON target_token_trades(token_out_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_target_user ON target_token_trades(user_address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_target_flags ON target_token_trades(is_target_token_in, is_target_token_out)')
            
            conn.commit()
            logger.info("✅ Output tables created successfully")
            
        except Exception as e:
            logger.error(f"Error setting up tables: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_token_info_with_rate_limit(self, token_address: str) -> TokenInfo:
        """Get token information with caching and rate limiting"""
        if token_address in self.token_cache:
            return self.token_cache[token_address]
            
        try:
            erc20_abi = [
                {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "payable": False, "stateMutability": "view", "type": "function"},
                {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "payable": False, "stateMutability": "view", "type": "function"},
                {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "payable": False, "stateMutability": "view", "type": "function"}
            ]
            
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address), 
                abi=erc20_abi
            )
            
            # Each contract call uses 1 RPC request, we make 3 calls
            self.track_rpc_request()  # symbol
            symbol = contract.functions.symbol().call()
            
            self.track_rpc_request()  # decimals  
            decimals = contract.functions.decimals().call()
            
            self.track_rpc_request()  # name
            name = contract.functions.name().call()
            
            token_info = TokenInfo(
                address=token_address,
                symbol=symbol,
                decimals=decimals,
                name=name
            )
            
            self.token_cache[token_address] = token_info
            return token_info
            
        except Exception as e:
            logger.warning(f"Could not get token info for {token_address}: {e}")
            token_info = TokenInfo(
                address=token_address,
                symbol="UNKNOWN",
                decimals=18,
                name="Unknown Token"
            )
            self.token_cache[token_address] = token_info
            return token_info
    
    def is_target_trade(self, transfer_events: List[Dict]) -> bool:
        """Check if any transfer involves our target tokens"""
        for transfer in transfer_events:
            if transfer['token'].lower() in self.target_tokens:
                return True
        return False
    
    def parse_transfer_events(self, logs) -> List[Dict]:
        """Parse Transfer events from transaction logs"""
        transfer_events = []
        
        for log in logs:
            if len(log.topics) >= 3:
                log_topic = log.topics[0].hex()
                
                if log_topic == self.transfer_topic:
                    try:
                        from_addr = "0x" + log.topics[1].hex()[-40:]
                        to_addr = "0x" + log.topics[2].hex()[-40:]
                        
                        if log.data and log.data.hex():
                            amount = int(log.data.hex(), 16)
                        else:
                            amount = 0
                        
                        transfer_events.append({
                            "token": log.address,
                            "from": from_addr.lower(),
                            "to": to_addr.lower(),
                            "amount": amount
                        })
                        
                    except Exception as e:
                        continue
        
        return transfer_events
    
    def analyze_transaction_for_trades(self, tx_hash: str) -> List[TradeEvent]:
        """Analyze transaction and return only trades involving target tokens"""
        try:
            tx = self.get_transaction_with_rate_limit(tx_hash)
            receipt = self.get_transaction_receipt_with_rate_limit(tx_hash)
            
            timestamp = self.get_block_timestamp_with_rate_limit(tx.blockNumber)
            user_address = tx['from'].lower()
            
            # Parse transfer events
            transfer_events = self.parse_transfer_events(receipt.logs)
            
            if not transfer_events or not self.is_target_trade(transfer_events):
                return []
            
            # Analyze trades
            trades = self.identify_trades(transfer_events, user_address, tx_hash, tx.blockNumber, timestamp, receipt.gasUsed)
            
            # Filter trades to only include those with target tokens
            filtered_trades = []
            for trade in trades:
                is_target_in = trade.token_in.address.lower() in self.target_tokens
                is_target_out = trade.token_out.address.lower() in self.target_tokens
                
                if is_target_in or is_target_out:
                    trade.is_target_token_in = is_target_in
                    trade.is_target_token_out = is_target_out
                    filtered_trades.append(trade)
            
            return filtered_trades
            
        except Exception as e:
            logger.error(f"Error analyzing transaction {tx_hash}: {e}")
            return []
    
    def identify_trades(self, transfer_events: List[Dict], user_address: str, 
                       tx_hash: str, block_number: int, timestamp: int, gas_used: int) -> List[TradeEvent]:
        """Identify trades from transfer events"""
        
        user_sends = []
        for transfer in transfer_events:
            if transfer['from'] == user_address:
                token_info = self.get_token_info_with_rate_limit(transfer['token'])
                amount = transfer['amount'] / (10 ** token_info.decimals)
                user_sends.append({
                    "token": transfer['token'],
                    "token_info": token_info,
                    "amount": amount
                })
        
        user_receives = []
        for transfer in transfer_events:
            if transfer['to'] == user_address:
                token_info = self.get_token_info_with_rate_limit(transfer['token'])
                amount = transfer['amount'] / (10 ** token_info.decimals)
                user_receives.append({
                    "token": transfer['token'],
                    "token_info": token_info,
                    "amount": amount
                })
        
        trades = []
        
        if user_receives:
            for receive in user_receives:
                matching_send = None
                for send in user_sends:
                    if send['token'] != receive['token']:
                        matching_send = send
                        break
                
                if matching_send:
                    trade_type = self.determine_trade_type(matching_send['token_info'], receive['token_info'])
                    
                    trade = TradeEvent(
                        tx_hash=tx_hash,
                        block_number=block_number,
                        timestamp=timestamp,
                        user_address=user_address,
                        token_in=matching_send['token_info'],
                        token_out=receive['token_info'],
                        amount_in=matching_send['amount'],
                        amount_out=receive['amount'],
                        trade_type=trade_type,
                        gas_used=gas_used,
                        contract_used="ParaSwap"
                    )
                    
                    trades.append(trade)
        
        return trades
    
    def determine_trade_type(self, token_in: TokenInfo, token_out: TokenInfo) -> str:
        """Determine if this is a BUY or SELL"""
        quote_tokens = {"USDC", "USDT", "DAI", "FRAX", "AVAX", "WAVAX", "WETH", "ETH", "WBTC", "BTC", "WETH.e"}
        
        if token_in.symbol in quote_tokens and token_out.symbol not in quote_tokens:
            return "BUY"
        elif token_in.symbol not in quote_tokens and token_out.symbol in quote_tokens:
            return "SELL"
        else:
            return "SWAP"
    
    def save_trade(self, trade: TradeEvent):
        """Save filtered trade to PostgreSQL"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO target_token_trades 
                (tx_hash, block_number, timestamp, user_address, token_in_address, token_in_symbol,
                 token_out_address, token_out_symbol, amount_in, amount_out, trade_type, 
                 usd_value, gas_used, contract_used, is_target_token_in, is_target_token_out)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tx_hash) DO NOTHING
            ''', (
                trade.tx_hash, trade.block_number, trade.timestamp, trade.user_address,
                trade.token_in.address, trade.token_in.symbol, trade.token_out.address, 
                trade.token_out.symbol, trade.amount_in, trade.amount_out, trade.trade_type,
                trade.usd_value, trade.gas_used, trade.contract_used,
                getattr(trade, 'is_target_token_in', False),
                getattr(trade, 'is_target_token_out', False)
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def update_progress(self, last_block: int, blocks_scanned: int, trades_found: int):
        """Update scanning progress"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE target_scan_progress 
                SET last_scanned_block = %s, 
                    total_blocks_scanned = total_blocks_scanned + %s, 
                    target_token_trades = target_token_trades + %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (last_block, blocks_scanned, trades_found))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def scan_for_target_tokens(self, start_block: int = None, end_block: int = None):
        """Scan for trades involving only our target tokens"""
        
        if start_block is None:
            start_block = START_BLOCK
        if end_block is None:
            end_block = self.w3.eth.block_number
            
        logger.info(f"🎯 Scanning for trades involving {len(self.target_tokens)} target tokens")
        logger.info(f"Scanning blocks {start_block:,} to {end_block:,}")
        
        total_trades = 0
        target_trades = 0
        current_batch_start = start_block
        
        while current_batch_start <= end_block:
            batch_end = min(current_batch_start + BATCH_SIZE - 1, end_block)
            
            logger.info(f"📦 Processing batch: blocks {current_batch_start:,} to {batch_end:,}")
            
            batch_target_trades = 0
            
            for block_num in range(current_batch_start, batch_end + 1):
                try:
                    block = self.get_block_with_rate_limit(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        if tx.to and tx.to.lower() in self.paraswap_addresses:
                            total_trades += 1
                            
                            trades = self.analyze_transaction_for_trades(tx.hash.hex())
                            
                            for trade in trades:
                                self.save_trade(trade)
                                batch_target_trades += 1
                                target_trades += 1
                                
                                target_info = ""
                                if getattr(trade, 'is_target_token_in', False):
                                    target_info += f"[TARGET IN: {trade.token_in.symbol}] "
                                if getattr(trade, 'is_target_token_out', False):
                                    target_info += f"[TARGET OUT: {trade.token_out.symbol}] "
                                
                                logger.info(f"🎯 Block {block_num}: {target_info}{trade.trade_type} {trade.amount_in:.4f} {trade.token_in.symbol} → {trade.amount_out:.4f} {trade.token_out.symbol}")
                    
                    if block_num % 10 == 0:
                        logger.info(f"   Processed block {block_num:,} | RPC requests: {self.request_count}/{RPC_RATE_LIMIT}")
                        
                except Exception as e:
                    logger.error(f"Error processing block {block_num}: {e}")
                    continue
            
            # Update progress after each batch
            blocks_in_batch = batch_end - current_batch_start + 1
            self.update_progress(batch_end, blocks_in_batch, batch_target_trades)
            
            logger.info(f"✅ Batch complete: {batch_target_trades} target token trades found | Total RPC requests: {self.request_count}")
            
            # Brief pause between batches and reset request counter for next batch
            time.sleep(1)
            
            # Reset request counter if we're starting a new time window
            elapsed_since_start = time.time() - self.batch_start_time
            if elapsed_since_start >= 60:
                logger.info(f"⏰ Resetting RPC counter after {elapsed_since_start:.1f}s")
                self.request_count = 0
                self.batch_start_time = time.time()
            
            current_batch_start = batch_end + 1
        
        logger.info(f"🎉 Scan complete!")
        logger.info(f"   Total ParaSwap trades: {total_trades:,}")
        logger.info(f"   Target token trades: {target_trades:,}")
        logger.info(f"   Target trade percentage: {target_trades/total_trades*100:.2f}%" if total_trades > 0 else "   No trades found")
        
        return target_trades

def main():
    print("=" * 80)
    print("AUTOMATED POSTGRESQL TOKEN SCANNER")
    print("=" * 80)
    
    try:
        scanner = AutoPostgresScanner()
        
        if not scanner.target_tokens:
            print("❌ No target tokens loaded. Check your token_deployments table.")
            return
        
        print(f"✅ Ready to scan with {len(scanner.target_tokens):,} target tokens")
        
        # Ask for block range
        start = input(f"Start block (default {START_BLOCK:,}): ").strip()
        start_block = int(start) if start else START_BLOCK
        
        end = input("End block (default: current): ").strip()
        end_block = int(end) if end else None
        
        # Start scanning
        target_trades = scanner.scan_for_target_tokens(start_block, end_block)
        
        print(f"\n📊 RESULTS:")
        print(f"Target token trades found: {target_trades:,}")
        print(f"Data saved to PostgreSQL table: target_token_trades")
        
    except Exception as e:
        logger.error(f"Scanner failed: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
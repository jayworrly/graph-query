#!/usr/bin/env python3
import os
import json
import requests
import pandas as pd
from tqdm import tqdm
import psycopg2
from psycopg2.extras import execute_values
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
ANKR_API_KEY = os.getenv('ANKR_API_KEY')
ALCHEMY_URL = os.getenv('ALCHEMY_URL')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# RPC endpoints to try
RPC_ENDPOINTS = []
if ANKR_API_KEY:
    RPC_ENDPOINTS.append(f"https://rpc.ankr.com/avalanche/{ANKR_API_KEY}")
if ALCHEMY_URL:
    RPC_ENDPOINTS.append(ALCHEMY_URL)

# Public fallbacks
RPC_ENDPOINTS.extend([
    "https://api.avax.network/ext/bc/C/rpc",
    "https://avalanche-c-chain.publicnode.com",
    "https://rpc.ankr.com/avalanche"
])

# Constants
TRANSFER_EVENT_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
PARASWAP_ADDRESS = "0x6a000f20005980200259b80c5102003040001068"

# Configuration
MIN_RECENT_ACTIVITY_BLOCKS = 100000  # Only scan tokens active in last 100k blocks
MAX_TOKENS_TO_SCAN = 500  # Limit for testing
SCAN_BLOCK_RANGE = 50000  # How many recent blocks to scan

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
            response = self.session.post(self.rpc_url, json=payload, timeout=30)
            result = response.json()
            
            if "error" in result:
                raise Exception(f"RPC Error: {result['error']}")
            
            return result["result"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network Error: {e}")
    
    def get_block_number(self):
        """Get latest block number"""
        result = self._make_request("eth_blockNumber", [])
        return int(result, 16)
    
    def get_logs(self, from_block, to_block, address=None, topics=None):
        """Get logs using raw RPC"""
        params = {
            "fromBlock": from_block,
            "toBlock": to_block
        }
        
        if address:
            params["address"] = address
        if topics:
            params["topics"] = topics
        
        return self._make_request("eth_getLogs", [params])

def find_working_rpc():
    """Find a working RPC endpoint"""
    for rpc_url in RPC_ENDPOINTS:
        try:
            print(f"Testing RPC: {rpc_url}")
            client = AvaxRPCClient(rpc_url)
            
            # Test basic connection
            block_num = client.get_block_number()
            print(f"✅ {rpc_url} works! Latest block: {block_num}")
            
            # Test a simple log query
            from_block = hex(block_num - 10)
            to_block = hex(block_num)
            
            logs = client.get_logs(
                from_block=from_block,
                to_block=to_block
            )
            
            print(f"✅ Basic log query works! Found {len(logs)} logs in last 10 blocks")
            return client, block_num
            
        except Exception as e:
            print(f"❌ {rpc_url} failed: {e}")
    
    raise Exception("No working RPC endpoint found!")

def load_active_arena_tokens(latest_block):
    """Load Arena tokens that have recent activity"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        # Find tokens with recent activity
        cutoff_block = latest_block - MIN_RECENT_ACTIVITY_BLOCKS
        
        query = """
        SELECT DISTINCT 
            td.token_address,
            MAX(be.block_number) as last_activity_block,
            COUNT(be.id) as total_events,
            td.name,
            td.symbol
        FROM token_deployments td
        INNER JOIN bonding_events be ON td.id = be.token_address
        WHERE td.token_address IS NOT NULL 
        AND be.block_number IS NOT NULL
        AND be.block_number > %s
        GROUP BY td.token_address, td.name, td.symbol
        ORDER BY last_activity_block DESC
        LIMIT %s;
        """
        
        df = pd.read_sql_query(query, conn, params=[cutoff_block, MAX_TOKENS_TO_SCAN])
        conn.close()
        
        # Clean up addresses
        valid_tokens = []
        for _, row in df.iterrows():
            token_addr = str(row['token_address']).lower().strip()
            if not token_addr.startswith('0x'):
                token_addr = '0x' + token_addr
            if len(token_addr) == 42:  # Valid Ethereum address length
                valid_tokens.append({
                    'address': token_addr,
                    'name': row['name'],
                    'symbol': row['symbol'],
                    'last_activity': row['last_activity_block'],
                    'total_events': row['total_events']
                })
        
        print(f"Found {len(valid_tokens)} active Arena tokens (active since block {cutoff_block})")
        
        # Show top tokens by activity
        if valid_tokens:
            print("\nTop 10 most active tokens:")
            for i, token in enumerate(valid_tokens[:10]):
                print(f"  {i+1}. {token['symbol']} ({token['name'][:30]}) - {token['total_events']} events, last: {token['last_activity']}")
        
        return valid_tokens
        
    except Exception as e:
        print(f"Error loading tokens from database: {e}")
        return []

def fetch_paraswap_transfers(rpc_client, tokens, latest_block):
    """Fetch transfer logs for ParaSwap interactions"""
    logs = []
    
    # Define scan range
    start_block = latest_block - SCAN_BLOCK_RANGE
    from_block_hex = hex(start_block)
    to_block_hex = hex(latest_block)
    
    print(f"\nScanning blocks {start_block} to {latest_block} ({SCAN_BLOCK_RANGE} blocks)")
    print(f"Hex format: {from_block_hex} to {to_block_hex}")
    
    successful_requests = 0
    failed_requests = 0
    paraswap_transfers = 0
    
    # Process in small batches
    batch_size = 5
    
    for i in range(0, len(tokens), batch_size):
        batch = tokens[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}/{(len(tokens) + batch_size - 1)//batch_size}")
        
        for token_info in tqdm(batch, desc=f"Batch {i//batch_size + 1}"):
            token_address = token_info['address']
            token_symbol = token_info['symbol']
            
            try:
                # Get all transfer logs for this token in the range
                token_logs = rpc_client.get_logs(
                    from_block=from_block_hex,
                    to_block=to_block_hex,
                    address=token_address,
                    topics=[TRANSFER_EVENT_SIG]
                )
                
                # Filter for ParaSwap-related transfers
                paraswap_logs = []
                for log in token_logs:
                    topics = log['topics']
                    if len(topics) >= 3:
                        from_addr = "0x" + topics[1][-40:]
                        to_addr = "0x" + topics[2][-40:]
                        
                        # Check if either from or to is ParaSwap
                        if (from_addr.lower() == PARASWAP_ADDRESS.lower() or 
                            to_addr.lower() == PARASWAP_ADDRESS.lower()):
                            paraswap_logs.append(log)
                
                if paraswap_logs:
                    logs.extend(paraswap_logs)
                    paraswap_transfers += len(paraswap_logs)
                    print(f"  {token_symbol}: {len(paraswap_logs)} ParaSwap transfers")
                
                successful_requests += 1
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                failed_requests += 1
                print(f"  Error with {token_symbol} ({token_address}): {e}")
                
                # Stop if too many failures
                if failed_requests > 50:
                    print("Too many failures, stopping...")
                    break
                
                time.sleep(0.5)
    
    print(f"\nScan complete:")
    print(f"- Successful requests: {successful_requests}")
    print(f"- Failed requests: {failed_requests}")
    print(f"- ParaSwap transfers found: {paraswap_transfers}")
    
    return logs

def parse_and_label_logs(logs):
    """Parse and label the transfer logs"""
    data = []
    
    for log in logs:
        try:
            # Parse log data
            block_number = int(log['blockNumber'], 16)
            tx_hash = log['transactionHash']
            
            topics = log['topics']
            from_addr = "0x" + topics[1][-40:]
            to_addr = "0x" + topics[2][-40:]
            
            # Parse amount
            amount_hex = log['data']
            amount = int(amount_hex, 16) if amount_hex and amount_hex != '0x' else 0
            
            token_address = log['address'].lower()
            
            # Label the transaction
            label = 'unknown'
            if to_addr.lower() == PARASWAP_ADDRESS.lower():
                label = 'SELL'  # Token going TO ParaSwap
            elif from_addr.lower() == PARASWAP_ADDRESS.lower():
                label = 'BUY'   # Token coming FROM ParaSwap
            
            data.append({
                "block_number": block_number,
                "tx_hash": tx_hash,
                "from_address": from_addr.lower(),
                "to_address": to_addr.lower(),
                "amount": amount,
                "token_address": token_address,
                "label": label
            })
            
        except Exception as e:
            print(f"Error parsing log: {e}")
            continue
    
    df = pd.DataFrame(data)
    
    if len(df) > 0:
        print(f"\nLabeling summary:")
        print(f"- BUY transactions: {len(df[df['label'] == 'BUY'])}")
        print(f"- SELL transactions: {len(df[df['label'] == 'SELL'])}")
        print(f"- Unknown transactions: {len(df[df['label'] == 'unknown'])}")
        
        # Show token breakdown
        token_summary = df.groupby(['token_address', 'label']).size().unstack(fill_value=0)
        if len(token_summary) > 0:
            print(f"\nPer-token summary:")
            print(token_summary.head(10))
    
    return df

def upload_to_postgres(df):
    """Upload results to PostgreSQL"""
    if len(df) == 0:
        print("No data to upload.")
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
            # Create table with indexes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS paraswap_arena_transfers (
                    id SERIAL PRIMARY KEY,
                    block_number BIGINT,
                    tx_hash VARCHAR(66),
                    from_address VARCHAR(66),
                    to_address VARCHAR(66),
                    amount NUMERIC(78, 0),
                    token_address VARCHAR(66),
                    label VARCHAR(16),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_token ON paraswap_arena_transfers(token_address);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_label ON paraswap_arena_transfers(label);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_block ON paraswap_arena_transfers(block_number);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_paraswap_tx ON paraswap_arena_transfers(tx_hash);')
            
            # Insert data
            records = df[['block_number', 'tx_hash', 'from_address', 'to_address', 'amount', 'token_address', 'label']].values.tolist()
            execute_values(cursor,
                """
                INSERT INTO paraswap_arena_transfers
                (block_number, tx_hash, from_address, to_address, amount, token_address, label)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                records
            )
            conn.commit()
        
        conn.close()
        print(f"✅ Uploaded {len(df)} transfers to paraswap_arena_transfers table.")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    print("ParaSwap Arena Transfer Scanner")
    print("=" * 50)
    
    # Find working RPC
    try:
        rpc_client, latest_block = find_working_rpc()
    except Exception as e:
        print(f"Failed to connect to any RPC: {e}")
        exit(1)
    
    # Load active tokens
    active_tokens = load_active_arena_tokens(latest_block)
    if not active_tokens:
        print("No active tokens found!")
        exit(1)
    
    print(f"\nWill scan {len(active_tokens)} tokens for ParaSwap activity")
    
    # Fetch ParaSwap transfers
    logs = fetch_paraswap_transfers(rpc_client, active_tokens, latest_block)
    
    if logs:
        print(f"\nProcessing {len(logs)} ParaSwap transfer logs...")
        
        # Parse and label
        df = parse_and_label_logs(logs)
        
        if len(df) > 0:
            # Save to CSV
            filename = f"paraswap_arena_transfers_{latest_block}.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Saved to {filename}")
            
            # Show sample data
            print(f"\nSample data:")
            print(df.head(10))
            
            # Upload to database
            upload_to_postgres(df)
            
            # Summary stats
            print(f"\n📊 Final Summary:")
            print(f"- Total ParaSwap transfers: {len(df)}")
            print(f"- Unique tokens: {df['token_address'].nunique()}")
            print(f"- Unique transactions: {df['tx_hash'].nunique()}")
            print(f"- Block range: {df['block_number'].min()} to {df['block_number'].max()}")
            
        else:
            print("No valid transfer data to process")
    else:
        print("No ParaSwap transfers found in the specified range")
    
    print("\n✅ Scan complete!")
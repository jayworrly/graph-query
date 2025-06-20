import psycopg2
from web3 import Web3
from datetime import datetime
from dotenv import load_dotenv
import time
import os
import logging
from multiprocessing import Pool

# Load environment variables
load_dotenv()

print("Starting Bonding Tracker...")

# Configuration
ARENA_FACTORY = Web3.to_checksum_address('0xF16784dcAf838a3e16bEF7711a62D12413c39BD1')
WAVAX_ADDRESS = Web3.to_checksum_address('0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7')

# ABIs
FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"}
        ],
        "name": "getPair",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
            {"indexed": False, "internalType": "address", "name": "pair", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "PairCreated",
        "type": "event"
    }
]

TOKEN_ABI = [
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
]

class BondingTracker:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider('https://api.avax.network/ext/bc/C/rpc'))
        self.factory_contract = self.w3.eth.contract(address=ARENA_FACTORY, abi=FACTORY_ABI)
        
    def _get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT')
            )
        except Exception as e:
            logging.error(f"Database connection error: {str(e)}")
            return None
            
    def _find_pair_creation_block(self, token_address, deployment_block, current_block):
        """Find block where pair was created"""
        try:
            chunk_size = 2000
            for start_block in range(deployment_block, current_block + 1, chunk_size):
                end_block = min(start_block + chunk_size - 1, current_block)
                
                try:
                    # Search for token as token0
                    events1 = self.factory_contract.events.PairCreated.get_logs(
                        fromBlock=start_block, toBlock=end_block,
                        argument_filters={'token0': token_address}
                    )
                    
                    # Search for token as token1  
                    events2 = self.factory_contract.events.PairCreated.get_logs(
                        fromBlock=start_block, toBlock=end_block,
                        argument_filters={'token1': token_address}
                    )
                    
                    # Find WAVAX pairs
                    for event in events1 + events2:
                        if (event['args']['token0'].lower() == WAVAX_ADDRESS.lower() or 
                            event['args']['token1'].lower() == WAVAX_ADDRESS.lower()):
                            return event['blockNumber']
                except Exception:
                    continue
            return None
        except Exception:
            return None
    
    def _is_token_compatible(self, token_address):
        """Check if token is compatible with standard interface"""
        try:
            contract = self.w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=TOKEN_ABI)
            contract.functions.decimals().call()
            return True
        except Exception:
            return False
    
    def scan_pair_events(self, blocks_back=2000):
        """Scan for recent PairCreated events and update bonding status"""
        try:
            current_block = self.w3.eth.block_number
            start_block = max(current_block - blocks_back, 0)
            
            print(f"Scanning blocks {start_block} to {current_block} for PairCreated events...")
            
            # Get PairCreated events
            pair_events = self.factory_contract.events.PairCreated.get_logs(
                fromBlock=start_block,
                toBlock=current_block
            )
            
            print(f"Found {len(pair_events)} PairCreated events")
            
            conn = self._get_db_connection()
            if not conn:
                return False
                
            bonded_count = 0
            try:
                with conn.cursor() as cur:
                    for event in pair_events:
                        token0 = event['args']['token0']
                        token1 = event['args']['token1']
                        pair_address = event['args']['pair']
                        block_number = event['blockNumber']
                        
                        # Check if either token is WAVAX (indicating a bonding event)
                        bonded_token = None
                        if token0.lower() == WAVAX_ADDRESS.lower():
                            bonded_token = token1
                        elif token1.lower() == WAVAX_ADDRESS.lower():
                            bonded_token = token0
                        
                        if bonded_token:
                            # Check if this token exists in our database
                            cur.execute("""
                                SELECT token_address FROM token_deployments 
                                WHERE token_address = %s AND lp_deployed = FALSE
                            """, (bonded_token,))
                            
                            if cur.fetchone():
                                # Update the token as bonded
                                block = self.w3.eth.get_block(block_number)
                                bonded_at = datetime.fromtimestamp(block['timestamp'])
                                
                                cur.execute("""
                                    UPDATE token_deployments
                                    SET lp_deployed = TRUE, pair_address = %s, bonded_at = %s,
                                        bonded_block_number = %s, bonding_error = NULL
                                    WHERE token_address = %s
                                """, (pair_address, bonded_at, block_number, bonded_token))
                                
                                bonded_count += 1
                                print(f"Found bonded token from events: {bonded_token}")
                
                conn.commit()
                print(f"Event scan completed: {bonded_count} tokens updated from events")
                
            except Exception:
                conn.rollback()
            finally:
                conn.close()
                
            return True
                
        except Exception:
            print("Event scanning failed, falling back to individual checks")
            return False
    
    def _check_bonding(self, token_address, deployment_block=None):
        """Check if token is bonded and get bonding info"""
        try:
            if not self._is_token_compatible(token_address):
                return {'is_bonded': False, 'pair_address': None, 'timestamp': None, 
                       'block_number': None, 'error': 'Token not compatible'}
            
            pair_address = self.factory_contract.functions.getPair(token_address, WAVAX_ADDRESS).call()
            
            if pair_address == '0x0000000000000000000000000000000000000000':
                return {'is_bonded': False, 'pair_address': None, 'timestamp': None,
                       'block_number': None, 'error': None}
            
            current_block = self.w3.eth.block_number
            creation_block = self._find_pair_creation_block(
                token_address, deployment_block or 0, current_block
            )
            
            if creation_block:
                block = self.w3.eth.get_block(creation_block)
                return {
                    'is_bonded': True, 'pair_address': pair_address,
                    'timestamp': datetime.fromtimestamp(block['timestamp']),
                    'block_number': creation_block, 'error': None
                }
            else:
                return {
                    'is_bonded': True, 'pair_address': pair_address,
                    'timestamp': None, 'block_number': None,
                    'error': 'Could not determine bonding time'
                }
        except Exception:
            return {'is_bonded': False, 'pair_address': None, 'timestamp': None,
                   'block_number': None, 'error': 'Check failed'}
    
    def update_bonding_status(self, hours_back=24):
        """Update bonding status for recently deployed tokens only"""
        conn = self._get_db_connection()
        if not conn:
            return
            
        try:
            with conn.cursor() as cur:
                # Only check tokens deployed in the last X hours
                cur.execute("""
                    SELECT token_address, block_number
                    FROM token_deployments
                    WHERE lp_deployed = FALSE 
                    AND bonding_error IS NULL
                    AND timestamp >= NOW() - INTERVAL '%s hours'
                    ORDER BY block_number ASC
                """, (hours_back,))
                
                tokens = cur.fetchall()
                print(f"Checking {len(tokens)} recently deployed tokens for bonding status...")
                
                bonded_count = 0
                for token_address, deployment_block in tokens:
                    try:
                        info = self._check_bonding(token_address, deployment_block)
                        
                        if info['is_bonded']:
                            cur.execute("""
                                UPDATE token_deployments
                                SET lp_deployed = TRUE, pair_address = %s, bonded_at = %s,
                                    bonded_block_number = %s, bonding_error = NULL
                                WHERE token_address = %s
                            """, (info['pair_address'], info['timestamp'], 
                                 info['block_number'], token_address))
                            bonded_count += 1
                            print(f"Found bonded token: {token_address}")
                        else:
                            cur.execute("""
                                UPDATE token_deployments SET bonding_error = %s
                                WHERE token_address = %s
                            """, (info['error'], token_address))
                        
                        conn.commit()
                    except Exception:
                        continue
                
                print(f"Completed: {bonded_count} newly bonded tokens found")
        except Exception:
            pass
        finally:
            conn.close()
    
    def run(self, hours_back=24):
        """Main execution method - uses efficient event scanning first"""
        # First try the super efficient event scanning approach
        if self.scan_pair_events():
            print("Event scanning completed successfully")
        
        # Then check recently deployed tokens that might not have been caught
        self.update_bonding_status(hours_back)
        print("Bonding tracker completed")

def main():
    import sys
    tracker = BondingTracker()
    
    # Allow customizing how far back to check (default 24 hours)
    hours_back = 24
    if len(sys.argv) > 1:
        try:
            hours_back = int(sys.argv[1])
        except:
            pass
    
    tracker.run(hours_back)

if __name__ == "__main__":
    main()
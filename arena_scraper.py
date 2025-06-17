import os
import sys
import time
import json
import logging
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import backoff
from web3 import Web3

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arena_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class SubgraphMigrationTracker:
    def __init__(self, subgraph_url: str):
        """Initialize with your subgraph endpoint URL"""
        self.subgraph_url = subgraph_url
        self.migration_cache = {}
        
    def fetch_all_migrations(self, first: int = 1000, skip: int = 0) -> List[Dict[str, Any]]:
        """Fetch migration data from subgraph"""
        query = """
        {
          signerSets(first: %d, skip: %d, orderBy: blockTimestamp, orderDirection: desc) {
            id
            user
            signer
            previousSigner
            blockNumber
            blockTimestamp
            transactionHash
          }
        }
        """ % (first, skip)
        
        try:
            response = requests.post(
                self.subgraph_url,
                json={'query': query},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if 'errors' in data:
                logging.error(f"GraphQL errors: {data['errors']}")
                return []
                
            return data.get('data', {}).get('signerSets', [])
            
        except Exception as e:
            logging.error(f"Error fetching migrations from subgraph: {str(e)}")
            return []
    
    def get_migration_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get all migration mappings: old_address -> migration_data"""
        all_migrations = []
        skip = 0
        batch_size = 1000
        
        while True:
            migrations = self.fetch_all_migrations(first=batch_size, skip=skip)
            if not migrations:
                break
                
            all_migrations.extend(migrations)
            skip += batch_size
            
            # If we got less than batch_size, we've reached the end
            if len(migrations) < batch_size:
                break
                
            time.sleep(0.5)  # Be nice to the subgraph
        
        # Create mapping from old address to migration data
        migration_map = {}
        for migration in all_migrations:
            old_address = migration['previousSigner'].lower()
            new_address = migration['signer'].lower()
            
            migration_map[old_address] = {
                'old_address': old_address,
                'new_address': new_address,
                'user': migration['user'].lower(),
                'transaction_hash': migration['transactionHash'],
                'block_number': int(migration['blockNumber']),
                'block_timestamp': int(migration['blockTimestamp']),
                'migration_id': migration['id']
            }
        
        logging.info(f"Loaded {len(migration_map)} wallet migrations from subgraph")
        return migration_map
    
    def check_migration(self, address: str) -> Optional[Dict[str, Any]]:
        """Check if an address has been migrated"""
        address = address.lower()
        return self.migration_cache.get(address)

class ArenaScraper:
    """Main scraper class for Arena.trade API"""
    
    def __init__(self, batch_size: int = 100, delay: float = 1.5, subgraph_url: str = None):
        """Initialize the scraper with configuration"""
        self.api_url = "https://api.arena.trade/user_summary"
        self.batch_size = batch_size
        self.delay = delay
        self.db = Database()
        
        # Set up session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://arena.trade',
            'Referer': 'https://arena.trade/',
            'sec-ch-ua': '"Google Chrome";v="91", "Chromium";v="91"',
            'sec-ch-ua-mobile': '?0',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site'
        })
        
        # Initialize migration tracker
        if subgraph_url:
            self.migration_tracker = SubgraphMigrationTracker(subgraph_url)
            # Load all migrations at startup
            self.migration_tracker.migration_cache = self.migration_tracker.get_migration_mappings()
        else:
            logging.warning("No subgraph URL provided - migration tracking disabled")
            self.migration_tracker = None
        
    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, requests.exceptions.HTTPError),
        max_tries=5,
        max_time=300,
        giveup=lambda e: isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 403
    )
    def fetch_users(self, offset: int = 0) -> List[Dict[str, Any]]:
        """Fetch users from Arena.trade API with retry logic"""
        params = {
            'order': 'last_price.desc.nullslast',
            'limit': self.batch_size,
            'offset': offset
        }
        
        try:
            response = self.session.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Add delay to respect rate limits
            time.sleep(self.delay)
            
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logging.warning("Rate limit hit, backing off...")
                time.sleep(5)  # Additional delay for rate limits
            elif e.response.status_code == 403:
                logging.error("Access forbidden. Please check API access requirements.")
                raise
            raise
        except Exception as e:
            logging.error(f"Error fetching users: {str(e)}")
            raise

    def validate_user_data(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize user data"""
        try:
            # Validate wallet address
            if not Web3.is_address(user.get('user_address', '')):
                raise ValueError(f"Invalid wallet address: {user.get('user_address')}")
            
            # Convert timestamp to datetime
            last_updated = datetime.fromtimestamp(user.get('last_updated', 0))
            
            # Handle None values for numeric fields
            last_price = float(user.get('last_price', 0) or 0)
            traders_holding = int(user.get('traders_holding', 0) or 0)
            portfolio_total_pnl = float(user.get('portfolio_total_pnl', 0) or 0)
            
            user_address = Web3.to_checksum_address(user['user_address'])
            
            # Check for migration data
            migration_data = None
            original_address = None
            is_migrated = False
            
            if self.migration_tracker:
                # Check if this address is a migrated address (new address)
                for old_addr, migration_info in self.migration_tracker.migration_cache.items():
                    if migration_info['new_address'].lower() == user_address.lower():
                        migration_data = migration_info
                        original_address = Web3.to_checksum_address(migration_info['old_address'])
                        is_migrated = True
                        break
                
                # Also check if this is an old address that has been migrated from
                migration_from_this_addr = self.migration_tracker.check_migration(user_address)
                if migration_from_this_addr:
                    logging.info(f"Found old address that migrated: {user_address} -> {migration_from_this_addr['new_address']}")
            
            # Sanitize and validate other fields
            validated_user = {
                'user_address': user_address,
                'twitter_handle': user.get('twitter_handle', ''),
                'twitter_username': user.get('twitter_username', ''),
                'twitter_pfp_url': user.get('twitter_pfp_url', ''),
                'last_price': last_price,
                'traders_holding': traders_holding,
                'portfolio_total_pnl': portfolio_total_pnl,
                'last_updated': last_updated,
                'original_address': original_address,
                'is_migrated': is_migrated
            }
            
            # Add migration metadata if available
            if migration_data:
                validated_user['migration_data'] = migration_data
                
            return validated_user
            
        except Exception as e:
            logging.error(f"Error validating user data: {str(e)}")
            raise

    def process_users(self, users: List[Dict[str, Any]]) -> None:
        """Process and store user data"""
        validated_users = []
        for user in users:
            try:
                validated_user = self.validate_user_data(user)
                validated_users.append(validated_user)
                
                # Log migration info if found
                if validated_user.get('is_migrated'):
                    logging.info(f"Migrated wallet found: {validated_user['original_address']} -> {validated_user['user_address']}")
                    
            except Exception as e:
                logging.error(f"Error processing user {user.get('user_address')}: {str(e)}")
                continue
        
        if validated_users:
            self.db.upsert_users(validated_users)

    def fetch_groups_plus_recent(self, min_supply_eth=75000, limit=15, offset=0):
        url = "https://api.arena.trade/rpc/groups_plus_recent"
        params = {
            "in_min_supply_eth": min_supply_eth,
            "in_limit": limit,
            "in_offset": offset
        }
        headers = self.session.headers
        try:
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching groups_plus_recent: {e}")
            return []

    def log_new_wallets_from_groups(self):
        groups = self.fetch_groups_plus_recent()
        for group in groups:
            creator = group.get('creator_address')
            logging.info(f"Group creator wallet: {creator}")

    def sync_missing_migrated_wallets(self):
        """Find and sync wallet data for migrated addresses that might not be in the main API"""
        if not self.migration_tracker:
            logging.warning("Migration tracker not available - skipping migrated wallet sync")
            return
            
        logging.info("Checking for missing migrated wallet data...")
        
        # Get all new addresses from migrations
        new_addresses = [migration['new_address'] for migration in self.migration_tracker.migration_cache.values()]
        
        # Check which ones we don't have in our database
        missing_addresses = self.db.get_missing_addresses(new_addresses)
        
        if missing_addresses:
            logging.info(f"Found {len(missing_addresses)} migrated addresses not in database")
            
            # Try to fetch data for these addresses from the API
            # Note: This assumes the API accepts individual address queries
            # You may need to modify based on your API capabilities
            for address in missing_addresses:
                try:
                    # This is a placeholder - you'll need to implement based on your API
                    user_data = self.fetch_individual_user(address)
                    if user_data:
                        self.process_users([user_data])
                except Exception as e:
                    logging.error(f"Error fetching data for migrated address {address}: {str(e)}")

    def fetch_individual_user(self, address: str) -> Optional[Dict[str, Any]]:
        """Fetch individual user data - implement based on your API capabilities"""
        # This is a placeholder method - you'll need to implement this
        # based on whether your API supports individual address queries
        logging.warning(f"Individual user fetch not implemented for {address}")
        return None

    def run(self, limit: Optional[int] = None, continuous: bool = False, sync_migrations: bool = True) -> None:
        """Run the scraper with specified parameters"""
        # Log wallets from groups_plus_recent for comparison
        self.log_new_wallets_from_groups()
        
        # Sync missing migrated wallets if requested
        if sync_migrations:
            self.sync_missing_migrated_wallets()
        
        offset = 0
        total_processed = 0
        migration_count = 0
        
        try:
            while True:
                logging.info(f"Fetching users (offset: {offset}, batch size: {self.batch_size})")
                
                users = self.fetch_users(offset)
                if not users:
                    logging.info("No more users to process")
                    break
                
                # Count migrations in this batch
                batch_migrations = 0
                for user in users:
                    try:
                        validated_user = self.validate_user_data(user)
                        if validated_user.get('is_migrated'):
                            batch_migrations += 1
                    except:
                        pass
                
                migration_count += batch_migrations
                
                self.process_users(users)
                
                total_processed += len(users)
                logging.info(f"Processed {total_processed} users ({migration_count} migrations found)")
                
                if limit and total_processed >= limit:
                    logging.info(f"Reached limit of {limit} users")
                    break
                
                if not continuous and len(users) < self.batch_size:
                    logging.info("Reached end of available users")
                    break
                
                offset += self.batch_size
                
        except KeyboardInterrupt:
            logging.info("Scraper stopped by user")
        except Exception as e:
            logging.error(f"Error in scraper: {str(e)}")
        finally:
            logging.info(f"Final stats: {total_processed} users processed, {migration_count} migrations found")
            self.db.close()

class Database:
    """Database connection and operations"""
    
    def __init__(self):
        """Initialize database connection"""
        self.conn = None
        self._connect()
    
    def _connect(self) -> psycopg2.extensions.connection:
        """Create database connection"""
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT')
            )
            return self.conn
        except Exception as e:
            logging.error(f"Database connection error: {str(e)}")
            raise
    
    def upsert_users(self, users: List[Dict[str, Any]]) -> None:
        """Upsert user data into database"""
        if not users:
            return
            
        try:
            with self.conn.cursor() as cur:
                # Prepare data for upsert
                values = []
                for user in users:
                    values.append((
                        user['user_address'],
                        user['twitter_handle'],
                        user['twitter_username'],
                        user['twitter_pfp_url'],
                        user['last_price'],
                        user['traders_holding'],
                        user['portfolio_total_pnl'],
                        user['last_updated'],
                        user.get('original_address'),
                        user.get('is_migrated', False)
                    ))
                
                # Upsert users
                execute_values(cur, """
                    INSERT INTO arena_users (
                        user_address, twitter_handle, twitter_username, twitter_pfp_url,
                        last_price, traders_holding, portfolio_total_pnl, last_updated,
                        original_address, is_migrated
                    ) VALUES %s
                    ON CONFLICT (user_address) DO UPDATE SET
                        twitter_handle = EXCLUDED.twitter_handle,
                        twitter_username = EXCLUDED.twitter_username,
                        twitter_pfp_url = EXCLUDED.twitter_pfp_url,
                        last_price = EXCLUDED.last_price,
                        traders_holding = EXCLUDED.traders_holding,
                        portfolio_total_pnl = EXCLUDED.portfolio_total_pnl,
                        last_updated = EXCLUDED.last_updated,
                        original_address = EXCLUDED.original_address,
                        is_migrated = EXCLUDED.is_migrated
                """, values)
                
                self.conn.commit()
                
        except Exception as e:
            logging.error(f"Error upserting users: {str(e)}")
            self.conn.rollback()
            raise
    
    def get_missing_addresses(self, addresses: List[str]) -> List[str]:
        """Get list of addresses not in database"""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT user_address FROM arena_users 
                    WHERE user_address = ANY(%s)
                """, (addresses,))
                existing = {row[0] for row in cur.fetchall()}
                return [addr for addr in addresses if addr not in existing]
        except Exception as e:
            logging.error(f"Error getting missing addresses: {str(e)}")
            return addresses
    
    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Arena.trade API Scraper with Migration Support')
    parser.add_argument('--limit', type=int, help='Total number of users to scrape')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of users per batch')
    parser.add_argument('--delay', type=float, default=1.5, help='Delay between requests in seconds')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--subgraph-url', type=str, help='Subgraph endpoint URL for migration data')
    parser.add_argument('--no-sync-migrations', action='store_true', help='Skip syncing missing migrated wallets')
    return parser.parse_args()

def main() -> None:
    """Main entry point"""
    args = parse_args()
    
    # Get subgraph URL from args, environment, or use default
    subgraph_url = (args.subgraph_url or 
                   os.getenv('SUBGRAPH_URL') or 
                   'https://api.studio.thegraph.com/query/18408/signer-tracker/version/latest')
    
    logging.info(f"Using subgraph URL: {subgraph_url}")
    
    try:
        scraper = ArenaScraper(
            batch_size=args.batch_size,
            delay=args.delay,
            subgraph_url=subgraph_url
        )
        scraper.run(
            limit=args.limit,
            continuous=args.continuous,
            sync_migrations=not args.no_sync_migrations
        )
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
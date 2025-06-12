import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime
from psycopg2.extras import RealDictCursor
from db_connection import get_bonded_arena_tokens
from dexscreener_api import get_token_market_data

load_dotenv()

class MarketDataUpdater:
    def __init__(self):
        self.conn_params = {
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_NAME'), 
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'port': os.getenv('DB_PORT', 5432)
        }
    
    def _get_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(**self.conn_params)
        except:
            return None
    
    def _ensure_table(self):
        """Create table and add website column if needed"""
        conn = self._get_connection()
        if not conn:
            return False
            
        try:
            with conn.cursor() as cur:
                # Create table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS arena_market_data (
                        token_address VARCHAR(255) PRIMARY KEY,
                        token_name VARCHAR(255),
                        token_symbol VARCHAR(255),
                        market_cap BIGINT,
                        price_usd NUMERIC(20, 10),
                        volume_24h NUMERIC(20, 2),
                        liquidity_usd NUMERIC(20, 2),
                        website VARCHAR(255),
                        last_updated TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                
                # Add website column if missing
                cur.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'arena_market_data' AND column_name = 'website';
                """)
                
                if not cur.fetchone():
                    cur.execute("ALTER TABLE arena_market_data ADD COLUMN website VARCHAR(255);")
                
                conn.commit()
                return True
        except:
            return False
        finally:
            conn.close()
    
    def _get_bonded_tokens(self):
        """Get list of bonded token addresses"""
        try:
            bonded_tokens_df = get_bonded_arena_tokens()
            if bonded_tokens_df is None or bonded_tokens_df.empty:
                return []
            return bonded_tokens_df['token_address'].tolist()
        except:
            return []
    
    def _get_market_data(self, token_addresses):
        """Fetch market data from API"""
        try:
            return get_token_market_data(token_addresses, chain_id="avalanche") or {}
        except:
            return {}
    
    def _update_database(self, market_data):
        """Update database with market data"""
        conn = self._get_connection()
        if not conn:
            return
            
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for address, data in market_data.items():
                    try:
                        # Extract data
                        token_name = data.get('name', 'Unknown')
                        token_symbol = data.get('symbol', 'Unknown')
                        market_cap = int(data.get('market_cap')) if data.get('market_cap') is not None else None
                        price_usd = data.get('price_usd')
                        volume_24h = data.get('volume_24h')
                        liquidity_usd = data.get('liquidity_usd')
                        website = data.get('website')
                        current_time = datetime.now()
                        
                        # Check if record exists
                        cur.execute("SELECT token_address FROM arena_market_data WHERE token_address = %s", (address,))
                        
                        if cur.fetchone():
                            # Update existing
                            cur.execute("""
                                UPDATE arena_market_data 
                                SET token_name = %s, token_symbol = %s, market_cap = %s,
                                    price_usd = %s, volume_24h = %s, liquidity_usd = %s,
                                    website = %s, last_updated = %s
                                WHERE token_address = %s
                            """, (token_name, token_symbol, market_cap, price_usd, 
                                 volume_24h, liquidity_usd, website, current_time, address))
                        else:
                            # Insert new
                            cur.execute("""
                                INSERT INTO arena_market_data (
                                    token_address, token_name, token_symbol, market_cap,
                                    price_usd, volume_24h, liquidity_usd, website, last_updated
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (address, token_name, token_symbol, market_cap,
                                 price_usd, volume_24h, liquidity_usd, website, current_time))
                    except:
                        continue
                
                conn.commit()
        except:
            pass
        finally:
            conn.close()
    
    def update_market_data(self):
        """Main update process"""
        if not self._ensure_table():
            return
            
        token_addresses = self._get_bonded_tokens()
        if not token_addresses:
            return
            
        market_data = self._get_market_data(token_addresses)
        if not market_data:
            return
            
        self._update_database(market_data)
    
    def test_connection(self):
        """Test database connection"""
        conn = self._get_connection()
        if not conn:
            return False
            
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                
                cur.execute("SELECT current_database();")
                db_name = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' ORDER BY table_name;
                """)
                tables = [table[0] for table in cur.fetchall()]
                
                print(f"✓ PostgreSQL Version: {version}")
                print(f"✓ Connected to database: {db_name}")
                print(f"✓ Existing tables: {tables}")
                return True
        except:
            return False
        finally:
            conn.close()

def main():
    import sys
    updater = MarketDataUpdater()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        updater.test_connection()
    else:
        updater.update_market_data()

if __name__ == "__main__":
    main()
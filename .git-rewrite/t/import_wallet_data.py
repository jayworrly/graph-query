import pandas as pd
from db_connection import get_db_connection
import os
from sqlalchemy import text

def create_wallet_tables(engine):
    """Create necessary tables if they don't exist"""
    with engine.connect() as connection:
        # Create users table to track usernames across platforms
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                bio TEXT,
                is_verified BOOLEAN,
                avatar_url TEXT,
                twitter VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create wallets table to track all wallets and their platforms
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS wallets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                address VARCHAR(42) NOT NULL,
                platform VARCHAR(50) NOT NULL,  -- 'blub', 'wink', 'salvor'
                initial_balance_usd DECIMAL(20, 2),
                total_usd_sold DECIMAL(20, 2),
                total_collections INTEGER,
                total_nft_items INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Commit the changes
        connection.commit()

def import_blub_data(engine):
    """Import data from blub wallet CSV file"""
    try:
        # Read the CSV file
        df = pd.read_csv('blub/wallet_data.csv')
        
        # Clean and prepare the data
        df['address'] = df['address'].str.lower()  # Normalize addresses to lowercase
        df['username_norm'] = df['name'].astype(str).str.strip().str.lower()  # Normalize usernames
        
        with engine.connect() as connection:
            for _, row in df.iterrows():
                # First, ensure user exists
                user_result = connection.execute(text("""
                    INSERT INTO users (username, name, twitter)
                    VALUES (:username, :name, :twitter)
                    ON CONFLICT (username) DO UPDATE 
                    SET name = EXCLUDED.name,
                        twitter = EXCLUDED.twitter,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """), {
                    'username': row['username_norm'],
                    'name': row['name'],
                    'twitter': row['social']
                }).fetchone()
                
                # Then insert wallet
                connection.execute(text("""
                    INSERT INTO wallets (user_id, address, platform, initial_balance_usd, total_usd_sold)
                    VALUES (:user_id, :address, 'blub', :initial_balance_usd, :total_usd_sold)
                    ON CONFLICT (address, platform) DO UPDATE 
                    SET initial_balance_usd = EXCLUDED.initial_balance_usd,
                        total_usd_sold = EXCLUDED.total_usd_sold,
                        updated_at = CURRENT_TIMESTAMP
                """), {
                    'user_id': user_result[0],
                    'address': row['address'],
                    'initial_balance_usd': row['initial_balance_usd'],
                    'total_usd_sold': row['total_usd_sold']
                })
            
            connection.commit()
        print(f"Successfully processed {len(df)} records from blub wallet data")
        
    except Exception as e:
        print(f"Error importing blub data: {str(e)}")

def import_wink_data(engine):
    """Import data from wink wallet CSV file"""
    try:
        # Read the CSV file
        df = pd.read_csv('wink/wink_wallet_data.csv')
        
        # Clean and prepare the data
        df['address'] = df['address'].str.lower()  # Normalize addresses to lowercase
        df['username_norm'] = df['name'].astype(str).str.strip().str.lower()  # Normalize usernames
        
        with engine.connect() as connection:
            for _, row in df.iterrows():
                # First, ensure user exists
                user_result = connection.execute(text("""
                    INSERT INTO users (username, name, twitter)
                    VALUES (:username, :name, :twitter)
                    ON CONFLICT (username) DO UPDATE 
                    SET name = EXCLUDED.name,
                        twitter = EXCLUDED.twitter,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """), {
                    'username': row['username_norm'],
                    'name': row['name'],
                    'twitter': row['social']
                }).fetchone()
                
                # Then insert wallet
                connection.execute(text("""
                    INSERT INTO wallets (user_id, address, platform, initial_balance_usd, total_usd_sold)
                    VALUES (:user_id, :address, 'wink', :initial_balance_usd, :total_usd_sold)
                    ON CONFLICT (address, platform) DO UPDATE 
                    SET initial_balance_usd = EXCLUDED.initial_balance_usd,
                        total_usd_sold = EXCLUDED.total_usd_sold,
                        updated_at = CURRENT_TIMESTAMP
                """), {
                    'user_id': user_result[0],
                    'address': row['address'],
                    'initial_balance_usd': row['initial_balance_usd'],
                    'total_usd_sold': row['total_usd_sold']
                })
            
            connection.commit()
        print(f"Successfully processed {len(df)} records from wink wallet data")
        
    except Exception as e:
        print(f"Error importing wink data: {str(e)}")

def import_salvor_data(engine):
    """Import data from salvor wallet CSV file"""
    try:
        # Read the CSV file
        df = pd.read_csv('salvor/salvor_mass_collection.csv')
        
        # Clean and prepare the data
        df['wallet_address'] = df['wallet_address'].str.lower()  # Normalize addresses to lowercase
        df['username_norm'] = df['username'].astype(str).str.strip().str.lower()  # Normalize usernames
        
        # Handle is_verified field - convert NaN to False
        df['is_verified'] = df['is_verified'].fillna(False)
        df['is_verified'] = df['is_verified'].map({'True': True, 'False': False, True: True, False: False})
        
        # Convert numeric columns to integers
        df['total_collections'] = pd.to_numeric(df['total_collections'], errors='coerce').fillna(0).astype(int)
        df['total_nft_items'] = pd.to_numeric(df['total_nft_items'], errors='coerce').fillna(0).astype(int)
        
        with engine.connect() as connection:
            for _, row in df.iterrows():
                # First, ensure user exists
                user_result = connection.execute(text("""
                    INSERT INTO users (username, name, bio, is_verified, avatar_url, twitter)
                    VALUES (:username, :name, :bio, :is_verified, :avatar_url, :twitter)
                    ON CONFLICT (username) DO UPDATE 
                    SET name = EXCLUDED.name,
                        bio = EXCLUDED.bio,
                        is_verified = EXCLUDED.is_verified,
                        avatar_url = EXCLUDED.avatar_url,
                        twitter = EXCLUDED.twitter,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """), {
                    'username': row['username_norm'],
                    'name': row['name'],
                    'bio': row['bio'] if pd.notna(row['bio']) else None,
                    'is_verified': bool(row['is_verified']),
                    'avatar_url': row['avatar_url'] if pd.notna(row['avatar_url']) else None,
                    'twitter': row['twitter'] if pd.notna(row['twitter']) else None
                }).fetchone()
                
                # Then insert wallet
                connection.execute(text("""
                    INSERT INTO wallets (user_id, address, platform, total_collections, total_nft_items)
                    VALUES (:user_id, :address, 'salvor', :total_collections, :total_nft_items)
                    ON CONFLICT (address, platform) DO UPDATE 
                    SET total_collections = EXCLUDED.total_collections,
                        total_nft_items = EXCLUDED.total_nft_items,
                        updated_at = CURRENT_TIMESTAMP
                """), {
                    'user_id': user_result[0],
                    'address': row['wallet_address'],
                    'total_collections': row['total_collections'],
                    'total_nft_items': row['total_nft_items']
                })
            
            connection.commit()
        print(f"Successfully processed {len(df)} records from salvor wallet data")
        
    except Exception as e:
        print(f"Error importing salvor data: {str(e)}")

def main():
    # Get database connection
    engine = get_db_connection()
    if not engine:
        print("Failed to connect to database. Please check your database configuration.")
        return
    
    try:
        # Create tables
        print("Creating database tables...")
        create_wallet_tables(engine)
        
        # Import data
        print("\nImporting blub wallet data...")
        import_blub_data(engine)
        
        print("\nImporting wink wallet data...")
        import_wink_data(engine)
        
        print("\nImporting salvor wallet data...")
        import_salvor_data(engine)
        
        print("\nData import completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 
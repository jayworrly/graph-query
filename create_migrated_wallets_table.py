import os
import psycopg2
from dotenv import load_dotenv
from arena_scraper import SubgraphMigrationTracker
import requests

# Load environment variables
load_dotenv()

# Set up The Graph endpoint from .env
SUBGRAPH_URL = os.getenv('SUBGRAPH_URL')

# Function to fetch all migrations using cursor-based pagination (id_gt)
def fetch_all_migrations_cursor(subgraph_url, batch_size=1000):
    all_migrations = []
    last_id = ""
    while True:
        if last_id:
            query = f'''
            {{
              signerSets(first: {batch_size}, where: {{id_gt: "{last_id}"}}) {{
                id
                user
                signer
                previousSigner
                blockNumber
                blockTimestamp
                transactionHash
              }}
            }}
            '''
        else:
            query = f'''
            {{
              signerSets(first: {batch_size}) {{
                id
                user
                signer
                previousSigner
                blockNumber
                blockTimestamp
                transactionHash
              }}
            }}
            '''
        resp = requests.post(subgraph_url, json={'query': query}, headers={'Content-Type': 'application/json'})
        resp.raise_for_status()
        data = resp.json()
        batch = data['data']['signerSets']
        if not batch:
            break
        all_migrations.extend(batch)
        last_id = batch[-1]['id']
        if len(batch) < batch_size:
            break
    return all_migrations

# 1. Get all migration mappings from The Graph using cursor-based pagination
all_migrations = fetch_all_migrations_cursor(SUBGRAPH_URL, batch_size=1000)
print(f"Fetched {len(all_migrations)} migration events from The Graph.")

# Build migration_map as in get_migration_mappings
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

# 2. Get all wallet addresses and usernames from your database
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    dbname=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
cur = conn.cursor()
cur.execute("SELECT user_address, twitter_username FROM arena_users")
arena_usernames = {row[0].lower(): row[1] for row in cur.fetchall()}

# 3. Insert all migrations, labeling and adding usernames if in arena_users
for migration in migration_map.values():
    original_wallet = migration['old_address']
    users_wallet = migration['new_address']
    original_username = arena_usernames.get(original_wallet)
    users_username = arena_usernames.get(users_wallet)
    cur.execute("""
        INSERT INTO migrated_wallets (original_wallet, users_wallet, original_username, users_username)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (original_wallet, users_wallet) DO UPDATE SET
            original_username = EXCLUDED.original_username,
            users_username = EXCLUDED.users_username
    """, (original_wallet, users_wallet, original_username, users_username))
conn.commit()
cur.close()
conn.close()

print("migrated_wallets table populated with usernames.") 
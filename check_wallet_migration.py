import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_wallet_migration(wallet_address):
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cur = conn.cursor()
    query = """
        SELECT * FROM migrated_wallets
        WHERE LOWER(original_wallet) = LOWER(%s) OR LOWER(users_wallet) = LOWER(%s)
    """
    cur.execute(query, (wallet_address, wallet_address))
    rows = cur.fetchall()
    if not rows:
        print(f"No migration found for wallet: {wallet_address}")
    else:
        for row in rows:
            print("Migration record:")
            print(f"  id: {row[0]}")
            print(f"  original_wallet: {row[1]}")
            print(f"  users_wallet: {row[2]}")
            print(f"  original_username: {row[3]}")
            print(f"  users_username: {row[4]}")
            print("-" * 40)
    cur.close()
    conn.close()

if __name__ == "__main__":
    wallet = "0x1e320A12935461Bd2FB62f91bfADb019038c2eF6"
    check_wallet_migration(wallet) 
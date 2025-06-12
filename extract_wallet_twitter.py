import os
import psycopg2
from dotenv import load_dotenv

def extract_wallet_twitter_data():
    # Load environment variables
    load_dotenv()
    
    # Connect to the database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    # Query to get wallet addresses and Twitter handles
    query = """
    SELECT DISTINCT user_address, twitter_handle 
    FROM arena_users 
    WHERE user_address IS NOT NULL
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Format the results
    formatted_data = []
    for wallet, twitter in results:
        twitter_handle = twitter if twitter else 'N/A'
        formatted_data.append(f"({wallet}, '{twitter_handle}')")
    
    # Write to file
    with open('wallet_twitter_mapping.txt', 'w') as f:
        f.write("VALUES\n")
        f.write(",\n".join(formatted_data))
    
    conn.close()
    print(f"Successfully extracted {len(formatted_data)} wallet-Twitter mappings")

if __name__ == "__main__":
    extract_wallet_twitter_data() 
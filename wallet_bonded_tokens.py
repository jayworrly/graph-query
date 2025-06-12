import psycopg2
from typing import List, Dict, Any
import json
import os
from dotenv import load_dotenv
import requests
import time

def fetch_arena_groups(limit: int = 15, offset: int = 0, min_supply_eth: int = 75000) -> List[Dict]:
    """Fetch groups data from Arena.trade API"""
    url = f"https://api.arena.trade/rpc/groups_plus_recent"
    params = {
        "in_min_supply_eth": min_supply_eth,
        "in_limit": limit,
        "in_offset": offset
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://arena.trade',
        'Referer': 'https://arena.trade/'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching Arena groups: {str(e)}")
        return []

def get_wallet_bonded_tokens():
    # Load environment variables
    load_dotenv()
    
    # Connect to the database using environment variables
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    # Query to get wallet addresses and their bonded tokens
    query = """
    SELECT DISTINCT 
        td.deployer_wallet,
        td.token_address,
        td.token_name,
        td.token_symbol,
        u.twitter_handle,
        td.bonded_at
    FROM token_deployments td
    LEFT JOIN arena_users u ON td.deployer_wallet = u.user_address
    WHERE td.bonded_at IS NOT NULL
    ORDER BY td.deployer_wallet, td.bonded_at DESC
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Organize results by wallet
    wallet_data = {}
    for wallet, token_address, token_name, token_symbol, twitter_handle, bonded_at in results:
        if wallet not in wallet_data:
            wallet_data[wallet] = {
                'twitter_handle': twitter_handle if twitter_handle else 'N/A',
                'bonded_tokens': []
            }
        
        wallet_data[wallet]['bonded_tokens'].append({
            'token_address': token_address,
            'token_name': token_name,
            'token_symbol': token_symbol,
            'bonded_at': bonded_at.isoformat() if bonded_at else None
        })
    
    # Fetch additional data from Arena.trade API
    arena_groups = fetch_arena_groups()
    for group in arena_groups:
        creator_address = group.get('creator_address')
        if creator_address:
            if creator_address not in wallet_data:
                wallet_data[creator_address] = {
                    'twitter_handle': group.get('creator_twitter_handle', 'N/A'),
                    'bonded_tokens': []
                }
            
            # Add token if it's not already in the list
            token_address = group.get('token_contract_address')
            if token_address:
                token_exists = any(t['token_address'] == token_address 
                                 for t in wallet_data[creator_address]['bonded_tokens'])
                if not token_exists:
                    wallet_data[creator_address]['bonded_tokens'].append({
                        'token_address': token_address,
                        'token_name': group.get('token_name', ''),
                        'token_symbol': group.get('token_symbol', ''),
                        'bonded_at': None  # API doesn't provide bonding time
                    })
    
    # Write to JSON file
    with open('wallet_bonded_tokens.json', 'w') as f:
        json.dump(wallet_data, f, indent=2)
    
    # Write to text file in a readable format
    with open('wallet_bonded_tokens.txt', 'w') as f:
        for wallet, data in wallet_data.items():
            f.write(f"Wallet: {wallet}\n")
            f.write(f"Twitter: {data['twitter_handle']}\n")
            f.write("Bonded Tokens:\n")
            for token in data['bonded_tokens']:
                f.write(f"  - {token['token_name']} ({token['token_symbol']}): {token['token_address']}\n")
                if token['bonded_at']:
                    f.write(f"    Bonded at: {token['bonded_at']}\n")
            f.write("\n")
    
    conn.close()
    print(f"Successfully processed {len(wallet_data)} wallets with bonded tokens")

if __name__ == "__main__":
    get_wallet_bonded_tokens() 
import os
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional
import time

# Load environment variables
load_dotenv()

def get_token_market_data(token_addresses: List[str], chain_id: str = "avalanche") -> Optional[Dict]:
    """
    Fetch market data for tokens from Dexscreener API.
    
    Args:
        token_addresses: List of token addresses to fetch data for
        chain_id: Chain ID (default: "avalanche")
    
    Returns:
        Dictionary mapping token addresses to their market data, or None if request fails
    """
    try:
        base_url = "https://api.dexscreener.com/latest/dex"
        all_market_data = {}
        
        for address in token_addresses:
            address_lower = address.lower()
            url = f"{base_url}/search?q={address_lower}"
            
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                
                if 'pairs' in data and data['pairs']:
                    avalanche_pairs = [
                        pair for pair in data['pairs'] 
                        if pair.get('chainId', '').lower() == chain_id.lower() and 
                           pair.get('baseToken', {}).get('address', '').lower() == address_lower
                    ]

                    most_liquid_pair = None
                    max_liquidity = -1
                    
                    if avalanche_pairs:
                        for pair in avalanche_pairs:
                            current_liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                            if current_liquidity > max_liquidity:
                                max_liquidity = current_liquidity
                                most_liquid_pair = pair
                                
                    if most_liquid_pair:
                        market_cap = None
                        if most_liquid_pair.get('marketCap') is not None:
                            market_cap = float(most_liquid_pair['marketCap'])
                        elif most_liquid_pair.get('fdv') is not None:
                            market_cap = float(most_liquid_pair['fdv'])

                        all_market_data[address_lower] = {
                            'name': most_liquid_pair['baseToken'].get('name', 'Unknown'),
                            'symbol': most_liquid_pair['baseToken'].get('symbol', 'Unknown'),
                            'market_cap': market_cap,
                            'price_usd': float(most_liquid_pair.get('priceUsd', 0)) if most_liquid_pair.get('priceUsd') else None,
                            'volume_24h': float(most_liquid_pair.get('volume', {}).get('h24', 0)) if most_liquid_pair.get('volume', {}).get('h24') else None,
                            'liquidity_usd': float(most_liquid_pair.get('liquidity', {}).get('usd', 0)) if most_liquid_pair.get('liquidity', {}).get('usd') else None
                        }
                
                time.sleep(0.1)

            except requests.exceptions.RequestException:
                continue
            except Exception:
                continue
        
        return all_market_data if all_market_data else None
        
    except Exception:
        return None


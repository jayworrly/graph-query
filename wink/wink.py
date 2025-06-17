import json
import csv
import pandas as pd
from typing import List, Dict, Any

def extract_wallet_data(json_file_path: str = 'wink_data.json', output_format: str = 'csv') -> List[Dict[str, str]]:
    """
    Extract wallet addresses, names, and social media links from ALL wallets in JSON file.
    
    Args:
        json_file_path (str): Path to the JSON file containing wallet data
        output_format (str): Output format - 'csv', 'json', or 'console'
    
    Returns:
        List[Dict[str, str]]: List of extracted wallet data from ALL wallets
    """
    try:
        print(f"Reading JSON file: {json_file_path}")
        
        # Read the JSON file
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Handle different JSON structures
        if isinstance(data, list):
            wallet_entries = data
            print(f"Found {len(wallet_entries)} wallets to process")
        elif isinstance(data, dict):
            # If it's a single object, put it in a list
            wallet_entries = [data]
            print("Found 1 wallet to process")
        else:
            raise ValueError("JSON data should be either a list or a single object")
        
        extracted_data = []
        
        print("Processing all wallets...")
        for i, entry in enumerate(wallet_entries, 1):
            # Extract the required fields
            wallet_info = {
                'address': entry.get('address', 'N/A'),
                'name': entry.get('name', 'N/A'),
                'social': entry.get('social', 'N/A'),
                'index': entry.get('index', 'N/A'),
                'initial_balance_usd': entry.get('initial_balance_usd', 0),
                'total_usd_sold': entry.get('total_usd_sold', 0)
            }
            extracted_data.append(wallet_info)
            
            # Show progress for large files
            if i % 100 == 0:
                print(f"  Processed {i}/{len(wallet_entries)} wallets...")
        
        print(f"✓ Successfully processed ALL {len(extracted_data)} wallets from the file")
        
        # Output the data in the specified format
        if output_format.lower() == 'csv':
            output_to_csv(extracted_data)
        elif output_format.lower() == 'json':
            output_to_json(extracted_data)
        elif output_format.lower() == 'console':
            output_to_console(extracted_data)
        
        return extracted_data
        
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def output_to_csv(data: List[Dict[str, str]], filename: str = 'wink_wallet_data.csv'):
    """Save extracted data to CSV file."""
    if not data:
        print("No data to save.")
        return
    
    try:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
        print(f"Total wallets extracted: {len(data)}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def output_to_json(data: List[Dict[str, str]], filename: str = 'wink_wallet_data_extracted.json'):
    """Save extracted data to JSON file."""
    if not data:
        print("No data to save.")
        return
    
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
        print(f"Total wallets extracted: {len(data)}")
    except Exception as e:
        print(f"Error saving to JSON: {e}")

def output_to_console(data: List[Dict[str, str]]):
    """Print extracted data to console."""
    if not data:
        print("No data found.")
        return
    
    print("\n" + "="*80)
    print("EXTRACTED WALLET DATA")
    print("="*80)
    
    for i, wallet in enumerate(data, 1):
        print(f"\n{i}. Wallet Information:")
        print(f"   Address: {wallet['address']}")
        print(f"   Name: {wallet['name']}")
        print(f"   Social: {wallet['social']}")
        print(f"   Index: {wallet['index']}")
        print(f"   Initial Balance USD: ${wallet['initial_balance_usd']}")
        print(f"   Total USD Sold: ${wallet['total_usd_sold']}")
        print("-" * 50)
    
    print(f"\nTotal wallets processed: {len(data)}")

def extract_specific_fields_only(json_file_path: str = 'wink_data.json') -> List[Dict[str, str]]:
    """
    Extract only wallet, social, and name fields from ALL wallets (minimal extraction).
    
    Args:
        json_file_path (str): Path to the JSON file containing all wallet data
    
    Returns:
        List[Dict[str, str]]: List with only address, name, and social fields from ALL wallets
    """
    try:
        print(f"Reading JSON file for minimal extraction: {json_file_path}")
        
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if isinstance(data, list):
            wallet_entries = data
            print(f"Found {len(wallet_entries)} wallets to process")
        elif isinstance(data, dict):
            wallet_entries = [data]
            print("Found 1 wallet to process")
        else:
            raise ValueError("JSON data should be either a list or a single object")
        
        minimal_data = []
        print("Extracting minimal data from all wallets...")
        
        for i, entry in enumerate(wallet_entries, 1):
            minimal_info = {
                'wallet_address': entry.get('address', 'N/A'),
                'name': entry.get('name', 'N/A'),
                'social_media': entry.get('social', 'N/A')
            }
            minimal_data.append(minimal_info)
            
            # Show progress for large files
            if i % 100 == 0:
                print(f"  Processed {i}/{len(wallet_entries)} wallets...")
        
        print(f"✓ Successfully extracted data from ALL {len(minimal_data)} wallets")
        return minimal_data
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    """Main function to demonstrate usage - processes ALL wallets in your JSON file."""
    print("="*60)
    print("WINK WALLET DATA EXTRACTOR - Processes ALL wallets in JSON file")
    print("="*60)
    
    # Example usage
    json_file = input("\nEnter the path to your JSON file containing all wallet data (default: wink_data.json): ").strip()
    
    if not json_file:
        json_file = 'wink_data.json'
        print("No file path provided. Using default: wink_data.json")
    
    print("\nChoose output format:")
    print("1. CSV file (recommended for spreadsheet use)")
    print("2. JSON file") 
    print("3. Console output")
    print("4. Minimal extraction (wallet, name, social only)")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        extract_wallet_data(json_file, 'csv')
    elif choice == '2':
        extract_wallet_data(json_file, 'json')
    elif choice == '3':
        extract_wallet_data(json_file, 'console')
    elif choice == '4':
        minimal_data = extract_specific_fields_only(json_file)
        output_to_console(minimal_data)
        
        # Also save minimal data to CSV
        if minimal_data:
            df = pd.DataFrame(minimal_data)
            df.to_csv('wink_minimal_wallet_data.csv', index=False)
            print("\nMinimal data also saved to: wink_minimal_wallet_data.csv")
    else:
        print("Invalid choice. Defaulting to console output.")
        extract_wallet_data(json_file, 'console')

if __name__ == "__main__":
    main() 
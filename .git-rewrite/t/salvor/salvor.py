import requests
import json

class SalvorWorkingCollector:
    def __init__(self):
        self.session = requests.Session()
        
        # Working headers extracted from browser dev tools
        self.working_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Authorization': 'Bearer dc60f312-ccc6-44fb-8840-045cc0be2d05',
            'Visitor-Id': 'a5a32739-bd31-4101-a624-d3db0a5881b0',
            'Priority': 'u=1, i',
            'Referer': 'https://salvor.io/jaywurrly',
            'Sec-Ch-Ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
    
    def test_with_browser_headers(self, username: str):
        """
        Test API call with browser-like headers
        """
        url = f"https://salvor.io/api/users/{username}"
        
        try:
            response = self.session.get(url, headers=self.working_headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Content-Length: {response.headers.get('content-length')}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\nResponse structure:")
                print(f"Success: {data.get('success')}")
                print(f"Message: {data.get('message')}")
                print(f"Data length: {len(data.get('data', []))}")
                
                if data.get('data'):
                    print(f"\n🎉 SUCCESS! Got data for {username}")
                    print(json.dumps(data, indent=2))
                    return data
                else:
                    print(f"Still empty data array")
            else:
                print(f"Error: {response.status_code}")
                print(response.text[:200])
                
        except Exception as e:
            print(f"Error: {e}")
        
        return None
    
    def extract_user_data(self, user_data):
        """
        Extract comprehensive information from user API response
        """
        if not user_data or not user_data.get('data'):
            return None
        
        # The data is directly in the response
        data = user_data['data']
        if isinstance(data, list):
            if len(data) == 0:
                return None
            user_info = data[0]
        else:
            user_info = data
        
        # Extract main user information
        extracted = {
            'uuid': user_info.get('uuid', 'N/A'),
            'username': user_info.get('username', 'N/A'),
            'name': user_info.get('name', 'N/A'),
            'wallet_address': user_info.get('address', 'N/A'),
            'type': user_info.get('type', 'N/A'),
            'bio': user_info.get('bio', 'N/A'),
            'avatar_url': user_info.get('avatarUrl', 'N/A'),
            'is_verified': user_info.get('isVerified', False),
            'is_email_verified': user_info.get('isEmailVerified', False),
            'status': user_info.get('status', 'N/A'),
            'twitter_link': user_info.get('links', {}).get('twitter', 'N/A'),
            'total_collections': len(user_info.get('nftCollections', [])),
            'total_nft_items': sum(col.get('itemCount', 0) for col in user_info.get('nftCollections', [])),
        }
        
        # Extract NFT collection details
        collections = user_info.get('nftCollections', [])
        collection_addresses = []
        verified_collections = []
        salvor_collections = []
        
        for col in collections:
            if col.get('address'):
                collection_addresses.append(col['address'])
            if col.get('isVerified'):
                verified_collections.append(col.get('name', 'Unknown'))
            if col.get('isSalvor'):
                salvor_collections.append(col.get('name', 'Unknown'))
        
        extracted.update({
            'collection_addresses': '; '.join(collection_addresses),
            'verified_collections': '; '.join(verified_collections),
            'salvor_collections': '; '.join(salvor_collections),
            'verified_collection_count': len(verified_collections),
            'salvor_collection_count': len(salvor_collections),
        })
        
        return extracted
    
    def collect_multiple_users(self, usernames):
        """
        Collect data for multiple users
        """
        collected = []
        total = len(usernames)
        
        print(f"\n=== COLLECTING {total} USERS ===")
        
        for i, username in enumerate(usernames, 1):
            print(f"\nProcessing {i}/{total}: {username}")
            
            data = self.test_with_browser_headers(username)
            if data:
                extracted = self.extract_user_data(data)
                if extracted:
                    collected.append(extracted)
                    print(f"✅ Collected: {extracted['username']} - {extracted['wallet_address']}")
                else:
                    print(f"❌ Could not extract data for {username}")
            else:
                print(f"❌ No data found for {username}")
            
            # Rate limiting
            import time
            time.sleep(1)  # 1 second between requests
        
        return collected
    
    def save_to_csv(self, data, filename='salvor_users.csv'):
        """
        Save collected data to CSV
        """
        if not data:
            print("No data to save")
            return
        
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        
        print(f"\n💾 Data saved to {filename}")
        print(f"📊 Total users collected: {len(data)}")
    
    def discover_users(self):
        """
        Try to discover valid usernames using various methods
        """
        print("\n=== USER DISCOVERY ===")
        
        # Test known usernames
        known_users = ['jaywurrly', 'jayworrly', 'skeptic', 'CG777']
        
        # Test common patterns
        common_patterns = [
            'admin', 'test', 'demo', 'user', 'creator', 'artist',
            'alice', 'bob', 'charlie', 'dave', 'eve',
            'user1', 'user2', 'user3', 'player1', 'collector'
        ]
        
        all_usernames = known_users + common_patterns
        valid_users = []
        
        for username in all_usernames:
            print(f"Testing: {username}")
            data = self.test_with_browser_headers(username)
            if data and data.get('data'):
                valid_users.append(username)
                print(f"✅ Found valid user: {username}")
            
            import time
            time.sleep(0.5)  # Brief delay
        
        return valid_users
    
    def create_detailed_collections_report(self, user_data, username):
        """
        Create a detailed report of all NFT collections for a user
        """
        import csv
        
        if not user_data or not user_data.get('data'):
            return
        
        data = user_data['data']
        if isinstance(data, list):
            user_info = data[0] if data else {}
        else:
            user_info = data
        
        collections = user_info.get('nftCollections', [])
        if not collections:
            print(f"No collections found for {username}")
            return
        
        # Create detailed collections CSV
        filename = f"{username}_collections_detailed.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'username', 'user_wallet', 'collection_id', 'collection_name', 
                'collection_address', 'symbol', 'type', 'item_count', 
                'is_verified', 'is_salvor', 'description', 'image_url'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            user_wallet = user_info.get('address', 'N/A')
            
            for col in collections:
                writer.writerow({
                    'username': username,
                    'user_wallet': user_wallet,
                    'collection_id': col.get('id', 'N/A'),
                    'collection_name': col.get('name', 'N/A'),
                    'collection_address': col.get('address', 'N/A'),
                    'symbol': col.get('symbol', 'N/A'),
                    'type': col.get('type', 'N/A'),
                    'item_count': col.get('itemCount', 0),
                    'is_verified': col.get('isVerified', False),
                    'is_salvor': col.get('isSalvor', False),
                    'description': col.get('description', 'N/A'),
                    'image_url': col.get('imageUrl', 'N/A'),
                })
        
        print(f"📊 Detailed collections saved to {filename}")
        print(f"📈 Total collections for {username}: {len(collections)}")
        
        return filename
    
    def bulk_analysis_mode(self, usernames):
        """
        Comprehensive analysis mode for multiple users
        """
        print(f"\n🔍 BULK ANALYSIS MODE - {len(usernames)} USERS")
        print("="*60)
        
        all_users_data = []
        all_collections_data = []
        
        for i, username in enumerate(usernames, 1):
            print(f"\n[{i}/{len(usernames)}] Processing: {username}")
            
            user_data = self.test_with_browser_headers(username)
            if user_data and user_data.get('data'):
                # Extract user summary
                extracted = self.extract_user_data(user_data)
                if extracted:
                    all_users_data.append(extracted)
                    print(f"✅ {username}: {extracted['wallet_address']} ({extracted['total_collections']} collections)")
                    
                    # Create detailed collections report
                    self.create_detailed_collections_report(user_data, username)
                else:
                    print(f"❌ Could not extract data for {username}")
            else:
                print(f"❌ No data found for {username}")
            
            import time
            time.sleep(1)  # Rate limiting
        
        # Save summary report
        if all_users_data:
            self.save_to_csv(all_users_data, 'salvor_users_summary.csv')
            
            # Print analysis summary
            print(f"\n📋 ANALYSIS SUMMARY:")
            print(f"👥 Total users collected: {len(all_users_data)}")
            print(f"💰 Total NFT items across all users: {sum(u['total_nft_items'] for u in all_users_data)}")
            print(f"🏆 Verified users: {sum(1 for u in all_users_data if u['is_verified'])}")
            
            # Top collectors
            top_collectors = sorted(all_users_data, key=lambda x: x['total_nft_items'], reverse=True)[:5]
            print(f"\n🥇 TOP 5 NFT COLLECTORS:")
            for i, user in enumerate(top_collectors, 1):
                print(f"  {i}. {user['username']}: {user['total_nft_items']} items ({user['total_collections']} collections)")
        
        return all_users_data

def main():
    print("🎉 SALVOR USER DATA COLLECTOR - WORKING VERSION! 🎉")
    print("=" * 60)
    
    collector = SalvorWorkingCollector()
    
    # Test with the known working user first
    print("Testing with known user 'jaywurrly'...")
    test_result = collector.test_with_browser_headers("jaywurrly")
    
    if test_result and test_result.get('data'):
        print("\n🎉 SUCCESS! The headers are working!")
        print("Here's what the API returns:")
        
        # Show the structure of the response
        data_sample = test_result.get('data', [])
        if data_sample:
            print(json.dumps(data_sample[0] if isinstance(data_sample, list) else data_sample, indent=2))
        
        # Ask user what they want to do
        print("\n" + "="*60)
        print("🚀 CHOOSE YOUR COLLECTION STRATEGY:")
        print("1. 📝 Collect specific users (provide username list)")
        print("2. 🔍 Auto-discover and collect valid users") 
        print("3. 📊 Detailed analysis of single user")
        print("4. 🎯 Bulk analysis mode (comprehensive data)")
        print("5. 📋 Just show data structure")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            # Manual username input
            print("\n📝 MANUAL USER COLLECTION")
            print("Enter usernames to collect (one per line, empty line to finish):")
            usernames = []
            while True:
                username = input("Username: ").strip()
                if not username:
                    break
                usernames.append(username)
            
            if usernames:
                print(f"\n🚀 Collecting data for {len(usernames)} users...")
                collected_data = collector.collect_multiple_users(usernames)
                if collected_data:
                    collector.save_to_csv(collected_data)
                    
                    print("\n📋 COLLECTION SUMMARY:")
                    for user in collected_data:
                        print(f"👤 {user['username']}: {user['wallet_address']} ({user['total_collections']} collections)")
        
        elif choice == "2":
            # Auto-discovery mode
            print("\n🔍 AUTO-DISCOVERY MODE")
            print("Discovering valid users...")
            valid_users = collector.discover_users()
            
            if valid_users:
                print(f"\nFound {len(valid_users)} valid users: {valid_users}")
                collect_all = input("Collect data for all found users? (y/n): ").lower().strip()
                
                if collect_all == 'y':
                    collected_data = collector.collect_multiple_users(valid_users)
                    if collected_data:
                        collector.save_to_csv(collected_data)
        
        elif choice == "3":
            # Detailed single user analysis
            print("\n📊 DETAILED USER ANALYSIS")
            target_user = input("Enter username for detailed analysis: ").strip()
            
            if target_user:
                user_data = collector.test_with_browser_headers(target_user)
                if user_data and user_data.get('data'):
                    print(f"\n🎯 DETAILED ANALYSIS FOR: {target_user}")
                    
                    # Show extracted summary
                    extracted = collector.extract_user_data(user_data)
                    if extracted:
                        print("\n👤 USER PROFILE:")
                        for key, value in extracted.items():
                            if key not in ['collection_addresses']:  # Skip long address list
                                print(f"  {key}: {value}")
                    
                    # Create detailed collections report
                    collector.create_detailed_collections_report(user_data, target_user)
                    
                    print(f"\n✅ Complete analysis saved for {target_user}")
                else:
                    print(f"❌ No data found for {target_user}")
        
        elif choice == "4":
            # Bulk analysis mode
            print("\n🎯 BULK ANALYSIS MODE")
            print("This will create comprehensive reports for multiple users")
            
            # Get usernames for bulk analysis
            print("Enter usernames for bulk analysis (one per line, empty line to finish):")
            usernames = []
            while True:
                username = input("Username: ").strip()
                if not username:
                    break
                usernames.append(username)
            
            if usernames:
                collector.bulk_analysis_mode(usernames)
            else:
                print("❌ No usernames provided")
        
        elif choice == "5":
            # Just analyze structure
            print("\n📋 DATA STRUCTURE ANALYSIS")
            extracted = collector.extract_user_data(test_result)
            if extracted:
                print("\n🔍 Extracted user data fields:")
                for key, value in extracted.items():
                    print(f"  {key}: {value}")
                    
                print(f"\n📊 Sample NFT Collections:")
                collections = test_result['data'].get('nftCollections', [])[:3]  # Show first 3
                for i, col in enumerate(collections, 1):
                    print(f"  {i}. {col.get('name', 'Unknown')} ({col.get('itemCount', 0)} items)")
                    print(f"     Address: {col.get('address', 'N/A')}")
                    print(f"     Verified: {col.get('isVerified', False)}")
                    print()
        
        print(f"\n🎉 Collection complete! Check your CSV files for results.")
        print(f"💡 TIP: Each user's detailed collections are saved separately")
    
    else:
        print("\n❌ Headers still not working correctly.")
        print("The Authorization token might have expired.")
        print("Please refresh the page and copy new headers.")

if __name__ == "__main__":
    main()

# INSTRUCTIONS FOR EXTRACTING HEADERS:
"""
In your browser dev tools:

1. Click on the successful request to https://salvor.io/api/users/jayworrly
2. In the Headers tab, look for "Request Headers"
3. Copy ALL of them, especially:
   - Cookie (if present)
   - Authorization (if present)  
   - User-Agent
   - Referer
   - Any X-* custom headers

4. Replace the working_headers dictionary above with the real ones

Example of what you might see:
{
    'Cookie': 'session_id=abc123; csrf_token=def456',
    'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...',
    'X-CSRF-Token': 'some-token-here',
    'User-Agent': 'Mozilla/5.0...',
    'Referer': 'https://salvor.io/',
    'Accept': 'application/json'
}
"""
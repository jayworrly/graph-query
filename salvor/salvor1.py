import requests
import json
import time
import csv
import threading
from typing import List, Dict, Set
from concurrent.futures import ThreadPoolExecutor
import random

class SalvorMassCollector:
    def __init__(self):
        self.session = requests.Session()
        self.discovered_users = set()  # Track unique users found
        self.collected_data = []
        self.failed_requests = []
        
        # Working headers from browser
        self.working_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Authorization': 'Bearer dc60f312-ccc6-44fb-8840-045cc0be2d05',
            'Visitor-Id': 'a5a32739-bd31-4101-a624-d3db0a5881b0',
            'Priority': 'u=1, i',
            'Referer': 'https://salvor.io/',
            'Sec-Ch-Ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
    
    def discover_via_user_listing(self):
        """
        Try to find user listing endpoints with authentication - OPTIMIZED VERSION
        """
        print("\n🔍 METHOD 1: USER LISTING ENDPOINTS")
        print("="*50)
        
        # Test main endpoint first
        main_endpoint = "/api/users"
        print(f"Testing main endpoint: {main_endpoint}")
        
        try:
            url = f"https://salvor.io{main_endpoint}"
            response = self.session.get(url, headers=self.working_headers, params={"page": 1, "limit": 20}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data') and data['data'].get('row'):
                    print(f"🎉 SUCCESS! Found working endpoint: {main_endpoint}")
                    print(f"Sample user: {data['data']['row'][0]['username']} - {data['data']['row'][0]['address']}")
                    
                    # Get ALL users from this endpoint efficiently
                    print(f"\n📥 COLLECTING ALL USERS FROM {main_endpoint}")
                    all_users = self.collect_all_users_from_endpoint(url)
                    
                    print(f"✅ Collected {len(all_users)} total users from main endpoint")
                    return all_users
                else:
                    print(f"❌ Main endpoint returned empty data")
            else:
                print(f"❌ Main endpoint failed: Status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error testing main endpoint: {e}")
        
        # If main endpoint fails, try alternatives
        print("\n🔍 Trying alternative endpoints...")
        alternative_endpoints = [
            "/api/users/list",
            "/api/users/all", 
            "/api/profiles",
            "/api/creators",
        ]
        
        for endpoint in alternative_endpoints:
            try:
                url = f"https://salvor.io{endpoint}"
                response = self.session.get(url, headers=self.working_headers, params={"page": 1, "limit": 20}, timeout=5)
                time.sleep(0.5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('data'):
                        print(f"✅ Found alternative endpoint: {endpoint}")
                        all_users = self.collect_all_users_from_endpoint(url)
                        return all_users
                        
            except Exception as e:
                continue
        
        print("❌ No working user listing endpoints found")
        return set()
    
    def collect_all_users_from_endpoint(self, url):
        """
        Efficiently collect ALL users from a paginated endpoint
        """
        all_users = set()
        page = 1
        consecutive_empty = 0
        
        print(f"📊 Starting pagination collection...")
        
        while consecutive_empty < 3:  # Stop after 3 consecutive empty pages
            try:
                params = {"page": page, "limit": 100}  # Use larger page size for efficiency
                response = self.session.get(url, headers=self.working_headers, params=params, timeout=10)
                time.sleep(0.3)  # Faster rate limiting for mass collection
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('success') and data.get('data') and data['data'].get('row'):
                        users_on_page = data['data']['row']
                        page_user_count = len(users_on_page)
                        
                        # Extract usernames from this page
                        for user in users_on_page:
                            if user.get('username'):
                                all_users.add(user['username'])
                        
                        print(f"  📄 Page {page}: {page_user_count} users (Total: {len(all_users)})")
                        
                        if page_user_count == 0:
                            consecutive_empty += 1
                        else:
                            consecutive_empty = 0
                            
                        page += 1
                        
                        # Safety limit
                        if page > 200:
                            print("⚠️  Reached safety limit of 200 pages")
                            break
                            
                    else:
                        consecutive_empty += 1
                        page += 1
                else:
                    print(f"❌ Error on page {page}: Status {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"❌ Error collecting page {page}: {e}")
                consecutive_empty += 1
                page += 1
        
        print(f"✅ Pagination complete. Found {len(all_users)} unique users")
        return all_users
    
    def discover_via_collections(self):
        """
        Discover users by browsing collections and extracting owner information
        """
        print("\n🔍 METHOD 2: COLLECTION BROWSING")
        print("="*50)
        
        collection_endpoints = [
            "/api/collections",
            "/api/collections/browse", 
            "/api/collections/trending",
            "/api/collections/recent",
            "/api/nft/collections",
            "/api/marketplace/collections",
        ]
        
        found_users = set()
        
        for endpoint in collection_endpoints:
            try:
                url = f"https://salvor.io{endpoint}"
                print(f"Testing collections: {endpoint}")
                
                response = self.session.get(url, headers=self.working_headers, timeout=10)
                time.sleep(0.5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('data'):
                        print(f"✅ Found collections data at {endpoint}")
                        
                        # Extract user IDs from collections
                        collections = data['data'] if isinstance(data['data'], list) else [data['data']]
                        
                        for collection in collections:
                            if isinstance(collection, dict):
                                # Look for user/creator information
                                user_id = collection.get('userId')
                                creator = collection.get('creator')
                                owner = collection.get('owner')
                                
                                if user_id:
                                    # Try to get user by ID
                                    user_data = self.get_user_by_id(user_id)
                                    if user_data:
                                        found_users.add(user_data)
                                
                                if creator:
                                    found_users.add(creator)
                                    
                                if owner:
                                    found_users.add(owner)
                
            except Exception as e:
                print(f"Error with collections {endpoint}: {e}")
        
        print(f"📊 Found {len(found_users)} users via collections")
        return found_users
    
    def discover_via_activity_feeds(self):
        """
        Discover users through activity/transaction feeds
        """
        print("\n🔍 METHOD 3: ACTIVITY FEEDS")
        print("="*50)
        
        activity_endpoints = [
            "/api/activity",
            "/api/activity/recent", 
            "/api/transactions",
            "/api/sales",
            "/api/marketplace/activity",
            "/api/feed",
            "/api/events",
            "/api/listings",
            "/api/offers",
        ]
        
        found_users = set()
        
        for endpoint in activity_endpoints:
            try:
                url = f"https://salvor.io{endpoint}"
                print(f"Testing activity: {endpoint}")
                
                # Try with different pagination
                for page in range(1, 6):  # First 5 pages
                    params = {"page": page, "limit": 100}
                    response = self.session.get(url, headers=self.working_headers, params=params, timeout=10)
                    time.sleep(0.5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('data'):
                            print(f"✅ Found activity data at {endpoint} page {page}")
                            
                            # Extract users from activity
                            activities = data['data'] if isinstance(data['data'], list) else [data['data']]
                            
                            for activity in activities:
                                if isinstance(activity, dict):
                                    # Look for user references
                                    for key in ['buyer', 'seller', 'user', 'from', 'to', 'creator', 'owner']:
                                        if activity.get(key):
                                            found_users.add(activity[key])
                        else:
                            break  # No more data
                    else:
                        break  # Bad response
                        
            except Exception as e:
                print(f"Error with activity {endpoint}: {e}")
        
        print(f"📊 Found {len(found_users)} users via activity feeds")
        return found_users
    
    def discover_via_enumeration(self):
        """
        Discover users by systematic enumeration of common patterns
        """
        print("\n🔍 METHOD 4: SYSTEMATIC ENUMERATION")
        print("="*50)
        
        found_users = set()
        
        # Pattern 1: Common username patterns
        patterns = [
            # Single words
            ['admin', 'test', 'demo', 'user', 'guest', 'creator', 'artist', 'collector'],
            # With numbers
            [f'user{i}' for i in range(1, 100)],
            [f'creator{i}' for i in range(1, 50)],
            [f'artist{i}' for i in range(1, 50)],
            # Common names
            ['alice', 'bob', 'charlie', 'dave', 'eve', 'frank', 'grace', 'henry'],
            # Crypto/NFT related
            ['whale', 'diamond', 'hodler', 'bull', 'bear', 'moon', 'lambo', 'degen'],
        ]
        
        all_patterns = []
        for pattern_group in patterns:
            all_patterns.extend(pattern_group)
        
        print(f"Testing {len(all_patterns)} username patterns...")
        
        # Test in batches to avoid overwhelming
        batch_size = 10
        for i in range(0, len(all_patterns), batch_size):
            batch = all_patterns[i:i+batch_size]
            print(f"Testing batch {i//batch_size + 1}: {batch}")
            
            for username in batch:
                if self.test_username_exists(username):
                    found_users.add(username)
                    print(f"✅ Found user: {username}")
                
                time.sleep(0.2)  # Brief delay
        
        print(f"📊 Found {len(found_users)} users via enumeration")
        return found_users
    
    def discover_via_search_enumeration(self):
        """
        Use search endpoints to discover users
        """
        print("\n🔍 METHOD 5: SEARCH ENUMERATION")
        print("="*50)
        
        search_endpoints = [
            "/api/search",
            "/api/search/users",
            "/api/users/search",
            "/api/search/profiles",
        ]
        
        # Search terms that might return users
        search_terms = [
            'a', 'b', 'c', 'd', 'e',  # Single letters
            'user', 'creator', 'artist', 'collector',
            '0x', 'nft', 'crypto', 'art',
        ]
        
        found_users = set()
        
        for endpoint in search_endpoints:
            for term in search_terms:
                try:
                    url = f"https://salvor.io{endpoint}"
                    params = {
                        'q': term,
                        'query': term,
                        'search': term,
                        'limit': 100
                    }
                    
                    print(f"Searching '{term}' on {endpoint}")
                    response = self.session.get(url, headers=self.working_headers, params=params, timeout=10)
                    time.sleep(0.5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('data'):
                            users = self.extract_users_from_response(data)
                            found_users.update(users)
                            print(f"✅ Found {len(users)} users searching '{term}'")
                            
                except Exception as e:
                    print(f"Error searching {term} on {endpoint}: {e}")
        
        print(f"📊 Found {len(found_users)} users via search")
        return found_users
    
    def test_username_exists(self, username):
        """
        Test if a username exists
        """
        try:
            url = f"https://salvor.io/api/users/{username}"
            response = self.session.get(url, headers=self.working_headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('success') and data.get('data') and len(data['data']) > 0
                
        except Exception:
            pass
        return False
    
    def extract_users_from_response(self, data):
        """
        Extract usernames/user info from API response
        """
        users = set()
        
        def extract_recursive(obj):
            if isinstance(obj, dict):
                # Look for user-related fields
                if 'username' in obj:
                    users.add(obj['username'])
                elif 'name' in obj and 'address' in obj:
                    users.add(obj.get('username', obj.get('name')))
                
                # Recurse through all values
                for value in obj.values():
                    extract_recursive(value)
                    
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
        
        extract_recursive(data)
        return users
    
    def get_user_by_id(self, user_id):
        """
        Try to get user data by user ID
        """
        endpoints = [
            f"/api/users/{user_id}",
            f"/api/users/id/{user_id}",
            f"/api/profiles/{user_id}",
        ]
        
        for endpoint in endpoints:
            try:
                url = f"https://salvor.io{endpoint}"
                response = self.session.get(url, headers=self.working_headers, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('data'):
                        user_info = data['data']
                        if isinstance(user_info, list):
                            user_info = user_info[0] if user_info else None
                        
                        if user_info and user_info.get('username'):
                            return user_info['username']
                            
            except Exception:
                continue
        
        return None
    
    def paginate_endpoint(self, url, initial_params):
        """
        Paginate through an endpoint to get all data
        """
        all_users = set()
        page = initial_params.get('page', 1)
        
        while page <= 100:  # Safety limit
            params = initial_params.copy()
            params['page'] = page
            
            try:
                response = self.session.get(url, headers=self.working_headers, params=params, timeout=10)
                time.sleep(0.5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('data') and len(data['data']) > 0:
                        users = self.extract_users_from_response(data)
                        all_users.update(users)
                        print(f"  Page {page}: Found {len(users)} users")
                        page += 1
                    else:
                        break  # No more data
                else:
                    break  # Bad response
                    
            except Exception as e:
                print(f"Error paginating page {page}: {e}")
                break
        
        return all_users
    
    def collect_user_data(self, username):
        """
        Collect full data for a user
        """
        try:
            url = f"https://salvor.io/api/users/{username}"
            response = self.session.get(url, headers=self.working_headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    user_data = data['data']
                    if isinstance(user_data, list):
                        user_data = user_data[0] if user_data else None
                    
                    if user_data:
                        return {
                            'username': user_data.get('username', 'N/A'),
                            'wallet_address': user_data.get('address', 'N/A'),
                            'uuid': user_data.get('uuid', 'N/A'),
                            'name': user_data.get('name', 'N/A'),
                            'bio': user_data.get('bio', 'N/A'),
                            'is_verified': user_data.get('isVerified', False),
                            'total_collections': len(user_data.get('nftCollections', [])),
                            'total_nft_items': sum(col.get('itemCount', 0) for col in user_data.get('nftCollections', [])),
                            'collection_addresses': '; '.join([col.get('address', '') for col in user_data.get('nftCollections', []) if col.get('address')]),
                        }
            
        except Exception as e:
            self.failed_requests.append(f"{username}: {e}")
        
        return None
    
    def run_mass_discovery(self):
        """
        Streamlined mass discovery that avoids loops and actually collects data
        """
        print("🚀 SALVOR MASS USER DISCOVERY")
        print("="*60)
        print("Efficiently discovering ALL users on the platform...")
        
        all_discovered_users = set()
        
        # Method 1: Try the main user listing endpoint first (we know this works!)
        print("\n🎯 PRIORITY: Testing main user listing endpoint...")
        users_from_listing = self.discover_via_user_listing()
        
        if users_from_listing and len(users_from_listing) > 100:
            print(f"🎉 SUCCESS! Found {len(users_from_listing)} users from main endpoint")
            all_discovered_users.update(users_from_listing)
            
            # Since we found the main endpoint, skip other discovery methods for efficiency
            print("✅ Main endpoint successful - proceeding to data collection")
            
        else:
            print("⚠️  Main endpoint didn't work well, trying other methods...")
            
            # Only run other methods if main endpoint fails
            other_methods = [
                ("Collections", self.discover_via_collections),
                ("Activity Feeds", self.discover_via_activity_feeds),
                ("Enumeration", self.discover_via_enumeration),
                ("Search", self.discover_via_search_enumeration),
            ]
            
            for method_name, method_func in other_methods:
                print(f"\n🔍 Trying {method_name}...")
                try:
                    users = method_func()
                    all_discovered_users.update(users)
                    print(f"💡 {method_name} found {len(users)} users")
                    
                    # If we find a good number of users, proceed to collection
                    if len(all_discovered_users) > 50:
                        print(f"✅ Found sufficient users ({len(all_discovered_users)}), proceeding to collection")
                        break
                        
                except Exception as e:
                    print(f"❌ Error in {method_name}: {e}")
        
        print(f"\n🎉 DISCOVERY PHASE COMPLETE!")
        print(f"📊 Total unique users discovered: {len(all_discovered_users)}")
        
        if len(all_discovered_users) > 0:
            # Now collect FULL DATA for all discovered users
            print(f"\n📥 STARTING FULL DATA COLLECTION...")
            print(f"🔄 Collecting wallet addresses and profile data for {len(all_discovered_users)} users...")
            
            collected_data = self.efficient_bulk_collect(list(all_discovered_users))
            
            if collected_data:
                self.save_mass_collection(collected_data)
                self.print_collection_summary(collected_data)
                
                print(f"\n🎊 SUCCESS! Collected {len(collected_data)} complete user profiles!")
                return collected_data
            else:
                print("❌ Data collection failed")
        else:
            print("❌ No users discovered. Check authentication tokens.")
        
        return []
    
    def efficient_bulk_collect(self, usernames):
        """
        Efficiently collect full user data without redundant requests
        """
        print(f"\n🚀 EFFICIENT BULK COLLECTION")
        print("="*50)
        
        collected_data = []
        failed_count = 0
        
        # Process in optimized batches
        batch_size = 50
        total_batches = (len(usernames) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(usernames))
            batch = usernames[start_idx:end_idx]
            
            print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch)} users)")
            
            for i, username in enumerate(batch):
                try:
                    # Use the individual user endpoint we know works
                    url = f"https://salvor.io/api/users/{username}"
                    response = self.session.get(url, headers=self.working_headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success') and data.get('data'):
                            user_data = data['data']
                            if isinstance(user_data, list) and user_data:
                                user_data = user_data[0]
                            
                            if user_data and user_data.get('address'):
                                # Extract the key information we want
                                extracted = {
                                    'username': user_data.get('username', username),
                                    'wallet_address': user_data.get('address', 'N/A'),
                                    'name': user_data.get('name', 'N/A'),
                                    'uuid': user_data.get('uuid', 'N/A'),
                                    'bio': user_data.get('bio', 'N/A'),
                                    'is_verified': user_data.get('isVerified', False),
                                    'avatar_url': user_data.get('avatarUrl', 'N/A'),
                                    'twitter': user_data.get('links', {}).get('twitter', 'N/A'),
                                    'total_collections': len(user_data.get('nftCollections', [])),
                                    'total_nft_items': sum(col.get('itemCount', 0) for col in user_data.get('nftCollections', [])),
                                }
                                
                                collected_data.append(extracted)
                                
                                # Progress indicator
                                if len(collected_data) % 10 == 0:
                                    print(f"  ✅ Collected {len(collected_data)} profiles...")
                            else:
                                failed_count += 1
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1
                        
                    # Rate limiting - be respectful
                    time.sleep(0.5)
                    
                except Exception as e:
                    failed_count += 1
                    if failed_count % 10 == 0:
                        print(f"  ⚠️  {failed_count} failures so far...")
            
            # Batch progress
            print(f"  📊 Batch {batch_num + 1} complete: {len(collected_data)} total collected")
        
        print(f"\n✅ COLLECTION COMPLETE!")
        print(f"📈 Successfully collected: {len(collected_data)} profiles")
        print(f"❌ Failed requests: {failed_count}")
        print(f"🎯 Success rate: {len(collected_data)/(len(collected_data)+failed_count)*100:.1f}%")
        
        return collected_data
    
    def bulk_collect_user_data(self, usernames):
        """
        Collect data for all users efficiently
        """
        print(f"🔄 Bulk collecting data for {len(usernames)} users...")
        
        # Use threading for faster collection (but be respectful)
        def collect_batch(batch_usernames):
            batch_data = []
            for username in batch_usernames:
                data = self.collect_user_data(username)
                if data:
                    batch_data.append(data)
                    print(f"✅ {username}: {data['wallet_address']}")
                else:
                    print(f"❌ Failed: {username}")
                
                time.sleep(0.5)  # Rate limiting
            return batch_data
        
        # Process in batches
        batch_size = 20
        all_data = []
        
        for i in range(0, len(usernames), batch_size):
            batch = usernames[i:i+batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}/{(len(usernames)-1)//batch_size + 1}")
            
            batch_data = collect_batch(batch)
            all_data.extend(batch_data)
        
        # Save results
        if all_data:
            self.save_mass_collection(all_data)
            self.print_collection_summary(all_data)
        
        return all_data
    
    def save_mass_collection(self, data):
        """
        Save mass collection results
        """
        # Main summary file
        with open('salvor_mass_collection.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys() if data else []
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        
        # Wallet addresses only file (for easy import)
        with open('salvor_wallet_addresses.txt', 'w') as f:
            for user in data:
                if user['wallet_address'] != 'N/A':
                    f.write(f"{user['wallet_address']}\n")
        
        print(f"💾 Mass collection saved to salvor_mass_collection.csv")
        print(f"💰 Wallet addresses saved to salvor_wallet_addresses.txt")
    
    def print_collection_summary(self, data):
        """
        Print summary of collection results
        """
        print(f"\n🎉 MASS COLLECTION SUMMARY")
        print("="*60)
        print(f"👥 Total users collected: {len(data)}")
        print(f"💰 Unique wallet addresses: {len(set(u['wallet_address'] for u in data if u['wallet_address'] != 'N/A'))}")
        print(f"🏆 Verified users: {sum(1 for u in data if u['is_verified'])}")
        print(f"💎 Total NFT items: {sum(u['total_nft_items'] for u in data)}")
        print(f"🗂️ Total collections: {sum(u['total_collections'] for u in data)}")
        
        # Top collectors
        if data:
            top_collectors = sorted(data, key=lambda x: x['total_nft_items'], reverse=True)[:10]
            print(f"\n🥇 TOP 10 NFT COLLECTORS:")
            for i, user in enumerate(top_collectors, 1):
                print(f"  {i:2d}. {user['username']:20s} | {user['wallet_address']:42s} | {user['total_nft_items']:4d} items")

def main():
    print("🚀 SALVOR MASS WALLET ADDRESS COLLECTOR")
    print("="*60)
    print("This will attempt to discover and collect ALL wallet addresses from Salvor.io")
    print("Using multiple discovery methods for maximum coverage...")
    
    # Confirm before starting
    confirm = input("\nStart mass collection? This may take a while. (y/n): ").lower().strip()
    
    if confirm == 'y':
        collector = SalvorMassCollector()
        discovered_users = collector.run_mass_discovery()
        
        print(f"\n🎊 COLLECTION COMPLETE!")
        print(f"Check the generated CSV files for all wallet addresses and user data.")
    else:
        print("Collection cancelled.")

if __name__ == "__main__":
    main()
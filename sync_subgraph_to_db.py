import requests
import json
from setup_graph_database import get_graph_db_connection
from sqlalchemy import text
from datetime import datetime
import time

SUBGRAPH_URL = "https://api.studio.thegraph.com/query/18408/arena-tracker/graph deploy arena-tracker"
BATCH_SIZE = 1000

def sync_all_token_deployments():
    """Sync ALL token deployments from subgraph to database using pagination"""
    print("1. Syncing ALL token deployments...")
    
    total_synced = 0
    skip = 0
    
    while True:
        # Using only basic fields that we know exist in v0.0.5
        query = """
        {
          tokenDeployments(first: %d, skip: %d, orderBy: deployedAt, orderDirection: desc) {
            id
            tokenAddress
            creator
            tokenId
            deployedAt
            name
            symbol
            migrationStatus
            bondingProgress
            avaxRaised
            totalTrades
          }
        }
        """ % (BATCH_SIZE, skip)
        
        try:
            print(f"📡 Fetching tokens batch {skip//BATCH_SIZE + 1} (skip: {skip})...")
            response = requests.post(SUBGRAPH_URL, json={'query': query})
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                break
            
            if 'data' in data and 'tokenDeployments' in data['data']:
                tokens = data['data']['tokenDeployments']
                
                if not tokens:  # No more data
                    print(f"✅ No more tokens to fetch (reached end)")
                    break
                    
                print(f"🔄 Processing {len(tokens)} tokens...")
                engine = get_graph_db_connection()
                batch_synced = 0
                
                for token in tokens:
                    try:
                        with engine.connect() as connection:
                            transaction = connection.begin()
                            try:
                                # Insert only basic fields, set others to defaults
                                connection.execute(text("""
                                    INSERT INTO token_deployments (
                                        id, token_address, creator, token_id, deployed_at,
                                        name, symbol, decimals, total_supply,
                                        bonding_progress, migration_status, current_price_avax,
                                        avax_raised, migration_threshold, pair_address,
                                        total_avax_volume, total_buy_volume, total_sell_volume,
                                        total_trades, total_buys, total_sells, unique_traders,
                                        market_cap_avax, liquidity_avax, holders,
                                        price_high_24h, price_low_24h, volume_24h, price_change_24h,
                                        last_trade_timestamp, last_update_timestamp
                                    ) VALUES (
                                        :id, :token_address, :creator, :token_id, :deployed_at,
                                        :name, :symbol, 18, 1000000000000000000000000000,
                                        :bonding_progress, :migration_status, 0.0,
                                        :avax_raised, 500.0, NULL,
                                        0.0, 0.0, 0.0,
                                        :total_trades, 0, 0, 0,
                                        0.0, 0.0, 0,
                                        0.0, 0.0, 0.0, 0.0,
                                        :deployed_at, :deployed_at
                                    )
                                    ON CONFLICT (id) DO UPDATE SET
                                        bonding_progress = EXCLUDED.bonding_progress,
                                        migration_status = EXCLUDED.migration_status,
                                        avax_raised = EXCLUDED.avax_raised,
                                        total_trades = EXCLUDED.total_trades,
                                        updated_at = CURRENT_TIMESTAMP
                                """), {
                                    'id': token['id'],
                                    'token_address': token['tokenAddress'],
                                    'creator': token['creator'],
                                    'token_id': int(token['tokenId']),
                                    'deployed_at': int(token['deployedAt']),
                                    'name': token['name'],
                                    'symbol': token['symbol'],
                                    'bonding_progress': float(token['bondingProgress']),
                                    'migration_status': token['migrationStatus'],
                                    'avax_raised': float(token['avaxRaised']),
                                    'total_trades': int(token['totalTrades'])
                                })
                                transaction.commit()
                                batch_synced += 1
                            except Exception as e:
                                transaction.rollback()
                                if "NumericValueOutOfRange" in str(e):
                                    print(f"⚠️ Skipping token {token['name']}: Large numeric values")
                                else:
                                    print(f"⚠️ Skipping token {token['name']}: {str(e)[:100]}...")
                                continue
                    except Exception as e:
                        print(f"❌ Connection error for token {token['name']}: {e}")
                        continue
                
                total_synced += batch_synced
                skip += BATCH_SIZE
                print(f"📊 Synced batch: {batch_synced}/{len(tokens)} tokens (Total: {total_synced})")
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print("❌ Error fetching token deployments:", data)
                break
                
        except Exception as e:
            print(f"❌ Error syncing token deployments batch: {e}")
            break
    
    print(f"✅ Synced {total_synced} total token deployments")

def sync_all_bonding_events():
    """Sync ALL bonding events from subgraph to database using pagination"""
    print("2. Syncing ALL bonding events...")
    
    # Temporarily disable foreign key constraints
    engine = get_graph_db_connection()
    with engine.connect() as connection:
        connection.execute(text("ALTER TABLE bonding_events DROP CONSTRAINT IF EXISTS bonding_events_token_address_fkey"))
        connection.commit()
    
    total_synced = 0
    skip = 0
    
    while True:
        query = """
        {
          bondingEvents(first: %d, skip: %d, orderBy: timestamp, orderDirection: desc) {
            id
            token {
              id
            }
            user
            avaxAmount
            tokenAmount
            priceAvax
            bondingProgress
            cumulativeAvax
            tradeType
            protocolFee
            creatorFee
            referralFee
            timestamp
            blockNumber
            transactionHash
            gasPrice
            gasUsed
          }
        }
        """ % (BATCH_SIZE, skip)
        
        try:
            response = requests.post(SUBGRAPH_URL, json={'query': query})
            data = response.json()
            
            if 'data' in data and 'bondingEvents' in data['data']:
                events = data['data']['bondingEvents']
                
                if not events:  # No more data
                    break
                
                batch_synced = 0
                
                for event in events:
                    try:
                        with engine.connect() as connection:
                            transaction = connection.begin()
                            try:
                                connection.execute(text("""
                                    INSERT INTO bonding_events (
                                        id, token_address, user_address, avax_amount, token_amount,
                                        price_avax, bonding_progress, cumulative_avax, trade_type,
                                        protocol_fee, creator_fee, referral_fee,
                                        timestamp, block_number, transaction_hash, gas_price, gas_used
                                    ) VALUES (
                                        :id, :token_address, :user_address, :avax_amount, :token_amount,
                                        :price_avax, :bonding_progress, :cumulative_avax, :trade_type,
                                        :protocol_fee, :creator_fee, :referral_fee,
                                        :timestamp, :block_number, :transaction_hash, :gas_price, :gas_used
                                    )
                                    ON CONFLICT (id) DO NOTHING
                                """), {
                                    'id': event['id'],
                                    'token_address': event['token']['id'],
                                    'user_address': event['user'],
                                    'avax_amount': float(event['avaxAmount']),
                                    'token_amount': float(event['tokenAmount']),
                                    'price_avax': float(event['priceAvax']),
                                    'bonding_progress': float(event['bondingProgress']),
                                    'cumulative_avax': float(event['cumulativeAvax']),
                                    'trade_type': event['tradeType'],
                                    'protocol_fee': float(event['protocolFee']),
                                    'creator_fee': float(event['creatorFee']),
                                    'referral_fee': float(event['referralFee']),
                                    'timestamp': int(event['timestamp']),
                                    'block_number': int(event['blockNumber']),
                                    'transaction_hash': event['transactionHash'],
                                    'gas_price': int(event['gasPrice']),
                                    'gas_used': int(event['gasUsed'])
                                })
                                transaction.commit()
                                batch_synced += 1
                            except Exception as e:
                                transaction.rollback()
                                print(f"⚠️ Skipping bonding event {event['id']}: {str(e)[:100]}...")
                                continue
                    except Exception as e:
                        print(f"❌ Connection error for bonding event {event['id']}: {e}")
                        continue
                
                total_synced += batch_synced
                skip += BATCH_SIZE
                print(f"📊 Synced batch: {batch_synced}/{len(events)} bonding events (Total: {total_synced})")
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print("❌ Error fetching bonding events:", data)
                break
                
        except Exception as e:
            print(f"❌ Error syncing bonding events batch: {e}")
            break
    
    print(f"✅ Synced {total_synced} total bonding events")

def sync_all_user_activity():
    """Sync ALL user activity from subgraph to database using pagination"""
    print("3. Syncing ALL user activity...")
    
    total_synced = 0
    skip = 0
    
    while True:
        query = """
        {
          userActivities(first: %d, skip: %d, orderBy: totalVolumeAvax, orderDirection: desc) {
            id
            userAddress
            totalTrades
            totalVolumeAvax
            totalTokensBought
            totalTokensSold
            totalFeesSpent
            uniqueTokensTraded
            firstTradeTimestamp
            lastTradeTimestamp
          }
        }
        """ % (BATCH_SIZE, skip)
        
        try:
            response = requests.post(SUBGRAPH_URL, json={'query': query})
            data = response.json()
            
            if 'data' in data and 'userActivities' in data['data']:
                activities = data['data']['userActivities']
                
                if not activities:  # No more data
                    break
                
                engine = get_graph_db_connection()
                batch_synced = 0
                
                for activity in activities:
                    try:
                        with engine.connect() as connection:
                            transaction = connection.begin()
                            try:
                                connection.execute(text("""
                                    INSERT INTO user_activity (
                                        id, user_address, total_trades, total_volume_avax,
                                        total_tokens_bought, total_tokens_sold, total_fees_spent,
                                        unique_tokens_traded, first_trade_timestamp, last_trade_timestamp
                                    ) VALUES (
                                        :id, :user_address, :total_trades, :total_volume_avax,
                                        :total_tokens_bought, :total_tokens_sold, :total_fees_spent,
                                        :unique_tokens_traded, :first_trade_timestamp, :last_trade_timestamp
                                    )
                                    ON CONFLICT (id) DO UPDATE SET
                                        total_trades = EXCLUDED.total_trades,
                                        total_volume_avax = EXCLUDED.total_volume_avax,
                                        total_tokens_bought = EXCLUDED.total_tokens_bought,
                                        total_tokens_sold = EXCLUDED.total_tokens_sold,
                                        total_fees_spent = EXCLUDED.total_fees_spent,
                                        unique_tokens_traded = EXCLUDED.unique_tokens_traded,
                                        last_trade_timestamp = EXCLUDED.last_trade_timestamp,
                                        updated_at = CURRENT_TIMESTAMP
                                """), {
                                    'id': activity['id'],
                                    'user_address': activity['userAddress'],
                                    'total_trades': int(activity['totalTrades']),
                                    'total_volume_avax': float(activity['totalVolumeAvax']),
                                    'total_tokens_bought': float(activity['totalTokensBought']),
                                    'total_tokens_sold': float(activity['totalTokensSold']),
                                    'total_fees_spent': float(activity['totalFeesSpent']),
                                    'unique_tokens_traded': int(activity['uniqueTokensTraded']),
                                    'first_trade_timestamp': int(activity['firstTradeTimestamp']),
                                    'last_trade_timestamp': int(activity['lastTradeTimestamp'])
                                })
                                transaction.commit()
                                batch_synced += 1
                            except Exception as e:
                                transaction.rollback()
                                print(f"⚠️ Skipping user activity {activity['id']}: {str(e)[:100]}...")
                                continue
                    except Exception as e:
                        print(f"❌ Connection error for user activity {activity['id']}: {e}")
                        continue
                
                total_synced += batch_synced
                skip += BATCH_SIZE
                print(f"📊 Synced batch: {batch_synced}/{len(activities)} user activities (Total: {total_synced})")
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print("❌ Error fetching user activities:", data)
                break
                
        except Exception as e:
            print(f"❌ Error syncing user activities batch: {e}")
            break
    
    print(f"✅ Synced {total_synced} total user activities")

def run_full_sync():
    """Run complete sync of ALL data from subgraph to database"""
    print("🚀 Starting COMPLETE sync from subgraph to database...")
    print(f"📋 Using batch size: {BATCH_SIZE}")
    
    start_time = time.time()
    
    # Sync all data in proper order
    sync_all_token_deployments()
    sync_all_bonding_events()
    sync_all_user_activity()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n✅ COMPLETE sync finished!")
    print(f"⏱️ Total time: {duration:.2f} seconds")

def sync_historical_token_deployments():
    """Sync historical token deployments using timestamp-based pagination"""
    print("1. Syncing HISTORICAL token deployments (oldest first)...")
    
    total_synced = 0
    last_timestamp = 0  # Start from the beginning of time
    
    while True:
        # Use timestamp filtering instead of skip to avoid the 5000 limit
        query = """
        {
          tokenDeployments(first: %d, where: {deployedAt_gt: %d}, orderBy: deployedAt, orderDirection: asc) {
            id
            tokenAddress
            creator
            tokenId
            deployedAt
            name
            symbol
            migrationStatus
            bondingProgress
            avaxRaised
            totalTrades
          }
        }
        """ % (BATCH_SIZE, last_timestamp)
        
        try:
            print(f"📡 Fetching historical tokens from timestamp {last_timestamp}...")
            response = requests.post(SUBGRAPH_URL, json={'query': query})
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                break
            
            if 'data' in data and 'tokenDeployments' in data['data']:
                tokens = data['data']['tokenDeployments']
                
                if not tokens:  # No more data
                    print(f"✅ No more historical tokens to fetch")
                    break
                    
                print(f"🔄 Processing {len(tokens)} historical tokens...")
                engine = get_graph_db_connection()
                batch_synced = 0
                
                for token in tokens:
                    try:
                        with engine.connect() as connection:
                            transaction = connection.begin()
                            try:
                                # Insert only basic fields, set others to defaults
                                connection.execute(text("""
                                    INSERT INTO token_deployments (
                                        id, token_address, creator, token_id, deployed_at,
                                        name, symbol, decimals, total_supply,
                                        bonding_progress, migration_status, current_price_avax,
                                        avax_raised, migration_threshold, pair_address,
                                        total_avax_volume, total_buy_volume, total_sell_volume,
                                        total_trades, total_buys, total_sells, unique_traders,
                                        market_cap_avax, liquidity_avax, holders,
                                        price_high_24h, price_low_24h, volume_24h, price_change_24h,
                                        last_trade_timestamp, last_update_timestamp
                                    ) VALUES (
                                        :id, :token_address, :creator, :token_id, :deployed_at,
                                        :name, :symbol, 18, 1000000000000000000000000000,
                                        :bonding_progress, :migration_status, 0.0,
                                        :avax_raised, 500.0, NULL,
                                        0.0, 0.0, 0.0,
                                        :total_trades, 0, 0, 0,
                                        0.0, 0.0, 0,
                                        0.0, 0.0, 0.0, 0.0,
                                        :deployed_at, :deployed_at
                                    )
                                    ON CONFLICT (id) DO NOTHING
                                """), {
                                    'id': token['id'],
                                    'token_address': token['tokenAddress'],
                                    'creator': token['creator'],
                                    'token_id': int(token['tokenId']),
                                    'deployed_at': int(token['deployedAt']),
                                    'name': token['name'],
                                    'symbol': token['symbol'],
                                    'bonding_progress': float(token['bondingProgress']),
                                    'migration_status': token['migrationStatus'],
                                    'avax_raised': float(token['avaxRaised']),
                                    'total_trades': int(token['totalTrades'])
                                })
                                transaction.commit()
                                batch_synced += 1
                            except Exception as e:
                                transaction.rollback()
                                if "NumericValueOutOfRange" in str(e):
                                    print(f"⚠️ Skipping token {token['name']}: Large numeric values")
                                elif "duplicate key" not in str(e).lower():
                                    print(f"⚠️ Skipping token {token['name']}: {str(e)[:100]}...")
                                continue
                    except Exception as e:
                        print(f"❌ Connection error for token {token['name']}: {e}")
                        continue
                
                # Update last_timestamp to the latest timestamp in this batch
                if tokens:
                    last_timestamp = max(int(token['deployedAt']) for token in tokens)
                
                total_synced += batch_synced
                print(f"📊 Synced batch: {batch_synced}/{len(tokens)} tokens (Total: {total_synced})")
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print("❌ Error fetching token deployments:", data)
                break
                
        except Exception as e:
            print(f"❌ Error syncing historical token deployments: {e}")
            break
    
    print(f"✅ Synced {total_synced} total historical token deployments")

def sync_historical_bonding_events():
    """Sync historical bonding events using timestamp-based pagination"""
    print("2. Syncing HISTORICAL bonding events...")
    
    # Temporarily disable foreign key constraints
    engine = get_graph_db_connection()
    with engine.connect() as connection:
        connection.execute(text("ALTER TABLE bonding_events DROP CONSTRAINT IF EXISTS bonding_events_token_address_fkey"))
        connection.commit()
    
    total_synced = 0
    last_timestamp = 0  # Start from the beginning of time
    
    while True:
        query = """
        {
          bondingEvents(first: %d, where: {timestamp_gt: %d}, orderBy: timestamp, orderDirection: asc) {
            id
            token {
              id
            }
            user
            avaxAmount
            tokenAmount
            priceAvax
            bondingProgress
            cumulativeAvax
            tradeType
            protocolFee
            creatorFee
            referralFee
            timestamp
            blockNumber
            transactionHash
            gasPrice
            gasUsed
          }
        }
        """ % (BATCH_SIZE, last_timestamp)
        
        try:
            print(f"📡 Fetching historical bonding events from timestamp {last_timestamp}...")
            response = requests.post(SUBGRAPH_URL, json={'query': query})
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                break
            
            if 'data' in data and 'bondingEvents' in data['data']:
                events = data['data']['bondingEvents']
                
                if not events:  # No more data
                    print(f"✅ No more historical bonding events to fetch")
                    break
                
                batch_synced = 0
                
                for event in events:
                    try:
                        with engine.connect() as connection:
                            transaction = connection.begin()
                            try:
                                connection.execute(text("""
                                    INSERT INTO bonding_events (
                                        id, token_address, user_address, avax_amount, token_amount,
                                        price_avax, bonding_progress, cumulative_avax, trade_type,
                                        protocol_fee, creator_fee, referral_fee,
                                        timestamp, block_number, transaction_hash, gas_price, gas_used
                                    ) VALUES (
                                        :id, :token_address, :user_address, :avax_amount, :token_amount,
                                        :price_avax, :bonding_progress, :cumulative_avax, :trade_type,
                                        :protocol_fee, :creator_fee, :referral_fee,
                                        :timestamp, :block_number, :transaction_hash, :gas_price, :gas_used
                                    )
                                    ON CONFLICT (id) DO NOTHING
                                """), {
                                    'id': event['id'],
                                    'token_address': event['token']['id'],
                                    'user_address': event['user'],
                                    'avax_amount': float(event['avaxAmount']),
                                    'token_amount': float(event['tokenAmount']),
                                    'price_avax': float(event['priceAvax']),
                                    'bonding_progress': float(event['bondingProgress']),
                                    'cumulative_avax': float(event['cumulativeAvax']),
                                    'trade_type': event['tradeType'],
                                    'protocol_fee': float(event['protocolFee']),
                                    'creator_fee': float(event['creatorFee']),
                                    'referral_fee': float(event['referralFee']),
                                    'timestamp': int(event['timestamp']),
                                    'block_number': int(event['blockNumber']),
                                    'transaction_hash': event['transactionHash'],
                                    'gas_price': int(event['gasPrice']),
                                    'gas_used': int(event['gasUsed'])
                                })
                                transaction.commit()
                                batch_synced += 1
                            except Exception as e:
                                transaction.rollback()
                                if "duplicate key" not in str(e).lower():
                                    print(f"⚠️ Skipping bonding event {event['id']}: {str(e)[:100]}...")
                                continue
                    except Exception as e:
                        print(f"❌ Connection error for bonding event {event['id']}: {e}")
                        continue
                
                # Update last_timestamp to the latest timestamp in this batch
                if events:
                    last_timestamp = max(int(event['timestamp']) for event in events)
                
                total_synced += batch_synced
                print(f"📊 Synced batch: {batch_synced}/{len(events)} bonding events (Total: {total_synced})")
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print("❌ Error fetching bonding events:", data)
                break
                
        except Exception as e:
            print(f"❌ Error syncing historical bonding events: {e}")
            break
    
    print(f"✅ Synced {total_synced} total historical bonding events")

def run_historical_sync():
    """Run historical sync to get data beyond the GraphQL skip limit"""
    print("🚀 Starting HISTORICAL sync to get data beyond 7000 records...")
    print("📋 Using timestamp-based pagination to bypass skip limits")
    
    start_time = time.time()
    
    # Sync historical data
    sync_historical_token_deployments()
    sync_historical_bonding_events()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n✅ HISTORICAL sync finished!")
    print(f"⏱️ Total time: {duration:.2f} seconds")

if __name__ == "__main__":
    # Check if user wants historical sync
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "historical":
        run_historical_sync()
    else:
        run_full_sync() 
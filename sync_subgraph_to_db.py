import requests
import json
from setup_graph_database import get_graph_db_connection
from sqlalchemy import text
from datetime import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()

SUBGRAPH_URL = os.getenv("SUBGRAPH_URL")
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

def sync_paraswap_trades():
    """Sync Paraswap trades from the enhanced subgraph schema"""
    print("4. Syncing Paraswap trades...")
    
    total_synced = 0
    skip = 0
    
    while True:
        # Updated query to match our enhanced schema
        query = """
        {
          paraswapTrades(first: %d, skip: %d, orderBy: timestamp, orderDirection: desc) {
            id
            uuid
            initiator
            beneficiary
            partner
            srcToken
            destToken
            srcAmount
            receivedAmount
            expectedAmount
            tradeType
            isBuy
            srcTokenIsArena
            destTokenIsArena
            arenaToken {
              id
            }
            priceRatio
            slippagePercent
            feePercent
            feeAmount
            avaxValueIn
            avaxValueOut
            estimatedUsdValue
            processingLatency
            timestamp
            blockNumber
            transactionHash
            gasPrice
            gasUsed
          }
        }
        """ % (BATCH_SIZE, skip)
        
        try:
            print(f"📡 Fetching Paraswap trades batch {skip//BATCH_SIZE + 1} (skip: {skip})...")
            response = requests.post(SUBGRAPH_URL, json={'query': query})
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                break
            
            if 'data' in data and 'paraswapTrades' in data['data']:
                trades = data['data']['paraswapTrades']
                
                if not trades:  # No more data
                    print(f"✅ No more Paraswap trades to fetch")
                    break
                    
                print(f"🔄 Processing {len(trades)} Paraswap trades...")
                engine = get_graph_db_connection()
                batch_synced = 0
                
                # Create enhanced table if it doesn't exist
                with engine.connect() as connection:
                    connection.execute(text("""
                        CREATE TABLE IF NOT EXISTS paraswap_trades (
                            id VARCHAR(255) PRIMARY KEY,
                            uuid VARCHAR(66) NOT NULL,
                            initiator VARCHAR(66) NOT NULL,
                            beneficiary VARCHAR(66) NOT NULL,
                            partner VARCHAR(66),
                            src_token VARCHAR(66) NOT NULL,
                            dest_token VARCHAR(66) NOT NULL,
                            src_amount DECIMAL(50, 18) NOT NULL,
                            received_amount DECIMAL(50, 18) NOT NULL,
                            expected_amount DECIMAL(50, 18) NOT NULL,
                            trade_type VARCHAR(20) NOT NULL,
                            is_buy BOOLEAN NOT NULL,
                            src_token_is_arena BOOLEAN NOT NULL DEFAULT FALSE,
                            dest_token_is_arena BOOLEAN NOT NULL DEFAULT FALSE,
                            arena_token VARCHAR(66),
                            price_ratio DECIMAL(50, 18) NOT NULL,
                            slippage_percent DECIMAL(10, 4) NOT NULL,
                            fee_percent DECIMAL(10, 4) NOT NULL,
                            fee_amount DECIMAL(50, 18) NOT NULL,
                            avax_value_in DECIMAL(50, 18) DEFAULT 0,
                            avax_value_out DECIMAL(50, 18) DEFAULT 0,
                            estimated_usd_value DECIMAL(50, 18) DEFAULT 0,
                            processing_latency BIGINT DEFAULT 0,
                            timestamp BIGINT NOT NULL,
                            block_number BIGINT NOT NULL,
                            transaction_hash VARCHAR(66) NOT NULL,
                            gas_price BIGINT NOT NULL,
                            gas_used BIGINT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """))
                    connection.commit()
                
                for trade in trades:
                    try:
                        with engine.connect() as connection:
                            transaction = connection.begin()
                            try:
                                arena_token_id = trade['arenaToken']['id'] if trade['arenaToken'] else None
                                
                                connection.execute(text("""
                                    INSERT INTO paraswap_trades (
                                        id, uuid, initiator, beneficiary, partner,
                                        src_token, dest_token, src_amount, received_amount, expected_amount,
                                        trade_type, is_buy, src_token_is_arena, dest_token_is_arena, arena_token,
                                        price_ratio, slippage_percent, fee_percent, fee_amount,
                                        avax_value_in, avax_value_out, estimated_usd_value, processing_latency,
                                        timestamp, block_number, transaction_hash, gas_price, gas_used
                                    ) VALUES (
                                        :id, :uuid, :initiator, :beneficiary, :partner,
                                        :src_token, :dest_token, :src_amount, :received_amount, :expected_amount,
                                        :trade_type, :is_buy, :src_token_is_arena, :dest_token_is_arena, :arena_token,
                                        :price_ratio, :slippage_percent, :fee_percent, :fee_amount,
                                        :avax_value_in, :avax_value_out, :estimated_usd_value, :processing_latency,
                                        :timestamp, :block_number, :transaction_hash, :gas_price, :gas_used
                                    )
                                    ON CONFLICT (id) DO UPDATE SET
                                        received_amount = EXCLUDED.received_amount,
                                        slippage_percent = EXCLUDED.slippage_percent,
                                        fee_amount = EXCLUDED.fee_amount,
                                        avax_value_in = EXCLUDED.avax_value_in,
                                        avax_value_out = EXCLUDED.avax_value_out,
                                        estimated_usd_value = EXCLUDED.estimated_usd_value,
                                        processing_latency = EXCLUDED.processing_latency
                                """),
                                {
                                    'id': trade['id'],
                                    'uuid': trade['uuid'],
                                    'initiator': trade['initiator'],
                                    'beneficiary': trade['beneficiary'],
                                    'partner': trade['partner'],
                                    'src_token': trade['srcToken'],
                                    'dest_token': trade['destToken'],
                                    'src_amount': float(trade['srcAmount']),
                                    'received_amount': float(trade['receivedAmount']),
                                    'expected_amount': float(trade['expectedAmount']),
                                    'trade_type': trade['tradeType'],
                                    'is_buy': trade['isBuy'],
                                    'src_token_is_arena': trade['srcTokenIsArena'],
                                    'dest_token_is_arena': trade['destTokenIsArena'],
                                    'arena_token': arena_token_id,
                                    'price_ratio': float(trade['priceRatio']),
                                    'slippage_percent': float(trade['slippagePercent']),
                                    'fee_percent': float(trade['feePercent']),
                                    'fee_amount': float(trade['feeAmount']),
                                    'avax_value_in': float(trade['avaxValueIn']),
                                    'avax_value_out': float(trade['avaxValueOut']),
                                    'estimated_usd_value': float(trade['estimatedUsdValue']),
                                    'processing_latency': int(trade['processingLatency']),
                                    'timestamp': int(trade['timestamp']),
                                    'block_number': int(trade['blockNumber']),
                                    'transaction_hash': trade['transactionHash'],
                                    'gas_price': int(trade['gasPrice']),
                                    'gas_used': int(trade['gasUsed'])
                                })
                                transaction.commit()
                                batch_synced += 1
                            except Exception as e:
                                transaction.rollback()
                                print(f"Error inserting trade {trade['id']}: {e}")
                    except Exception as e:
                        print(f"Error connecting to database: {e}")
                
                total_synced += batch_synced
                skip += BATCH_SIZE
                print(f"📊 Synced batch: {batch_synced}/{len(trades)} trades (Total: {total_synced})")
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print("❌ Error fetching Paraswap trades:", data)
                break
                
        except Exception as e:
            print(f"❌ Error syncing Paraswap trades batch: {e}")
            break
    
    print(f"✅ Synced {total_synced} total Paraswap trades")

def sync_arena_token_paraswap_stats():
    """Sync Arena token Paraswap statistics"""
    print("5. Syncing Arena token Paraswap stats...")
    
    total_synced = 0
    skip = 0
    
    while True:
        query = """
        {
          arenaTokenParaswapStats(first: %d, skip: %d, orderBy: lastUpdateTimestamp, orderDirection: desc) {
            id
            token {
              id
            }
            totalParaswapTrades
            totalParaswapVolumeAvax
            totalBuyVolumeAvax
            totalSellVolumeAvax
            trades24h
            volume24hAvax
            lastParaswapPrice
            priceHigh24h
            priceLow24h
            averageSlippage
            largestTrade
            firstParaswapTrade
            lastParaswapTrade
            lastUpdateTimestamp
          }
        }
        """ % (BATCH_SIZE, skip)
        
        try:
            print(f"📡 Fetching Arena token Paraswap stats batch {skip//BATCH_SIZE + 1} (skip: {skip})...")
            response = requests.post(SUBGRAPH_URL, json={'query': query})
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                break
            
            if 'data' in data and 'arenaTokenParaswapStats' in data['data']:
                stats = data['data']['arenaTokenParaswapStats']
                
                if not stats:  # No more data
                    print(f"✅ No more Arena token Paraswap stats to fetch")
                    break
                    
                print(f"🔄 Processing {len(stats)} Arena token Paraswap stats...")
                engine = get_graph_db_connection()
                batch_synced = 0
                
                # Create table if it doesn't exist
                with engine.connect() as connection:
                    connection.execute(text("""
                        CREATE TABLE IF NOT EXISTS arena_token_paraswap_stats (
                            id VARCHAR(255) PRIMARY KEY,
                            token_address VARCHAR(66) NOT NULL,
                            total_paraswap_trades INT DEFAULT 0,
                            total_paraswap_volume_avax DECIMAL(50, 18) DEFAULT 0,
                            total_buy_volume_avax DECIMAL(50, 18) DEFAULT 0,
                            total_sell_volume_avax DECIMAL(50, 18) DEFAULT 0,
                            trades_24h INT DEFAULT 0,
                            volume_24h_avax DECIMAL(50, 18) DEFAULT 0,
                            last_paraswap_price DECIMAL(50, 18) DEFAULT 0,
                            price_high_24h DECIMAL(50, 18) DEFAULT 0,
                            price_low_24h DECIMAL(50, 18) DEFAULT 999999999,
                            average_slippage DECIMAL(10, 4) DEFAULT 0,
                            largest_trade DECIMAL(50, 18) DEFAULT 0,
                            first_paraswap_trade BIGINT,
                            last_paraswap_trade BIGINT,
                            last_update_timestamp BIGINT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """))
                    connection.commit()
                
                for stat in stats:
                    try:
                        with engine.connect() as connection:
                            transaction = connection.begin()
                            try:
                                connection.execute(text("""
                                    INSERT INTO arena_token_paraswap_stats (
                                        id, token_address, total_paraswap_trades, total_paraswap_volume_avax,
                                        total_buy_volume_avax, total_sell_volume_avax, trades_24h, volume_24h_avax,
                                        last_paraswap_price, price_high_24h, price_low_24h, average_slippage,
                                        largest_trade, first_paraswap_trade, last_paraswap_trade, last_update_timestamp
                                    ) VALUES (
                                        :id, :token_address, :total_paraswap_trades, :total_paraswap_volume_avax,
                                        :total_buy_volume_avax, :total_sell_volume_avax, :trades_24h, :volume_24h_avax,
                                        :last_paraswap_price, :price_high_24h, :price_low_24h, :average_slippage,
                                        :largest_trade, :first_paraswap_trade, :last_paraswap_trade, :last_update_timestamp
                                    )
                                    ON CONFLICT (id) DO UPDATE SET
                                        total_paraswap_trades = EXCLUDED.total_paraswap_trades,
                                        total_paraswap_volume_avax = EXCLUDED.total_paraswap_volume_avax,
                                        total_buy_volume_avax = EXCLUDED.total_buy_volume_avax,
                                        total_sell_volume_avax = EXCLUDED.total_sell_volume_avax,
                                        trades_24h = EXCLUDED.trades_24h,
                                        volume_24h_avax = EXCLUDED.volume_24h_avax,
                                        last_paraswap_price = EXCLUDED.last_paraswap_price,
                                        price_high_24h = EXCLUDED.price_high_24h,
                                        price_low_24h = EXCLUDED.price_low_24h,
                                        average_slippage = EXCLUDED.average_slippage,
                                        largest_trade = EXCLUDED.largest_trade,
                                        last_paraswap_trade = EXCLUDED.last_paraswap_trade,
                                        last_update_timestamp = EXCLUDED.last_update_timestamp
                                """),
                                {
                                    'id': stat['id'],
                                    'token_address': stat['token']['id'],
                                    'total_paraswap_trades': int(stat['totalParaswapTrades']),
                                    'total_paraswap_volume_avax': float(stat['totalParaswapVolumeAvax']),
                                    'total_buy_volume_avax': float(stat['totalBuyVolumeAvax']),
                                    'total_sell_volume_avax': float(stat['totalSellVolumeAvax']),
                                    'trades_24h': int(stat['trades24h']),
                                    'volume_24h_avax': float(stat['volume24hAvax']),
                                    'last_paraswap_price': float(stat['lastParaswapPrice']),
                                    'price_high_24h': float(stat['priceHigh24h']),
                                    'price_low_24h': float(stat['priceLow24h']),
                                    'average_slippage': float(stat['averageSlippage']),
                                    'largest_trade': float(stat['largestTrade']),
                                    'first_paraswap_trade': int(stat['firstParaswapTrade']),
                                    'last_paraswap_trade': int(stat['lastParaswapTrade']),
                                    'last_update_timestamp': int(stat['lastUpdateTimestamp'])
                                })
                                transaction.commit()
                                batch_synced += 1
                            except Exception as e:
                                transaction.rollback()
                                print(f"Error inserting stat {stat['id']}: {e}")
                    except Exception as e:
                        print(f"Error connecting to database: {e}")
                
                total_synced += batch_synced
                skip += BATCH_SIZE
                print(f"📊 Synced batch: {batch_synced}/{len(stats)} stats (Total: {total_synced})")
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print("❌ Error fetching Arena token Paraswap stats:", data)
                break
                
        except Exception as e:
            print(f"❌ Error syncing Arena token Paraswap stats batch: {e}")
            break
    
    print(f"✅ Synced {total_synced} total Arena token Paraswap stats")

def sync_real_time_trade_alerts():
    """Sync real-time trade alerts"""
    print("6. Syncing real-time trade alerts...")
    
    total_synced = 0
    skip = 0
    
    while True:
        query = """
        {
          realTimeTradeAlerts(first: %d, skip: %d, orderBy: timestamp, orderDirection: desc) {
            id
            paraswapTrade {
              id
            }
            bondingEvent {
              id
            }
            alertType
            significance
            tradeValueAvax
            priceImpact
            volumeRatio
            timestamp
            blockNumber
          }
        }
        """ % (BATCH_SIZE, skip)
        
        try:
            print(f"📡 Fetching real-time trade alerts batch {skip//BATCH_SIZE + 1} (skip: {skip})...")
            response = requests.post(SUBGRAPH_URL, json={'query': query})
            data = response.json()
            
            if 'errors' in data:
                print(f"❌ GraphQL errors: {data['errors']}")
                break
            
            if 'data' in data and 'realTimeTradeAlerts' in data['data']:
                alerts = data['data']['realTimeTradeAlerts']
                
                if not alerts:  # No more data
                    print(f"✅ No more real-time trade alerts to fetch")
                    break
                    
                print(f"🔄 Processing {len(alerts)} real-time trade alerts...")
                engine = get_graph_db_connection()
                batch_synced = 0
                
                # Create table if it doesn't exist
                with engine.connect() as connection:
                    connection.execute(text("""
                        CREATE TABLE IF NOT EXISTS real_time_trade_alerts (
                            id VARCHAR(255) PRIMARY KEY,
                            paraswap_trade_id VARCHAR(255),
                            bonding_event_id VARCHAR(255),
                            alert_type VARCHAR(50) NOT NULL,
                            significance VARCHAR(20) NOT NULL,
                            trade_value_avax DECIMAL(50, 18) NOT NULL,
                            price_impact DECIMAL(10, 4) NOT NULL,
                            volume_ratio DECIMAL(10, 4) DEFAULT 0,
                            timestamp BIGINT NOT NULL,
                            block_number BIGINT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """))
                    connection.commit()
                
                for alert in alerts:
                    try:
                        with engine.connect() as connection:
                            transaction = connection.begin()
                            try:
                                paraswap_trade_id = alert['paraswapTrade']['id'] if alert['paraswapTrade'] else None
                                bonding_event_id = alert['bondingEvent']['id'] if alert['bondingEvent'] else None
                                
                                connection.execute(text("""
                                    INSERT INTO real_time_trade_alerts (
                                        id, paraswap_trade_id, bonding_event_id, alert_type, significance,
                                        trade_value_avax, price_impact, volume_ratio, timestamp, block_number
                                    ) VALUES (
                                        :id, :paraswap_trade_id, :bonding_event_id, :alert_type, :significance,
                                        :trade_value_avax, :price_impact, :volume_ratio, :timestamp, :block_number
                                    )
                                    ON CONFLICT (id) DO UPDATE SET
                                        trade_value_avax = EXCLUDED.trade_value_avax,
                                        price_impact = EXCLUDED.price_impact,
                                        volume_ratio = EXCLUDED.volume_ratio
                                """),
                                {
                                    'id': alert['id'],
                                    'paraswap_trade_id': paraswap_trade_id,
                                    'bonding_event_id': bonding_event_id,
                                    'alert_type': alert['alertType'],
                                    'significance': alert['significance'],
                                    'trade_value_avax': float(alert['tradeValueAvax']),
                                    'price_impact': float(alert['priceImpact']),
                                    'volume_ratio': float(alert['volumeRatio']),
                                    'timestamp': int(alert['timestamp']),
                                    'block_number': int(alert['blockNumber'])
                                })
                                transaction.commit()
                                batch_synced += 1
                            except Exception as e:
                                transaction.rollback()
                                print(f"Error inserting alert {alert['id']}: {e}")
                    except Exception as e:
                        print(f"Error connecting to database: {e}")
                
                total_synced += batch_synced
                skip += BATCH_SIZE
                print(f"📊 Synced batch: {batch_synced}/{len(alerts)} alerts (Total: {total_synced})")
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print("❌ Error fetching real-time trade alerts:", data)
                break
                
        except Exception as e:
            print(f"❌ Error syncing real-time trade alerts batch: {e}")
            break
    
    print(f"✅ Synced {total_synced} total real-time trade alerts")

def run_full_sync():
    """Run complete sync of ALL data from subgraph to database"""
    print("🚀 Starting COMPLETE sync from subgraph to database...")
    print(f"📋 Using batch size: {BATCH_SIZE}")
    
    start_time = time.time()
    
    # Sync all data in proper order
    sync_all_token_deployments()
    sync_all_bonding_events()
    sync_all_user_activity()
    sync_paraswap_trades()
    sync_arena_token_paraswap_stats()
    sync_real_time_trade_alerts()
    
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

def test_subgraph_connection():
    """Test what data is available in the subgraph"""
    print("🔍 Testing subgraph connection and available data...")
    
    # Test basic connection
    test_query = """
    {
      _meta {
        block {
          number
          hash
        }
        deployment
        hasIndexingErrors
      }
    }
    """
    
    try:
        response = requests.post(SUBGRAPH_URL, json={'query': test_query})
        data = response.json()
        
        if 'errors' in data:
            print(f"❌ Subgraph connection errors: {data['errors']}")
            return False
        
        if 'data' in data and '_meta' in data['data']:
            meta = data['data']['_meta']
            print(f"✅ Subgraph connected - Block: {meta['block']['number']}")
            if meta.get('hasIndexingErrors'):
                print(f"⚠️ Subgraph has indexing errors!")
        
        # Test token deployments count
        count_query = """
        {
          tokenDeployments(first: 1) {
            id
          }
        }
        """
        
        response = requests.post(SUBGRAPH_URL, json={'query': count_query})
        data = response.json()
        
        if 'data' in data and 'tokenDeployments' in data['data']:
            tokens = data['data']['tokenDeployments']
            print(f"📊 Found {len(tokens)} token deployments in test query")
        
        # Test paraswap trades specifically
        paraswap_query = """
        {
          paraswapTrades(first: 5) {
            id
            uuid
            tradeType
            srcToken
            destToken
            timestamp
          }
        }
        """
        
        print("🔍 Testing Paraswap trades query...")
        response = requests.post(SUBGRAPH_URL, json={'query': paraswap_query})
        data = response.json()
        
        if 'errors' in data:
            print(f"❌ Paraswap query errors: {data['errors']}")
        elif 'data' in data:
            if 'paraswapTrades' in data['data']:
                trades = data['data']['paraswapTrades']
                print(f"✅ Found {len(trades)} Paraswap trades")
                for trade in trades:
                    print(f"   - Trade {trade['id']}: {trade['tradeType']} at {trade['timestamp']}")
            else:
                print("❌ No 'paraswapTrades' field in response")
                print(f"Available fields: {list(data['data'].keys())}")
        else:
            print(f"❌ Unexpected response: {data}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing subgraph: {e}")
        return False

def check_paraswap_contract_activity():
    """Check if the Paraswap contract address has any activity"""
    print("🔍 Checking Paraswap contract activity...")
    
    # The contract address from subgraph.yaml
    paraswap_address = "0x6A000F20005980200259B80c5102003040001068"
    print(f"📋 Contract address: {paraswap_address}")
    
    # Check if we can find any events from this contract in recent blocks
    recent_events_query = """
    {
      _meta {
        block {
          number
        }
      }
    }
    """
    
    try:
        response = requests.post(SUBGRAPH_URL, json={'query': recent_events_query})
        data = response.json()
        
        if 'data' in data and '_meta' in data['data']:
            current_block = data['data']['_meta']['block']['number']
            print(f"📊 Subgraph current block: {current_block}")
        
        # Also check if there are any PostBondingTrade entities (alternate entity name)
        post_bonding_query = """
        {
          postBondingTrades(first: 5) {
            id
            tokenAddress
            from
            to
            amount
            timestamp
          }
        }
        """
        
        print("🔍 Checking for PostBondingTrade entities...")
        response = requests.post(SUBGRAPH_URL, json={'query': post_bonding_query})
        data = response.json()
        
        if 'errors' in data:
            print(f"❌ PostBondingTrade query errors: {data['errors']}")
        elif 'data' in data:
            if 'postBondingTrades' in data['data']:
                trades = data['data']['postBondingTrades']
                print(f"✅ Found {len(trades)} PostBondingTrade entities")
                for trade in trades:
                    print(f"   - Trade {trade['id']}: {trade['amount']} tokens at {trade['timestamp']}")
            else:
                print("❌ No 'postBondingTrades' field found")
        
    except Exception as e:
        print(f"❌ Error checking contract activity: {e}")

def check_token_migration_status():
    """Check how many tokens have migrated and should be generating Paraswap trades"""
    print("🔍 Checking token migration status...")
    
    migration_query = """
    {
      tokenDeployments(first: 100, orderBy: deployedAt, orderDirection: desc) {
        id
        name
        symbol
        migrationStatus
        bondingProgress
        avaxRaised
        totalTrades
        pairAddress
      }
    }
    """
    
    try:
        response = requests.post(SUBGRAPH_URL, json={'query': migration_query})
        data = response.json()
        
        if 'errors' in data:
            print(f"❌ Migration query errors: {data['errors']}")
            return
        
        if 'data' in data and 'tokenDeployments' in data['data']:
            tokens = data['data']['tokenDeployments']
            
            bonding_count = 0
            close_to_migration_count = 0
            migrated_count = 0
            
            print(f"📊 Analyzing {len(tokens)} tokens...")
            
            for token in tokens:
                status = token['migrationStatus']
                if status == 'BONDING':
                    bonding_count += 1
                elif status == 'CLOSE_TO_MIGRATION':
                    close_to_migration_count += 1
                elif status == 'MIGRATED':
                    migrated_count += 1
                    print(f"   ✅ MIGRATED: {token['name']} ({token['symbol']}) - Pair: {token.get('pairAddress', 'N/A')}")
            
            print(f"\n📈 Migration Status Summary:")
            print(f"   🔵 BONDING: {bonding_count} tokens")
            print(f"   🟡 CLOSE_TO_MIGRATION: {close_to_migration_count} tokens") 
            print(f"   🟢 MIGRATED: {migrated_count} tokens")
            
            if migrated_count == 0:
                print("\n💡 Insight: No tokens have migrated yet!")
                print("   This explains why there are no Paraswap trades.")
                print("   Paraswap trades only happen AFTER tokens migrate to DEX pairs.")
            else:
                print(f"\n💡 Insight: {migrated_count} tokens have migrated.")
                print("   These should be generating Paraswap trades if users are trading them.")
                
    except Exception as e:
        print(f"❌ Error checking migration status: {e}")

if __name__ == "__main__":
    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "historical":
            run_historical_sync()
        elif sys.argv[1] == "test":
            test_subgraph_connection()
            check_paraswap_contract_activity()
            check_token_migration_status()
        else:
            print("Usage: python sync_subgraph_to_db.py [historical|test]")
    else:
        run_full_sync() 
#!/usr/bin/env python3
"""
Test script to verify wallet analysis API functionality
Tests the bonding curve API fixes for wei conversion, token symbols, and P&L calculations
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from setup_graph_database import get_graph_db_connection
from sqlalchemy import text

def test_database_connectivity():
    """Test basic database connectivity and data availability"""
    print("🔗 TESTING DATABASE CONNECTIVITY")
    print("=" * 50)
    
    engine = get_graph_db_connection()
    if not engine:
        print("❌ Could not connect to database")
        return False
    
    try:
        with engine.connect() as conn:
            # Check bonding_events table
            result = conn.execute(text("SELECT COUNT(*) FROM bonding_events"))
            bonding_count = result.scalar()
            print(f"📊 Bonding events: {bonding_count:,}")
            
            # Check token_deployments table
            result = conn.execute(text("SELECT COUNT(*) FROM token_deployments"))
            tokens_count = result.scalar()
            print(f"🪙 Token deployments: {tokens_count:,}")
            
            # Check wallet_labels table
            result = conn.execute(text("SELECT COUNT(*) FROM wallet_labels"))
            labels_count = result.scalar()
            print(f"🏷️ Wallet labels: {labels_count:,}")
            
            if bonding_count > 0:
                print("✅ Database connectivity successful")
                return True
            else:
                print("⚠️ No bonding events found")
                return False
                
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_api_query_logic():
    """Test the exact SQL queries used in our API"""
    print("\n🧪 TESTING API QUERY LOGIC")
    print("=" * 50)
    
    engine = get_graph_db_connection()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # Find a wallet with trading activity
            find_wallet_query = """
            SELECT 
                user_address,
                COUNT(*) as trade_count,
                SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buys,
                SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sells
            FROM bonding_events 
            GROUP BY user_address 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
            """
            
            result = conn.execute(text(find_wallet_query))
            wallets = result.fetchall()
            
            if not wallets:
                print("⚠️ No wallets found with trading activity")
                return False
            
            print("📋 Top trading wallets:")
            for i, wallet in enumerate(wallets, 1):
                print(f"  {i}. {wallet.user_address[:10]}...{wallet.user_address[-6:]} - {wallet.trade_count} trades ({wallet.buys}B/{wallet.sells}S)")
            
            # Test our API query on the most active wallet
            test_address = wallets[0].user_address
            print(f"\n🎯 Testing API logic with wallet: {test_address[:10]}...{test_address[-6:]}")
            
            # Test the main analysis query from our API
            analysis_query = """
            WITH user_trades AS (
              SELECT 
                be.user_address,
                be.token_address,
                be.trade_type,
                be.avax_amount,
                be.token_amount,
                be.price_avax,
                be.protocol_fee,
                be.creator_fee,
                be.referral_fee,
                be.timestamp,
                be.transaction_hash,
                td.name as token_name,
                td.symbol as token_symbol,
                -- Calculate total cost including fees for BUY trades
                CASE 
                  WHEN be.trade_type = 'BUY' THEN be.avax_amount + be.protocol_fee + be.creator_fee + be.referral_fee
                  ELSE be.avax_amount - be.protocol_fee - be.creator_fee - be.referral_fee
                END as net_avax_amount
              FROM bonding_events be
              LEFT JOIN token_deployments td ON be.token_address = td.id
              WHERE LOWER(be.user_address) = LOWER(:address)
            ),
            position_pnl AS (
              SELECT 
                token_address,
                token_name,
                token_symbol,
                COUNT(*) as trades,
                SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
                SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
                SUM(CASE WHEN trade_type = 'BUY' THEN net_avax_amount ELSE 0 END) as total_buy_cost,
                SUM(CASE WHEN trade_type = 'SELL' THEN net_avax_amount ELSE 0 END) as total_sell_revenue,
                SUM(CASE WHEN trade_type = 'BUY' THEN token_amount ELSE 0 END) as tokens_bought,
                SUM(CASE WHEN trade_type = 'SELL' THEN token_amount ELSE 0 END) as tokens_sold,
                -- Calculate P&L: sell revenue - buy cost
                (SUM(CASE WHEN trade_type = 'SELL' THEN net_avax_amount ELSE 0 END) - 
                 SUM(CASE WHEN trade_type = 'BUY' THEN net_avax_amount ELSE 0 END)) as position_pnl
              FROM user_trades
              GROUP BY token_address, token_name, token_symbol
            ),
            wallet_summary AS (
              SELECT 
                COUNT(*) as total_trades,
                COUNT(DISTINCT token_address) as unique_tokens,
                SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as total_buys,
                SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as total_sells,
                SUM(CASE WHEN trade_type = 'BUY' THEN net_avax_amount ELSE 0 END) as total_invested,
                SUM(CASE WHEN trade_type = 'SELL' THEN net_avax_amount ELSE 0 END) as total_revenue,
                SUM(CASE WHEN trade_type = 'SELL' THEN net_avax_amount ELSE 0 END) - 
                SUM(CASE WHEN trade_type = 'BUY' THEN net_avax_amount ELSE 0 END) as total_pnl,
                AVG(net_avax_amount) as avg_trade_size,
                MIN(timestamp) as first_trade_time,
                MAX(timestamp) as last_trade_time
              FROM user_trades
            )
            SELECT 
              ws.*,
              -- Calculate win rate based on profitable positions
              (SELECT COUNT(*) FROM position_pnl WHERE position_pnl > 0) as profitable_trades,
              (SELECT COUNT(*) FROM position_pnl WHERE position_pnl < 0) as losing_trades,
              (SELECT MAX(position_pnl) FROM position_pnl) as biggest_win,
              (SELECT MIN(position_pnl) FROM position_pnl) as biggest_loss
            FROM wallet_summary ws
            """
            
            result = conn.execute(text(analysis_query), {'address': test_address})
            stats = result.fetchone()
            
            if stats:
                print(f"✅ Analysis query successful!")
                print(f"  📊 Total trades: {stats.total_trades}")
                print(f"  💰 Total P&L: {float(stats.total_pnl or 0):.4f} AVAX")
                print(f"  📈 Total invested: {float(stats.total_invested or 0):.4f} AVAX")
                print(f"  📉 Total revenue: {float(stats.total_revenue or 0):.4f} AVAX")
                print(f"  🎯 Profitable trades: {stats.profitable_trades or 0}")
                print(f"  ❌ Losing trades: {stats.losing_trades or 0}")
                print(f"  🥇 Biggest win: {float(stats.biggest_win or 0):.4f} AVAX")
                print(f"  💸 Biggest loss: {float(stats.biggest_loss or 0):.4f} AVAX")
                
                # Test recent trades query with token symbols
                recent_trades_query = """
                SELECT 
                  be.trade_type,
                  be.token_address,
                  td.name as token_name,
                  td.symbol as token_symbol,
                  be.avax_amount,
                  be.token_amount,
                  be.price_avax,
                  be.protocol_fee + be.creator_fee + be.referral_fee as total_fees,
                  CASE 
                    WHEN be.trade_type = 'BUY' THEN -(be.avax_amount + be.protocol_fee + be.creator_fee + be.referral_fee)
                    ELSE be.avax_amount - be.protocol_fee - be.creator_fee - be.referral_fee
                  END as pnl_impact,
                  be.timestamp,
                  be.transaction_hash
                FROM bonding_events be
                LEFT JOIN token_deployments td ON be.token_address = td.id
                WHERE LOWER(be.user_address) = LOWER(:address)
                ORDER BY be.timestamp DESC
                LIMIT 5
                """
                
                trades_result = conn.execute(text(recent_trades_query), {'address': test_address})
                trades = trades_result.fetchall()
                
                print(f"\n📝 Recent trades (showing 5):")
                for i, trade in enumerate(trades, 1):
                    token_name = trade.token_symbol or trade.token_name or 'Unknown'
                    pnl_symbol = '+' if float(trade.pnl_impact or 0) >= 0 else ''
                    print(f"  {i}. {trade.trade_type} {token_name} - {float(trade.avax_amount):.4f} AVAX (P&L: {pnl_symbol}{float(trade.pnl_impact or 0):.4f})")
                
                return True
            else:
                print("❌ Analysis query returned no results")
                return False
                
    except Exception as e:
        print(f"❌ API query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_token_symbol_joins():
    """Test that token symbol joins are working correctly"""
    print("\n🏷️ TESTING TOKEN SYMBOL JOINS")
    print("=" * 50)
    
    engine = get_graph_db_connection()
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            # Test join effectiveness
            join_test_query = """
            SELECT 
                COUNT(*) as total_bonding_events,
                COUNT(td.name) as events_with_token_names,
                COUNT(td.symbol) as events_with_token_symbols,
                ROUND(COUNT(td.name)::numeric / COUNT(*)::numeric * 100, 2) as name_coverage_percent,
                ROUND(COUNT(td.symbol)::numeric / COUNT(*)::numeric * 100, 2) as symbol_coverage_percent
            FROM bonding_events be
            LEFT JOIN token_deployments td ON be.token_address = td.id
            """
            
            result = conn.execute(text(join_test_query))
            stats = result.fetchone()
            
            print(f"📊 Join coverage analysis:")
            print(f"  Total bonding events: {stats.total_bonding_events:,}")
            print(f"  Events with token names: {stats.events_with_token_names:,} ({stats.name_coverage_percent}%)")
            print(f"  Events with token symbols: {stats.events_with_token_symbols:,} ({stats.symbol_coverage_percent}%)")
            
            if float(stats.name_coverage_percent) > 0:
                print("✅ Token symbol joins are working!")
                
                # Show some examples
                examples_query = """
                SELECT DISTINCT
                    be.token_address,
                    td.name,
                    td.symbol,
                    COUNT(*) as trade_count
                FROM bonding_events be
                LEFT JOIN token_deployments td ON be.token_address = td.id
                WHERE td.name IS NOT NULL
                GROUP BY be.token_address, td.name, td.symbol
                ORDER BY COUNT(*) DESC
                LIMIT 5
                """
                
                examples_result = conn.execute(text(examples_query))
                examples = examples_result.fetchall()
                
                print(f"\n🎯 Token examples with symbols:")
                for token in examples:
                    print(f"  {token.name} ({token.symbol}) - {token.trade_count} trades")
                
                return True
            else:
                print("⚠️ Token symbol joins not working - no token names found")
                return False
                
    except Exception as e:
        print(f"❌ Token symbol join test failed: {e}")
        return False

def main():
    """Run all API functionality tests"""
    print("🧪 WALLET ANALYSIS API FUNCTIONALITY TEST")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Database connectivity
    if test_database_connectivity():
        success_count += 1
    
    # Test 2: API query logic
    if test_api_query_logic():
        success_count += 1
    
    # Test 3: Token symbol joins
    if test_token_symbol_joins():
        success_count += 1
    
    print(f"\n🏁 TEST RESULTS")
    print("=" * 30)
    print(f"✅ Passed: {success_count}/{total_tests} tests")
    
    if success_count == total_tests:
        print("🎉 All tests passed! API should be working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return success_count == total_tests

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Enhanced Profit/Loss Analysis with Wallet Labels

This script provides comprehensive profit/loss analysis using the imported
Arena user labels and investigates any address matching issues.
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from sqlalchemy import text
from setup_graph_database import get_graph_db_connection

def check_wallet_matching():
    """Check how many wallets match between bonding_events and wallet_labels"""
    print("🔍 CHECKING WALLET ADDRESS MATCHING")
    print("=" * 60)
    
    engine = get_graph_db_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # Get counts from each table
            bonding_wallets = conn.execute(text("SELECT COUNT(DISTINCT user_address) FROM bonding_events")).scalar()
            labeled_wallets = conn.execute(text("SELECT COUNT(*) FROM wallet_labels")).scalar()
            
            # Find matches
            matching_query = """
            SELECT COUNT(DISTINCT be.user_address) as matching_wallets
            FROM bonding_events be
            INNER JOIN wallet_labels wl ON be.user_address = wl.wallet_address
            """
            matching_wallets = conn.execute(text(matching_query)).scalar()
            
            print(f"📊 Wallets in bonding_events: {bonding_wallets:,}")
            print(f"🏷️ Wallets with labels: {labeled_wallets:,}")
            print(f"🤝 Matching wallets: {matching_wallets:,}")
            print(f"📈 Match rate: {(matching_wallets/bonding_wallets*100):.1f}%")
            
            if matching_wallets == 0:
                print("\n⚠️ No matching wallets found!")
                print("🔍 Investigating address format differences...")
                
                # Show sample addresses from each table
                be_sample = conn.execute(text("SELECT DISTINCT user_address FROM bonding_events LIMIT 5")).fetchall()
                wl_sample = conn.execute(text("SELECT wallet_address FROM wallet_labels LIMIT 5")).fetchall()
                
                print("\n📋 Sample bonding_events addresses:")
                for addr in be_sample:
                    print(f"  {addr[0]}")
                
                print("\n📋 Sample wallet_labels addresses:")
                for addr in wl_sample:
                    print(f"  {addr[0]}")
                
                # Check if it's a case sensitivity issue
                case_insensitive_match = conn.execute(text("""
                    SELECT COUNT(DISTINCT be.user_address) as matching_wallets
                    FROM bonding_events be
                    INNER JOIN wallet_labels wl ON LOWER(be.user_address) = LOWER(wl.wallet_address)
                """)).scalar()
                
                print(f"\n🔍 Case-insensitive matches: {case_insensitive_match:,}")
                
                if case_insensitive_match > 0:
                    print("💡 Address case sensitivity issue detected!")
                    print("🔧 We can fix this by normalizing addresses to lowercase")
                    
                    # Normalize addresses in wallet_labels
                    conn.execute(text("UPDATE wallet_labels SET wallet_address = LOWER(wallet_address)"))
                    conn.commit()
                    print("✅ Normalized wallet_labels addresses to lowercase")
                    
                    # Recheck matches
                    new_matches = conn.execute(text(matching_query)).scalar()
                    print(f"🎯 New match count: {new_matches:,}")
            
            return matching_wallets
            
    except Exception as e:
        print(f"❌ Error checking wallet matching: {e}")
        return 0

def enhanced_profit_analysis_with_labels():
    """Enhanced profit analysis with wallet labels"""
    print("\n🌟 ENHANCED PROFIT ANALYSIS WITH ARENA USER LABELS")
    print("=" * 70)
    
    engine = get_graph_db_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # Enhanced analysis query with proper label matching
            query = """
            WITH user_trades AS (
                SELECT 
                    LOWER(user_address) as user_address,
                    SUM(CASE WHEN trade_type = 'BUY' THEN avax_amount + protocol_fee + creator_fee + referral_fee ELSE 0 END) as total_invested,
                    SUM(CASE WHEN trade_type = 'SELL' THEN avax_amount - protocol_fee - creator_fee - referral_fee ELSE 0 END) as total_revenue,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
                    SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
                    COUNT(DISTINCT token_address) as unique_tokens
                FROM bonding_events
                GROUP BY LOWER(user_address)
                HAVING COUNT(*) >= 2
            )
            SELECT 
                ut.user_address,
                COALESCE(wl.label, 'Anonymous') as wallet_label,
                COALESCE(wl.user_type, 'Unknown') as user_type,
                CASE WHEN wl.is_verified THEN '✅' ELSE '❓' END as verified_status,
                COALESCE(wl.risk_level, 'UNKNOWN') as risk_level,
                ROUND((ut.total_revenue - ut.total_invested)::numeric, 4) as net_pnl_avax,
                ROUND(
                    CASE 
                        WHEN ut.total_invested > 0 THEN ((ut.total_revenue - ut.total_invested) / ut.total_invested * 100)
                        ELSE 0 
                    END::numeric, 2
                ) as roi_percentage,
                ut.total_trades,
                ut.buy_trades,
                ut.sell_trades,
                ut.unique_tokens,
                wl.tags,
                CASE WHEN wl.wallet_address IS NOT NULL THEN 'Labeled' ELSE 'Anonymous' END as label_status
            FROM user_trades ut
            LEFT JOIN wallet_labels wl ON ut.user_address = wl.wallet_address
            WHERE ut.total_invested > 0
            ORDER BY net_pnl_avax DESC
            LIMIT 20
            """
            
            df = pd.read_sql(query, conn)
            
            if df.empty:
                print("⚠️ No trading data found for analysis")
                return
            
            # Count labeled vs anonymous
            labeled_count = len(df[df['label_status'] == 'Labeled'])
            anonymous_count = len(df[df['label_status'] == 'Anonymous'])
            
            print(f"📊 Top 20 traders: {labeled_count} labeled, {anonymous_count} anonymous")
            print()
            
            print("🏆 TOP 20 PERFORMERS WITH ENHANCED LABELS:")
            print("-" * 70)
            
            for i, (_, row) in enumerate(df.iterrows(), 1):
                # Status indicators
                verified = row['verified_status']
                risk_color = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🔴', 'UNKNOWN': '⚪'}.get(row['risk_level'], '⚪')
                labeled_icon = '🏷️' if row['label_status'] == 'Labeled' else '👤'
                
                print(f"{i:2d}. {labeled_icon} {row['wallet_label']} ({row['user_type']}) {verified}")
                print(f"    Address: {row['user_address'][:10]}...{row['user_address'][-6:]}")
                print(f"    P&L: {row['net_pnl_avax']:,.4f} AVAX ({row['roi_percentage']:+.1f}% ROI)")
                print(f"    Risk: {risk_color} {row['risk_level']} | Trades: {row['total_trades']} ({row['buy_trades']}B/{row['sell_trades']}S)")
                print(f"    Tokens: {row['unique_tokens']} | Tags: {row['tags'] or 'None'}")
                print()
            
            # Summary statistics by user type
            print("\n📈 PERFORMANCE BY USER TYPE:")
            print("-" * 50)
            
            summary_query = """
            WITH user_trades AS (
                SELECT 
                    LOWER(user_address) as user_address,
                    SUM(CASE WHEN trade_type = 'BUY' THEN avax_amount + protocol_fee + creator_fee + referral_fee ELSE 0 END) as total_invested,
                    SUM(CASE WHEN trade_type = 'SELL' THEN avax_amount - protocol_fee - creator_fee - referral_fee ELSE 0 END) as total_revenue,
                    COUNT(*) as total_trades
                FROM bonding_events
                GROUP BY LOWER(user_address)
                HAVING COUNT(*) >= 2
            )
            SELECT 
                COALESCE(wl.user_type, 'Unknown') as user_type,
                COUNT(*) as trader_count,
                ROUND(AVG(ut.total_revenue - ut.total_invested)::numeric, 4) as avg_pnl,
                ROUND(SUM(ut.total_revenue - ut.total_invested)::numeric, 4) as total_pnl,
                COUNT(CASE WHEN (ut.total_revenue - ut.total_invested) > 0 THEN 1 END) as profitable_traders,
                ROUND(
                    (COUNT(CASE WHEN (ut.total_revenue - ut.total_invested) > 0 THEN 1 END)::float / COUNT(*) * 100)::numeric, 1
                ) as win_rate_percent
            FROM user_trades ut
            LEFT JOIN wallet_labels wl ON ut.user_address = wl.wallet_address
            WHERE ut.total_invested > 0
            GROUP BY COALESCE(wl.user_type, 'Unknown')
            ORDER BY total_pnl DESC
            """
            
            summary_df = pd.read_sql(summary_query, conn)
            
            for _, row in summary_df.iterrows():
                print(f"{row['user_type']}:")
                print(f"  Traders: {row['trader_count']:,} ({row['profitable_traders']} profitable)")
                print(f"  Win Rate: {row['win_rate_percent']:.1f}%")
                print(f"  Avg P&L: {row['avg_pnl']:,.4f} AVAX")
                print(f"  Total P&L: {row['total_pnl']:,.4f} AVAX")
                print()
            
    except Exception as e:
        print(f"❌ Error in enhanced analysis: {e}")

def show_labeled_wallet_examples():
    """Show examples of successfully labeled wallets"""
    print("\n🏷️ EXAMPLES OF LABELED WALLETS")
    print("=" * 50)
    
    engine = get_graph_db_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            query = """
            SELECT 
                wl.wallet_address,
                wl.label,
                wl.user_type,
                wl.risk_level,
                wl.tags,
                CASE WHEN be.user_address IS NOT NULL THEN 'Active Trader' ELSE 'No Trading Activity' END as trading_status
            FROM wallet_labels wl
            LEFT JOIN (
                SELECT DISTINCT LOWER(user_address) as user_address 
                FROM bonding_events
            ) be ON wl.wallet_address = be.user_address
            ORDER BY RANDOM()
            LIMIT 10
            """
            
            df = pd.read_sql(query, conn)
            
            if df.empty:
                print("⚠️ No labeled wallets found")
                return
            
            for i, (_, row) in enumerate(df.iterrows(), 1):
                trading_icon = '📈' if row['trading_status'] == 'Active Trader' else '💤'
                print(f"{i:2d}. {trading_icon} {row['label']} ({row['user_type']})")
                print(f"    Address: {row['wallet_address'][:10]}...{row['wallet_address'][-6:]}")
                print(f"    Risk: {row['risk_level']} | Status: {row['trading_status']}")
                print(f"    Tags: {row['tags'] or 'None'}")
                print()
            
    except Exception as e:
        print(f"❌ Error showing examples: {e}")

def main():
    """Main analysis function"""
    print("🔥 ENHANCED ARENA TERMINAL PROFIT ANALYSIS")
    print("=" * 70)
    
    # Check wallet matching
    matches = check_wallet_matching()
    
    # Run enhanced analysis
    enhanced_profit_analysis_with_labels()
    
    # Show examples of labeled wallets
    show_labeled_wallet_examples()
    
    print("\n" + "=" * 70)
    print("✅ ENHANCED ANALYSIS COMPLETE!")
    print("=" * 70)
    
    if matches > 0:
        print("🎯 Wallet labels are successfully integrated with trading data!")
    else:
        print("⚠️ Limited wallet label integration. Consider:")
        print("  • Checking for address format differences")
        print("  • Verifying data sources align")
        print("  • Adding more wallet label sources")

if __name__ == "__main__":
    main() 
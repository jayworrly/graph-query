#!/usr/bin/env python3
"""
Quick Profit/Loss Analysis

Fast analysis of wallet performance using aggregate queries
on the bonding_events table.
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from sqlalchemy import text
from setup_graph_database import get_graph_db_connection

def quick_profit_analysis():
    print("⚡ QUICK WALLET PROFIT/LOSS ANALYSIS")
    print("=" * 60)
    print("🔥 Processing 788,000+ bonding events...")
    print()
    
    engine = get_graph_db_connection()
    if not engine:
        print("❌ Could not connect to database")
        return
    
    try:
        with engine.connect() as conn:
            
            # 1. Simple P&L calculation (revenue - costs per user)
            print("💰 CALCULATING WALLET PERFORMANCE...")
            
            query = """
            WITH user_trades AS (
                SELECT 
                    user_address,
                    SUM(CASE WHEN trade_type = 'BUY' THEN avax_amount + protocol_fee + creator_fee + referral_fee ELSE 0 END) as total_invested,
                    SUM(CASE WHEN trade_type = 'SELL' THEN avax_amount - protocol_fee - creator_fee - referral_fee ELSE 0 END) as total_revenue,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
                    SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
                    COUNT(DISTINCT token_address) as unique_tokens,
                    SUM(protocol_fee + creator_fee + referral_fee) as total_fees_paid,
                    MIN(timestamp) as first_trade,
                    MAX(timestamp) as last_trade
                FROM bonding_events
                GROUP BY user_address
                HAVING COUNT(*) >= 2  -- At least 2 trades for meaningful analysis
            )
            SELECT 
                user_address,
                total_trades,
                buy_trades,
                sell_trades,
                unique_tokens,
                ROUND(total_invested::numeric, 4) as invested_avax,
                ROUND(total_revenue::numeric, 4) as revenue_avax,
                ROUND((total_revenue - total_invested)::numeric, 4) as net_pnl_avax,
                ROUND(total_fees_paid::numeric, 4) as fees_paid_avax,
                ROUND(
                    CASE 
                        WHEN total_invested > 0 THEN ((total_revenue - total_invested) / total_invested * 100)
                        ELSE 0 
                    END::numeric, 2
                ) as roi_percentage,
                CASE 
                    WHEN (total_revenue - total_invested) > 0 THEN 'PROFITABLE'
                    WHEN (total_revenue - total_invested) < 0 THEN 'LOSING'
                    ELSE 'BREAK_EVEN'
                END as status
            FROM user_trades
            WHERE total_invested > 0  -- Only users who actually bought something
            ORDER BY net_pnl_avax DESC
            """
            
            print("🔍 Running analysis query...")
            df = pd.read_sql(query, conn)
            
            if df.empty:
                print("❌ No trading data found")
                return
            
            # Overall Statistics
            total_wallets = len(df)
            profitable = len(df[df['status'] == 'PROFITABLE'])
            losing = len(df[df['status'] == 'LOSING'])
            break_even = len(df[df['status'] == 'BREAK_EVEN'])
            
            print(f"\n📊 ECOSYSTEM OVERVIEW")
            print("-" * 40)
            print(f"Total Analyzed Wallets: {total_wallets:,}")
            print(f"Profitable Wallets: {profitable:,} ({profitable/total_wallets*100:.1f}%)")
            print(f"Losing Wallets: {losing:,} ({losing/total_wallets*100:.1f}%)")
            print(f"Break-even Wallets: {break_even:,} ({break_even/total_wallets*100:.1f}%)")
            print(f"Total Ecosystem P&L: {df['net_pnl_avax'].sum():,.4f} AVAX")
            print(f"Average Wallet P&L: {df['net_pnl_avax'].mean():,.4f} AVAX")
            print(f"Total Volume: {(df['invested_avax'].sum() + df['revenue_avax'].sum()):,.2f} AVAX")
            
            # Top 15 Most Profitable
            print(f"\n🏆 TOP 15 MOST PROFITABLE WALLETS")
            print("-" * 60)
            
            top_performers = df.head(15)
            for i, (_, row) in enumerate(top_performers.iterrows()):
                print(f"{i+1:2d}. {row['user_address'][:10]}...{row['user_address'][-6:]}")
                print(f"    💰 Profit: {row['net_pnl_avax']:,.4f} AVAX ({row['roi_percentage']:+.1f}% ROI)")
                print(f"    📊 Trades: {row['total_trades']} ({row['buy_trades']} buys, {row['sell_trades']} sells)")
                print(f"    🪙 Tokens: {row['unique_tokens']} | 💸 Fees: {row['fees_paid_avax']:.4f} AVAX")
                print()
            
            # Top 15 Biggest Losers
            print(f"📉 TOP 15 BIGGEST LOSERS")
            print("-" * 60)
            
            worst_performers = df.tail(15)
            for i, (_, row) in enumerate(worst_performers.iterrows()):
                print(f"{i+1:2d}. {row['user_address'][:10]}...{row['user_address'][-6:]}")
                print(f"    💸 Loss: {row['net_pnl_avax']:,.4f} AVAX ({row['roi_percentage']:+.1f}% ROI)")
                print(f"    📊 Trades: {row['total_trades']} ({row['buy_trades']} buys, {row['sell_trades']} sells)")
                print(f"    🪙 Tokens: {row['unique_tokens']} | 💸 Fees: {row['fees_paid_avax']:.4f} AVAX")
                print()
                
            # Performance by trading activity level
            print(f"📈 PERFORMANCE BY TRADING ACTIVITY")
            print("-" * 60)
            
            # Define trader categories
            df['trader_category'] = pd.cut(df['total_trades'], 
                                         bins=[0, 5, 20, 100, float('inf')], 
                                         labels=['Light (2-5 trades)', 'Moderate (6-20)', 'Active (21-100)', 'Heavy (100+)'])
            
            category_stats = df.groupby('trader_category').agg({
                'user_address': 'count',
                'net_pnl_avax': ['mean', 'sum'],
                'roi_percentage': 'mean',
                'total_trades': 'sum'
            }).round(4)
            
            category_stats.columns = ['wallets', 'avg_pnl', 'total_pnl', 'avg_roi', 'total_trades']
            
            for category, stats in category_stats.iterrows():
                profitable_in_cat = len(df[(df['trader_category'] == category) & (df['status'] == 'PROFITABLE')])
                print(f"{category}:")
                print(f"  Wallets: {int(stats['wallets']):,} ({profitable_in_cat} profitable)")
                print(f"  Avg P&L: {stats['avg_pnl']:,.4f} AVAX | Total P&L: {stats['total_pnl']:,.4f} AVAX")
                print(f"  Avg ROI: {stats['avg_roi']:+.2f}% | Total Trades: {int(stats['total_trades']):,}")
                print()
            
            # Top tokens by volume
            print(f"🪙 TOP TOKENS BY TRADING VOLUME")
            print("-" * 60)
            
            token_query = """
            SELECT 
                be.token_address,
                td.name,
                td.symbol,
                COUNT(*) as total_trades,
                COUNT(DISTINCT be.user_address) as unique_traders,
                SUM(be.avax_amount) as total_volume_avax,
                SUM(CASE WHEN be.trade_type = 'BUY' THEN be.avax_amount ELSE 0 END) as buy_volume,
                SUM(CASE WHEN be.trade_type = 'SELL' THEN be.avax_amount ELSE 0 END) as sell_volume
            FROM bonding_events be
            LEFT JOIN token_deployments td ON be.token_address = td.id
            GROUP BY be.token_address, td.name, td.symbol
            ORDER BY total_volume_avax DESC
            LIMIT 10
            """
            
            df_tokens = pd.read_sql(token_query, conn)
            
            for i, (_, token) in enumerate(df_tokens.iterrows()):
                name = token['name'] or 'Unknown'
                symbol = token['symbol'] or '???'
                print(f"{i+1:2d}. {name} ({symbol})")
                print(f"    Volume: {token['total_volume_avax']:,.2f} AVAX")
                print(f"    Trades: {token['total_trades']:,} | Traders: {token['unique_traders']:,}")
                print(f"    Buy Vol: {token['buy_volume']:,.2f} | Sell Vol: {token['sell_volume']:,.2f}")
                print()
            
            # Save results
            filename = f"quick_profit_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            print(f"💾 Results saved to: {filename}")
            print(f"📊 Analysis complete! Processed data for {total_wallets:,} active wallets")
            
    except Exception as e:
        print(f"❌ Error in analysis: {e}")

if __name__ == "__main__":
    quick_profit_analysis() 
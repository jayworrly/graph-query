#!/usr/bin/env python3
"""
Wallet Profit/Loss Analysis Script

This script analyzes trading data from the Arena Terminal bonding events 
to identify which wallets are making profit and which are losing money.
"""

import pandas as pd
from sqlalchemy import text, create_engine
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from setup_graph_database import get_graph_db_connection
import os
from datetime import datetime

def format_currency(value):
    """Format currency values for display"""
    if pd.isna(value) or value == 0:
        return "0.0000"
    return f"{float(value):,.4f}"

def format_percentage(value):
    """Format percentage values for display"""
    if pd.isna(value) or value == 0:
        return "0.00%"
    return f"{float(value):+.2f}%"

def analyze_wallet_profits():
    """Main analysis function"""
    print("=" * 80)
    print("ARENA TERMINAL - WALLET PROFIT/LOSS ANALYSIS")
    print("=" * 80)
    print(f"Analysis run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    engine = get_graph_db_connection()
    if not engine:
        print("❌ Could not connect to database")
        return
    
    try:
        with engine.connect() as conn:
            
            # 1. Overall Statistics
            print("📊 OVERALL ECOSYSTEM STATISTICS")
            print("-" * 50)
            
            query = """
            SELECT 
                COUNT(*) as total_active_wallets,
                SUM(CASE WHEN total_pnl_avax > 0 THEN 1 ELSE 0 END) as profitable_wallets,
                SUM(CASE WHEN total_pnl_avax < 0 THEN 1 ELSE 0 END) as losing_wallets,
                SUM(CASE WHEN total_pnl_avax = 0 THEN 1 ELSE 0 END) as break_even_wallets,
                ROUND((SUM(CASE WHEN total_pnl_avax > 0 THEN 1 ELSE 0 END)::float / COUNT(*) * 100)::numeric, 2) as percent_profitable,
                ROUND(SUM(total_pnl_avax)::numeric, 4) as total_ecosystem_pnl,
                ROUND(AVG(total_pnl_avax)::numeric, 4) as avg_wallet_pnl,
                SUM(total_trades) as total_trades_all
            FROM user_activity
            WHERE total_trades > 0
            """
            
            df_stats = pd.read_sql(query, conn)
            
            if not df_stats.empty:
                stats = df_stats.iloc[0]
                print(f"Total Active Wallets: {stats['total_active_wallets']:,}")
                print(f"Profitable Wallets: {stats['profitable_wallets']:,} ({stats['percent_profitable']:.1f}%)")
                print(f"Losing Wallets: {stats['losing_wallets']:,}")
                print(f"Break-even Wallets: {stats['break_even_wallets']:,}")
                print(f"Total Ecosystem P&L: {format_currency(stats['total_ecosystem_pnl'])} AVAX")
                print(f"Average Wallet P&L: {format_currency(stats['avg_wallet_pnl'])} AVAX")
                print(f"Total Trades: {stats['total_trades_all']:,}")
            
            print("\n" + "=" * 80)
            
            # 2. Top 10 Most Profitable Wallets
            print("🏆 TOP 10 MOST PROFITABLE WALLETS")
            print("-" * 50)
            
            query = """
            SELECT 
                user_address as wallet,
                ROUND(total_pnl_avax::numeric, 4) as total_profit_avax,
                ROUND(portfolio_roi::numeric, 2) as roi_percentage,
                total_trades,
                profitable_trades,
                losing_trades,
                ROUND(win_rate::numeric, 2) as win_rate_percent,
                unique_tokens_traded
            FROM user_activity 
            WHERE total_pnl_avax > 0
            ORDER BY total_pnl_avax DESC
            LIMIT 10
            """
            
            df_winners = pd.read_sql(query, conn)
            
            if not df_winners.empty:
                for i, row in df_winners.iterrows():
                    print(f"{i+1:2d}. {row['wallet'][:10]}...{row['wallet'][-6:]}")
                    print(f"    Profit: {format_currency(row['total_profit_avax'])} AVAX ({format_percentage(row['roi_percentage'])})")
                    print(f"    Trades: {row['total_trades']} ({row['profitable_trades']} wins, {row['losing_trades']} losses)")
                    print(f"    Win Rate: {row['win_rate_percent']:.1f}% | Tokens: {row['unique_tokens_traded']}")
                    print()
            
            print("=" * 80)
            
            # 3. Top 10 Biggest Losers
            print("📉 TOP 10 BIGGEST LOSERS")
            print("-" * 50)
            
            query = """
            SELECT 
                user_address as wallet,
                ROUND(total_pnl_avax::numeric, 4) as total_loss_avax,
                ROUND(portfolio_roi::numeric, 2) as roi_percentage,
                total_trades,
                profitable_trades,
                losing_trades,
                ROUND(win_rate::numeric, 2) as win_rate_percent,
                unique_tokens_traded
            FROM user_activity 
            WHERE total_pnl_avax < 0
            ORDER BY total_pnl_avax ASC
            LIMIT 10
            """
            
            df_losers = pd.read_sql(query, conn)
            
            if not df_losers.empty:
                for i, row in df_losers.iterrows():
                    print(f"{i+1:2d}. {row['wallet'][:10]}...{row['wallet'][-6:]}")
                    print(f"    Loss: {format_currency(row['total_loss_avax'])} AVAX ({format_percentage(row['roi_percentage'])})")
                    print(f"    Trades: {row['total_trades']} ({row['profitable_trades']} wins, {row['losing_trades']} losses)")
                    print(f"    Win Rate: {row['win_rate_percent']:.1f}% | Tokens: {row['unique_tokens_traded']}")
                    print()
            
            print("=" * 80)
            
            # 4. Trading Performance by Category
            print("📈 TRADING PERFORMANCE BY CATEGORY")
            print("-" * 50)
            
            query = """
            SELECT 
                CASE 
                    WHEN total_pnl_avax > 0 THEN 'PROFITABLE' 
                    WHEN total_pnl_avax < 0 THEN 'LOSING'
                    ELSE 'BREAK_EVEN'
                END as trader_category,
                COUNT(*) as number_of_wallets,
                ROUND(AVG(total_pnl_avax)::numeric, 4) as avg_pnl_per_wallet,
                ROUND(SUM(total_pnl_avax)::numeric, 4) as total_category_pnl,
                ROUND(AVG(portfolio_roi)::numeric, 2) as avg_roi_percentage,
                ROUND(AVG(win_rate)::numeric, 2) as avg_win_rate,
                SUM(total_trades) as total_trades_in_category
            FROM user_activity
            WHERE total_trades > 0
            GROUP BY 
                CASE 
                    WHEN total_pnl_avax > 0 THEN 'PROFITABLE' 
                    WHEN total_pnl_avax < 0 THEN 'LOSING'
                    ELSE 'BREAK_EVEN'
                END
            ORDER BY total_category_pnl DESC
            """
            
            df_categories = pd.read_sql(query, conn)
            
            if not df_categories.empty:
                for _, row in df_categories.iterrows():
                    print(f"{row['trader_category']} TRADERS:")
                    print(f"  Wallets: {row['number_of_wallets']:,}")
                    print(f"  Total P&L: {format_currency(row['total_category_pnl'])} AVAX")
                    print(f"  Avg P&L per Wallet: {format_currency(row['avg_pnl_per_wallet'])} AVAX")
                    print(f"  Avg ROI: {format_percentage(row['avg_roi_percentage'])}")
                    print(f"  Avg Win Rate: {row['avg_win_rate']:.1f}%")
                    print(f"  Total Trades: {row['total_trades_in_category']:,}")
                    print()
            
            print("=" * 80)
            
            # 5. Recent High-Volume Traders
            print("🔥 RECENT HIGH-VOLUME TRADERS (P&L ANALYSIS)")
            print("-" * 50)
            
            query = """
            WITH recent_volume AS (
                SELECT 
                    user_address,
                    COUNT(*) as recent_trades,
                    SUM(avax_amount) as recent_volume_avax
                FROM bonding_events 
                WHERE timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days')
                GROUP BY user_address
                HAVING SUM(avax_amount) > 1.0  -- At least 1 AVAX volume
                ORDER BY recent_volume_avax DESC
                LIMIT 10
            )
            SELECT 
                rv.user_address as wallet,
                ROUND(rv.recent_volume_avax::numeric, 4) as recent_7d_volume,
                rv.recent_trades as recent_7d_trades,
                COALESCE(ROUND(ua.total_pnl_avax::numeric, 4), 0) as total_pnl,
                COALESCE(ROUND(ua.portfolio_roi::numeric, 2), 0) as roi_percentage,
                COALESCE(ua.total_trades, 0) as total_trades,
                COALESCE(ROUND(ua.win_rate::numeric, 2), 0) as win_rate
            FROM recent_volume rv
            LEFT JOIN user_activity ua ON rv.user_address = ua.user_address
            ORDER BY rv.recent_volume_avax DESC
            """
            
            df_recent = pd.read_sql(query, conn)
            
            if not df_recent.empty:
                for i, row in df_recent.iterrows():
                    print(f"{i+1:2d}. {row['wallet'][:10]}...{row['wallet'][-6:]}")
                    print(f"    Recent Volume: {format_currency(row['recent_7d_volume'])} AVAX ({row['recent_7d_trades']} trades)")
                    print(f"    Total P&L: {format_currency(row['total_pnl'])} AVAX ({format_percentage(row['roi_percentage'])})")
                    print(f"    Overall: {row['total_trades']} trades | {row['win_rate']:.1f}% win rate")
                    print()
            
            print("=" * 80)
            print("✅ Analysis complete!")
            
    except Exception as e:
        print(f"❌ Error running analysis: {e}")

def save_detailed_report():
    """Save a detailed CSV report of all wallet performance"""
    print("\n📋 Generating detailed CSV report...")
    
    engine = get_graph_db_connection()
    if not engine:
        print("❌ Could not connect to database")
        return
    
    try:
        with engine.connect() as conn:
            query = """
            SELECT 
                user_address as wallet,
                total_trades,
                ROUND(total_volume_avax::numeric, 4) as total_volume_avax,
                ROUND(total_investment_avax::numeric, 4) as total_invested_avax,
                ROUND(realized_pnl_avax::numeric, 4) as realized_profit_loss,
                ROUND(unrealized_pnl_avax::numeric, 4) as unrealized_profit_loss,
                ROUND(total_pnl_avax::numeric, 4) as total_profit_loss,
                ROUND(portfolio_roi::numeric, 2) as roi_percentage,
                CASE 
                    WHEN total_pnl_avax > 0 THEN 'PROFITABLE' 
                    WHEN total_pnl_avax < 0 THEN 'LOSING'
                    ELSE 'BREAK_EVEN'
                END as status,
                profitable_trades,
                losing_trades,
                ROUND(win_rate::numeric, 2) as win_rate_percent,
                unique_tokens_traded,
                ROUND(largest_win_avax::numeric, 4) as biggest_win,
                ROUND(largest_loss_avax::numeric, 4) as biggest_loss
            FROM user_activity 
            WHERE total_trades > 0
            ORDER BY total_pnl_avax DESC
            """
            
            df_report = pd.read_sql(query, conn)
            
            if not df_report.empty:
                filename = f"wallet_profit_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df_report.to_csv(filename, index=False)
                print(f"✅ Detailed report saved to: {filename}")
                print(f"📊 Report contains {len(df_report)} wallets")
            else:
                print("⚠️ No data found for report")
                
    except Exception as e:
        print(f"❌ Error generating report: {e}")

if __name__ == "__main__":
    analyze_wallet_profits()
    
    # Ask if user wants detailed CSV report
    response = input("\nWould you like to generate a detailed CSV report? (y/n): ").lower().strip()
    if response == 'y' or response == 'yes':
        save_detailed_report()
    
    print("\n🎯 For more detailed analysis, you can run individual queries from 'profit_loss_analysis.sql'") 
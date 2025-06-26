#!/usr/bin/env python3
"""
Manual Profit/Loss Calculator

This script calculates profit/loss directly from the bonding_events table
using FIFO (First In, First Out) accounting methodology.
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from sqlalchemy import text
from setup_graph_database import get_graph_db_connection
from collections import defaultdict, deque
import numpy as np

class FIFOPortfolioTracker:
    """
    Tracks portfolio positions using FIFO (First In, First Out) methodology
    for calculating realized profits and losses.
    """
    
    def __init__(self):
        self.positions = defaultdict(lambda: {
            'holdings': deque(),  # (quantity, price) tuples
            'total_quantity': 0,
            'realized_pnl': 0,
            'total_bought': 0,
            'total_sold': 0,
            'total_cost': 0,
            'total_revenue': 0
        })
    
    def buy(self, token_address, quantity, price_per_token):
        """Record a buy transaction"""
        position = self.positions[token_address]
        position['holdings'].append((quantity, price_per_token))
        position['total_quantity'] += quantity
        position['total_bought'] += quantity
        position['total_cost'] += quantity * price_per_token
    
    def sell(self, token_address, quantity, price_per_token):
        """Record a sell transaction and calculate realized P&L"""
        position = self.positions[token_address]
        
        if position['total_quantity'] < quantity:
            # This shouldn't happen with clean data, but handle gracefully
            print(f"Warning: Selling more than held for {token_address}")
            return 0
        
        remaining_to_sell = quantity
        total_cost_basis = 0
        
        # Use FIFO to determine cost basis
        while remaining_to_sell > 0 and position['holdings']:
            held_quantity, held_price = position['holdings'][0]
            
            if held_quantity <= remaining_to_sell:
                # Sell entire holding
                total_cost_basis += held_quantity * held_price
                remaining_to_sell -= held_quantity
                position['holdings'].popleft()
            else:
                # Partial sell
                total_cost_basis += remaining_to_sell * held_price
                position['holdings'][0] = (held_quantity - remaining_to_sell, held_price)
                remaining_to_sell = 0
        
        # Calculate P&L for this trade
        revenue = quantity * price_per_token
        trade_pnl = revenue - total_cost_basis
        
        # Update position tracking
        position['total_quantity'] -= quantity
        position['total_sold'] += quantity
        position['realized_pnl'] += trade_pnl
        position['total_revenue'] += revenue
        
        return trade_pnl
    
    def get_unrealized_pnl(self, token_address, current_price):
        """Calculate unrealized P&L for current holdings"""
        position = self.positions[token_address]
        
        if position['total_quantity'] == 0:
            return 0
        
        # Calculate average cost of remaining holdings
        total_cost = sum(qty * price for qty, price in position['holdings'])
        current_value = position['total_quantity'] * current_price
        
        return current_value - total_cost
    
    def get_position_summary(self, token_address):
        """Get complete position summary"""
        position = self.positions[token_address]
        
        return {
            'current_quantity': position['total_quantity'],
            'total_bought': position['total_bought'],
            'total_sold': position['total_sold'],
            'total_cost': position['total_cost'],
            'total_revenue': position['total_revenue'],
            'realized_pnl': position['realized_pnl'],
            'avg_buy_price': position['total_cost'] / position['total_bought'] if position['total_bought'] > 0 else 0,
            'avg_sell_price': position['total_revenue'] / position['total_sold'] if position['total_sold'] > 0 else 0
        }

def calculate_manual_pnl():
    """Calculate P&L manually from bonding_events table"""
    print("🔢 MANUAL PROFIT/LOSS CALCULATION FROM BONDING EVENTS")
    print("=" * 70)
    
    engine = get_graph_db_connection()
    if not engine:
        print("❌ Could not connect to database")
        return
    
    try:
        with engine.connect() as conn:
            # Fetch all bonding events ordered by user and timestamp
            query = """
            SELECT 
                user_address,
                token_address,
                trade_type,
                avax_amount,
                token_amount,
                price_avax,
                protocol_fee,
                creator_fee,
                referral_fee,
                timestamp,
                transaction_hash
            FROM bonding_events
            ORDER BY user_address, timestamp
            """
            
            print("📊 Loading bonding events...")
            df = pd.read_sql(query, conn)
            
            if df.empty:
                print("⚠️ No bonding events found in database")
                return
            
            print(f"✅ Loaded {len(df):,} bonding events")
            
            # Group by user and calculate P&L
            user_portfolios = {}
            user_results = []
            
            print("💰 Calculating P&L for each wallet...")
            
            for user_address in df['user_address'].unique():
                user_data = df[df['user_address'] == user_address].sort_values('timestamp')
                portfolio = FIFOPortfolioTracker()
                
                total_fees_paid = 0
                trade_count = 0
                
                for _, trade in user_data.iterrows():
                    trade_count += 1
                    
                    # Calculate effective price including fees
                    fees = trade['protocol_fee'] + trade['creator_fee'] + trade['referral_fee']
                    total_fees_paid += fees
                    
                    if trade['trade_type'] == 'BUY':
                        # For buys, add fees to cost basis
                        effective_price = (trade['avax_amount'] + fees) / trade['token_amount']
                        portfolio.buy(trade['token_address'], trade['token_amount'], effective_price)
                    
                    elif trade['trade_type'] == 'SELL':
                        # For sells, subtract fees from revenue
                        effective_price = (trade['avax_amount'] - fees) / trade['token_amount']
                        portfolio.sell(trade['token_address'], trade['token_amount'], effective_price)
                
                # Calculate total portfolio metrics
                total_realized_pnl = 0
                total_cost = 0
                total_revenue = 0
                tokens_traded = 0
                
                for token_address in portfolio.positions:
                    position = portfolio.get_position_summary(token_address)
                    total_realized_pnl += position['realized_pnl']
                    total_cost += position['total_cost']
                    total_revenue += position['total_revenue']
                    if position['total_bought'] > 0 or position['total_sold'] > 0:
                        tokens_traded += 1
                
                # Calculate ROI
                roi = (total_realized_pnl / total_cost * 100) if total_cost > 0 else 0
                
                user_results.append({
                    'wallet': user_address,
                    'total_trades': trade_count,
                    'unique_tokens': tokens_traded,
                    'total_cost': total_cost,
                    'total_revenue': total_revenue,
                    'realized_pnl': total_realized_pnl,
                    'total_fees_paid': total_fees_paid,
                    'roi_percentage': roi,
                    'net_pnl_after_fees': total_realized_pnl - total_fees_paid
                })
                
                user_portfolios[user_address] = portfolio
            
            # Convert to DataFrame and sort by P&L
            results_df = pd.DataFrame(user_results)
            results_df = results_df.sort_values('realized_pnl', ascending=False)
            
            print(f"\n📈 MANUAL CALCULATION RESULTS ({len(results_df)} wallets)")
            print("=" * 70)
            
            # Summary statistics
            profitable_wallets = len(results_df[results_df['realized_pnl'] > 0])
            losing_wallets = len(results_df[results_df['realized_pnl'] < 0])
            break_even_wallets = len(results_df[results_df['realized_pnl'] == 0])
            
            print(f"Profitable Wallets: {profitable_wallets} ({profitable_wallets/len(results_df)*100:.1f}%)")
            print(f"Losing Wallets: {losing_wallets} ({losing_wallets/len(results_df)*100:.1f}%)")
            print(f"Break-even Wallets: {break_even_wallets}")
            print(f"Total Ecosystem P&L: {results_df['realized_pnl'].sum():.4f} AVAX")
            print(f"Average Wallet P&L: {results_df['realized_pnl'].mean():.4f} AVAX")
            print()
            
            # Top 10 performers
            print("🏆 TOP 10 PERFORMERS (Manual Calculation)")
            print("-" * 50)
            
            for i, (_, row) in enumerate(results_df.head(10).iterrows()):
                print(f"{i+1:2d}. {row['wallet'][:10]}...{row['wallet'][-6:]}")
                print(f"    P&L: {row['realized_pnl']:,.4f} AVAX (ROI: {row['roi_percentage']:+.2f}%)")
                print(f"    Trades: {row['total_trades']} | Tokens: {row['unique_tokens']}")
                print(f"    Invested: {row['total_cost']:,.4f} | Revenue: {row['total_revenue']:,.4f}")
                print(f"    Fees Paid: {row['total_fees_paid']:,.4f} | Net P&L: {row['net_pnl_after_fees']:,.4f}")
                print()
            
            # Bottom 10 performers
            print("📉 BOTTOM 10 PERFORMERS (Manual Calculation)")
            print("-" * 50)
            
            for i, (_, row) in enumerate(results_df.tail(10).iterrows()):
                print(f"{i+1:2d}. {row['wallet'][:10]}...{row['wallet'][-6:]}")
                print(f"    P&L: {row['realized_pnl']:,.4f} AVAX (ROI: {row['roi_percentage']:+.2f}%)")
                print(f"    Trades: {row['total_trades']} | Tokens: {row['unique_tokens']}")
                print(f"    Invested: {row['total_cost']:,.4f} | Revenue: {row['total_revenue']:,.4f}")
                print(f"    Fees Paid: {row['total_fees_paid']:,.4f} | Net P&L: {row['net_pnl_after_fees']:,.4f}")
                print()
            
            # Save detailed results
            filename = f"manual_pnl_calculation_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            results_df.to_csv(filename, index=False)
            print(f"✅ Detailed results saved to: {filename}")
            
            return results_df, user_portfolios
            
    except Exception as e:
        print(f"❌ Error in manual calculation: {e}")
        return None, None

def compare_calculations():
    """Compare manual calculations with pre-calculated user_activity table"""
    print("\n🔍 COMPARING MANUAL VS PRE-CALCULATED RESULTS")
    print("=" * 60)
    
    engine = get_graph_db_connection()
    if not engine:
        print("❌ Could not connect to database")
        return
    
    try:
        with engine.connect() as conn:
            # Get pre-calculated results
            query = """
            SELECT 
                user_address as wallet,
                ROUND(realized_pnl_avax::numeric, 4) as precalc_realized_pnl,
                ROUND(portfolio_roi::numeric, 2) as precalc_roi,
                total_trades as precalc_trades
            FROM user_activity
            WHERE total_trades > 0
            ORDER BY realized_pnl_avax DESC
            LIMIT 20
            """
            
            df_precalc = pd.read_sql(query, conn)
            
            if df_precalc.empty:
                print("⚠️ No pre-calculated data found in user_activity table")
                print("💡 You may need to run the sync process to populate user_activity table")
                return
            
            print(f"📊 Found {len(df_precalc)} wallets in user_activity table")
            print("\nSample comparison (top 10 wallets):")
            print("-" * 60)
            
            for _, row in df_precalc.head(10).iterrows():
                print(f"{row['wallet'][:10]}...{row['wallet'][-6:]}")
                print(f"  Pre-calc P&L: {row['precalc_realized_pnl']:,.4f} AVAX")
                print(f"  Pre-calc ROI: {row['precalc_roi']:+.2f}%")
                print(f"  Trades: {row['precalc_trades']}")
                print()
                
    except Exception as e:
        print(f"❌ Error comparing calculations: {e}")

if __name__ == "__main__":
    # Run manual calculation
    manual_results, portfolios = calculate_manual_pnl()
    
    if manual_results is not None:
        # Compare with pre-calculated if available
        compare_calculations()
        
        print("\n" + "=" * 70)
        print("✅ Manual P&L calculation complete!")
        print("💡 This method calculates realized P&L using FIFO accounting")
        print("💡 For unrealized P&L, you'd need current token prices")
        print("💡 The pre-calculated tables should give similar results if they're up to date") 
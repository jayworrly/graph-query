#!/usr/bin/env python3
"""
Specific Wallet Lookup

This script looks up detailed trading information for a specific wallet address.
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from sqlalchemy import text
from setup_graph_database import get_graph_db_connection

def lookup_wallet(wallet_address):
    """Look up detailed information for a specific wallet"""
    print(f"🔍 WALLET LOOKUP: {wallet_address}")
    print("=" * 80)
    
    # Normalize address to lowercase
    wallet_address = wallet_address.lower()
    
    engine = get_graph_db_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # 1. Check if wallet has a label
            label_query = """
            SELECT 
                wallet_address,
                label,
                user_type,
                risk_level,
                is_verified,
                tags,
                notes,
                created_at
            FROM wallet_labels
            WHERE wallet_address = :wallet_address
            """
            
            label_result = conn.execute(text(label_query), {'wallet_address': wallet_address})
            label_data = label_result.fetchone()
            
            if label_data:
                print("🏷️ WALLET LABEL INFORMATION:")
                print(f"  Name: {label_data.label}")
                print(f"  Type: {label_data.user_type}")
                print(f"  Risk Level: {label_data.risk_level}")
                print(f"  Verified: {'✅' if label_data.is_verified else '❓'}")
                print(f"  Tags: {label_data.tags or 'None'}")
                print(f"  Notes: {label_data.notes or 'None'}")
                print(f"  Added: {label_data.created_at}")
            else:
                print("🏷️ WALLET LABEL: Anonymous (no label found)")
            
            # 2. Trading summary
            summary_query = """
            SELECT 
                COUNT(*) as total_trades,
                COUNT(DISTINCT token_address) as unique_tokens,
                SUM(CASE WHEN trade_type = 'BUY' THEN 1 ELSE 0 END) as buy_trades,
                SUM(CASE WHEN trade_type = 'SELL' THEN 1 ELSE 0 END) as sell_trades,
                SUM(CASE WHEN trade_type = 'BUY' THEN avax_amount + protocol_fee + creator_fee + referral_fee ELSE 0 END) as total_invested,
                SUM(CASE WHEN trade_type = 'SELL' THEN avax_amount - protocol_fee - creator_fee - referral_fee ELSE 0 END) as total_revenue,
                MIN(timestamp) as first_trade,
                MAX(timestamp) as last_trade,
                SUM(protocol_fee + creator_fee + referral_fee) as total_fees_paid
            FROM bonding_events
            WHERE LOWER(user_address) = :wallet_address
            """
            
            summary_result = conn.execute(text(summary_query), {'wallet_address': wallet_address})
            summary = summary_result.fetchone()
            
            if summary and summary.total_trades > 0:
                net_pnl = (summary.total_revenue or 0) - (summary.total_invested or 0)
                roi = ((net_pnl / summary.total_invested) * 100) if summary.total_invested > 0 else 0
                
                print(f"\n📊 TRADING SUMMARY:")
                print(f"  Total Trades: {summary.total_trades:,}")
                print(f"  Buy Trades: {summary.buy_trades:,}")
                print(f"  Sell Trades: {summary.sell_trades:,}")
                print(f"  Unique Tokens: {summary.unique_tokens:,}")
                print(f"  Total Invested: {summary.total_invested:.4f} AVAX")
                print(f"  Total Revenue: {summary.total_revenue:.4f} AVAX")
                print(f"  Net P&L: {net_pnl:+.4f} AVAX")
                print(f"  ROI: {roi:+.1f}%")
                print(f"  Total Fees: {summary.total_fees_paid:.4f} AVAX")
                print(f"  First Trade: {pd.to_datetime(summary.first_trade, unit='s')}")
                print(f"  Last Trade: {pd.to_datetime(summary.last_trade, unit='s')}")
                
                # 3. Top tokens traded
                tokens_query = """
                SELECT 
                    td.name as token_name,
                    td.symbol as token_symbol,
                    be.token_address,
                    COUNT(*) as trades,
                    SUM(CASE WHEN be.trade_type = 'BUY' THEN 1 ELSE 0 END) as buys,
                    SUM(CASE WHEN be.trade_type = 'SELL' THEN 1 ELSE 0 END) as sells,
                    SUM(CASE WHEN be.trade_type = 'BUY' THEN be.avax_amount ELSE 0 END) as avax_bought,
                    SUM(CASE WHEN be.trade_type = 'SELL' THEN be.avax_amount ELSE 0 END) as avax_sold,
                    (SUM(CASE WHEN be.trade_type = 'SELL' THEN be.avax_amount ELSE 0 END) - 
                     SUM(CASE WHEN be.trade_type = 'BUY' THEN be.avax_amount ELSE 0 END)) as token_pnl
                FROM bonding_events be
                LEFT JOIN token_deployments td ON be.token_address = td.id
                WHERE LOWER(be.user_address) = :wallet_address
                GROUP BY be.token_address, td.name, td.symbol
                ORDER BY trades DESC
                LIMIT 10
                """
                
                tokens_result = conn.execute(text(tokens_query), {'wallet_address': wallet_address})
                tokens = tokens_result.fetchall()
                
                print(f"\n🪙 TOP 10 TOKENS TRADED:")
                print("-" * 80)
                for i, token in enumerate(tokens, 1):
                    token_name = token.token_name or f"Token_{token.token_address[-6:]}"
                    symbol = token.token_symbol or "UNK"
                    print(f"{i:2d}. {token_name} ({symbol})")
                    print(f"    Address: {token.token_address}")
                    print(f"    Trades: {token.trades} ({token.buys}B/{token.sells}S)")
                    print(f"    Volume: {token.avax_bought:.4f} AVAX bought, {token.avax_sold:.4f} AVAX sold")
                    print(f"    Token P&L: {token.token_pnl:+.4f} AVAX")
                    print()
                
                # 4. Recent trades
                recent_query = """
                SELECT 
                    be.trade_type,
                    be.avax_amount,
                    be.token_amount,
                    be.price_avax,
                    be.timestamp,
                    be.token_address,
                    td.name as token_name,
                    td.symbol as token_symbol
                FROM bonding_events be
                LEFT JOIN token_deployments td ON be.token_address = td.id
                WHERE LOWER(be.user_address) = :wallet_address
                ORDER BY be.timestamp DESC
                LIMIT 15
                """
                
                recent_result = conn.execute(text(recent_query), {'wallet_address': wallet_address})
                recent_trades = recent_result.fetchall()
                
                print(f"📈 RECENT 15 TRADES:")
                print("-" * 80)
                for i, trade in enumerate(recent_trades, 1):
                    token_name = trade.token_name or f"Token_{trade.token_address[-6:]}"
                    symbol = trade.token_symbol or "UNK"
                    trade_time = pd.to_datetime(trade.timestamp, unit='s')
                    trade_icon = "🟢" if trade.trade_type == "BUY" else "🔴"
                    
                    print(f"{i:2d}. {trade_icon} {trade.trade_type} {token_name} ({symbol})")
                    print(f"    Amount: {trade.avax_amount:.4f} AVAX for {trade.token_amount:.2f} tokens")
                    print(f"    Price: {trade.price_avax:.8f} AVAX per token")
                    print(f"    Time: {trade_time}")
                    print()
                
                # 5. Performance ranking
                ranking_query = """
                WITH user_pnl AS (
                    SELECT 
                        LOWER(user_address) as user_address,
                        (SUM(CASE WHEN trade_type = 'SELL' THEN avax_amount - protocol_fee - creator_fee - referral_fee ELSE 0 END) - 
                         SUM(CASE WHEN trade_type = 'BUY' THEN avax_amount + protocol_fee + creator_fee + referral_fee ELSE 0 END)) as net_pnl,
                        COUNT(*) as trades
                    FROM bonding_events
                    GROUP BY LOWER(user_address)
                    HAVING COUNT(*) >= 2
                ),
                ranked_users AS (
                    SELECT 
                        user_address,
                        net_pnl,
                        trades,
                        ROW_NUMBER() OVER (ORDER BY net_pnl DESC) as rank
                    FROM user_pnl
                    WHERE net_pnl IS NOT NULL
                )
                SELECT rank, net_pnl, trades
                FROM ranked_users
                WHERE user_address = :wallet_address
                """
                
                rank_result = conn.execute(text(ranking_query), {'wallet_address': wallet_address})
                rank_data = rank_result.fetchone()
                
                if rank_data:
                    print(f"🏆 PERFORMANCE RANKING:")
                    print(f"  Rank: #{rank_data.rank:,} out of all traders")
                    print(f"  P&L: {rank_data.net_pnl:+.4f} AVAX")
                    print(f"  Trades: {rank_data.trades:,}")
                
            else:
                print(f"\n⚠️ No trading activity found for this wallet address")
                print("🔍 Double-checking if wallet exists in bonding_events...")
                
                # Check exact matches
                check_query = """
                SELECT user_address, COUNT(*) as trades
                FROM bonding_events 
                WHERE user_address ILIKE :wallet_pattern
                GROUP BY user_address
                """
                
                check_result = conn.execute(text(check_query), {'wallet_pattern': f'%{wallet_address[-10:]}%'})
                similar = check_result.fetchall()
                
                if similar:
                    print(f"Found similar addresses:")
                    for addr in similar[:5]:
                        print(f"  {addr.user_address} ({addr.trades} trades)")
                
    except Exception as e:
        print(f"❌ Error looking up wallet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Look up the specific wallet
    excel_baller_address = "0x5dd019ce1d1b39b8f7e89c71dcce9634ba9c810f"
    lookup_wallet(excel_baller_address) 
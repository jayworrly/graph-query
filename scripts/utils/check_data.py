#!/usr/bin/env python3
"""
Quick database data check
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from setup_graph_database import get_graph_db_connection
from sqlalchemy import text

def check_data():
    print("🔍 CHECKING DATABASE DATA")
    print("=" * 40)
    
    engine = get_graph_db_connection()
    if not engine:
        print("❌ Could not connect to database")
        return
    
    try:
        with engine.connect() as conn:
            # Check bonding_events
            result = conn.execute(text("SELECT COUNT(*) FROM bonding_events"))
            bonding_count = result.scalar()
            print(f"📊 Bonding events: {bonding_count:,}")
            
            if bonding_count > 0:
                # Show sample bonding event
                result = conn.execute(text("""
                    SELECT user_address, trade_type, avax_amount, token_amount, timestamp 
                    FROM bonding_events 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """))
                sample = result.fetchone()
                if sample:
                    print(f"   Latest: {sample.trade_type} by {sample.user_address[:10]}...")
                    print(f"   Amount: {sample.avax_amount} AVAX for {sample.token_amount} tokens")
            
            # Check user_activity
            result = conn.execute(text("SELECT COUNT(*) FROM user_activity"))
            user_count = result.scalar()
            print(f"👥 User activity records: {user_count:,}")
            
            # Check token_deployments
            result = conn.execute(text("SELECT COUNT(*) FROM token_deployments"))
            token_count = result.scalar()
            print(f"🪙 Token deployments: {token_count:,}")
            
            if bonding_count > 0:
                # Check unique users in bonding events
                result = conn.execute(text("SELECT COUNT(DISTINCT user_address) FROM bonding_events"))
                unique_users = result.scalar()
                print(f"🔄 Unique traders: {unique_users:,}")
                
                # Check buy vs sell distribution
                result = conn.execute(text("""
                    SELECT trade_type, COUNT(*) as count 
                    FROM bonding_events 
                    GROUP BY trade_type
                """))
                trades = result.fetchall()
                for trade in trades:
                    print(f"   {trade.trade_type}: {trade.count:,} trades")
            
            print("\n" + "=" * 40)
            if bonding_count == 0:
                print("⚠️  No bonding events found!")
                print("💡 You may need to sync data from your subgraph")
            elif user_count == 0:
                print("⚠️  No user activity records found!")
                print("💡 You can still analyze using the manual calculator")
            else:
                print("✅ Data available for analysis!")
                
    except Exception as e:
        print(f"❌ Error checking data: {e}")

if __name__ == "__main__":
    check_data() 
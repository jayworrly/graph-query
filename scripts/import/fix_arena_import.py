#!/usr/bin/env python3
"""
Fixed Arena Users Import

This script properly imports arena users with better error handling
and debugging to ensure the data is actually saved.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from setup_graph_database import get_graph_db_connection

load_dotenv()

# Database connection parameters
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD") 
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def get_avalanche_tokens_connection():
    """Get connection to the avalanche_tokens database"""
    try:
        engine = create_engine(
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/avalanche_tokens"
        )
        return engine
    except Exception as e:
        print(f"❌ Error connecting to avalanche_tokens database: {e}")
        return None

def import_arena_users_fixed():
    """Import arena users with proper error handling and commits"""
    print("🏷️ FIXED ARENA USERS IMPORT")
    print("=" * 50)
    
    source_engine = get_avalanche_tokens_connection()
    target_engine = get_graph_db_connection()
    
    if not source_engine or not target_engine:
        print("❌ Database connection failed")
        return
    
    try:
        # Get arena users data
        query = """
        SELECT 
            user_address,
            twitter_handle,
            twitter_username,
            twitter_pfp_url,
            last_price,
            traders_holding,
            portfolio_total_pnl,
            created_at
        FROM arena_users
        WHERE user_address IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 1000  -- Start with first 1000 for testing
        """
        
        print("📊 Loading arena users data...")
        df = pd.read_sql(query, source_engine)
        
        if df.empty:
            print("⚠️ No arena users data found")
            return
        
        print(f"✅ Loaded {len(df)} arena users")
        print(f"Sample addresses from arena_users:")
        for i, row in df.head(3).iterrows():
            print(f"  {row['user_address']} -> {row['twitter_username'] or row['twitter_handle']}")
        
        # Clear any existing test data
        with target_engine.connect() as target_conn:
            # Delete any test records
            target_conn.execute(text("DELETE FROM wallet_labels WHERE user_type = 'test'"))
            target_conn.commit()
            print("🧹 Cleared test data")
        
        # Import data in small batches with explicit commits
        batch_size = 100
        total_imported = 0
        
        with target_engine.connect() as target_conn:
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                print(f"📦 Processing batch {i//batch_size + 1}: {len(batch)} records")
                
                for _, row in batch.iterrows():
                    try:
                        # Create label
                        label = (
                            row['twitter_username'] or 
                            row['twitter_handle'] or 
                            f"Arena_User_{row['user_address'][-6:]}"
                        )
                        
                        # Determine user type and risk level
                        user_type = 'arena_user'
                        risk_level = 'UNKNOWN'
                        
                        if row['portfolio_total_pnl'] and pd.notna(row['portfolio_total_pnl']):
                            pnl = float(row['portfolio_total_pnl'])
                            if pnl > 1000:
                                risk_level = 'LOW'
                                user_type = 'profitable_trader'
                            elif pnl > 0:
                                risk_level = 'MEDIUM'
                                user_type = 'profitable_trader'
                            else:
                                risk_level = 'HIGH'
                        
                        if row['traders_holding'] and pd.notna(row['traders_holding']) and row['traders_holding'] > 100:
                            user_type = 'popular_trader'
                        
                        # Insert record
                        insert_query = text("""
                            INSERT INTO wallet_labels 
                            (wallet_address, label, user_type, company_name, email, 
                             registration_date, is_verified, risk_level, notes, tags)
                            VALUES 
                            (:wallet_address, :label, :user_type, NULL, NULL,
                             :registration_date, false, :risk_level, :notes, :tags)
                            ON CONFLICT (wallet_address) DO UPDATE SET
                                label = EXCLUDED.label,
                                user_type = EXCLUDED.user_type,
                                risk_level = EXCLUDED.risk_level,
                                notes = EXCLUDED.notes,
                                tags = EXCLUDED.tags,
                                updated_at = CURRENT_TIMESTAMP
                        """)
                        
                        # Create tags
                        tags = []
                        if row['twitter_handle']:
                            tags.append('twitter_user')
                        if row['traders_holding'] and pd.notna(row['traders_holding']) and row['traders_holding'] > 50:
                            tags.append('popular')
                        if row['portfolio_total_pnl'] and pd.notna(row['portfolio_total_pnl']) and row['portfolio_total_pnl'] > 0:
                            tags.append('profitable')
                        
                        target_conn.execute(insert_query, {
                            'wallet_address': row['user_address'].lower(),  # Normalize to lowercase
                            'label': label[:255],  # Ensure it fits
                            'user_type': user_type,
                            'registration_date': row['created_at'],
                            'risk_level': risk_level,
                            'notes': f"Arena user with {row['traders_holding'] or 0} traders holding, P&L: {row['portfolio_total_pnl'] or 0}",
                            'tags': tags if tags else None
                        })
                        
                        total_imported += 1
                        
                    except Exception as e:
                        print(f"⚠️ Error importing {row['user_address']}: {e}")
                        continue
                
                # Commit batch
                target_conn.commit()
                print(f"✅ Committed batch {i//batch_size + 1}")
        
        print(f"\n🎉 Successfully imported {total_imported} wallet labels!")
        
        # Verify import
        with target_engine.connect() as target_conn:
            result = target_conn.execute(text("SELECT COUNT(*) FROM wallet_labels"))
            final_count = result.scalar()
            print(f"📊 Final wallet_labels count: {final_count}")
            
            # Show sample
            result = target_conn.execute(text("""
                SELECT wallet_address, label, user_type, risk_level 
                FROM wallet_labels 
                LIMIT 5
            """))
            samples = result.fetchall()
            
            print("\nSample imported records:")
            for sample in samples:
                print(f"  {sample.wallet_address[:10]}...{sample.wallet_address[-6:]} -> {sample.label} ({sample.user_type}, {sample.risk_level})")
        
        return total_imported
        
    except Exception as e:
        print(f"❌ Error in import: {e}")
        import traceback
        traceback.print_exc()
        return 0

def test_address_matching():
    """Test how many imported addresses match bonding events"""
    print("\n🔍 TESTING ADDRESS MATCHING")
    print("=" * 40)
    
    engine = get_graph_db_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # Check matches
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT be.user_address) as matches
                FROM bonding_events be
                INNER JOIN wallet_labels wl ON LOWER(be.user_address) = wl.wallet_address
            """))
            matches = result.scalar()
            
            # Total wallets in each
            be_count = conn.execute(text("SELECT COUNT(DISTINCT user_address) FROM bonding_events")).scalar()
            wl_count = conn.execute(text("SELECT COUNT(*) FROM wallet_labels")).scalar()
            
            print(f"📊 Bonding events wallets: {be_count:,}")
            print(f"🏷️ Labeled wallets: {wl_count:,}")
            print(f"🤝 Matching wallets: {matches:,}")
            
            if matches > 0:
                print(f"📈 Match rate: {(matches/be_count*100):.1f}%")
                
                # Show some matching examples
                result = conn.execute(text("""
                    SELECT be.user_address, wl.label, wl.user_type
                    FROM bonding_events be
                    INNER JOIN wallet_labels wl ON LOWER(be.user_address) = wl.wallet_address
                    LIMIT 5
                """))
                examples = result.fetchall()
                
                print("\n🎯 Matching examples:")
                for ex in examples:
                    print(f"  {ex.user_address[:10]}...{ex.user_address[-6:]} -> {ex.label} ({ex.user_type})")
            else:
                print("⚠️ No matches found - addresses are in different formats")
                
                # Show format comparison
                print("\nFormat comparison:")
                be_sample = conn.execute(text("SELECT user_address FROM bonding_events LIMIT 2")).fetchall()
                wl_sample = conn.execute(text("SELECT wallet_address FROM wallet_labels LIMIT 2")).fetchall()
                
                print("Bonding events format:")
                for addr in be_sample:
                    print(f"  {addr[0]}")
                
                print("Wallet labels format:")
                for addr in wl_sample:
                    print(f"  {addr[0]}")
            
    except Exception as e:
        print(f"❌ Error testing matches: {e}")

if __name__ == "__main__":
    print("🔧 FIXING ARENA USERS IMPORT")
    print("=" * 60)
    
    # Import arena users
    imported = import_arena_users_fixed()
    
    if imported > 0:
        # Test matching
        test_address_matching()
        
        print(f"\n✅ IMPORT COMPLETE!")
        print(f"🎯 Imported {imported} Arena user labels")
        print("🔥 Ready for enhanced profit/loss analysis!")
    else:
        print("❌ Import failed - check error messages above") 
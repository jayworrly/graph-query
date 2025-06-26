#!/usr/bin/env python3
"""
Import Wallet Labels from Avalanche Tokens Database

This script imports wallet data from your existing avalanche_tokens database
and adds meaningful labels to the graph_query database for enhanced analysis.
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

# Database connection parameters (reusing from .env)
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

def discover_table_structure():
    """Discover the table structure in avalanche_tokens database"""
    print("🔍 DISCOVERING AVALANCHE_TOKENS DATABASE STRUCTURE")
    print("=" * 60)
    
    engine = get_avalanche_tokens_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # Get all tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            print(f"📋 Found {len(tables)} tables:")
            for table in tables:
                print(f"  • {table}")
            
            # For each table, show structure and sample data
            for table in tables:
                print(f"\n🔍 Table: {table}")
                print("-" * 30)
                
                # Show column structure
                result = conn.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                print("Columns:")
                for col in columns:
                    nullable = "NULL" if col.is_nullable == "YES" else "NOT NULL"
                    print(f"  {col.column_name}: {col.data_type} ({nullable})")
                
                # Show sample data
                try:
                    result = conn.execute(text(f"SELECT * FROM {table} LIMIT 3"))
                    samples = result.fetchall()
                    if samples:
                        print("\nSample data:")
                        for i, row in enumerate(samples, 1):
                            print(f"  Row {i}: {list(row)}")
                    else:
                        print("  No data found")
                except Exception as e:
                    print(f"  Error reading sample data: {e}")
                
                print()
                
    except Exception as e:
        print(f"❌ Error discovering structure: {e}")

def import_wallet_labels(table_name=None, preview_only=False):
    """
    Import wallet labels from avalanche_tokens database
    Based on your sample data format
    """
    print("📥 IMPORTING WALLET LABELS FROM AVALANCHE_TOKENS")
    print("=" * 60)
    
    source_engine = get_avalanche_tokens_connection()
    target_engine = get_graph_db_connection()
    
    if not source_engine or not target_engine:
        print("❌ Database connection failed")
        return
    
    # If no table name provided, try to discover it
    if not table_name:
        print("🔍 No table name provided. Discovering tables...")
        discover_table_structure()
        print("\n💡 Please specify the table name that contains wallet data")
        return
    
    try:
        with source_engine.connect() as source_conn:
            
            # Based on your sample data, let's try different column name possibilities
            possible_queries = [
                # Query 1: Assuming columns based on your sample data order
                f"""
                SELECT 
                    col1 as wallet_address,
                    col2 as username,
                    col3 as display_name,
                    col4 as profile_image_url,
                    col5 as price_value,
                    col6 as follower_count,
                    col7 as total_value,
                    col8 as last_activity,
                    col9 as created_at,
                    col10 as updated_at
                FROM {table_name}
                LIMIT 10
                """,
                
                # Query 2: Try common column names
                f"""
                SELECT 
                    address as wallet_address,
                    username,
                    display_name,
                    profile_image_url,
                    created_at,
                    updated_at
                FROM {table_name}
                LIMIT 10
                """,
                
                # Query 3: Generic approach - get all columns
                f"SELECT * FROM {table_name} LIMIT 5"
            ]
            
            # Try each query until one works
            df = None
            for i, query in enumerate(possible_queries, 1):
                try:
                    print(f"🔍 Trying query approach {i}...")
                    df = pd.read_sql(query, source_conn)
                    if not df.empty:
                        print(f"✅ Successfully read data with approach {i}")
                        break
                except Exception as e:
                    print(f"⚠️ Query approach {i} failed: {e}")
                    continue
            
            if df is None or df.empty:
                print("❌ Could not read data from any query approach")
                print("💡 Please share the exact column names from your table")
                return
            
            print(f"\n📊 Found {len(df)} records")
            print("\nSample data structure:")
            print(df.head())
            print(f"\nColumns: {list(df.columns)}")
            
            if preview_only:
                print("\n👁️ Preview mode - not importing data yet")
                return df
            
            # Transform data for import
            print("\n🔄 Transforming data for import...")
            
            # Try to map columns intelligently based on data types and patterns
            wallet_labels_data = []
            
            for _, row in df.iterrows():
                # Find wallet address (should be 42 chars starting with 0x)
                wallet_address = None
                label = None
                
                for col in df.columns:
                    value = str(row[col])
                    if value.startswith('0x') and len(value) == 42:
                        wallet_address = value
                        break
                
                # If we found wallet address, find a suitable label
                if wallet_address:
                    # Look for text fields that could be usernames/labels
                    for col in df.columns:
                        value = str(row[col])
                        if (value and 
                            not value.startswith('0x') and 
                            not value.startswith('http') and
                            len(value) > 2 and len(value) < 100 and
                            not value.replace('.', '').replace('-', '').replace(':', '').replace(' ', '').isdigit()):
                            label = value
                            break
                    
                    if label:
                        wallet_labels_data.append({
                            'wallet_address': wallet_address,
                            'label': label,
                            'user_type': 'imported',
                            'risk_level': 'UNKNOWN',
                            'is_verified': False
                        })
            
            if not wallet_labels_data:
                print("❌ Could not identify wallet addresses and labels in the data")
                print("💡 Please check the data format and column structure")
                return
            
            print(f"✅ Prepared {len(wallet_labels_data)} wallet labels for import")
            
            # Import to graph_query database
            import_df = pd.DataFrame(wallet_labels_data)
            
            with target_engine.connect() as target_conn:
                # Check for existing wallets
                existing_query = "SELECT wallet_address FROM wallet_labels"
                try:
                    existing_df = pd.read_sql(existing_query, target_conn)
                    existing_addresses = set(existing_df['wallet_address'].tolist())
                    
                    # Filter out existing addresses
                    new_wallets = import_df[~import_df['wallet_address'].isin(existing_addresses)]
                    
                    if len(new_wallets) == 0:
                        print("⚠️ All wallet addresses already exist in the database")
                        return
                    
                    print(f"📊 Importing {len(new_wallets)} new wallet labels...")
                    
                    # Import new wallets
                    new_wallets.to_sql('wallet_labels', target_conn, 
                                     if_exists='append', index=False, method='multi')
                    
                    print(f"✅ Successfully imported {len(new_wallets)} wallet labels!")
                    
                except Exception as e:
                    print(f"⚠️ Error checking existing wallets: {e}")
                    print("Attempting full import...")
                    
                    import_df.to_sql('wallet_labels', target_conn, 
                                   if_exists='append', index=False, method='multi')
                    print(f"✅ Imported {len(import_df)} wallet labels!")
            
            return import_df
            
    except Exception as e:
        print(f"❌ Error importing wallet labels: {e}")
        return None

def test_enhanced_analysis():
    """Test the enhanced analysis with wallet labels"""
    print("\n🌟 TESTING ENHANCED ANALYSIS WITH WALLET LABELS")
    print("=" * 60)
    
    engine = get_graph_db_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # Test query with labels
            query = """
            WITH recent_trades AS (
                SELECT 
                    be.user_address,
                    COUNT(*) as trade_count,
                    SUM(be.avax_amount) as total_volume,
                    SUM(CASE WHEN be.trade_type = 'BUY' THEN be.avax_amount ELSE -be.avax_amount END) as net_flow
                FROM bonding_events be
                WHERE be.timestamp > EXTRACT(EPOCH FROM NOW() - INTERVAL '7 days')
                GROUP BY be.user_address
                ORDER BY total_volume DESC
                LIMIT 10
            )
            SELECT 
                rt.user_address,
                COALESCE(wl.label, 'Anonymous') as wallet_label,
                COALESCE(wl.user_type, 'Unknown') as user_type,
                rt.trade_count,
                ROUND(rt.total_volume::numeric, 4) as volume_7d,
                ROUND(rt.net_flow::numeric, 4) as net_flow_7d,
                wl.is_verified
            FROM recent_trades rt
            LEFT JOIN wallet_labels wl ON rt.user_address = wl.wallet_address
            """
            
            df = pd.read_sql(query, conn)
            
            if df.empty:
                print("⚠️ No recent trading data found")
                return
            
            print("🏆 TOP RECENT TRADERS (Last 7 days) WITH LABELS:")
            print("-" * 60)
            
            for i, (_, row) in enumerate(df.iterrows(), 1):
                verified = "✅" if row.get('is_verified') else "❓"
                print(f"{i:2d}. {row['wallet_label']} ({row['user_type']}) {verified}")
                print(f"    Address: {row['user_address'][:10]}...{row['user_address'][-6:]}")
                print(f"    Volume: {row['volume_7d']} AVAX | Trades: {row['trade_count']}")
                print(f"    Net Flow: {row['net_flow_7d']} AVAX")
                print()
            
    except Exception as e:
        print(f"❌ Error testing enhanced analysis: {e}")

def interactive_import():
    """Interactive import process"""
    print("🏷️ AVALANCHE TOKENS WALLET IMPORT")
    print("=" * 60)
    
    # First, discover structure
    print("Step 1: Discovering database structure...")
    discover_table_structure()
    
    # Ask user for table name
    print("\n" + "=" * 60)
    table_name = input("📝 Enter the table name containing wallet data: ").strip()
    
    if not table_name:
        print("❌ No table name provided")
        return
    
    # Preview data
    print(f"\nStep 2: Previewing data from '{table_name}'...")
    preview_df = import_wallet_labels(table_name, preview_only=True)
    
    if preview_df is not None:
        # Confirm import
        print("\n" + "=" * 60)
        response = input("🚀 Proceed with import? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            print("\nStep 3: Importing wallet labels...")
            result_df = import_wallet_labels(table_name, preview_only=False)
            
            if result_df is not None:
                print("\nStep 4: Testing enhanced analysis...")
                test_enhanced_analysis()
                
                print("\n✅ IMPORT COMPLETE!")
                print("🎯 Your profit/loss analysis now includes meaningful wallet labels!")
        else:
            print("❌ Import cancelled by user")

if __name__ == "__main__":
    interactive_import() 
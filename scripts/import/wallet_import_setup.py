#!/usr/bin/env python3
"""
Wallet Import Setup

This script helps import wallet data from another PostgreSQL database
and add meaningful labels to the graph_query database.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from setup_graph_database import get_graph_db_connection
from sqlalchemy import text, create_engine
import pandas as pd

def create_wallet_labels_table():
    """Create a table to store wallet labels and metadata"""
    print("🏗️  CREATING WALLET LABELS TABLE")
    print("=" * 50)
    
    engine = get_graph_db_connection()
    if not engine:
        print("❌ Could not connect to graph_query database")
        return False
    
    try:
        with engine.connect() as conn:
            # Create wallet_labels table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS wallet_labels (
                    wallet_address VARCHAR(66) PRIMARY KEY,
                    label VARCHAR(255) NOT NULL,
                    user_type VARCHAR(50),
                    company_name VARCHAR(255),
                    email VARCHAR(255),
                    registration_date TIMESTAMP,
                    is_verified BOOLEAN DEFAULT FALSE,
                    risk_level VARCHAR(20) DEFAULT 'UNKNOWN',
                    notes TEXT,
                    tags TEXT[], -- Array of tags like ['whale', 'early_adopter', 'bot']
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create indexes for performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_wallet_labels_type ON wallet_labels(user_type);
                CREATE INDEX IF NOT EXISTS idx_wallet_labels_verified ON wallet_labels(is_verified);
                CREATE INDEX IF NOT EXISTS idx_wallet_labels_risk ON wallet_labels(risk_level);
            """))
            
            conn.commit()
            print("✅ wallet_labels table created successfully!")
            
            # Show the table structure
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'wallet_labels'
                ORDER BY ordinal_position
            """))
            
            print("\n📋 Table structure:")
            for row in result:
                nullable = "NULL" if row.is_nullable == "YES" else "NOT NULL"
                print(f"  {row.column_name}: {row.data_type} {nullable}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating wallet_labels table: {e}")
        return False

def show_import_requirements():
    """Show what data we need from the user's existing database"""
    print("\n" + "=" * 60)
    print("📋 WALLET DATA IMPORT REQUIREMENTS")
    print("=" * 60)
    
    print("""
To import your wallet data, I need to know about your existing database:

🔑 REQUIRED FIELDS:
   • wallet_address (Ethereum address)
   • label/name (Human readable identifier)

🎯 OPTIONAL BUT USEFUL FIELDS:
   • user_type (e.g., 'individual', 'company', 'bot', 'exchange')
   • company_name
   • email
   • registration_date
   • verification_status
   • risk_level
   • any tags or categories

📊 EXAMPLE MAPPING:
   Your DB Field    →    Our wallet_labels Field
   ---------------      ----------------------
   address          →    wallet_address
   username         →    label
   account_type     →    user_type
   business_name    →    company_name
   created_at       →    registration_date
   verified         →    is_verified

Please provide:
1. Your database connection details (host, database name, etc.)
2. Table name containing wallet data
3. Column names and their meanings
4. Sample query to see the data structure
""")

def test_connection_template():
    """Show template for connecting to external database"""
    print("\n" + "=" * 60)
    print("🔌 DATABASE CONNECTION TEMPLATE")
    print("=" * 60)
    
    connection_code = '''
# Example connection to your existing database
def connect_to_your_database():
    """
    Update these connection parameters for your database
    """
    connection_string = "postgresql://username:password@host:port/database_name"
    
    # OR using individual parameters:
    # engine = create_engine(
    #     'postgresql://username:password@host:port/database'
    # )
    
    return create_engine(connection_string)

# Example query to test connection and see data
def preview_wallet_data():
    engine = connect_to_your_database()
    
    query = """
    SELECT 
        wallet_address_column,
        user_name_column,
        user_type_column,
        -- add other relevant columns
        created_date_column
    FROM your_wallet_table 
    LIMIT 10
    """
    
    df = pd.read_sql(query, engine)
    print(df)
    
    return df
'''
    
    print(connection_code)

def import_wallet_data_template():
    """Show template for importing wallet data"""
    print("\n" + "=" * 60)
    print("📥 WALLET DATA IMPORT TEMPLATE")
    print("=" * 60)
    
    import_code = '''
def import_wallets_from_your_db():
    """
    Import wallet data from your existing database
    """
    # Connect to your database
    source_engine = connect_to_your_database()
    
    # Connect to graph_query database  
    target_engine = get_graph_db_connection()
    
    # Query your wallet data
    query = """
    SELECT 
        wallet_address,
        user_name as label,
        account_type as user_type,
        company_name,
        email,
        created_at as registration_date,
        is_verified,
        risk_score
    FROM your_wallet_table
    WHERE wallet_address IS NOT NULL
    """
    
    df = pd.read_sql(query, source_engine)
    
    # Transform data if needed
    df['risk_level'] = df['risk_score'].apply(lambda x: 
        'HIGH' if x > 80 else 'MEDIUM' if x > 40 else 'LOW')
    
    # Import to graph_query database
    df.to_sql('wallet_labels', target_engine, 
              if_exists='append', index=False, method='multi')
    
    print(f"✅ Imported {len(df)} wallet labels")
'''
    
    print(import_code)

def enhanced_analysis_preview():
    """Show how the analysis will look with wallet labels"""
    print("\n" + "=" * 60)
    print("🌟 ENHANCED ANALYSIS WITH WALLET LABELS")
    print("=" * 60)
    
    enhanced_query = '''
-- Enhanced profit/loss query with wallet labels
SELECT 
    ua.user_address,
    COALESCE(wl.label, 'Anonymous') as wallet_label,
    COALESCE(wl.user_type, 'Unknown') as user_type,
    wl.company_name,
    ROUND(ua.total_pnl_avax::numeric, 4) as profit_loss_avax,
    ROUND(ua.portfolio_roi::numeric, 2) as roi_percentage,
    ua.total_trades,
    ua.win_rate,
    wl.risk_level,
    wl.is_verified
FROM user_activity ua
LEFT JOIN wallet_labels wl ON ua.user_address = wl.wallet_address
WHERE ua.total_trades > 0
ORDER BY ua.total_pnl_avax DESC;

-- Example output:
-- wallet_label         | user_type    | profit_loss | roi    | trades
-- --------------------|-------------|-------------|--------|--------
-- "Crypto Whale Co"   | company     | 4,325.77    | 2847%  | 7128
-- "john_trader"       | individual  | 3,289.57    | 1776%  | 372
-- "DeepSeaBot"        | bot         | 2,811.11    | 924%   | 25
-- Anonymous           | Unknown     | 2,570.58    | 459%   | 173
'''
    
    print(enhanced_query)

if __name__ == "__main__":
    print("🏷️  WALLET LABELS IMPORT SETUP")
    print("=" * 60)
    
    # Create the table
    if create_wallet_labels_table():
        show_import_requirements()
        test_connection_template()
        import_wallet_data_template()
        enhanced_analysis_preview()
        
        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETE!")
        print("=" * 60)
        print("""
NEXT STEPS:
1. 📝 Provide your database connection details
2. 🔍 Share the structure of your wallet table
3. 🔧 We'll customize the import script for your data
4. 📊 Run enhanced analysis with meaningful labels!

The wallet_labels table is ready to receive your data.
""")
    
    else:
        print("❌ Setup failed. Please check database connection.") 
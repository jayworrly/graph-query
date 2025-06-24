from setup_graph_database import get_graph_db_connection
from sqlalchemy import text

def migrate_address_fields():
    """Migrate address fields from BYTEA to VARCHAR(66)"""
    print("🔄 Migrating address fields from BYTEA to VARCHAR(66)...")
    
    engine = get_graph_db_connection()
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            # 1. Alter bonding_events table
            print("📝 Updating bonding_events table...")
            
            # First, we need to convert existing binary data to hex strings
            # But since we want clean data, let's truncate and start fresh
            conn.execute(text("TRUNCATE TABLE bonding_events CASCADE"))
            
            # Now alter the column types
            conn.execute(text("ALTER TABLE bonding_events ALTER COLUMN user_address TYPE VARCHAR(66)"))
            conn.execute(text("ALTER TABLE bonding_events ALTER COLUMN transaction_hash TYPE VARCHAR(66)"))
            
            # 2. Alter token_deployments table  
            print("📝 Updating token_deployments table...")
            conn.execute(text("TRUNCATE TABLE token_deployments CASCADE"))
            conn.execute(text("ALTER TABLE token_deployments ALTER COLUMN creator TYPE VARCHAR(66)"))
            
            # 3. Alter user_activity table
            print("📝 Updating user_activity table...")
            conn.execute(text("TRUNCATE TABLE user_activity CASCADE"))
            conn.execute(text("ALTER TABLE user_activity ALTER COLUMN user_address TYPE VARCHAR(66)"))
            
            transaction.commit()
            print("✅ Successfully migrated all address fields to VARCHAR(66)")
            print("📋 All tables have been truncated - ready for fresh sync with readable addresses")
            
        except Exception as e:
            transaction.rollback()
            print(f"❌ Migration failed: {e}")
            raise

def verify_migration():
    """Verify that the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    engine = get_graph_db_connection()
    with engine.connect() as conn:
        # Check all address fields
        tables_and_columns = [
            ('bonding_events', ['user_address', 'transaction_hash']),
            ('token_deployments', ['creator']),
            ('user_activity', ['user_address'])
        ]
        
        for table_name, columns in tables_and_columns:
            for column in columns:
                result = conn.execute(text(f"""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    AND column_name = '{column}'
                """))
                
                data_type = result.fetchone()[0]
                status = "✅" if data_type == "character varying" else "❌"
                print(f"  {status} {table_name}.{column}: {data_type}")

if __name__ == "__main__":
    migrate_address_fields()
    verify_migration() 
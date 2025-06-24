from setup_graph_database import get_graph_db_connection
from sqlalchemy import text

def check_schema():
    engine = get_graph_db_connection()
    with engine.connect() as conn:
        # Check bonding_events table schema
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'bonding_events' 
            AND column_name IN ('user_address', 'transaction_hash')
            ORDER BY column_name
        """))
        
        print("🔍 Current bonding_events table schema:")
        for row in result:
            print(f"  {row.column_name}: {row.data_type}")
        
        # Check token_deployments table schema  
        result2 = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'token_deployments' 
            AND column_name = 'creator'
        """))
        
        print("\n🔍 Current token_deployments table schema:")
        for row in result2:
            print(f"  {row.column_name}: {row.data_type}")

if __name__ == "__main__":
    check_schema() 
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

# Database connection parameters
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
MAIN_DB_NAME = os.getenv("DB_NAME")  # Your existing database
GRAPH_DB_NAME = "graph_queries"  # New database for graph data

def create_graph_database():
    """Create the graph_queries database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (not to a specific database)
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database='postgres'  # Connect to default postgres database
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = connection.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (GRAPH_DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {GRAPH_DB_NAME}")
            print(f"✅ Created database: {GRAPH_DB_NAME}")
        else:
            print(f"📋 Database {GRAPH_DB_NAME} already exists")
            
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")

def get_graph_db_connection():
    """Get connection to the graph_queries database"""
    try:
        engine = create_engine(
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{GRAPH_DB_NAME}"
        )
        return engine
    except Exception as e:
        print(f"❌ Error connecting to graph database: {e}")
        return None

def drop_graph_tables():
    """Drop all existing graph database tables"""
    print("🗑️ Dropping existing tables...")
    
    engine = get_graph_db_connection()
    
    with engine.connect() as connection:
        # Drop tables in reverse order due to foreign key constraints
        tables_to_drop = [
            'user_trading_sessions',
            'user_portfolio_snapshots', 
            'user_token_positions',
            'user_activity',
            'bonding_events',
            'token_deployments'
        ]
        
        for table in tables_to_drop:
            try:
                connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"✅ Dropped table: {table}")
            except Exception as e:
                print(f"⚠️ Could not drop table {table}: {e}")
        
        connection.commit()

def create_graph_tables():
    """Create all tables for portfolio tracking"""
    engine = get_graph_db_connection()
    if not engine:
        return
    
    with engine.connect() as connection:
        # Token Deployments table (Enhanced)
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS token_deployments (
                id VARCHAR(66) PRIMARY KEY, -- token address
                token_address VARCHAR(66) NOT NULL,
                creator VARCHAR(66) NOT NULL,
                token_id BIGINT NOT NULL,
                deployed_at BIGINT NOT NULL,
                name VARCHAR(255) NOT NULL,
                symbol VARCHAR(100) NOT NULL,
                decimals INTEGER NOT NULL,
                total_supply DECIMAL(50, 18) NOT NULL,
                
                -- Bonding Progress
                bonding_progress DECIMAL(10, 2) NOT NULL,
                migration_status VARCHAR(20) NOT NULL,
                current_price_avax DECIMAL(50, 18) NOT NULL,
                avax_raised DECIMAL(50, 18) NOT NULL,
                migration_threshold DECIMAL(50, 18) NOT NULL,
                pair_address VARCHAR(66),
                
                -- Trading Statistics
                total_avax_volume DECIMAL(50, 18) NOT NULL,
                total_buy_volume DECIMAL(50, 18) NOT NULL,
                total_sell_volume DECIMAL(50, 18) NOT NULL,
                total_trades INTEGER NOT NULL,
                total_buys INTEGER NOT NULL,
                total_sells INTEGER NOT NULL,
                unique_traders INTEGER NOT NULL,
                
                -- Market Data
                market_cap_avax DECIMAL(50, 18) NOT NULL,
                liquidity_avax DECIMAL(50, 18) NOT NULL,
                holders INTEGER NOT NULL,
                
                -- Price History
                price_high_24h DECIMAL(50, 18) NOT NULL,
                price_low_24h DECIMAL(50, 18) NOT NULL,
                volume_24h DECIMAL(50, 18) NOT NULL,
                price_change_24h DECIMAL(50, 18) NOT NULL,
                
                -- Timestamps
                last_trade_timestamp BIGINT NOT NULL,
                last_update_timestamp BIGINT NOT NULL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Bonding Events table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS bonding_events (
                id VARCHAR(255) PRIMARY KEY,
                token_address VARCHAR(66) NOT NULL,
                user_address VARCHAR(66) NOT NULL,
                avax_amount DECIMAL(50, 18) NOT NULL,
                token_amount DECIMAL(50, 18) NOT NULL,
                price_avax DECIMAL(50, 18) NOT NULL,
                bonding_progress DECIMAL(10, 2) NOT NULL,
                cumulative_avax DECIMAL(50, 18) NOT NULL,
                trade_type VARCHAR(4) NOT NULL,
                
                -- Fee Information
                protocol_fee DECIMAL(50, 18) NOT NULL,
                creator_fee DECIMAL(50, 18) NOT NULL,
                referral_fee DECIMAL(50, 18) NOT NULL,
                
                -- Context
                timestamp BIGINT NOT NULL,
                block_number BIGINT NOT NULL,
                transaction_hash VARCHAR(66) NOT NULL,
                gas_price BIGINT NOT NULL,
                gas_used BIGINT NOT NULL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (token_address) REFERENCES token_deployments(id)
            );
        """))
        
        # User Activity table (Enhanced with Portfolio Tracking)
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id VARCHAR(42) PRIMARY KEY, -- wallet address
                user_address VARCHAR(66) NOT NULL,
                total_trades INTEGER NOT NULL,
                total_volume_avax DECIMAL(50, 18) NOT NULL,
                total_tokens_bought DECIMAL(50, 18) NOT NULL,
                total_tokens_sold DECIMAL(50, 18) NOT NULL,
                total_fees_spent DECIMAL(50, 18) NOT NULL,
                unique_tokens_traded INTEGER NOT NULL,
                first_trade_timestamp BIGINT NOT NULL,
                last_trade_timestamp BIGINT NOT NULL,
                
                -- Portfolio Tracking
                current_portfolio_value_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                total_investment_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                realized_pnl_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                unrealized_pnl_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                total_pnl_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                
                -- Performance Metrics
                win_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,
                profitable_trades INTEGER NOT NULL DEFAULT 0,
                losing_trades INTEGER NOT NULL DEFAULT 0,
                average_profit_per_trade DECIMAL(50, 18) NOT NULL DEFAULT 0,
                average_loss_per_trade DECIMAL(50, 18) NOT NULL DEFAULT 0,
                largest_win_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                largest_loss_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                
                -- Risk Metrics
                sharpe_ratio DECIMAL(10, 4) NOT NULL DEFAULT 0,
                max_drawdown_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                portfolio_roi DECIMAL(10, 2) NOT NULL DEFAULT 0,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # User Token Positions table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS user_token_positions (
                id VARCHAR(110) PRIMARY KEY, -- user-token address
                user_address VARCHAR(42) NOT NULL,
                token_address VARCHAR(66) NOT NULL,
                
                -- Current Holdings
                current_balance DECIMAL(50, 18) NOT NULL DEFAULT 0,
                current_value_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                
                -- Trading History
                total_bought DECIMAL(50, 18) NOT NULL DEFAULT 0,
                total_sold DECIMAL(50, 18) NOT NULL DEFAULT 0,
                total_buy_value_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                total_sell_value_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                
                -- Cost Basis & P&L
                average_buy_price DECIMAL(50, 18) NOT NULL DEFAULT 0,
                average_sell_price DECIMAL(50, 18) NOT NULL DEFAULT 0,
                realized_pnl_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                unrealized_pnl_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                total_pnl_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                
                -- Position Metrics
                percent_of_portfolio DECIMAL(5, 2) NOT NULL DEFAULT 0,
                holding_period_days DECIMAL(10, 2) NOT NULL DEFAULT 0,
                
                -- Trading Statistics
                total_trades INTEGER NOT NULL DEFAULT 0,
                total_buys INTEGER NOT NULL DEFAULT 0,
                total_sells INTEGER NOT NULL DEFAULT 0,
                is_open BOOLEAN NOT NULL DEFAULT FALSE,
                
                -- Timestamps
                first_buy_timestamp BIGINT NOT NULL,
                last_buy_timestamp BIGINT,
                last_sell_timestamp BIGINT,
                last_update_timestamp BIGINT NOT NULL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_address) REFERENCES user_activity(id),
                FOREIGN KEY (token_address) REFERENCES token_deployments(id)
            );
        """))
        
        # User Portfolio Snapshots table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS user_portfolio_snapshots (
                id VARCHAR(100) PRIMARY KEY, -- user-timestamp
                user_address VARCHAR(42) NOT NULL,
                
                -- Portfolio Value
                total_value_avax DECIMAL(50, 18) NOT NULL,
                total_investment_avax DECIMAL(50, 18) NOT NULL,
                total_pnl_avax DECIMAL(50, 18) NOT NULL,
                
                -- Performance Metrics
                portfolio_roi DECIMAL(10, 2) NOT NULL,
                win_rate DECIMAL(5, 2) NOT NULL,
                
                -- Context
                timestamp BIGINT NOT NULL,
                block_number BIGINT NOT NULL,
                period VARCHAR(10) NOT NULL, -- HOURLY, DAILY
                
                -- Number of positions
                active_positions INTEGER NOT NULL,
                total_positions INTEGER NOT NULL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_address) REFERENCES user_activity(id)
            );
        """))
        
        # User Trading Sessions table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS user_trading_sessions (
                id VARCHAR(55) PRIMARY KEY, -- user-date
                user_address VARCHAR(42) NOT NULL,
                date VARCHAR(10) NOT NULL, -- YYYY-MM-DD
                
                -- Daily Trading Stats
                trades_count INTEGER NOT NULL DEFAULT 0,
                volume_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                pnl_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                fees_spent DECIMAL(50, 18) NOT NULL DEFAULT 0,
                
                -- Session Performance
                winning_trades INTEGER NOT NULL DEFAULT 0,
                losing_trades INTEGER NOT NULL DEFAULT 0,
                break_even_trades INTEGER NOT NULL DEFAULT 0,
                
                -- Best and Worst Trades
                best_trade_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                worst_trade_avax DECIMAL(50, 18) NOT NULL DEFAULT 0,
                
                -- Timestamps
                first_trade_timestamp BIGINT NOT NULL,
                last_trade_timestamp BIGINT NOT NULL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (user_address) REFERENCES user_activity(id)
            );
        """))
        
        # Price Snapshots table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS price_snapshots (
                id VARCHAR(100) PRIMARY KEY, -- token-timestamp
                token_address VARCHAR(66) NOT NULL,
                price_avax DECIMAL(50, 18) NOT NULL,
                volume_avax DECIMAL(50, 18) NOT NULL,
                trades INTEGER NOT NULL,
                timestamp BIGINT NOT NULL,
                period VARCHAR(10) NOT NULL, -- HOURLY, DAILY
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (token_address) REFERENCES token_deployments(id)
            );
        """))
        
        # Create indexes for better query performance
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bonding_events_user ON bonding_events(user_address);
            CREATE INDEX IF NOT EXISTS idx_bonding_events_token ON bonding_events(token_address);
            CREATE INDEX IF NOT EXISTS idx_bonding_events_timestamp ON bonding_events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_bonding_events_trade_type ON bonding_events(trade_type);
            
            CREATE INDEX IF NOT EXISTS idx_user_token_positions_user ON user_token_positions(user_address);
            CREATE INDEX IF NOT EXISTS idx_user_token_positions_token ON user_token_positions(token_address);
            CREATE INDEX IF NOT EXISTS idx_user_token_positions_open ON user_token_positions(is_open);
            
            CREATE INDEX IF NOT EXISTS idx_user_activity_volume ON user_activity(total_volume_avax DESC);
            CREATE INDEX IF NOT EXISTS idx_user_activity_pnl ON user_activity(total_pnl_avax DESC);
            CREATE INDEX IF NOT EXISTS idx_user_activity_roi ON user_activity(portfolio_roi DESC);
            
            CREATE INDEX IF NOT EXISTS idx_token_deployments_creator ON token_deployments(creator);
            CREATE INDEX IF NOT EXISTS idx_token_deployments_status ON token_deployments(migration_status);
            CREATE INDEX IF NOT EXISTS idx_token_deployments_volume ON token_deployments(total_avax_volume DESC);
            
            CREATE INDEX IF NOT EXISTS idx_price_snapshots_token_time ON price_snapshots(token_address, timestamp);
            CREATE INDEX IF NOT EXISTS idx_trading_sessions_date ON user_trading_sessions(date);
        """))
        
        connection.commit()
        print("✅ All graph database tables created successfully!")

if __name__ == "__main__":
    print("🚀 Setting up graph-queries database...")
    create_graph_database()
    drop_graph_tables()
    create_graph_tables()
    print("✅ Graph database setup complete!")
    print("\n📋 Next steps:")
    print("1. Rebuild the subgraph: cd arena-tracker && npm run codegen && npm run build")
    print("2. Deploy the subgraph with portfolio tracking")
    print("3. Create sync script to populate the database") 
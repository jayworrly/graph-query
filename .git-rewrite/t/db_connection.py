import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd
import sqlalchemy

load_dotenv()

# Database connection parameters from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

def get_db_connection():
    """
    Create and return a database connection using SQLAlchemy
    """
    try:
        engine = sqlalchemy.create_engine(
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        return engine
    except Exception:
        return None

def execute_query(query: str, params: tuple = None) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a pandas DataFrame
    """
    engine = get_db_connection()
    if engine:
        try:
            with engine.connect() as connection:
                # Convert params to tuple if it's a list
                if isinstance(params, list):
                    params = tuple(params)
                df = pd.read_sql(sqlalchemy.text(query), connection, params=params)
            return df
        except Exception:
            return None
    return None

def get_bonded_arena_tokens() -> pd.DataFrame:
    """
    Fetches token address, token name, and token symbol for tokens launched from the 
    Arena Factory that have bonded (lp_deployed = TRUE).
    Assumes 'lp_deployed' is a boolean column and 'token_address', 'token_name', 'token_symbol' exist.
    """
    query = """
    SELECT
        token_address,
        token_name,
        token_symbol
    FROM
        token_deployments
    WHERE
        lp_deployed = TRUE
    """
    return execute_query(query)

def get_arena_market_data() -> pd.DataFrame:
    """
    Fetches all market data from the arena_market_data table.
    """
    query = """
    SELECT
        token_address,
        token_name,
        token_symbol,
        market_cap,
        price_usd,
        volume_24h,
        liquidity_usd,
        last_updated
    FROM
        arena_market_data
    ORDER BY
        market_cap DESC
    """
    return execute_query(query)

if __name__ == "__main__":
    get_bonded_arena_tokens()
    get_arena_market_data() 
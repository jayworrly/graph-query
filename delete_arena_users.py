import psycopg2
import os
from dotenv import load_dotenv

def delete_all_arena_users():
    # Load environment variables
    load_dotenv()
    
    # Connect to the database using environment variables
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    cursor = conn.cursor()
    
    # Delete all records from arena_users
    query = "DELETE FROM arena_users"
    cursor.execute(query)
    conn.commit()
    
    print(f"Successfully deleted {cursor.rowcount} records from arena_users")
    
    conn.close()

if __name__ == "__main__":
    delete_all_arena_users() 
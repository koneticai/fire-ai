"""
Database initialization script for FireMode Compliance Platform.
Reads DATABASE_URL from environment and executes schema.sql to set up the database.
"""

import os
import sys
import psycopg2
from pathlib import Path

def init_database():
    """Initialize the database with the schema."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not found")
        sys.exit(1)
    
    # Get the directory containing this script
    current_dir = Path(__file__).parent
    schema_path = current_dir / "schema.sql"
    
    if not schema_path.exists():
        print(f"ERROR: Schema file not found at {schema_path}")
        sys.exit(1)
    
    conn = None
    try:
        # Read the schema file
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Connect to the database
        print("Connecting to database...")
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        
        # Execute the schema
        print("Executing database schema...")
        with conn.cursor() as cursor:
            cursor.execute(schema_sql)
        
        print("Database initialization completed successfully!")
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_database()
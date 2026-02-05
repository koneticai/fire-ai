#!/usr/bin/env python3
"""
One-shot Supabase seeding script for AS1851-2012 rules.

This script:
1. Creates the as1851_rules table if it doesn't exist
2. Seeds all 60 validated rules
3. Verifies the seeding

Run locally (not in Cowork sandbox):
    export DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[N]-[REGION].pooler.supabase.com:6543/postgres"
    pip install sqlalchemy psycopg2-binary
    python scripts/seed_supabase.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def get_database_url() -> str:
    """Get DATABASE_URL from environment variable."""
    url = os.getenv("DATABASE_URL")
    if not url:
        print("❌ DATABASE_URL environment variable not set")
        print("\nSet it with:")
        print('  export DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-[N]-[REGION].pooler.supabase.com:6543/postgres"')
        print("\nSee CLAUDE.md for connection string format.")
        sys.exit(1)
    return url


# SQL to create table (includes category and test_frequency)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS as1851_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    test_frequency VARCHAR(50),
    rule_schema JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(rule_code, version)
);

CREATE INDEX IF NOT EXISTS idx_as1851_rules_code ON as1851_rules(rule_code);
CREATE INDEX IF NOT EXISTS idx_as1851_rules_category ON as1851_rules(category);
CREATE INDEX IF NOT EXISTS idx_as1851_rules_frequency ON as1851_rules(test_frequency);
CREATE INDEX IF NOT EXISTS idx_as1851_rules_schema ON as1851_rules USING GIN(rule_schema);
"""


def main():
    print("=" * 60)
    print("AS1851-2012 Supabase Seeding Script")
    print("=" * 60)

    # Import here to fail fast if not installed
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("❌ SQLAlchemy not installed. Run: pip install sqlalchemy psycopg2-binary")
        sys.exit(1)

    # Get database URL from environment
    database_url = get_database_url()

    # Load rules JSON
    script_dir = Path(__file__).parent
    json_path = script_dir.parent / "data" / "as1851_rules_all_systems.json"

    if not json_path.exists():
        print(f"❌ Rules file not found: {json_path}")
        sys.exit(1)

    print(f"\n📂 Loading rules from: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        rules = json.load(f)
    print(f"📊 Loaded {len(rules)} rules")

    # Connect to Supabase
    print(f"\n🔌 Connecting to Supabase...")
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Test connection
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL")

            # Create table
            print(f"\n📋 Creating as1851_rules table...")
            conn.execute(text(CREATE_TABLE_SQL))
            conn.commit()
            print(f"✅ Table ready")

            # Seed rules using savepoints for transaction safety
            print(f"\n🌱 Seeding {len(rules)} rules...")
            inserted, skipped, errors = 0, 0, 0

            for rule in rules:
                # Use savepoint for each rule to isolate failures
                try:
                    with conn.begin_nested():
                        # Check if exists
                        result = conn.execute(
                            text("SELECT id FROM as1851_rules WHERE rule_code = :code"),
                            {"code": rule["rule_code"]}
                        )
                        if result.fetchone():
                            skipped += 1
                            continue

                        # Insert with category and test_frequency
                        conn.execute(
                            text("""
                                INSERT INTO as1851_rules
                                (rule_code, version, rule_name, description, category, test_frequency, rule_schema, is_active, created_at, updated_at)
                                VALUES (:code, :version, :name, :desc, :category, :frequency, CAST(:schema AS jsonb), :active, :created, :updated)
                            """),
                            {
                                "code": rule["rule_code"],
                                "version": rule["version"],
                                "name": rule["rule_name"],
                                "desc": rule["description"],
                                "category": rule.get("category", "unknown"),
                                "frequency": rule.get("test_frequency", "unknown"),
                                "schema": json.dumps(rule["rule_schema"]),
                                "active": rule["is_active"],
                                "created": rule["created_at"],
                                "updated": rule["updated_at"]
                            }
                        )
                        inserted += 1
                        print(f"   ✅ {rule['rule_code']}")

                except Exception as e:
                    # Savepoint automatically rolled back, transaction remains valid
                    print(f"   ❌ {rule['rule_code']}: {e}")
                    errors += 1

            conn.commit()

            # Summary
            print(f"\n" + "=" * 60)
            print("SEEDING RESULTS")
            print("=" * 60)
            print(f"✅ Inserted: {inserted}")
            print(f"⏭️  Skipped:  {skipped} (already exist)")
            print(f"❌ Errors:   {errors}")

            # Verify
            print(f"\n🔍 Verifying...")
            result = conn.execute(text("SELECT COUNT(*) FROM as1851_rules WHERE is_active = true"))
            total = result.scalar()
            print(f"📊 Total rules in database: {total}")

            # Category breakdown
            result = conn.execute(text("""
                SELECT category, COUNT(*) as count
                FROM as1851_rules
                GROUP BY category
                ORDER BY category
            """))
            print(f"\n📋 By Category:")
            for row in result:
                print(f"   • {row[0]}: {row[1]} rules")

            # Frequency breakdown
            result = conn.execute(text("""
                SELECT test_frequency, COUNT(*) as count
                FROM as1851_rules
                GROUP BY test_frequency
                ORDER BY test_frequency
            """))
            print(f"\n📅 By Test Frequency:")
            for row in result:
                print(f"   • {row[0]}: {row[1]} rules")

            print(f"\n✅ Seeding complete!")
            print("=" * 60)

    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("\nTroubleshooting:")
        print("1. Check DATABASE_URL environment variable is set correctly")
        print("2. Use transaction pooler (port 6543), not direct connection")
        print("3. Verify the Supabase project is active")
        print("4. See CLAUDE.md for connection string format")
        sys.exit(1)


if __name__ == "__main__":
    main()

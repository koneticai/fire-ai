#!/usr/bin/env python3
"""
One-shot Supabase seeding script for AS1851-2012 rules.

This script:
1. Creates the as1851_rules table if it doesn't exist
2. Seeds all 60 validated rules
3. Verifies the seeding

Run locally (not in Cowork sandbox):
    pip install sqlalchemy psycopg2-binary
    python scripts/seed_supabase.py
"""

import json
from datetime import datetime
from pathlib import Path

# Supabase connection string (URL-encoded password)
DATABASE_URL = "postgresql://postgres.efxehdkquqbynavkfkdy:yh%2AhRngC33h@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# SQL to create table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS as1851_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code VARCHAR(50) NOT NULL,
    version VARCHAR(50) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    description TEXT,
    rule_schema JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(rule_code, version)
);

CREATE INDEX IF NOT EXISTS idx_as1851_rules_code ON as1851_rules(rule_code);
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
        return

    # Load rules JSON
    script_dir = Path(__file__).parent
    json_path = script_dir.parent / "data" / "as1851_rules_all_systems.json"

    if not json_path.exists():
        print(f"❌ Rules file not found: {json_path}")
        return

    print(f"\n📂 Loading rules from: {json_path}")
    with open(json_path) as f:
        rules = json.load(f)
    print(f"📊 Loaded {len(rules)} rules")

    # Connect to Supabase
    print(f"\n🔌 Connecting to Supabase...")
    try:
        engine = create_engine(DATABASE_URL)
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

            # Seed rules
            print(f"\n🌱 Seeding {len(rules)} rules...")
            inserted, skipped, errors = 0, 0, 0

            for rule in rules:
                try:
                    # Check if exists
                    result = conn.execute(
                        text("SELECT id FROM as1851_rules WHERE rule_code = :code"),
                        {"code": rule["rule_code"]}
                    )
                    if result.fetchone():
                        skipped += 1
                        continue

                    # Insert
                    conn.execute(
                        text("""
                            INSERT INTO as1851_rules
                            (rule_code, version, rule_name, description, rule_schema, is_active, created_at, updated_at)
                            VALUES (:code, :version, :name, :desc, :schema::jsonb, :active, :created, :updated)
                        """),
                        {
                            "code": rule["rule_code"],
                            "version": rule["version"],
                            "name": rule["rule_name"],
                            "desc": rule["description"],
                            "schema": json.dumps(rule["rule_schema"]),
                            "active": rule["is_active"],
                            "created": rule["created_at"],
                            "updated": rule["updated_at"]
                        }
                    )
                    inserted += 1
                    print(f"   ✅ {rule['rule_code']}")

                except Exception as e:
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
                SELECT
                    CASE
                        WHEN rule_code LIKE '%SP-%' THEN 'Stair Pressurization'
                        WHEN rule_code LIKE '%FD-%' THEN 'Fire Doors'
                        WHEN rule_code LIKE '%SC-%' THEN 'Smoke Control'
                    END as category,
                    COUNT(*) as count
                FROM as1851_rules
                GROUP BY 1
                ORDER BY 1
            """))
            print(f"\n📋 By Category:")
            for row in result:
                print(f"   • {row[0]}: {row[1]} rules")

            print(f"\n✅ Seeding complete!")
            print("=" * 60)

    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your network connection")
        print("2. Verify the Supabase project is active")
        print("3. Check the database password is correct")


if __name__ == "__main__":
    main()

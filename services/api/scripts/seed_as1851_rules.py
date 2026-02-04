#!/usr/bin/env python3
"""
AS1851-2012 Rule Seeding Script

Populates the as1851_rules table with compliance rule data extracted from
the AS1851-2012 Australian Standard for Routine Service of Fire Protection
Systems and Equipment (Amendment No. 1, November 2016).

This script is idempotent - can be run multiple times without creating duplicates.

Usage:
    export DATABASE_URL="postgresql://user:pass@localhost:5432/fireai"
    python seed_as1851_rules.py

Current Coverage (60 rules total):
    - Stair Pressurization Systems: 20 rules (SP-01 through SP-20)
    - Fire Doors: 20 rules (FD-01 through FD-20)
    - Smoke Control Systems: 20 rules (SC-01 through SC-20)

Data Source:
    - Validated via 17-agent research swarm (2026-02-04)
    - Overall confidence: 0.93 (93%)
    - Source: as1851_rules_all_systems.json

Future Expansion:
    - Alarm Panels: ~10-15 rules (AP-01 through AP-15)
    - +95 additional rules for 95% AS1851 coverage (see COVERAGE-GAP-ANALYSIS.md)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError


def get_sync_database_url() -> str:
    """Get synchronous database URL from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    # Convert async URL to sync URL if needed
    if "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    return database_url


def load_rules_json() -> List[Dict[str, Any]]:
    """Load AS1851 rules from JSON file"""
    # Get the data directory path (relative to this script)
    script_dir = Path(__file__).parent
    json_path = script_dir.parent.parent.parent / 'data' / 'as1851_rules_all_systems.json'

    if not json_path.exists():
        raise FileNotFoundError(
            f"AS1851 rules JSON file not found at: {json_path}\n"
            f"Expected location: {json_path.absolute()}"
        )

    print(f"📂 Loading rules from: {json_path}")

    with open(json_path, 'r') as f:
        rules = json.load(f)

    print(f"📊 Loaded {len(rules)} rules from JSON")
    return rules


def validate_rule_schema(rule: Dict[str, Any]) -> bool:
    """Validate that a rule has all required fields"""
    required_fields = [
        "rule_code", "version", "rule_name", "description",
        "category", "test_frequency", "rule_schema", "is_active"
    ]

    for field in required_fields:
        if field not in rule:
            print(f"⚠️  Warning: Rule missing required field '{field}': {rule.get('rule_code', 'UNKNOWN')}")
            return False

    # Validate rule_schema structure
    # Accept multiple valid formats from research (any non-reserved keys count as data spec)
    schema = rule["rule_schema"]
    reserved_keys = {"_validation", "classification_logic"}
    data_keys = set(schema.keys()) - reserved_keys
    has_data_spec = len(data_keys) > 0

    if not has_data_spec:
        print(f"⚠️  Warning: Rule schema missing data specification: {rule['rule_code']}")
        return False

    # Classification logic is required
    if "classification_logic" not in schema:
        print(f"⚠️  Warning: Rule schema missing 'classification_logic': {rule['rule_code']}")
        return False

    # Check confidence score if present (from validation metadata)
    validation_meta = schema.get("_validation", {})
    if validation_meta:
        confidence = validation_meta.get("confidence", 1.0)
        if confidence < 0.90:
            print(f"   ⚠️  Low confidence ({confidence:.2f}) for {rule['rule_code']}")

    return True


def seed_rules(session, rules: List[Dict[str, Any]]) -> tuple[int, int, int]:
    """
    Insert rules into as1851_rules table

    Returns:
        tuple: (inserted_count, skipped_count, error_count)
    """
    inserted = 0
    skipped = 0
    errors = 0

    for rule in rules:
        # Validate rule schema
        if not validate_rule_schema(rule):
            errors += 1
            continue

        try:
            # Check if rule already exists
            result = session.execute(text("""
                SELECT id, version FROM as1851_rules
                WHERE rule_code = :code
            """), {"code": rule["rule_code"]})

            existing = result.fetchone()

            if existing:
                print(f"⏭️  Rule {rule['rule_code']} already exists (version: {existing[1]})")
                skipped += 1
                continue

            # Insert new rule
            session.execute(text("""
                INSERT INTO as1851_rules (
                    rule_code, version, rule_name, description,
                    rule_schema, is_active, created_at, updated_at
                ) VALUES (
                    :code, :version, :name, :desc,
                    CAST(:schema AS jsonb), :active, :created, :updated
                )
            """), {
                "code": rule["rule_code"],
                "version": rule["version"],
                "name": rule["rule_name"],
                "desc": rule["description"],
                "schema": json.dumps(rule["rule_schema"]),
                "active": rule["is_active"],
                "created": rule.get("created_at", datetime.utcnow().isoformat()),
                "updated": datetime.utcnow().isoformat()
            })

            print(f"✅ Seeded: {rule['rule_code']} - {rule['rule_name']}")
            inserted += 1

        except IntegrityError as e:
            print(f"❌ Integrity error for {rule['rule_code']}: {e}")
            session.rollback()
            errors += 1
            continue
        except Exception as e:
            print(f"❌ Error seeding {rule['rule_code']}: {e}")
            session.rollback()
            errors += 1
            continue

    session.commit()
    return inserted, skipped, errors


def print_summary(inserted: int, skipped: int, errors: int, rules: List[Dict[str, Any]]):
    """Print summary statistics"""
    print("\n" + "="*70)
    print("🎉 AS1851-2012 RULE SEEDING COMPLETED")
    print("="*70)
    print(f"✅ Inserted: {inserted} rules")
    print(f"⏭️  Skipped:  {skipped} rules (already exist)")
    print(f"❌ Errors:   {errors} rules")
    print(f"📊 Total:    {len(rules)} rules processed")

    # Category breakdown
    categories = {}
    for rule in rules:
        cat = rule.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("\n📋 Category Breakdown:")
    for category, count in sorted(categories.items()):
        print(f"   • {category.replace('_', ' ').title()}: {count} rules")

    # Test frequency breakdown
    frequencies = {}
    for rule in rules:
        freq = rule.get("test_frequency", "unknown")
        frequencies[freq] = frequencies.get(freq, 0) + 1

    print("\n📅 Test Frequency Breakdown:")
    for frequency, count in sorted(frequencies.items()):
        print(f"   • {frequency.replace('_', ' ').title()}: {count} rules")

    print("="*70)

    if errors > 0:
        print(f"\n⚠️  {errors} errors occurred during seeding. Please review the logs above.")
        sys.exit(1)
    else:
        print("\n✨ All rules seeded successfully!")
        sys.exit(0)


def main():
    """Main seeding function"""
    print("🌱 Starting AS1851-2012 Rule Seeding...")
    print(f"🕐 Timestamp: {datetime.utcnow().isoformat()}")

    try:
        # Load rules from JSON
        rules = load_rules_json()

        # Create database connection
        database_url = get_sync_database_url()
        print(f"🔌 Connecting to database...")
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Verify as1851_rules table exists
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'as1851_rules'
                )
            """))
            table_exists = result.scalar()

            if not table_exists:
                print("❌ Error: as1851_rules table does not exist")
                print("   Run database migrations first: alembic upgrade head")
                sys.exit(1)

            print("✅ Database connection successful")
            print(f"📊 Found as1851_rules table")

            # Seed rules
            inserted, skipped, errors = seed_rules(session, rules)

            # Print summary
            print_summary(inserted, skipped, errors, rules)

        except Exception as e:
            session.rollback()
            print(f"❌ Error during seeding: {e}")
            raise
        finally:
            session.close()

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

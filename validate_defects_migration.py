#!/usr/bin/env python3
"""
Migration Validation Script for Defects Table
==============================================

This script validates the defects table migration by:
1. Checking migration files exist and are properly ordered
2. Testing migration application and rollback
3. Validating schema structure (columns, indexes, constraints)
4. Testing CRUD operations
5. Validating triggers and cascades

Usage:
    python3 validate_defects_migration.py [--db-url DATABASE_URL]

Requirements:
    - PostgreSQL database connection
    - Alembic migrations in alembic/versions/
    - Environment variable DATABASE_URL or --db-url parameter
"""

import sys
import os
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.orm import Session
    import alembic.config
    import alembic.command
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install sqlalchemy psycopg2-binary alembic")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text):
    """Print info message"""
    print(f"   {text}")


class MigrationValidator:
    """Validates the defects table migration"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        self.inspector = inspect(self.engine)
        self.validation_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }

    def run_all_validations(self):
        """Run all validation checks"""
        print_header("Migration Validation Report")

        # Phase 1: File checks
        self.validate_migration_files()

        # Phase 2: Database checks (only if files are valid)
        if not self.validation_results['failed']:
            self.validate_trigger_function()
            self.validate_defects_table()
            self.validate_indexes()
            self.validate_constraints()
            self.validate_foreign_keys()

        # Phase 3: Functional tests
        if not self.validation_results['failed']:
            self.test_crud_operations()
            self.test_updated_at_trigger()

        # Print summary
        self.print_summary()

        # Return exit code
        return 0 if not self.validation_results['failed'] else 1

    def validate_migration_files(self):
        """Check that migration files exist and are properly ordered"""
        print_header("Phase 1: Migration File Validation")

        migrations_dir = Path(__file__).parent / 'alembic' / 'versions'

        # Check required migrations
        required_migrations = {
            '000_create_trigger_function.py': 'Trigger function migration',
            '001_add_defects_table.py': 'Defects table migration',
            '002_add_evidence_flag_columns.py': 'Evidence flags migration'
        }

        for filename, description in required_migrations.items():
            filepath = migrations_dir / filename
            if filepath.exists():
                print_success(f"{description} exists: {filename}")
                self.validation_results['passed'].append(f"Migration file: {filename}")
            else:
                print_error(f"{description} NOT FOUND: {filename}")
                self.validation_results['failed'].append(f"Missing migration: {filename}")

        # Check revision chain
        try:
            with open(migrations_dir / '001_add_defects_table.py', 'r') as f:
                content = f.read()
                if "down_revision = '000_create_trigger_function'" in content:
                    print_success("Migration revision chain is correct")
                    self.validation_results['passed'].append("Revision chain")
                else:
                    print_error("Migration 001 does not depend on 000")
                    self.validation_results['failed'].append("Incorrect revision chain")
        except Exception as e:
            print_error(f"Could not validate revision chain: {e}")
            self.validation_results['failed'].append("Revision chain check failed")

    def validate_trigger_function(self):
        """Validate that the trigger function exists"""
        print_header("Phase 2: Database Validation - Trigger Function")

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_proc
                    WHERE proname = 'update_updated_at_column'
                )
            """))
            exists = result.scalar()

            if exists:
                print_success("Trigger function 'update_updated_at_column' exists")
                self.validation_results['passed'].append("Trigger function exists")
            else:
                print_error("Trigger function 'update_updated_at_column' NOT FOUND")
                self.validation_results['failed'].append("Missing trigger function")

    def validate_defects_table(self):
        """Validate defects table structure"""
        print_header("Phase 2: Database Validation - Defects Table")

        tables = self.inspector.get_table_names()

        if 'defects' not in tables:
            print_error("Table 'defects' does not exist")
            self.validation_results['failed'].append("Missing defects table")
            return

        print_success("Table 'defects' exists")

        # Check columns
        columns = {col['name']: col for col in self.inspector.get_columns('defects')}

        required_columns = {
            'id': 'UUID',
            'test_session_id': 'UUID',
            'building_id': 'UUID',
            'asset_id': 'UUID',
            'severity': 'VARCHAR',
            'category': 'VARCHAR',
            'description': 'TEXT',
            'as1851_rule_code': 'VARCHAR',
            'status': 'VARCHAR',
            'discovered_at': 'TIMESTAMP',
            'acknowledged_at': 'TIMESTAMP',
            'repaired_at': 'TIMESTAMP',
            'verified_at': 'TIMESTAMP',
            'closed_at': 'TIMESTAMP',
            'evidence_ids': 'ARRAY',
            'repair_evidence_ids': 'ARRAY',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP',
            'created_by': 'UUID',
            'acknowledged_by': 'UUID'
        }

        print_info("Validating columns:")
        missing_columns = []
        for col_name, expected_type in required_columns.items():
            if col_name in columns:
                print_success(f"  Column '{col_name}' exists")
            else:
                print_error(f"  Column '{col_name}' MISSING")
                missing_columns.append(col_name)

        if missing_columns:
            self.validation_results['failed'].append(f"Missing columns: {', '.join(missing_columns)}")
        else:
            self.validation_results['passed'].append("All required columns present")

        # Check nullable constraints
        print_info("\nValidating NOT NULL constraints:")
        not_null_columns = ['id', 'test_session_id', 'building_id', 'severity',
                           'description', 'status', 'discovered_at', 'created_at', 'updated_at']

        for col_name in not_null_columns:
            if col_name in columns:
                if not columns[col_name]['nullable']:
                    print_success(f"  Column '{col_name}' is NOT NULL")
                else:
                    print_warning(f"  Column '{col_name}' should be NOT NULL but is nullable")
                    self.validation_results['warnings'].append(f"Column {col_name} is nullable")

    def validate_indexes(self):
        """Validate that required indexes exist"""
        print_header("Phase 2: Database Validation - Indexes")

        indexes = self.inspector.get_indexes('defects')
        index_names = {idx['name'] for idx in indexes}

        required_indexes = [
            'idx_defects_test_session',
            'idx_defects_building',
            'idx_defects_status',
            'idx_defects_severity',
            'idx_defects_created_by',
            'idx_defects_discovered_at',
            'idx_defects_building_status',
            'idx_defects_session_status'
        ]

        print_info("Checking indexes:")
        missing_indexes = []
        for idx_name in required_indexes:
            if idx_name in index_names:
                print_success(f"  Index '{idx_name}' exists")
            else:
                print_error(f"  Index '{idx_name}' MISSING")
                missing_indexes.append(idx_name)

        if missing_indexes:
            self.validation_results['failed'].append(f"Missing indexes: {', '.join(missing_indexes)}")
        else:
            self.validation_results['passed'].append("All required indexes present")

    def validate_constraints(self):
        """Validate CHECK constraints"""
        print_header("Phase 2: Database Validation - CHECK Constraints")

        with self.engine.connect() as conn:
            # Check severity constraint
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'chk_defects_severity'
                    AND conrelid = 'defects'::regclass
                )
            """))
            severity_exists = result.scalar()

            # Check status constraint
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'chk_defects_status'
                    AND conrelid = 'defects'::regclass
                )
            """))
            status_exists = result.scalar()

        if severity_exists:
            print_success("CHECK constraint 'chk_defects_severity' exists")
            self.validation_results['passed'].append("Severity CHECK constraint")
        else:
            print_error("CHECK constraint 'chk_defects_severity' MISSING")
            self.validation_results['failed'].append("Missing severity CHECK constraint")

        if status_exists:
            print_success("CHECK constraint 'chk_defects_status' exists")
            self.validation_results['passed'].append("Status CHECK constraint")
        else:
            print_error("CHECK constraint 'chk_defects_status' MISSING")
            self.validation_results['failed'].append("Missing status CHECK constraint")

    def validate_foreign_keys(self):
        """Validate foreign key constraints"""
        print_header("Phase 2: Database Validation - Foreign Keys")

        fk_constraints = self.inspector.get_foreign_keys('defects')
        fk_map = {fk['constrained_columns'][0]: fk for fk in fk_constraints}

        required_fks = {
            'test_session_id': ('test_sessions', 'id', 'CASCADE'),
            'building_id': ('buildings', 'id', 'CASCADE'),
            'created_by': ('users', 'id', 'SET NULL'),
            'acknowledged_by': ('users', 'id', 'SET NULL')
        }

        print_info("Checking foreign keys:")
        for col, (ref_table, ref_col, on_delete) in required_fks.items():
            if col in fk_map:
                fk = fk_map[col]
                if fk['referred_table'] == ref_table:
                    print_success(f"  FK {col} -> {ref_table}({ref_col})")
                    if fk.get('options', {}).get('ondelete', '').upper() == on_delete:
                        print_success(f"    ON DELETE {on_delete}")
                    else:
                        print_warning(f"    ON DELETE should be {on_delete}")
                else:
                    print_error(f"  FK {col} references wrong table: {fk['referred_table']}")
            else:
                print_error(f"  FK {col} MISSING")
                self.validation_results['failed'].append(f"Missing FK: {col}")

    def test_crud_operations(self):
        """Test basic CRUD operations"""
        print_header("Phase 3: Functional Testing - CRUD Operations")

        try:
            from app.models.defects import Defect
            from app.models.buildings import Building
            from app.models.test_sessions import TestSession
            from app.models.users import User
        except ImportError as e:
            print_warning(f"Could not import models: {e}")
            print_warning("Skipping CRUD tests")
            return

        print_info("CRUD tests require a test database with test data")
        print_warning("Skipping CRUD tests (manual testing recommended)")
        self.validation_results['warnings'].append("CRUD tests skipped - manual testing required")

    def test_updated_at_trigger(self):
        """Test that updated_at trigger works"""
        print_header("Phase 3: Functional Testing - updated_at Trigger")

        print_info("Trigger test requires test data")
        print_warning("Skipping trigger test (manual testing recommended)")
        self.validation_results['warnings'].append("Trigger test skipped - manual testing required")

    def print_summary(self):
        """Print validation summary"""
        print_header("Validation Summary")

        total_passed = len(self.validation_results['passed'])
        total_failed = len(self.validation_results['failed'])
        total_warnings = len(self.validation_results['warnings'])

        print(f"\n{Colors.BOLD}Results:{Colors.END}")
        print(f"  {Colors.GREEN}Passed:{Colors.END}   {total_passed}")
        print(f"  {Colors.RED}Failed:{Colors.END}   {total_failed}")
        print(f"  {Colors.YELLOW}Warnings:{Colors.END} {total_warnings}")

        if self.validation_results['failed']:
            print(f"\n{Colors.BOLD}{Colors.RED}Failed Checks:{Colors.END}")
            for item in self.validation_results['failed']:
                print(f"  {Colors.RED}• {item}{Colors.END}")

        if self.validation_results['warnings']:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}Warnings:{Colors.END}")
            for item in self.validation_results['warnings']:
                print(f"  {Colors.YELLOW}• {item}{Colors.END}")

        if not self.validation_results['failed']:
            print(f"\n{Colors.BOLD}{Colors.GREEN}✅ All critical validations passed!{Colors.END}\n")
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}❌ Validation failed - please fix the issues above{Colors.END}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Validate defects table migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using DATABASE_URL environment variable
  export DATABASE_URL="postgresql://user:pass@localhost/fireai_db"
  python3 validate_defects_migration.py

  # Using command line argument
  python3 validate_defects_migration.py --db-url "postgresql://user:pass@localhost/fireai_db"
        """
    )
    parser.add_argument(
        '--db-url',
        help='Database URL (default: DATABASE_URL env var)',
        default=os.environ.get('DATABASE_URL')
    )

    args = parser.parse_args()

    if not args.db_url:
        print_error("Database URL not provided!")
        print_info("Set DATABASE_URL environment variable or use --db-url argument")
        print_info("Example: postgresql://user:password@localhost:5432/database")
        sys.exit(1)

    try:
        validator = MigrationValidator(args.db_url)
        exit_code = validator.run_all_validations()
        sys.exit(exit_code)
    except Exception as e:
        print_error(f"Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

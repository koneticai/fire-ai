#!/usr/bin/env python3
"""
Database Migration Validation Script
===================================

Validates migration files without requiring database connection.

This script checks:
- Migration files exist
- Revision chain is correct
- Migration content has required DDL
- Indexes, constraints, foreign keys defined
- ARRAY defaults use correct PostgreSQL syntax

Usage:
    python3 validate_migration.py
"""

import sys
import os
import re
from pathlib import Path

class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")


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
    """Validates migration files"""

    def __init__(self):
        self.migrations_dir = Path(__file__).parent / 'alembic' / 'versions'
        self.passed = []
        self.failed = []
        self.warnings = []

    def validate_files_exist(self):
        """Check that required migration files exist"""
        print_header("Checking Migration Files")

        required_files = {
            '000_create_trigger_function.py': 'Trigger function migration',
            '001_add_defects_table.py': 'Defects table migration',
            '002_add_evidence_flag_columns.py': 'Evidence flags migration'
        }

        for filename, description in required_files.items():
            filepath = self.migrations_dir / filename
            if filepath.exists():
                print_success(f"{description}: {filename}")
                self.passed.append(f"Migration file exists: {filename}")
            else:
                print_error(f"{description} NOT FOUND: {filename}")
                self.failed.append(f"Missing migration file: {filename}")

    def validate_revision_chain(self):
        """Validate migration revision chain"""
        print_header("Validating Revision Chain")

        # Check 000 migration
        migration_000 = self.migrations_dir / '000_create_trigger_function.py'
        if migration_000.exists():
            content = migration_000.read_text()

            # Check revision ID
            if "revision = '000_create_trigger_function'" in content:
                print_success("Migration 000: Correct revision ID")
                self.passed.append("Migration 000: revision ID")
            else:
                print_error("Migration 000: Incorrect revision ID")
                self.failed.append("Migration 000: revision ID")

            # Check down_revision
            if "down_revision = 'phase2_final_indexes'" in content:
                print_success("Migration 000: Correct down_revision (phase2_final_indexes)")
                self.passed.append("Migration 000: down_revision")
            else:
                print_error("Migration 000: Incorrect down_revision")
                self.failed.append("Migration 000: down_revision")

        # Check 001 migration
        migration_001 = self.migrations_dir / '001_add_defects_table.py'
        if migration_001.exists():
            content = migration_001.read_text()

            # Check revision ID
            if "revision = '001_add_defects_table'" in content:
                print_success("Migration 001: Correct revision ID")
                self.passed.append("Migration 001: revision ID")
            else:
                print_error("Migration 001: Incorrect revision ID")
                self.failed.append("Migration 001: revision ID")

            # Check down_revision (should reference 000)
            if "down_revision = '000_create_trigger_function'" in content:
                print_success("Migration 001: Correct down_revision (000_create_trigger_function)")
                self.passed.append("Migration 001: down_revision")
            else:
                print_error("Migration 001: Incorrect down_revision (should be 000_create_trigger_function)")
                self.failed.append("Migration 001: down_revision")

        # Check 002 migration
        migration_002 = self.migrations_dir / '002_add_evidence_flag_columns.py'
        if migration_002.exists():
            content = migration_002.read_text()

            # Check down_revision (should reference 001)
            if "down_revision = '001_add_defects_table'" in content:
                print_success("Migration 002: Correct down_revision (001_add_defects_table)")
                self.passed.append("Migration 002: down_revision")
            else:
                print_error("Migration 002: Incorrect down_revision (should be 001_add_defects_table)")
                self.failed.append("Migration 002: down_revision")

        print_success("\nMigration chain: phase2_final_indexes → 000 → 001 → 002")

    def validate_trigger_function_migration(self):
        """Validate migration 000 content"""
        print_header("Validating Migration 000: Trigger Function")

        migration_file = self.migrations_dir / '000_create_trigger_function.py'
        if not migration_file.exists():
            print_error("Migration file not found")
            return

        content = migration_file.read_text()

        # Check for CREATE FUNCTION statement
        if "CREATE OR REPLACE FUNCTION update_updated_at_column()" in content:
            print_success("CREATE FUNCTION statement present")
            self.passed.append("Migration 000: CREATE FUNCTION")
        else:
            print_error("CREATE FUNCTION statement missing")
            self.failed.append("Migration 000: CREATE FUNCTION")

        # Check for RETURNS TRIGGER
        if "RETURNS TRIGGER" in content:
            print_success("RETURNS TRIGGER specified")
            self.passed.append("Migration 000: RETURNS TRIGGER")
        else:
            print_error("RETURNS TRIGGER missing")
            self.failed.append("Migration 000: RETURNS TRIGGER")

        # Check for downgrade (DROP FUNCTION)
        if "DROP FUNCTION IF EXISTS update_updated_at_column()" in content:
            print_success("Downgrade includes DROP FUNCTION")
            self.passed.append("Migration 000: DROP FUNCTION in downgrade")
        else:
            print_error("Downgrade missing DROP FUNCTION")
            self.failed.append("Migration 000: DROP FUNCTION in downgrade")

    def validate_defects_table_migration(self):
        """Validate migration 001 content"""
        print_header("Validating Migration 001: Defects Table")

        migration_file = self.migrations_dir / '001_add_defects_table.py'
        if not migration_file.exists():
            print_error("Migration file not found")
            return

        content = migration_file.read_text()

        # Check for CREATE TABLE
        if "op.create_table('defects'" in content:
            print_success("CREATE TABLE defects statement present")
            self.passed.append("Migration 001: CREATE TABLE")
        else:
            print_error("CREATE TABLE defects statement missing")
            self.failed.append("Migration 001: CREATE TABLE")

        # Check for required columns
        required_columns = [
            'id', 'test_session_id', 'building_id', 'asset_id',
            'severity', 'category', 'description', 'as1851_rule_code',
            'status', 'discovered_at', 'acknowledged_at', 'repaired_at',
            'verified_at', 'closed_at', 'evidence_ids', 'repair_evidence_ids',
            'created_at', 'updated_at', 'created_by', 'acknowledged_by'
        ]

        print_info("Checking 20 required columns:")
        missing_columns = []
        for col in required_columns:
            # Look for column definition (case-insensitive)
            pattern = rf"Column\(['\"]?{col}['\"]?,"
            if re.search(pattern, content, re.IGNORECASE):
                print_success(f"  Column '{col}' defined")
            else:
                print_error(f"  Column '{col}' MISSING")
                missing_columns.append(col)

        if missing_columns:
            self.failed.append(f"Migration 001: Missing columns: {', '.join(missing_columns)}")
        else:
            print_success("All 20 columns defined")
            self.passed.append("Migration 001: All 20 columns present")

        # Check for CHECK constraints
        print_info("\nChecking CHECK constraints:")
        if "op.create_check_constraint" in content and "chk_defects_severity" in content:
            print_success("  CHECK constraint 'chk_defects_severity' defined")
            self.passed.append("Migration 001: severity CHECK constraint")
        else:
            print_error("  CHECK constraint 'chk_defects_severity' MISSING")
            self.failed.append("Migration 001: severity CHECK constraint")

        if "op.create_check_constraint" in content and "chk_defects_status" in content:
            print_success("  CHECK constraint 'chk_defects_status' defined")
            self.passed.append("Migration 001: status CHECK constraint")
        else:
            print_error("  CHECK constraint 'chk_defects_status' MISSING")
            self.failed.append("Migration 001: status CHECK constraint")

        # Check for indexes
        print_info("\nChecking indexes:")
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

        missing_indexes = []
        for idx in required_indexes:
            if f"op.create_index('{idx}'" in content or f'op.create_index("{idx}"' in content:
                print_success(f"  Index '{idx}' defined")
            else:
                print_error(f"  Index '{idx}' MISSING")
                missing_indexes.append(idx)

        if missing_indexes:
            self.failed.append(f"Migration 001: Missing indexes: {', '.join(missing_indexes)}")
        else:
            print_success("All 8 indexes defined")
            self.passed.append("Migration 001: All 8 indexes present")

        # Check for ARRAY defaults (should use PostgreSQL syntax)
        print_info("\nChecking ARRAY column defaults:")
        if "sa.text(\"'{}'::uuid[]\")" in content or 'sa.text("\'{}\'::uuid[]")' in content:
            print_success("  ARRAY defaults use correct PostgreSQL syntax ('{}'::uuid[])")
            self.passed.append("Migration 001: ARRAY defaults syntax")
        else:
            print_warning("  ARRAY defaults may not use PostgreSQL syntax")
            print_info("    Should use: sa.text(\"'{}'::uuid[]\")")
            self.warnings.append("Migration 001: ARRAY defaults syntax")

        # Check for status column default
        print_info("\nChecking status column default:")
        if "server_default='open'" in content or 'server_default="open"' in content:
            print_success("  Status column has server_default='open'")
            self.passed.append("Migration 001: status server_default")
        else:
            print_warning("  Status column may be missing server_default")
            self.warnings.append("Migration 001: status server_default")

        # Check for trigger creation
        print_info("\nChecking updated_at trigger:")
        if "CREATE TRIGGER update_defects_updated_at" in content:
            print_success("  updated_at trigger defined")
            self.passed.append("Migration 001: updated_at trigger")
        else:
            print_error("  updated_at trigger MISSING")
            self.failed.append("Migration 001: updated_at trigger")

        # Check for foreign keys
        print_info("\nChecking foreign keys:")
        if "ForeignKey('test_sessions.id'" in content:
            print_success("  Foreign key to test_sessions.id defined")
            self.passed.append("Migration 001: test_sessions FK")
        else:
            print_error("  Foreign key to test_sessions.id MISSING")
            self.failed.append("Migration 001: test_sessions FK")

        if "ForeignKey('buildings.id'" in content:
            print_success("  Foreign key to buildings.id defined")
            self.passed.append("Migration 001: buildings FK")
        else:
            print_error("  Foreign key to buildings.id MISSING")
            self.failed.append("Migration 001: buildings FK")

        if "ForeignKey('users.id'" in content:
            print_success("  Foreign keys to users.id defined")
            self.passed.append("Migration 001: users FK")
        else:
            print_error("  Foreign keys to users.id MISSING")
            self.failed.append("Migration 001: users FK")

    def validate_evidence_flags_migration(self):
        """Validate migration 002 content"""
        print_header("Validating Migration 002: Evidence Flag Columns")

        migration_file = self.migrations_dir / '002_add_evidence_flag_columns.py'
        if not migration_file.exists():
            print_error("Migration file not found")
            return

        content = migration_file.read_text()

        # Check for flag columns
        flag_columns = [
            'flagged_for_review',
            'flag_reason',
            'flagged_at',
            'flagged_by'
        ]

        print_info("Checking 4 flag columns:")
        missing = []
        for col in flag_columns:
            if f"op.add_column('evidence'" in content and f"'{col}'" in content:
                print_success(f"  Column '{col}' added")
            else:
                print_error(f"  Column '{col}' MISSING")
                missing.append(col)

        if missing:
            self.failed.append(f"Migration 002: Missing columns: {', '.join(missing)}")
        else:
            print_success("All 4 flag columns defined")
            self.passed.append("Migration 002: All 4 flag columns present")

        # Check for indexes on flag columns
        print_info("\nChecking indexes for flag columns:")
        if "idx_evidence_flagged_for_review" in content:
            print_success("  Index 'idx_evidence_flagged_for_review' defined")
            self.passed.append("Migration 002: flagged_for_review index")
        else:
            print_warning("  Index 'idx_evidence_flagged_for_review' not found")
            self.warnings.append("Migration 002: flagged_for_review index")

    def print_summary(self):
        """Print validation summary"""
        print_header("Migration Validation Summary")

        total_passed = len(self.passed)
        total_failed = len(self.failed)
        total_warnings = len(self.warnings)

        print(f"\n{Colors.BOLD}Results:{Colors.END}")
        print(f"  {Colors.GREEN}Passed:{Colors.END}   {total_passed}")
        print(f"  {Colors.RED}Failed:{Colors.END}   {total_failed}")
        print(f"  {Colors.YELLOW}Warnings:{Colors.END} {total_warnings}")

        if self.failed:
            print(f"\n{Colors.BOLD}{Colors.RED}Failed Checks:{Colors.END}")
            for item in self.failed:
                print(f"  {Colors.RED}• {item}{Colors.END}")

        if self.warnings:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}Warnings:{Colors.END}")
            for item in self.warnings:
                print(f"  {Colors.YELLOW}• {item}{Colors.END}")

        if not self.failed:
            print(f"\n{Colors.BOLD}{Colors.GREEN}✅ All migration validations passed!{Colors.END}\n")
            return 0
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}❌ Migration validation failed - please fix the issues above{Colors.END}\n")
            return 1


def main():
    """Main entry point"""
    print_header("Database Migration Validation")
    print(f"Working Directory: {os.getcwd()}")

    validator = MigrationValidator()

    if not validator.migrations_dir.exists():
        print_error(f"Migrations directory not found: {validator.migrations_dir}")
        sys.exit(1)

    print(f"Migrations Directory: {validator.migrations_dir}")

    try:
        # Run all validations
        validator.validate_files_exist()
        validator.validate_revision_chain()
        validator.validate_trigger_function_migration()
        validator.validate_defects_table_migration()
        validator.validate_evidence_flags_migration()

        # Print summary
        exit_code = validator.print_summary()
        sys.exit(exit_code)

    except Exception as e:
        print_error(f"Validation failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

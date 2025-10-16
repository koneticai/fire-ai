#!/usr/bin/env python3
"""
Model Import and Structure Validation Script
===========================================

Validates that all models import correctly and have the required attributes.

This script checks:
- Model imports work without errors
- All required attributes are present on models
- Enum types have correct values
- Relationships are properly configured
- __repr__ methods exist

Usage:
    python3 verify_models.py
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

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


class ModelValidator:
    """Validates model structure and imports"""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def validate_defect_model(self):
        """Validate Defect model structure"""
        print_header("Validating Defect Model")

        # Test import
        try:
            from app.models.defects import Defect
            print_success("Defect model imports successfully")
            self.passed.append("Defect model import")
        except Exception as e:
            print_error(f"Failed to import Defect model: {e}")
            self.failed.append("Defect model import")
            return

        # Check required attributes (20 columns)
        required_attrs = [
            'id', 'test_session_id', 'building_id', 'asset_id',
            'severity', 'category', 'description', 'as1851_rule_code',
            'status', 'discovered_at', 'acknowledged_at', 'repaired_at',
            'verified_at', 'closed_at', 'evidence_ids', 'repair_evidence_ids',
            'created_at', 'updated_at', 'created_by', 'acknowledged_by'
        ]

        print_info("Checking 20 required attributes:")
        missing = []
        for attr in required_attrs:
            if hasattr(Defect, attr):
                print_success(f"  Attribute '{attr}' exists")
            else:
                print_error(f"  Attribute '{attr}' MISSING")
                missing.append(attr)

        if missing:
            self.failed.append(f"Missing attributes: {', '.join(missing)}")
        else:
            print_success("All 20 required attributes present")
            self.passed.append("Defect model attributes (20/20)")

        # Check relationships
        print_info("\nChecking relationships:")
        expected_relationships = [
            'test_session', 'building',
            'created_by_user', 'acknowledged_by_user'
        ]

        missing_rels = []
        for rel in expected_relationships:
            if hasattr(Defect, rel):
                print_success(f"  Relationship '{rel}' configured")
            else:
                print_error(f"  Relationship '{rel}' MISSING")
                missing_rels.append(rel)

        if missing_rels:
            self.failed.append(f"Missing relationships: {', '.join(missing_rels)}")
        else:
            print_success("All 4 relationships configured")
            self.passed.append("Defect relationships (4/4)")

        # Check __repr__ method
        if hasattr(Defect, '__repr__'):
            print_success("__repr__ method implemented")
            self.passed.append("Defect __repr__ method")
        else:
            print_error("__repr__ method MISSING")
            self.failed.append("Defect __repr__ method")

        # Check table name
        if hasattr(Defect, '__tablename__'):
            table_name = Defect.__tablename__
            if table_name == 'defects':
                print_success(f"Table name correct: '{table_name}'")
                self.passed.append("Defect table name")
            else:
                print_error(f"Table name incorrect: '{table_name}' (expected: 'defects')")
                self.failed.append("Defect table name")

    def validate_defect_schemas(self):
        """Validate Defect Pydantic schemas"""
        print_header("Validating Defect Schemas")

        # Test schema imports
        try:
            from app.schemas.defect import (
                DefectSeverity, DefectStatus, DefectCreate, DefectUpdate,
                DefectRead, DefectWithEvidence, DefectListResponse
            )
            print_success("All defect schemas import successfully")
            self.passed.append("Defect schemas import")
        except Exception as e:
            print_error(f"Failed to import defect schemas: {e}")
            self.failed.append("Defect schemas import")
            return

        # Check DefectSeverity enum
        from app.schemas.defect import DefectSeverity
        expected_severities = ['critical', 'high', 'medium', 'low']
        actual_severities = [s.value for s in DefectSeverity]

        print_info("Checking DefectSeverity enum:")
        if set(actual_severities) == set(expected_severities):
            print_success(f"  DefectSeverity has correct values: {actual_severities}")
            self.passed.append("DefectSeverity enum (4 values)")
        else:
            print_error(f"  DefectSeverity values incorrect")
            print_error(f"    Expected: {expected_severities}")
            print_error(f"    Got: {actual_severities}")
            self.failed.append("DefectSeverity enum")

        # Check DefectStatus enum
        from app.schemas.defect import DefectStatus
        expected_statuses = [
            'open', 'acknowledged', 'repair_scheduled',
            'repaired', 'verified', 'closed'
        ]
        actual_statuses = [s.value for s in DefectStatus]

        print_info("\nChecking DefectStatus enum:")
        if set(actual_statuses) == set(expected_statuses):
            print_success(f"  DefectStatus has correct values: {actual_statuses}")
            self.passed.append("DefectStatus enum (6 values)")
        else:
            print_error(f"  DefectStatus values incorrect")
            print_error(f"    Expected: {expected_statuses}")
            print_error(f"    Got: {actual_statuses}")
            self.failed.append("DefectStatus enum")

    def validate_evidence_model(self):
        """Validate Evidence model with flag columns"""
        print_header("Validating Evidence Model")

        # Test import
        try:
            from app.models.evidence import Evidence
            print_success("Evidence model imports successfully")
            self.passed.append("Evidence model import")
        except Exception as e:
            print_error(f"Failed to import Evidence model: {e}")
            self.failed.append("Evidence model import")
            return

        # Check flag columns (added in migration 002)
        flag_columns = [
            'flagged_for_review', 'flag_reason',
            'flagged_at', 'flagged_by'
        ]

        print_info("Checking flag columns (from migration 002):")
        missing = []
        for col in flag_columns:
            if hasattr(Evidence, col):
                print_success(f"  Column '{col}' exists")
            else:
                print_error(f"  Column '{col}' MISSING")
                missing.append(col)

        if missing:
            self.failed.append(f"Missing Evidence flag columns: {', '.join(missing)}")
        else:
            print_success("All 4 flag columns present")
            self.passed.append("Evidence flag columns (4/4)")

        # Check relationship with User for flagged_by
        if hasattr(Evidence, 'flagged_by_user'):
            print_success("Relationship 'flagged_by_user' configured")
            self.passed.append("Evidence flagged_by_user relationship")
        else:
            print_warning("Relationship 'flagged_by_user' not found")
            self.warnings.append("Evidence flagged_by_user relationship missing")

    def validate_other_models(self):
        """Validate other required models"""
        print_header("Validating Other Models")

        models_to_check = [
            ('app.models.buildings', 'Building'),
            ('app.models.test_sessions', 'TestSession'),
            ('app.models.users', 'User'),
        ]

        for module_path, class_name in models_to_check:
            try:
                module = __import__(module_path, fromlist=[class_name])
                model_class = getattr(module, class_name)
                print_success(f"{class_name} model imports successfully")
                self.passed.append(f"{class_name} model import")
            except Exception as e:
                print_error(f"Failed to import {class_name} model: {e}")
                self.failed.append(f"{class_name} model import")

    def validate_relationships_bidirectional(self):
        """Validate that relationships are bidirectional"""
        print_header("Validating Bidirectional Relationships")

        try:
            from app.models.defects import Defect
            from app.models.buildings import Building
            from app.models.test_sessions import TestSession
            from app.models.users import User
        except Exception as e:
            print_error(f"Failed to import models for relationship check: {e}")
            return

        # Check Building → Defects
        print_info("Checking Building ↔ Defects relationship:")
        if hasattr(Building, 'defects'):
            print_success("  Building has 'defects' relationship")
            if hasattr(Defect, 'building'):
                print_success("  Defect has 'building' relationship")
                print_success("  Building ↔ Defects bidirectional relationship verified")
                self.passed.append("Building ↔ Defects relationship")
            else:
                print_error("  Defect missing 'building' relationship")
                self.failed.append("Building ↔ Defects relationship")
        else:
            print_error("  Building missing 'defects' relationship")
            self.failed.append("Building → Defects relationship")

        # Check TestSession → Defects
        print_info("\nChecking TestSession ↔ Defects relationship:")
        if hasattr(TestSession, 'defects'):
            print_success("  TestSession has 'defects' relationship")
            if hasattr(Defect, 'test_session'):
                print_success("  Defect has 'test_session' relationship")
                print_success("  TestSession ↔ Defects bidirectional relationship verified")
                self.passed.append("TestSession ↔ Defects relationship")
            else:
                print_error("  Defect missing 'test_session' relationship")
                self.failed.append("TestSession ↔ Defects relationship")
        else:
            print_error("  TestSession missing 'defects' relationship")
            self.failed.append("TestSession → Defects relationship")

        # Check User → Defects (created_defects)
        print_info("\nChecking User ↔ Defects (created) relationship:")
        if hasattr(User, 'created_defects'):
            print_success("  User has 'created_defects' relationship")
            if hasattr(Defect, 'created_by_user'):
                print_success("  Defect has 'created_by_user' relationship")
                print_success("  User ↔ Defects (created) bidirectional relationship verified")
                self.passed.append("User ↔ Defects (created) relationship")
            else:
                print_error("  Defect missing 'created_by_user' relationship")
                self.failed.append("User ↔ Defects (created) relationship")
        else:
            print_error("  User missing 'created_defects' relationship")
            self.failed.append("User → Defects (created) relationship")

    def print_summary(self):
        """Print validation summary"""
        print_header("Model Validation Summary")

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
            print(f"\n{Colors.BOLD}{Colors.GREEN}✅ All model validations passed!{Colors.END}\n")
            return 0
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}❌ Model validation failed - please fix the issues above{Colors.END}\n")
            return 1


def main():
    """Main entry point"""
    print_header("Model Import and Structure Validation")
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")

    validator = ModelValidator()

    try:
        # Run all validations
        validator.validate_defect_model()
        validator.validate_defect_schemas()
        validator.validate_evidence_model()
        validator.validate_other_models()
        validator.validate_relationships_bidirectional()

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

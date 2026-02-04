#!/usr/bin/env python3
"""
Validate AS1851 seed data WITHOUT requiring a database connection.

This script performs all validation checks that the seed script would run,
but skips the actual database insertion. Useful for CI/CD and pre-flight checks.

Usage:
    python scripts/validate_seed_data.py
"""

import json
from pathlib import Path
from typing import Dict, Any, List


def validate_rule_schema(rule: Dict[str, Any]) -> List[str]:
    """Validate a single rule and return list of issues."""
    issues = []

    required_fields = [
        "rule_code", "version", "rule_name", "description",
        "category", "test_frequency", "rule_schema", "is_active"
    ]

    for field in required_fields:
        if field not in rule:
            issues.append(f"Missing field: {field}")

    if "rule_schema" in rule:
        schema = rule["rule_schema"]

        # Check for data specification (multiple valid formats from research)
        # All rule_schema keys except _validation and classification_logic count as data spec
        reserved_keys = {"_validation", "classification_logic"}
        data_keys = set(schema.keys()) - reserved_keys
        has_data_spec = len(data_keys) > 0
        if not has_data_spec:
            issues.append("rule_schema missing data specification")

        # Check classification logic
        if "classification_logic" not in schema:
            issues.append("rule_schema missing classification_logic")

        # Check confidence
        validation_meta = schema.get("_validation", {})
        confidence = validation_meta.get("confidence", 1.0)
        if confidence < 0.85:
            issues.append(f"Low confidence: {confidence:.2f}")

    return issues


def main():
    print("=" * 60)
    print("AS1851 Seed Data Validation (No Database Required)")
    print("=" * 60)

    # Load JSON
    base_dir = Path(__file__).parent.parent
    json_path = base_dir / "data" / "as1851_rules_all_systems.json"

    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        exit(1)

    print(f"\n📂 Loading: {json_path}")

    with open(json_path) as f:
        rules = json.load(f)

    print(f"📊 Total rules: {len(rules)}")

    # Validate each rule
    print(f"\n🔍 Validating rules...\n")

    valid_count = 0
    invalid_count = 0
    warnings = []

    for rule in rules:
        issues = validate_rule_schema(rule)
        code = rule.get("rule_code", "UNKNOWN")

        if issues:
            invalid_count += 1
            print(f"❌ {code}")
            for issue in issues:
                print(f"   └─ {issue}")
        else:
            valid_count += 1
            # Check for warnings (low confidence)
            conf = rule.get("rule_schema", {}).get("_validation", {}).get("confidence", 1.0)
            if conf < 0.90:
                warnings.append(f"{code}: confidence {conf:.2f}")

    # Statistics
    print(f"\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    # Category breakdown
    categories = {}
    frequencies = {}
    for rule in rules:
        cat = rule.get("category", "unknown")
        freq = rule.get("test_frequency", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        frequencies[freq] = frequencies.get(freq, 0) + 1

    print(f"\n📋 By Category:")
    for cat, count in sorted(categories.items()):
        print(f"   • {cat.replace('_', ' ').title()}: {count}")

    print(f"\n📅 By Frequency:")
    for freq, count in sorted(frequencies.items(), key=lambda x: -x[1]):
        print(f"   • {freq.replace('_', ' ').title()}: {count}")

    print(f"\n📊 Summary:")
    print(f"   ✅ Valid:   {valid_count} rules")
    print(f"   ❌ Invalid: {invalid_count} rules")

    if warnings:
        print(f"\n⚠️  Low confidence warnings ({len(warnings)}):")
        for w in warnings[:5]:
            print(f"   • {w}")
        if len(warnings) > 5:
            print(f"   • ... and {len(warnings) - 5} more")

    # Final status
    print(f"\n" + "=" * 60)
    if invalid_count == 0:
        print("✅ ALL RULES VALID - Ready for database seeding")
        print("=" * 60)

        print(f"\n📝 Next steps:")
        print(f"   1. Start PostgreSQL (local, Docker, or cloud)")
        print(f"   2. Set DATABASE_URL environment variable")
        print(f"   3. Run: python services/api/scripts/seed_as1851_rules.py")

        exit(0)
    else:
        print(f"❌ {invalid_count} RULES FAILED VALIDATION")
        print("=" * 60)
        exit(1)


if __name__ == "__main__":
    main()

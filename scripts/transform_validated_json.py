#!/usr/bin/env python3
"""
Transform validated research JSON to database seed format.

Input:  /fire-ai/docs/research/as1851_rules_validated_MASTER.json
Output: /fire-ai/data/as1851_rules_all_systems.json

This script converts the nested category-based structure from the 17-agent
validation research into the flat array format expected by the seed script.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any


def generate_description(rule: Dict[str, Any], category_key: str) -> str:
    """Generate a meaningful description from rule data."""
    name = rule.get("rule_name", "")
    section = rule.get("section_reference", "")
    schema = rule.get("rule_schema", {})

    # Get key data points from schema
    required_data = schema.get("required_data", [])
    test_inputs = schema.get("test_inputs", [])
    inspection_items = list(schema.get("inspection_items", {}).keys())
    test_results = list(schema.get("test_results", {}).keys())

    # Build description parts
    desc_parts = []

    # Start with the rule purpose (strip category prefix from name)
    prefixes = [
        "Stair Pressurization - ",
        "Fire Doors - ",
        "Smoke Control - "
    ]
    purpose = name
    for prefix in prefixes:
        if purpose.startswith(prefix):
            purpose = purpose[len(prefix):]
            break

    desc_parts.append(purpose)

    # Add key requirements
    if required_data:
        items = ", ".join(required_data[:3])
        if len(required_data) > 3:
            items += f" (+{len(required_data) - 3} more)"
        desc_parts.append(f"Required data: {items}")
    elif test_inputs:
        items = ", ".join(test_inputs[:3])
        desc_parts.append(f"Test inputs: {items}")
    elif inspection_items:
        items = ", ".join(inspection_items[:3])
        if len(inspection_items) > 3:
            items += f" (+{len(inspection_items) - 3} more)"
        desc_parts.append(f"Inspection: {items}")
    elif test_results:
        items = ", ".join(test_results[:3])
        if len(test_results) > 3:
            items += f" (+{len(test_results) - 3} more)"
        desc_parts.append(f"Verification: {items}")

    # Add section reference
    if section:
        desc_parts.append(f"per AS1851-2012 {section}")

    return ". ".join(desc_parts) + "."


def determine_category(rule_code: str) -> str:
    """Determine category from rule code prefix."""
    if "-SP-" in rule_code:
        return "stair_pressurization"
    elif "-FD-" in rule_code:
        return "fire_doors"
    elif "-SC-" in rule_code:
        return "smoke_control"
    else:
        raise ValueError(f"Unknown rule code format: {rule_code}")


def transform_rule(rule: Dict[str, Any], category_key: str) -> Dict[str, Any]:
    """Transform a single rule from research format to seed format."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build the transformed rule
    transformed = {
        "rule_code": rule["rule_code"],
        "version": "1.0.0",
        "rule_name": rule["rule_name"],
        "description": generate_description(rule, category_key),
        "category": determine_category(rule["rule_code"]),
        "test_frequency": rule["test_frequency"],
        "rule_schema": rule["rule_schema"],
        "is_active": True,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    # Preserve validation metadata in schema for reference
    transformed["rule_schema"]["_validation"] = {
        "confidence": rule.get("confidence", 0.90),
        "section_reference": rule.get("section_reference", ""),
        "validated_date": "2026-02-04",
        "standard_version": "AS1851-2012 Amendment No. 1 (November 2016)"
    }

    # Note any validation issues from research
    if "validation_issue" in rule:
        transformed["rule_schema"]["_validation"]["issue_note"] = rule["validation_issue"]

    return transformed


def transform_validated_json(input_path: Path, output_path: Path) -> Dict[str, Any]:
    """Transform validated JSON to seed format."""
    print(f"📂 Reading: {input_path}")

    with open(input_path, "r") as f:
        validated_data = json.load(f)

    metadata = validated_data.get("metadata", {})
    rules_by_category = validated_data["rules"]
    transformed_rules: List[Dict[str, Any]] = []

    print(f"\n📊 Source Metadata:")
    print(f"   Standard: {metadata.get('standard', 'Unknown')}")
    print(f"   Amendment: {metadata.get('amendment', 'Unknown')}")
    print(f"   Confidence: {metadata.get('overall_confidence', 'Unknown')}")

    # Transform each category
    print(f"\n🔄 Transforming rules...")
    for category_key, rules in rules_by_category.items():
        print(f"   • {category_key}: {len(rules)} rules")
        for rule in rules:
            transformed = transform_rule(rule, category_key)
            transformed_rules.append(transformed)

    # Sort by rule_code for consistency
    transformed_rules.sort(key=lambda r: r["rule_code"])

    # Write output
    print(f"\n💾 Writing: {output_path}")
    print(f"   Total rules: {len(transformed_rules)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(transformed_rules, f, indent=2)

    # Calculate and display statistics
    stats = calculate_statistics(transformed_rules)

    print(f"\n✅ Transformation complete!")
    print(f"\n📊 Summary:")

    print("\n   By Category:")
    for cat, count in sorted(stats["categories"].items()):
        print(f"      • {cat.replace('_', ' ').title()}: {count} rules")

    print("\n   By Frequency:")
    for freq, count in sorted(stats["frequencies"].items(), key=lambda x: -x[1]):
        print(f"      • {freq.replace('_', ' ').title()}: {count} rules")

    print(f"\n   Confidence Range: {stats['min_confidence']:.2f} - {stats['max_confidence']:.2f}")
    print(f"   Average Confidence: {stats['avg_confidence']:.2f}")

    return stats


def calculate_statistics(rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistics from transformed rules."""
    categories: Dict[str, int] = {}
    frequencies: Dict[str, int] = {}
    confidences: List[float] = []

    for rule in rules:
        # Category counts
        cat = rule["category"]
        categories[cat] = categories.get(cat, 0) + 1

        # Frequency counts
        freq = rule["test_frequency"]
        frequencies[freq] = frequencies.get(freq, 0) + 1

        # Confidence values
        validation = rule["rule_schema"].get("_validation", {})
        conf = validation.get("confidence", 0.90)
        confidences.append(conf)

    return {
        "total_rules": len(rules),
        "categories": categories,
        "frequencies": frequencies,
        "min_confidence": min(confidences) if confidences else 0,
        "max_confidence": max(confidences) if confidences else 0,
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0
    }


def main():
    """Main entry point."""
    print("=" * 60)
    print("AS1851-2012 Validated JSON Transformation")
    print("=" * 60)

    # Paths relative to script location
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / "docs/research/as1851_rules_validated_MASTER.json"
    output_file = base_dir / "data/as1851_rules_all_systems.json"

    # Verify input exists
    if not input_file.exists():
        print(f"❌ Error: Input file not found: {input_file}")
        print(f"   Expected at: {input_file.absolute()}")
        exit(1)

    # Transform
    stats = transform_validated_json(input_file, output_file)

    print("\n" + "=" * 60)
    print(f"✅ Output saved to: {output_file}")
    print(f"📊 Total: {stats['total_rules']} rules ready for database seeding")
    print("=" * 60)

    # Verify JSON is valid
    print("\n🔍 Verifying output JSON...")
    with open(output_file, "r") as f:
        verify = json.load(f)
    print(f"   ✅ Valid JSON with {len(verify)} rules")


if __name__ == "__main__":
    main()

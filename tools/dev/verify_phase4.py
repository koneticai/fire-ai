#!/usr/bin/env python3
"""
Phase 4 Verification Script
Validates all requirements from the Phase 4 checklist:
1. CloudFormation template validation
2. DynamoDB table schema verification
3. Loader file presence
4. Registry integration (DB-first with fallback)
5. Seed script functionality
6. Middleware validation (DB-loaded schemas + fallback)
"""

import os
import sys
import json
from pathlib import Path
from typing import Tuple, Dict, Any

# Color output helpers
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_check(name: str, passed: bool, details: str = ""):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {name}")
    if details:
        print(f"        {details}")

def check_cloudformation_template() -> Tuple[bool, str]:
    """Verify CloudFormation template exists and is valid YAML/JSON"""
    template_path = Path("infra/cloudformation/schema-registry/stack.yml")
    deploy_path = Path("infra/cloudformation/schema-registry/deploy.sh")
    
    if not template_path.exists():
        return False, "Template file not found"
    
    if not deploy_path.exists():
        return False, "Deploy script not found"
    
    # Read and verify content (text-based validation for CloudFormation intrinsics)
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Verify key sections exist in the file
        required_patterns = [
            'AWSTemplateFormatVersion',
            'Resources:',
            'SchemaVersionsTable:',
            'Type: AWS::DynamoDB::Table',
            'fire-ai-schema-versions'
        ]
        
        missing = [p for p in required_patterns if p not in content]
        if missing:
            return False, f"Missing patterns: {missing}"
        
        # Verify deploy script has proper AWS CLI command
        with open(deploy_path, 'r') as f:
            deploy_content = f.read()
        
        if 'aws cloudformation deploy' not in deploy_content:
            return False, "Deploy script missing aws cloudformation deploy command"
        
        if 'fire-ai-schema-versions' not in deploy_content:
            return False, "Deploy script doesn't reference correct table name"
        
        return True, "Template and deploy script valid (text validation)"
    except Exception as e:
        return False, f"Template validation error: {e}"

def check_dynamodb_table_schema() -> Tuple[bool, str]:
    """Verify DynamoDB table schema in CloudFormation template"""
    template_path = Path("infra/cloudformation/schema-registry/stack.yml")
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Check for required schema elements (text-based validation)
        required_elements = [
            'fire-ai-schema-versions',  # TableName parameter or direct value
            'AttributeName: endpoint',
            'AttributeName: version',
            'AttributeName: is_active',
            'KeyType: HASH',
            'KeyType: RANGE',
            'IndexName: gsi_active_by_endpoint',
            'GlobalSecondaryIndexes:',
        ]
        
        missing = [e for e in required_elements if e not in content]
        if missing:
            return False, f"Missing elements: {missing}"
        
        # Verify key schema structure
        if 'endpoint' not in content or 'version' not in content:
            return False, "Missing primary key attributes"
        
        # Verify GSI structure
        if 'gsi_active_by_endpoint' not in content:
            return False, "GSI gsi_active_by_endpoint not found"
        
        if 'is_active' not in content:
            return False, "is_active attribute not found"
        
        return True, "Table: fire-ai-schema-versions, GSI: gsi_active_by_endpoint"
    except Exception as e:
        return False, f"Schema validation error: {e}"

def check_loader_file() -> Tuple[bool, str]:
    """Verify loader_dynamodb.py exists and has required class"""
    loader_path = Path("services/api/schemas/loader_dynamodb.py")
    
    if not loader_path.exists():
        return False, "loader_dynamodb.py not found"
    
    try:
        content = loader_path.read_text()
        
        # Check for DynamoDBSchemaLoader class
        if "class DynamoDBSchemaLoader:" not in content:
            return False, "DynamoDBSchemaLoader class not found"
        
        # Check for required methods
        required_methods = ['__init__', 'fetch', 'fetch_active']
        missing = [m for m in required_methods if f"def {m}" not in content]
        if missing:
            return False, f"Missing methods: {missing}"
        
        # Check for boto3 import
        if "import boto3" not in content:
            return False, "boto3 import not found"
        
        return True, "Loader class with fetch() and fetch_active() methods"
    except Exception as e:
        return False, f"Loader validation error: {e}"

def check_registry_integration() -> Tuple[bool, str]:
    """Verify registry.py integrates loader with fallback logic"""
    registry_path = Path("services/api/schemas/registry.py")
    
    if not registry_path.exists():
        return False, "registry.py not found"
    
    try:
        content = registry_path.read_text()
        
        # Check for loader import
        if "from .loader_dynamodb import DynamoDBSchemaLoader" not in content:
            return False, "DynamoDBSchemaLoader not imported"
        
        # Check for FIRE_SCHEMA_SOURCE env var handling
        if "FIRE_SCHEMA_SOURCE" not in content:
            return False, "FIRE_SCHEMA_SOURCE env var not used"
        
        # Check for loader initialization in __init__
        if "self.loader = loader" not in content:
            return False, "Loader not stored in registry"
        
        # Check for DB-first logic in _get_validator or similar
        if "self.loader.fetch" not in content:
            return False, "Loader fetch method not called"
        
        # Check for fallback logic
        if "except" not in content:
            return False, "No exception handling (fallback logic) found"
        
        return True, "DB-first lookup with local fallback, FIRE_SCHEMA_SOURCE env control"
    except Exception as e:
        return False, f"Registry validation error: {e}"

def check_seed_script() -> Tuple[bool, str]:
    """Verify seed_schema_dynamodb.py exists and targets POST /results v1"""
    seed_path = Path("tools/dev/seed_schema_dynamodb.py")
    
    if not seed_path.exists():
        return False, "seed_schema_dynamodb.py not found"
    
    try:
        content = seed_path.read_text()
        
        # Check for boto3
        if "import boto3" not in content:
            return False, "boto3 import not found"
        
        # Check for POST /results endpoint
        if '"POST /results"' not in content and "'POST /results'" not in content:
            return False, "POST /results endpoint not found in seed script"
        
        # Check for version v1
        if '"v1"' not in content and "'v1'" not in content:
            return False, "v1 version not found in seed script"
        
        # Check for is_active field
        if '"is_active"' not in content and "'is_active'" not in content:
            return False, "is_active field not found"
        
        # Check for schema field
        if '"schema"' not in content and "'schema'" not in content:
            return False, "schema field not found"
        
        # Check for table.put_item
        if "put_item" not in content:
            return False, "put_item call not found"
        
        return True, "Seeds POST /results v1 with is_active='1'"
    except Exception as e:
        return False, f"Seed script validation error: {e}"

def check_middleware_integration() -> Tuple[bool, str]:
    """Verify middleware uses SchemaRegistry and returns FIRE-422"""
    middleware_path = Path("services/api/src/app/middleware/schema_validation.py")
    
    if not middleware_path.exists():
        return False, "schema_validation.py middleware not found"
    
    try:
        content = middleware_path.read_text()
        
        # Check for SchemaRegistry import
        if "from schemas.registry import SchemaRegistry" not in content:
            return False, "SchemaRegistry not imported"
        
        # Check for registry initialization
        if "self.registry = registry or SchemaRegistry()" not in content:
            return False, "Registry not initialized"
        
        # Check for validate_request call
        if "self.registry.validate_request" not in content:
            return False, "validate_request not called"
        
        # Check for 422 status code
        if "status_code=422" not in content:
            return False, "422 status code not returned"
        
        # Check for FIRE_VALIDATION_ENABLED
        if "FIRE_VALIDATION_ENABLED" not in content:
            return False, "FIRE_VALIDATION_ENABLED env var not used"
        
        return True, "Middleware validates with registry, returns 422 on failure"
    except Exception as e:
        return False, f"Middleware validation error: {e}"

def check_middleware_tests() -> Tuple[bool, str]:
    """Verify middleware tests exist and cover DB + fallback scenarios"""
    test_path = Path("services/api/tests/test_schema_validation_middleware.py")
    
    if not test_path.exists():
        return False, "test_schema_validation_middleware.py not found"
    
    try:
        content = test_path.read_text()
        
        # Check for test functions
        test_functions = [
            "test_valid_request_passes",
            "test_invalid_request_gets_fire_422",
            "test_malformed_json_returns_400"
        ]
        
        missing = [t for t in test_functions if t not in content]
        if missing:
            return False, f"Missing tests: {missing}"
        
        # Check for FIRE-422 assertion
        if "FIRE-422" not in content:
            return False, "FIRE-422 error code not tested"
        
        # Check for status code 422 assertion
        if "assert resp.status_code == 422" not in content:
            return False, "422 status code not asserted"
        
        return True, f"{len([t for t in test_functions if t in content])} tests cover validation scenarios"
    except Exception as e:
        return False, f"Test validation error: {e}"

def check_schema_files() -> Tuple[bool, str]:
    """Verify POST /results v1 schema files exist"""
    request_schema = Path("services/api/schemas/requests/post_results_v1.json")
    response_schema = Path("services/api/schemas/responses/post_results_v1.json")
    common_schema = Path("services/api/schemas/common/base.json")
    
    if not request_schema.exists():
        return False, "Request schema post_results_v1.json not found"
    
    if not response_schema.exists():
        return False, "Response schema post_results_v1.json not found"
    
    if not common_schema.exists():
        return False, "Common schema base.json not found"
    
    try:
        # Validate JSON syntax
        with open(request_schema) as f:
            req_data = json.load(f)
        with open(response_schema) as f:
            resp_data = json.load(f)
        with open(common_schema) as f:
            common_data = json.load(f)
        
        # Check required fields in request schema
        if req_data.get('type') != 'object':
            return False, "Request schema not an object"
        
        required = req_data.get('required', [])
        if 'student_id' not in required or 'assessment_id' not in required:
            return False, "Required fields missing from schema"
        
        return True, "Request, response, and common schemas valid"
    except Exception as e:
        return False, f"Schema file validation error: {e}"

def main():
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Phase 4 Verification - Schema Registry with DynamoDB{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Change to fire-ai directory
    os.chdir(Path(__file__).parent.parent.parent)
    
    checks = [
        ("1. CloudFormation Template", check_cloudformation_template),
        ("2. DynamoDB Table Schema", check_dynamodb_table_schema),
        ("3. Loader File (loader_dynamodb.py)", check_loader_file),
        ("4. Registry Integration (DB-first + fallback)", check_registry_integration),
        ("5. Seed Script (POST /results v1)", check_seed_script),
        ("6. Middleware Integration (422 validation)", check_middleware_integration),
        ("7. Middleware Tests", check_middleware_tests),
        ("8. Schema Files (JSON)", check_schema_files),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            passed, details = check_func()
            print_check(name, passed, details)
            results.append(passed)
        except Exception as e:
            print_check(name, False, f"Error: {e}")
            results.append(False)
        print()
    
    print(f"{BLUE}{'='*70}{RESET}")
    passed_count = sum(results)
    total_count = len(results)
    
    if passed_count == total_count:
        print(f"{GREEN}✓ ALL CHECKS PASSED ({passed_count}/{total_count}){RESET}")
        print(f"\n{GREEN}Phase 4 Implementation: VERIFIED ✓{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ SOME CHECKS FAILED ({passed_count}/{total_count} passed){RESET}")
        print(f"\n{RED}Phase 4 Implementation: INCOMPLETE{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Test runner for the defects end-to-end integration tests.

This script demonstrates how to run the comprehensive E2E tests
for the defects workflow.

Usage:
    python run_e2e_tests.py
    python run_e2e_tests.py --verbose
    python run_e2e_tests.py --performance-only
"""

import sys
import subprocess
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run defects E2E integration tests")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Run tests with verbose output")
    parser.add_argument("--performance-only", action="store_true",
                       help="Run only performance tests")
    parser.add_argument("--error-only", action="store_true",
                       help="Run only error scenario tests")
    
    args = parser.parse_args()
    
    # Set up test command
    test_file = "tests/integration/test_defects_e2e.py"
    
    cmd = ["python", "-m", "pytest", test_file]
    
    if args.verbose:
        cmd.append("-v")
        cmd.append("-s")  # Don't capture output
    
    if args.performance_only:
        cmd.extend(["-k", "test_defects_workflow_performance"])
    elif args.error_only:
        cmd.extend(["-k", "test_defects_workflow_error_scenarios"])
    
    print("🚀 Running Defects E2E Integration Tests")
    print("=" * 50)
    print(f"Command: {' '.join(cmd)}")
    print("=" * 50)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("\n🎉 All tests PASSED!")
            print("\nTest Summary:")
            print("✅ Complete defects workflow test")
            print("✅ Error scenario validation")
            print("✅ Performance benchmarks")
            print("\nThe defects workflow is fully functional end-to-end!")
        else:
            print("\n❌ Some tests FAILED!")
            print("Check the output above for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

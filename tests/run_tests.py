#!/usr/bin/env python3
"""
Test runner for Home Assistant MCP.

This script runs all tests and provides a comprehensive report.
"""

import os
import sys
import argparse
import pytest
import time
from pathlib import Path

def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description='Run Home Assistant MCP tests')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Default to running all tests if no specific test type is selected
    run_unit = args.unit or not (args.unit or args.integration)
    run_integration = args.integration or not (args.unit or args.integration)
    
    print("=== Home Assistant MCP Test Runner ===")
    print(f"Project root: {project_root}")
    print(f"Python version: {sys.version}")
    print()
    
    start_time = time.time()
    
    # Create pytest arguments
    pytest_args = []
    
    # Add coverage if requested
    if args.coverage:
        pytest_args.extend([
            '--cov=src',
            '--cov-report=term',
            '--cov-report=html:coverage_report'
        ])
    
    # Add verbosity
    if args.verbose:
        pytest_args.append('-v')
    
    # Add test selection
    test_paths = []
    if run_unit:
        # Add unit test paths excluding integration tests
        for root, dirs, files in os.walk(project_root / 'tests'):
            if 'integration' in root:
                continue
                
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_paths.append(os.path.join(root, file))
    
    if run_integration:
        # Add integration test paths
        integration_dir = project_root / 'tests' / 'integration'
        if integration_dir.exists():
            for file in os.listdir(integration_dir):
                if file.startswith('test_') and file.endswith('.py'):
                    test_paths.append(os.path.join(integration_dir, file))
    
    # Print what we're running
    print("Running tests:")
    for path in test_paths:
        print(f"  - {os.path.relpath(path, project_root)}")
    print()
    
    # Run tests
    returncode = pytest.main(pytest_args + test_paths)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Tests run in {duration:.2f} seconds")
    print(f"Exit code: {returncode}")
    
    if returncode == 0:
        print("Result: All tests passed! 🎉")
    else:
        print("Result: Tests failed ❌")
    
    return returncode

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
test_logging_modes.py - Test logging validation in both strict and non-strict modes

This script verifies that our logging validation functions work correctly in both
strict and non-strict mode. It's designed to be run as part of CI to ensure that
the logging enforcement mechanisms remain robust.

Usage:
    python test_logging_modes.py
"""

import os
import sys
from pathlib import Path

# Ensure we can import from the parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import logging validation functions
from log_config import (
    validate_logger_configuration, 
    validate_formatter_consistency,
    validate_handler_configuration,
    configure_logging,
    get_logger
)

def test_strict_mode():
    """Test logging validation in strict mode"""
    print("\n=== Testing Strict Mode Validation ===")
    
    # line 30-32: Set strict mode environment variable
    os.environ['LOG_STRICT'] = '1'
    print("LOG_STRICT=1 (Strict mode enabled)")
    
    # line 34-35: Configure logging before testing
    configure_logging()
    
    # line 37-39: Create a test logger
    test_logger = get_logger("test_strict_mode")
    test_logger.info("Testing strict mode validation")
    
    # line 41-49: Run validation checks
    print("\nRunning formatter validation...")
    formatter_valid = validate_formatter_consistency()
    print(f"Formatter validation: {'✅ PASSED' if formatter_valid else '❌ FAILED'}")
    
    print("\nRunning handler validation...")
    handler_valid = validate_handler_configuration()
    print(f"Handler validation: {'✅ PASSED' if handler_valid else '❌ FAILED'}")
    
    print("\nRunning full validation...")
    all_valid = validate_logger_configuration()
    print(f"Full validation: {'✅ PASSED' if all_valid else '❌ FAILED'}")
    
    return formatter_valid and handler_valid and all_valid

def test_non_strict_mode():
    """Test logging validation in non-strict mode"""
    print("\n=== Testing Non-Strict Mode Validation ===")
    
    # line 60-62: Set non-strict mode environment variable
    os.environ['LOG_STRICT'] = '0'
    print("LOG_STRICT=0 (Non-strict mode enabled)")
    
    # line 64-65: Configure logging before testing
    configure_logging()
    
    # line 67-69: Create a test logger
    test_logger = get_logger("test_non_strict_mode")
    test_logger.info("Testing non-strict mode validation")
    
    # line 71-79: Run validation checks
    print("\nRunning formatter validation...")
    formatter_valid = validate_formatter_consistency()
    print(f"Formatter validation: {'✅ PASSED' if formatter_valid else '❌ FAILED'}")
    
    print("\nRunning handler validation...")
    handler_valid = validate_handler_configuration()
    print(f"Handler validation: {'✅ PASSED' if handler_valid else '❌ FAILED'}")
    
    print("\nRunning full validation...")
    all_valid = validate_logger_configuration()
    print(f"Full validation: {'✅ PASSED' if all_valid else '❌ FAILED'}")
    
    return formatter_valid and handler_valid and all_valid

def main():
    """Run all test modes and report results"""
    # line 89-91: Run both modes sequentially
    strict_result = test_strict_mode()
    non_strict_result = test_non_strict_mode()
    
    # line 93-103: Print final report
    print("\n=== Test Results Summary ===")
    print(f"Strict Mode Validation: {'✅ PASSED' if strict_result else '❌ FAILED'}")
    print(f"Non-Strict Mode Validation: {'✅ PASSED' if non_strict_result else '❌ FAILED'}")
    
    if strict_result and non_strict_result:
        print("\n✅ ALL TESTS PASSED ✅")
        return 0
    else:
        print("\n❌ TESTS FAILED ❌")
        return 1

if __name__ == "__main__":
    sys.exit(main())

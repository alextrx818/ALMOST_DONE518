#!/usr/bin/env python3
# line 1-2: Smoke test for logging system verification

"""
Comprehensive smoke test for the centralized logging system.
This script validates that:
1. All loggers are created through get_logger() or get_summary_logger()
2. All log entries follow the canonical format
3. All loggers have the correct handlers attached
4. All file handlers properly implement newest-first behavior

Usage:
    python3 tools/smoke_test_logging.py
"""

import sys
import os
import logging
import re
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import logging modules
# line 11-12: Import the required logging functions
from log_config import get_logger, PrependFileHandler
import log_config  # Import the full module for get_summary_logger, PrependFileHandler
from tools.validate_logging import validate_logging_compliance

# Create test directory
TEST_DIR = Path(__file__).parent.parent / "logs" / "smoke_test"
TEST_DIR.mkdir(exist_ok=True, parents=True)

# line 32-33: Setup test logger
def run_smoke_test():
    """Run comprehensive smoke test for the logging system."""
    test_logger = get_logger("smoke_test")
    test_logger.info("🔥 Starting smoke test for logging system")
    
    # line 38-39: Test 1: Basic logging with get_logger()
    test_logger.info("TEST 1: Basic logging functionality")
    log_file = Path(__file__).parent.parent / "logs" / "smoke_test.log"
    
    print(f"\n1️⃣ Testing basic logging to {log_file}")
    print(f"Current logger handlers: {test_logger.handlers}")
    
    # Create a direct test log with clear identification
    for i in range(3):
        msg = f"SMOKE TEST LOG ENTRY #{i+1} - {datetime.now().strftime('%H:%M:%S.%f')}"
        print(f"Writing log: {msg}")
        test_logger.info(msg)
    
    time.sleep(1.0)  # Allow more time for file operations
    
    # Debug file existence and content
    print(f"Log file exists: {log_file.exists()}")
    if log_file.exists():
        print(f"Log file size: {log_file.stat().st_size} bytes")
        print("Log file content:")
        try:
            with open(log_file, 'r') as f:
                print(f.read())
        except Exception as e:
            print(f"Error reading log file: {e}")
    
    # line 47-48: Verify log file exists and has newest-first entries
    if not log_file.exists():
        print("❌ FAIL: Log file was not created")
        return False
    
    if log_file.stat().st_size == 0:
        print("❌ FAIL: Log file is empty")
        return False
        
    with open(log_file, 'r') as f:
        content = f.read()
        lines = content.strip().split('\n')
        
        # line 58-60: Check if we have at least 3 lines
        if len(lines) < 3:
            print(f"❌ FAIL: Not enough log entries found (got {len(lines)}, expected at least 3)")
            print(f"Log content: {content}")
            return False
        
        # line 65-69: Check for the log entries in expected order
        # Verify line 0 has entry #3, line 1 has entry #2, and line 2 has entry #1
        has_correct_order = False
        
        # Look at the first 3 lines
        if len(lines) >= 3:
            if ("SMOKE TEST LOG ENTRY #3" in lines[0] and
                "SMOKE TEST LOG ENTRY #2" in lines[1] and
                "SMOKE TEST LOG ENTRY #1" in lines[2]):
                has_correct_order = True
        
        if has_correct_order:
            print("✅ PASS: Newest-first order confirmed")
        else:
            print("❌ FAIL: Log entries not in newest-first order")
            print(f"Log content: {content}")
            return False
    
    # line 91-92: Test 2: Check canonical log format
    print("\n2️⃣ Testing canonical log format")
    with open(log_file, 'r') as f:
        content = f.read()
        # Verify canonical format: ISO-8601 "YYYY-MM-DD HH:MM:SS,mmm [level] logger: message"
        # line 96-97: Define the exact ISO-8601 pattern used in our standard formatter
        iso_format = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \[\w+\] \w+: .+'
        
        lines = content.strip().split('\n')
        # line 100-101: Check only the first 3 lines which should have our newest logs
        # with the correct format
        if all(re.match(iso_format, line) for line in lines[:3]):
            print("✅ PASS: Log entries follow canonical ISO-8601 format")
        else:
            print("❌ FAIL: Log entries do not follow canonical ISO-8601 format")
            print(f"First line format: {lines[0] if lines else 'No lines'}")
            # Only report first few lines to avoid log bloat
            return False
    
    # line 77-78: Test 3: Verify summary logger integration
    print("\n3️⃣ Testing summary logger integration")
    # line 79-80: Use the updated get_summary_logger with name parameter
    summary_logger = log_config.get_summary_logger("smoke_test")
    summary_logger.info("TEST SUMMARY ENTRY - SMOKE TEST")
    time.sleep(0.5)  # Allow time for file operations
    
    # line 128-132: Verify summary log created in the proper location
    # The updated get_summary_logger uses a 'summary' subdirectory with named logs
    summary_log_file = Path(__file__).parent.parent / "logs" / "summary" / "smoke_test.log"
    
    # Verify the file exists and has content
    if not summary_log_file.exists():
        print(f"❌ FAIL: Summary log file was not created at {summary_log_file}")
        return False
    
    if summary_log_file.stat().st_size == 0:
        print(f"❌ FAIL: Summary log file exists but is empty at {summary_log_file}")
        return False
    
    with open(summary_log_file, 'r') as f:
        content = f.read()
        if "TEST SUMMARY ENTRY - SMOKE TEST" in content:
            print("✅ PASS: Summary logger integration confirmed")
        else:
            print("❌ FAIL: Summary logger entry not found")
            return False
    
    # line 94-95: Test 4: Run validation script in strict mode
    print("\n4️⃣ Running validation script in strict mode")
    try:
        valid = validate_logging_compliance(strict_mode=True)
        if valid:
            print("✅ PASS: Validation script passed in strict mode")
        else:
            print("❌ FAIL: Validation script failed in strict mode")
            return False
    except Exception as e:
        print(f"❌ FAIL: Validation script raised an exception: {e}")
        return False
    
    # line 107-108: Test 5: Check rotation configuration (cannot test directly)
    # line 164-166: Test 5: Verify log rotation configuration
    print("\n5️⃣ Verifying rotation configuration")
    # Find handlers of type PrependFileHandler
    handlers = [h for h in test_logger.handlers if isinstance(h, PrependFileHandler)]
    
    if not handlers:
        print("❌ FAIL: No PrependFileHandler found")
        return False
    
    handler = handlers[0]
    
    # line 174-177: Verify rotation config matches our requirements
    # The handler should use midnight rotation with at least 7 days retention
    # Case-insensitive check for 'midnight' (may appear as either 'midnight' or 'MIDNIGHT')
    when_value = getattr(handler, 'when', None)
    has_correct_when = when_value is not None and when_value.upper() == 'MIDNIGHT'
    has_sufficient_retention = getattr(handler, 'backupCount', 0) >= 7
    
    if has_correct_when and has_sufficient_retention:
        print("✅ PASS: Rotation configuration properly set")
        print(f"Handler config: when={getattr(handler, 'when', 'None')}, backupCount={getattr(handler, 'backupCount', 'None')}")
    else:
        print("❌ FAIL: Rotation configuration not properly set")
        print(f"Handler config: when={getattr(handler, 'when', 'None')}, backupCount={getattr(handler, 'backupCount', 'None')}")
        return False
    
    # line 124-125: Overall result
    print("\n✅ All smoke tests PASSED! The logging system is ready for deployment.")
    return True

if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)

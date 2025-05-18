#!/usr/bin/env python3
# line 1-2: Direct test of PrependFileHandler functionality

"""
Standalone test script for PrependFileHandler.
This script directly tests the logging handler without relying on the full logging system.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the PrependFileHandler directly
from log_config import PrependFileHandler

# line 19-20: Setup test directory and file
TEST_LOG_DIR = Path(__file__).parent.parent / "logs" / "test"
TEST_LOG_DIR.mkdir(exist_ok=True, parents=True)
TEST_LOG_FILE = TEST_LOG_DIR / "prepend_test.log"

# line 24-25: Setup a basic logger for testing
logger = get_logger("prepend_test")
logger.setLevel(logging.INFO)  # Ensure the logger level is set

# line 28-29: Remove any existing handlers to start fresh
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# line 32-33: Create and configure the handler directly
handler = PrependFileHandler(str(TEST_LOG_FILE), encoding='utf-8')
handler.setLevel(logging.INFO)  # Critical: Explicitly set handler level
# REMOVED inline Formatter – use get_standard_formatter()
# REMOVED: use central log_config.configure_logging() or get_logger()

# line 38-39: Write directly to the file with debug output
print(f"Testing PrependFileHandler...")
print(f"- Logger level: {logger.level}")
print(f"- Handler level: {handler.level}")
print(f"- Target file: {TEST_LOG_FILE}")

# line 44-45: Write test entries
for i in range(3):
    message = f"TEST ENTRY {i+1}"
    print(f"Writing: {message}")
    logger.info(message)
    time.sleep(0.5)  # Add delay to ensure distinct timestamps

# line 51-52: Verify file contents directly
if os.path.exists(TEST_LOG_FILE):
    file_size = os.path.getsize(TEST_LOG_FILE)
    print(f"Log file created successfully - Size: {file_size} bytes")
    
    # line 56-57: Display file contents
    print("\nFile contents:")
    with open(TEST_LOG_FILE, 'r') as f:
        print(f.read())
    
    # line 61-62: Check for newest-first order
    with open(TEST_LOG_FILE, 'r') as f:
        lines = f.readlines()
        if any(lines) and "TEST ENTRY 3" in lines[0] and "TEST ENTRY 1" in lines[-1]:
            print("✅ PASS: Newest-first ordering confirmed!")
        else:
            print(f"❌ FAIL: Newest-first ordering not working correctly!")
            print(f"First line: {lines[0] if lines else 'None'}")
            print(f"Last line: {lines[-1] if lines else 'None'}")
else:
    print(f"❌ ERROR: Log file was not created: {TEST_LOG_FILE}")

print("\nTest complete!")

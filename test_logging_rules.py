#!/usr/bin/env python3
"""
A simple, focused test script that demonstrates the new logging rules:

1. Newest-first log entries with PrependFileHandler
2. Persistent match counter
3. Centered match header formatting
4. Eastern Time Zone for all timestamps
"""
import os
import sys
import time
import logging
from pathlib import Path

# Add this directory to path and force reloading of modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Clear any existing modules to ensure we get fresh instances
for module in list(sys.modules.keys()):
    if module in ('log_config', 'combined_match_summary'):
        del sys.modules[module]

# Import the modules (will trigger fresh setup with new handlers)
from log_config import get_logger, ORCHESTRATOR_LOGGER, configure_logging
from combined_match_summary import write_combined_match_summary, get_combined_summary_logger

# Helper function to print section headers
def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

print("\n🔍 TESTING SPORTS BOT LOGGING RULES 🔍\n")

# 1. Test PrependFileHandler for newest-first entries
print_section("1. Testing PrependFileHandler (newest-first entries)")

# Set up test output file for direct verification
test_log_path = Path(script_dir) / "logs" / "prepend_test.log"
if test_log_path.exists():
    # Remove existing file to start fresh
    os.remove(test_log_path)

# Import our centralized logging facilities
from log_config import get_logger, PrependFileHandler, get_standard_formatter

# Create a specialized test logger using the central factory method
test_logger = get_logger("prepend_test")
test_logger.setLevel(logging.INFO)

# For this special test case, we'll add a dedicated PrependFileHandler
# Note: In normal application code, handlers should only be configured in log_config.py
file_handler = PrependFileHandler(str(test_log_path), when='midnight', backupCount=3)
file_handler.setFormatter(get_standard_formatter())
test_logger.addHandler(file_handler)

# Write entries in sequence - should appear in reverse order in log
print("Writing test entries to prepend_test.log...")
for i in range(1, 6):
    message = f"TEST ENTRY {i} - This should appear BELOW entry {i+1}"
    test_logger.info(message)
    print(f"  ✓ Wrote: {message}")
    time.sleep(1)  # Pause to ensure distinct timestamps

print("\nCheck prepend_test.log - entries should be newest-first (5,4,3,2,1)")
print(f"  File: {test_log_path}")

# 2. Test persistent match counter
print_section("2. Testing persistent match counter")

match_id_file = Path(script_dir) / "match_id.txt"
if match_id_file.exists():
    with open(match_id_file, 'r') as f:
        initial_id = f.read().strip()
    print(f"Initial match ID: {initial_id}")
else:
    print("match_id.txt does not exist yet")

# 3. Test match summary formatting with centered headers
print_section("3. Testing match summary formatting with centered headers")

# Sample match data
test_match = {
    "competition": "Champions League",
    "country": "Europe",
    "home_team": "Real Madrid",
    "away_team": "Bayern Munich",
    "status_id": 3,
    "score": [None, None, [3, 1], [2, 0]],
    "odds": {},
    "environment": {
        "weather": "Clear",
        "temperature": 65,
        "humidity": 52,
        "wind": "Gentle Breeze, 10 mph"
    }
}

# Write a match summary - should use persistent counter and centered headers
print("Writing match summary with centered headers...")
write_combined_match_summary(test_match)

# 4. Verify Eastern Time formatting
print_section("4. Verifying Eastern Time formatting for all logs")
print("All timestamps in logs should be in format: MM/DD/YYYY HH:MM:SS AM/PM EDT")
print("Check the timestamps in the console output and log files")

# Verify match_id.txt was incremented
if match_id_file.exists():
    with open(match_id_file, 'r') as f:
        final_id = f.read().strip()
    print(f"\nMatch ID after test: {final_id}")
    if initial_id and final_id:
        print(f"Match ID incremented by: {int(final_id) - int(initial_id)}")

print("\n📋 VERIFICATION STEPS:")
print("1. Check prepend_test.log - newest entries should be at the top (5,4,3,2,1)")
print("2. Check match_id.txt - should have incremented")
print("3. Check logs/combined_match_summary.logger - new entry should have centered header")
print("4. All timestamps should be in Eastern Time (EDT) format")

print("\n📁 FILES TO CHECK:")
print(f"  - {test_log_path}")
print(f"  - {match_id_file}")
print(f"  - {Path(script_dir) / 'logs' / 'combined_match_summary.logger'}")

print("\n✅ TEST COMPLETE ✅")

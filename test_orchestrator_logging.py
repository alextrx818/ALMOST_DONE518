#!/usr/bin/env python3
"""
Simple test file to verify the logger fixes in orchestrate_complete.py

This test directly examines the file content to ensure that the UnboundLocalError
has been fixed by proper logger initialization.
"""
import sys
import os
from pathlib import Path
import re

# Project root directory
PROJECT_ROOT = Path(__file__).parent

def check_file_for_pattern(file_path, pattern_to_find, pattern_to_avoid=None):
    """Check if a file contains a specific pattern and optionally doesn't contain another."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    found = pattern_to_find in content
    avoided = True if pattern_to_avoid is None else pattern_to_avoid not in content
    
    return found and avoided

def main():
    """Main test function to verify logger fixes."""
    print("Logger Fix Verification Test\n")
    
    # Test 1: Check that orchestrate_complete.py uses centralized logging
    orchestrate_path = PROJECT_ROOT / "orchestrate_complete.py"
    test1 = check_file_for_pattern(
        orchestrate_path,
        "from log_config import get_logger",
        "get_logger(__name__)"
    )
    print(f"✓ Test 1: Centralized logger import: {'PASS' if test1 else 'FAIL'}")
    
    # Test 2: Check that the logger shadowing issue is fixed
    test2 = check_file_for_pattern(
        orchestrate_path,
        "summary_logger = get_summary_logger()",
        "logger = logging.getLogger"
    )
    print(f"\u2713 Test 2: Logger shadowing fixed: {'PASS' if test2 else 'FAIL'}")
    
    # Test 3: Check that the run_complete_pipeline function uses the correct logger
    with open(orchestrate_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Find the run_complete_pipeline function
        match = re.search(r'async def run_complete_pipeline\(\):.*?(?=\n\n# NOTE FOR AI BOT:|$)', content, re.DOTALL)
        if match:
            function_code = match.group(0)
            
            # Remove comments to avoid false positives
            function_code_no_comments = re.sub(r'#.*$', '', function_code, flags=re.MULTILINE)
            
            # Check for bare 'logger' references outside of comments
            bare_logger_refs = re.findall(r'\blogger\b(?!\s*=\s*get_logger)', function_code_no_comments)
            
            # Check that summary_logger is used consistently
            test3 = len(bare_logger_refs) == 0 and 'summary_logger.info' in function_code
            print(f"\u2713 Test 3: run_complete_pipeline uses correct logger: {'PASS' if test3 else 'FAIL'}")
            if not test3:
                print(f"   Found {len(bare_logger_refs)} bare 'logger' references in the function")
        else:
            print("\u2713 Test 3: run_complete_pipeline function not found: FAIL")
            test3 = False
    
    # Overall result
    if test1 and test2 and test3:
        print("\nAll tests PASSED! Logger initialization issues have been fixed.")
        return 0
    else:
        print("\nSome tests FAILED. Issues remain with logger initialization.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

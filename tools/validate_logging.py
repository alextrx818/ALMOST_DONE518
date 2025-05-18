#!/usr/bin/env python3
# line 1-2: Runtime enforcement script for logging system standards

"""
Logging System Validation Tool

This script validates that all loggers in the Football Match Tracking System
comply with the standardized logging configuration rules.

Usage:
    python3 tools/validate_logging.py [--strict]

    --strict: Raise exceptions for non-compliant loggers (default: warnings only)
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our logging configuration
from log_config import get_standard_formatter, PrependFileHandler

def validate_logging_compliance(strict_mode=False):
    """
    # line 27-28: Validate that all loggers conform to the logging system standards
    
    Args:
        strict_mode: If True, raise exceptions for non-compliant loggers
                    If False, log warnings but allow execution to continue
    
    Returns:
        bool: True if all checks pass, False otherwise
    """
    print("🔍 Running Logging System Compliance Check...")
    all_valid = True
    
    # Track validation issues
    validation_issues = []
    
    # Examine all existing loggers
    logger_count = 0
    non_standard_formatters = 0
    missing_handlers = 0
    wrong_handler_types = 0
    
    # line 47-48: Iterate through all existing loggers
    for name, lg in logging.Logger.manager.loggerDict.items():
        if not isinstance(lg, logging.Logger):
            continue
            
        logger_count += 1
        handlers = lg.handlers
        
        # line 55-56: Check 1: Logger should have handlers
        if not handlers:
            validation_issues.append(f"❌ Logger '{name}' has no handlers")
            missing_handlers += 1
            all_valid = False
            continue
            
        # line 62-63: Check 2: At least one handler should have standard formatter
        has_standard_formatter = False
        for handler in handlers:
            # Skip handlers we're not interested in validating (NullHandler etc.)
            if isinstance(handler, logging.NullHandler):
                continue
                
            if hasattr(handler, 'formatter') and handler.formatter:
                fmt_string = getattr(handler.formatter, '_fmt', None)
                
                # line 72-73: Check for our standard format string
                standard_fmt = get_standard_formatter()._fmt
                if fmt_string == standard_fmt:
                    has_standard_formatter = True
                    break
        
        if not has_standard_formatter:
            validation_issues.append(f"❌ Logger '{name}' does not use standard formatter")
            non_standard_formatters += 1
            all_valid = False
        
        # line 83-84: Check 3: File handlers should be PrependFileHandler
        for handler in handlers:
            if isinstance(handler, logging.FileHandler) and not isinstance(handler, PrependFileHandler):
                validation_issues.append(f"❌ Logger '{name}' uses a standard FileHandler instead of PrependFileHandler")
                wrong_handler_types += 1
                all_valid = False
                break
    
    # line 92-93: Report validation results
    print(f"\n📊 Validation Summary:")
    print(f"   Total loggers analyzed: {logger_count}")
    print(f"   Missing handlers: {missing_handlers}")
    print(f"   Non-standard formatters: {non_standard_formatters}")
    print(f"   Wrong handler types: {wrong_handler_types}")
    
    # line 99-100: Print detailed validation issues
    if validation_issues:
        print("\n❗ Validation Issues:")
        for issue in validation_issues:
            print(f"   {issue}")
        
        if strict_mode:
            # line 106-107: In strict mode, raise an exception to prevent execution
            raise RuntimeError("Logging system validation failed. Fix the issues before continuing.")
        else:
            # line 110-111: In non-strict mode, just warn but allow execution to continue
            print("\n⚠️ WARNING: Logging system validation found issues. Fix them to ensure consistent logging.")
    else:
        print("\n✅ All checks passed! Logging system is compliant with standards.")
    
    return all_valid

if __name__ == "__main__":
    # line 119-120: Run the validation when executed directly
    strict = "--strict" in sys.argv
    validate_logging_compliance(strict_mode=strict)

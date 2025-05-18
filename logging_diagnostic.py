#!/usr/bin/env python3
"""
Diagnostic script to inventory all formatters in the logging system
"""
import logging
import logging.config
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our project's logging configuration
from log_config import get_logger

def print_handler_details(logger_name, logger):
    """Print details about a logger and its handlers"""
    print(f"\nLogger: {logger_name}")
    print(f"Level: {logging.getLevelName(logger.level)}")
    print(f"Propagate: {logger.propagate}")
    
    if not hasattr(logger, 'handlers') or len(logger.handlers) == 0:
        print("  No handlers")
        return
        
    print(f"Handlers: {len(logger.handlers)}")
    
    for i, handler in enumerate(logger.handlers):
        handler_type = type(handler).__name__
        handler_level = logging.getLevelName(handler.level)
        print(f"  Handler {i+1}: {handler_type} (level: {handler_level})")
        
        if hasattr(handler, 'baseFilename'):
            print(f"    File: {handler.baseFilename}")
            
        if handler.formatter:
            print(f"    Formatter: {type(handler.formatter).__name__}")
            print(f"      Format: '{handler.formatter._fmt}'")
            print(f"      DateFormat: '{handler.formatter.datefmt or 'None'}'")
            print(f"      Converter: {handler.formatter.converter.__name__ if hasattr(handler.formatter.converter, '__name__') else str(handler.formatter.converter)}")
            
            # Test the formatter directly
            test_record = logging.LogRecord(
                name=logger_name,
                level=logging.INFO,
                pathname=__file__,
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None
            )
            try:
                formatted = handler.formatter.format(test_record)
                print(f"      Sample output: '{formatted[:80] + '...' if len(formatted) > 80 else formatted}'")
            except Exception as e:
                print(f"      ERROR formatting: {e}")

# Print information about the root logger first
print("===== ROOT LOGGER =====")
print_handler_details("root", logging.getLogger())

# Then print details for all named loggers
print("\n===== NAMED LOGGERS =====")
for name, logger in sorted(logging.Logger.manager.loggerDict.items()):
    if not isinstance(logger, logging.Logger):
        # Skip PlaceHolder instances
        continue
    print_handler_details(name, logger)

# Now attempt a couple of test log messages
print("\n===== TEST LOG MESSAGES =====")

# Get our project's logger
test_logger = get_logger("diagnostic_test")
print(f"Test logger: {test_logger.name}, Level: {logging.getLevelName(test_logger.level)}")

# Since we're using the central factory, it should already have appropriate handlers
# But for diagnostic purposes, we'll ensure console output
test_logger.setLevel(logging.DEBUG)

# Try logging a message
try:
    print("Logging test message...")
    test_logger.info("This is a test message from the diagnostic script")
    print("Message logged successfully")
except Exception as e:
    print(f"ERROR logging message: {e}")
    import traceback
    traceback.print_exc()

# Check if we have any StandardTimestampFormatter instances
print("\n===== CUSTOM FORMATTER CLASSES =====")
try:
    from pure_json_fetch_cache import StandardTimestampFormatter as FetchFormatter
    print(f"FetchFormatter defined: {FetchFormatter.__name__}")
    print(f"formatTime method: {FetchFormatter.formatTime.__qualname__}")
except ImportError:
    print("Could not import StandardTimestampFormatter from pure_json_fetch_cache")

try:
    from merge_logic import StandardTimestampFormatter as MergeFormatter
    print(f"MergeFormatter defined: {MergeFormatter.__name__}")
    print(f"formatTime method: {MergeFormatter.formatTime.__qualname__}")
except ImportError:
    print("Could not import StandardTimestampFormatter from merge_logic")

print("\n===== TEST COMPLETE =====")

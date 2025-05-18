#!/usr/bin/env python3
# line 1-2: Test file for ensuring logging system consistency

import logging
import sys
import os
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our logging configuration
from log_config import get_logger, get_summary_logger, PrependFileHandler

def test_all_loggers_have_handlers():
    """
    # line 15-16: Test that all loggers created through the centralized system have handlers
    """
    # Create a few test loggers through our centralized system
    test_loggers = [
        "test_logger1",
        "test_logger2.child",
        "test_component"
    ]
    
    # Get loggers through our centralized system
    loggers = [get_logger(name) for name in test_loggers]
    
    # Check that each logger has at least one handler
    for idx, logger in enumerate(loggers):
        # line 29-30: Check that each logger has at least one handler
        assert logger.handlers, f"Logger {test_loggers[idx]} has no handlers"
        
        # line 33-34: Check that at least one handler is a Console handler
        has_console = any(isinstance(h, logging.StreamHandler) and 
                         not isinstance(h, logging.FileHandler)
                         for h in logger.handlers)
        assert has_console, f"Logger {test_loggers[idx]} has no console handler"
        
        # line 39-40: Check file handlers use PrependFileHandler for newest-first entries
        file_handlers = [h for h in logger.handlers 
                        if isinstance(h, logging.FileHandler)]
        for fh in file_handlers:
            assert isinstance(fh, PrependFileHandler), \
                f"File handler for {test_loggers[idx]} is not PrependFileHandler"

def test_summary_logger_uses_prepend_handler():
    """
    # line 47-48: Test that the summary logger uses PrependFileHandler for newest-first entries
    """
    # Get the summary logger
    # line 52: Update test to use required name parameter
    summary_logger = get_summary_logger("test_summary")
    
    # Verify it has handlers
    assert summary_logger.handlers, "Summary logger has no handlers"
    
    # Check that file handlers are PrependFileHandler
    file_handlers = [h for h in summary_logger.handlers 
                    if isinstance(h, logging.FileHandler)]
    assert file_handlers, "Summary logger has no file handlers"
    
    # line 60-61: Verify all file handlers are PrependFileHandler
    for handler in file_handlers:
        assert isinstance(handler, PrependFileHandler), \
            "Summary logger file handler is not PrependFileHandler"

def test_formatters_are_consistent():
    """
    # line 67-68: Test that all loggers use consistent formatting
    """
    # Create test loggers
    test_loggers = [get_logger(f"test_formatter_{i}") for i in range(3)]
    
    # Add the summary logger
    # line 75: Update test to use required name parameter
    test_loggers.append(get_summary_logger("test_summary"))
    
    # Extract all formatters
    all_formatters = []
    for logger in test_loggers:
        for handler in logger.handlers:
            if handler.formatter:
                # Save formatter format string
                fmt = getattr(handler.formatter, '_fmt', None)
                if fmt:
                    all_formatters.append(fmt)
    
    # line 84-85: We should have multiple formatters with standardized format strings
    assert all_formatters, "No formatters found in test loggers"
    
    # line 87-88: Check that we have consistent formatter formats (allowing for summary formatter)
    standard_formats = [fmt for fmt in all_formatters 
                       if '%(levelname)s' in fmt and '%(name)s' in fmt]
    assert standard_formats, "No standard formatters found"
    
    # Check that standard formats are consistent
    first_format = standard_formats[0]
    for fmt in standard_formats[1:]:
        assert fmt == first_format, \
            f"Inconsistent formatter formats: '{first_format}' vs '{fmt}'"

if __name__ == "__main__":
    # Run the tests directly if this script is executed
    test_all_loggers_have_handlers()
    test_summary_logger_uses_prepend_handler()
    test_formatters_are_consistent()
    print("✅ All logging consistency tests passed")

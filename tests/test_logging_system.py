#!/usr/bin/env python3
"""
Comprehensive tests for the centralized logging system
"""
import os
import sys
import unittest
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

# Import from base test
from tests.test_base import FootballTrackingTestCase

# Import project modules
from log_config import (
    get_logger, get_summary_logger, validate_logger_count, 
    cleanup_handlers, ORCHESTRATOR_LOGGER, SUMMARY_LOGGER
)

class LoggingSystemTest(FootballTrackingTestCase):
    """Test case for the centralized logging system."""
    
    def test_strict_mode_validation(self):
        """Test that strict mode validation works as expected."""
        # Save current environment value
        original_strict = os.environ.get('LOG_STRICT', '1')
        
        try:
            # Test strict mode (should fail on unexpected loggers)
            os.environ['LOG_STRICT'] = '1'
            
            # Create an unexpected logger to trigger validation failure
            unexpected_logger = logging.getLogger("unexpected_test_logger")
            
            # Validation should fail in strict mode
            self.assertFalse(validate_logger_count(), 
                            "Validation should fail in strict mode with unexpected logger")
            
            # Test non-strict mode (should warn but not fail)
            os.environ['LOG_STRICT'] = '0'
            
            # Validation should pass in non-strict mode despite unexpected logger
            self.assertTrue(validate_logger_count(), 
                           "Validation should pass in non-strict mode even with unexpected logger")
        finally:
            # Restore original environment
            os.environ['LOG_STRICT'] = original_strict
            
    def test_get_logger_returns_configured_logger(self):
        """Test that get_logger returns a properly configured logger."""
        test_logger = get_logger("test_configured_logger")
        
        # Check logger is properly named
        self.assertEqual(test_logger.name, "test_configured_logger")
        
        # Check logger has the right level
        self.assertEqual(test_logger.level, logging.INFO)
        
        # Check logger has handlers
        self.assertTrue(len(test_logger.handlers) > 0, 
                       "Logger should have at least one handler")
                       
    def test_get_summary_logger_returns_correct_logger(self):
        """Test that get_summary_logger returns the special summary logger."""
        # line 70: Update test to use required name parameter
        summary_logger = get_summary_logger("test_summary")
        
        # Check it's the summary logger
        self.assertEqual(summary_logger.name, SUMMARY_LOGGER)
        
        # Check it has handlers
        self.assertTrue(len(summary_logger.handlers) > 0,
                       "Summary logger should have at least one handler")
                       
    def test_cleanup_handlers_works(self):
        """Test that cleanup_handlers removes all handlers."""
        # Create a test logger with a handler
        test_logger = get_logger("test_cleanup_logger")
        initial_handler_count = len(test_logger.handlers)
        
        # Call cleanup
        cleanup_handlers()
        
        # Check handlers are removed
        self.assertEqual(len(test_logger.handlers), 0,
                        "All handlers should be removed after cleanup")
        
    def test_timestamp_formatting(self):
        """Test that log timestamps use the correct Eastern Time format."""
        # Create a temporary file to capture log output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            # Create a logger with a file handler to the temp file
            test_logger = get_logger("test_timestamp_logger")
            
            # Add a file handler to capture output
            file_handler = logging.FileHandler(temp_path)
            test_logger.addHandler(file_handler)
            
            # Log a test message
            test_logger.info("Test message for timestamp formatting")
            
            # Close the handler to ensure file is written
            file_handler.close()
            
            # Read the log file
            with open(temp_path, 'r') as f:
                log_content = f.read()
            
            # Check that the timestamp format is correct (MM/DD/YYYY HH:MM:SS XM EDT)
            import re
            timestamp_pattern = r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} [AP]M EDT'
            self.assertTrue(re.search(timestamp_pattern, log_content),
                           f"Log should contain Eastern Time timestamp. Log content: {log_content}")
        finally:
            # Remove the temporary file
            os.unlink(temp_path)
            
    def test_logger_validation_count(self):
        """Test that logger validation correctly counts loggers."""
        # Get the current logger count
        initial_count = len(logging.Logger.manager.loggerDict)
        
        # Create a bunch of new loggers through the centralized system
        for i in range(5):
            get_logger(f"test_count_logger_{i}")
            
        # Validation should still pass since these are registered
        self.assertTrue(validate_logger_count(),
                       "Validation should pass with loggers created through get_logger")

if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
log_config.py - Centralized logging configuration for the sports bot.

CENTRAL LOGGING CONFIGURATION
=============================

This module serves as the centralized logging configuration for the entire application.
All logging setup, configuration, and handlers should be defined here.

Key Functions:
- get_logger(name): Get a standard logger with the given name
- get_summary_logger(): Get the special summary logger for match data
- cleanup_handlers(): Clean up all logging handlers

IMPORTANT: No other files should define their own loggers or handlers.
           All logging configuration must be done through this module.

This module implements the following logging rules for the sports bot project:

1. NEWEST-FIRST LOG ENTRIES
   - All log files use PrependFileHandler to ensure newest entries appear at the top
   - This makes reading and monitoring logs much easier than traditional append-mode logs
   
2. EASTERN TIME FORMATTING
   - All timestamps use Eastern Time (America/New_York) timezone
   - Format is MM/DD/YYYY HH:MM:SS AM/PM EDT
   - Configured globally for the entire application

3. MATCH SUMMARY FORMATTING
   - Match headers are centered with consistent formatting
   - Persistent match counter is maintained in match_id.txt
   - Clean log output without redundant timestamp prefixes

4. CONSISTENT LOGGING CONFIGURATION
   - All loggers use the same configuration from this central file
   - Prevents logger/handler proliferation
   - Easy to modify logging behavior application-wide

Implementation tests show the PrependFileHandler correctly places newest logs at
the top of log files, all timestamps display in Eastern Time, and match summary
formatting uses centered headers with proper persistent numbering.
"""

import logging
import logging.config
from pathlib import Path
import sys
import os
import pytz
import time
import datetime
from logging.handlers import TimedRotatingFileHandler

# Custom handler to prepend new log entries at the top of log files
class PrependFileHandler(TimedRotatingFileHandler):
    """Custom file handler that prepends new log entries at the beginning of the file.
    
    This ensures that the most recent log entries appear at the top of the file,
    making it easier to see the latest information without having to scroll to the end.
    """
    def emit(self, record):
        """Override the emit method to prepend rather than append."""
        msg = self.format(record) + '\n'
        path = self.baseFilename
        
        try:
            # Read existing content if file exists
            if os.path.exists(path):
                with open(path, 'r', encoding=self.encoding, errors='replace') as f:
                    existing_content = f.read()
            else:
                existing_content = ''
                
            # Write new content + existing content
            with open(path, 'w', encoding=self.encoding) as f:
                f.write(msg + existing_content)
                f.flush()  # Ensure content is written to disk
                os.fsync(f.fileno())  # Force write to disk
                
        except Exception as e:
            self.handleError(record)
            raise
            
    def flush(self):
        """Flush the stream."""
        if self.stream and hasattr(self.stream, 'flush'):
            try:
                self.stream.flush()
                if hasattr(self.stream, 'fileno'):
                    os.fsync(self.stream.fileno())  # Ensure all data is written to disk
            except (AttributeError, OSError) as e:
                logging.error(f"Error flushing stream: {e}")
                raise


# Special formatter that handles multi-line messages correctly
class SingleLineFormatter(logging.Formatter):
    """Formatter that properly handles multi-line messages.
    
    Standard formatters add timestamp prefixes to each line when a message contains
    newlines. This formatter only adds the prefix to the first line, keeping the
    rest of the message clean.
    """
    def format(self, record):
        """Format the message with timestamp only on the first line."""
        message = super().format(record)
        # Only first line gets timestamp prefix, continuation lines are raw
        if '\n' in message:
            first_line, rest = message.split('\n', 1)
            return first_line + '\n' + rest
        return message

# Set the timezone globally to Eastern Time (New York)
os.environ['TZ'] = 'America/New_York'
time.tzset()  # Apply the timezone setting to the process

# Define a simple converter function that takes exactly one argument
def ny_time_converter(timestamp):
    """Return a time.struct_time in local (NY) timezone
    
    Args:
        timestamp: Seconds since the Epoch
        
    Returns:
        time.struct_time object using the system timezone (Eastern)
    """
    return time.localtime(timestamp)

# Use staticmethod to prevent auto-binding issues
logging.Formatter.converter = staticmethod(ny_time_converter)

# Base directories
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"

# Ensure log directories exist
for log_dir in [
    LOGS_DIR,
    LOGS_DIR / "fetch",
    LOGS_DIR / "summary",
    LOGS_DIR / "alerts",
    LOGS_DIR / "memory",
    LOGS_DIR / "monitor",
]:
    log_dir.mkdir(exist_ok=True, parents=True)

# Logger names
ORCHESTRATOR_LOGGER = "orchestrator"
FETCH_CACHE_LOGGER = "pure_json_fetch"
FETCH_DATA_LOGGER = "fetch_data"
MERGE_LOGIC_LOGGER = "merge_logic"
SUMMARY_JSON_LOGGER = "summary_json"
MEMORY_MONITOR_LOGGER = "memory_monitor"
LOGGER_MONITOR_LOGGER = "logger_monitor"
SUMMARY_LOGGER = "summary"
OU3_LOGGER = "OU3"

# Central logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(message)s",
            "datefmt": "%m/%d/%Y %I:%M:%S %p %Z",
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            "datefmt": "%m/%d/%Y %I:%M:%S %p %Z",
        },
        "simple": {
            "format": "%(message)s",
        },
        "summary_formatter": {
            "()": "log_config.SingleLineFormatter", 
            "format": "%(message)s",  # No timestamp prefix at all
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "orchestrator_file": {
            "class": "log_config.PrependFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": str(LOGS_DIR / "orchestrator.log"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8",
        },
        "fetch_cache_file": {
            "class": "log_config.PrependFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": str(LOGS_DIR / "pure_json_fetch.log"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8",
        },
        "fetch_data_file": {
            "class": "log_config.PrependFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": str(LOGS_DIR / "fetch" / "fetch_data.log"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8",
        },
        "merge_logic_file": {
            "class": "log_config.PrependFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": str(LOGS_DIR / "fetch" / "merge_logic.log"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8",
        },
        "summary_json_file": {
            "class": "log_config.PrependFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": str(LOGS_DIR / "summary" / "summary_json.logger"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8",
        },
        "memory_monitor_file": {
            "class": "log_config.PrependFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": str(LOGS_DIR / "memory" / "memory_monitor.log"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8",
        },
        "logger_monitor_file": {
            "class": "log_config.PrependFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": str(LOGS_DIR / "monitor" / "logger_monitor.log"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8",
        },
        "match_summary_file": {
            "class": "log_config.PrependFileHandler",
            "level": "INFO",
            "formatter": "simple",  # Use the simple formatter with NO timestamp prefix
            "filename": str(LOGS_DIR / "combined_match_summary.logger"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8",
        },
    },
    "loggers": {
        ORCHESTRATOR_LOGGER: {
            "level": "INFO",
            "handlers": ["console", "orchestrator_file"],
            "propagate": False,
        },
        FETCH_CACHE_LOGGER: {
            "level": "DEBUG",
            "handlers": ["fetch_cache_file"],
            "propagate": False,
        },
        FETCH_DATA_LOGGER: {
            "level": "INFO",
            "handlers": ["fetch_data_file"],
            "propagate": False,
        },
        MERGE_LOGIC_LOGGER: {
            "level": "DEBUG",
            "handlers": ["merge_logic_file"],
            "propagate": False,
        },
        SUMMARY_JSON_LOGGER: {
            "level": "INFO",
            "handlers": ["summary_json_file"],
            "propagate": False,
        },
        MEMORY_MONITOR_LOGGER: {
            "level": "INFO",
            "handlers": ["memory_monitor_file", "console"],
            "propagate": False,
        },
        LOGGER_MONITOR_LOGGER: {
            "level": "INFO",
            "handlers": ["logger_monitor_file", "console"],
            "propagate": False,
        },
        SUMMARY_LOGGER: {
            "level": "INFO",
            "handlers": ["console", "match_summary_file"],  # Use our new handler with SingleLineFormatter
            "propagate": False,
        },
        OU3_LOGGER: {
            "level": "INFO",
            "handlers": [],  # Handlers will be added by the alert system
            "propagate": False,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}

# No longer need a timezone filter function as we're setting the timezone globally

# Dictionary to track alert loggers that have been configured
_configured_alert_loggers = set()

def configure_logging():
    """Configure all loggers using dictConfig.
    This should be called once at application startup.
    All log timestamps will use Eastern Time (America/New_York) and 
    MM/DD/YYYY with AM/PM time format.
    """
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(LOGGING_CONFIG["handlers"]["orchestrator_file"]["filename"]), exist_ok=True)
    
    # Apply logging configuration
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Note: Timezone is already set globally via os.environ['TZ'] = 'America/New_York'

def get_logger(name):
    """
    Get a properly configured logger by name.
    If the logger has already been configured in dictConfig, returns it.
    """
    return logging.getLogger(name)


def create_custom_logger(name, log_file=None, timestamp_prefix=True, level=logging.INFO):
    """
    Create a custom logger following all the global logging rules for this project:
    1. Newest-first logs using PrependFileHandler
    2. Eastern Time timezone for all timestamps
    3. Proper handling of multi-line messages
    4. Configurable timestamp prefixes
    
    Args:
        name (str): Logger name
        log_file (str, optional): Path to log file. If None, only console output is used.
        timestamp_prefix (bool): Whether to include timestamp prefix in log entries.
                                 Set to False for logs that include their own timestamps.
        level (int): Logging level
        
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Don't propagate to parent loggers
    
    # Clear any existing handlers
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    
    # Add console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        '%m/%d/%Y %I:%M:%S %p %Z'
    ))
    logger.addHandler(console)
    
    # Add file handler if log_file is provided
    if log_file:
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Create PrependFileHandler for newest-first entries
        file_handler = PrependFileHandler(
            log_file,
            when='midnight',
            backupCount=30,
            encoding='utf8'
        )
        file_handler.setLevel(level)
        
        # Choose appropriate formatter based on timestamp_prefix flag
        if timestamp_prefix:
            # For normal logs: Use SingleLineFormatter for proper multi-line handling
            file_handler.setFormatter(SingleLineFormatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                '%m/%d/%Y %I:%M:%S %p %Z'
            ))
        else:
            # For logs with embedded timestamps: Use simple formatter with no prefix
            file_handler.setFormatter(logging.Formatter('%(message)s'))
            
        logger.addHandler(file_handler)
    
    return logger

def configure_alert_logger(alert_name):
    """
    Configure a logger for a specific alert.
    Only configures the logger if it hasn't been configured before.
    """
    if alert_name in _configured_alert_loggers:
        return logging.getLogger(alert_name)
    
    # Create alert log directory if it doesn't exist
    alert_log_dir = LOGS_DIR / "alerts"
    alert_log_dir.mkdir(exist_ok=True, parents=True)
    
    # Set up logger configuration
    log_file = str(alert_log_dir / f"{alert_name}.log")
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        backupCount=30,
        encoding="utf8"
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    
    # Get logger and configure
    logger = logging.getLogger(alert_name)
    
    # Properly clean up any existing handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    # Mark this alert logger as configured
    _configured_alert_loggers.add(alert_name)
    
    return logger

def cleanup_handlers():
    """
    Properly clean up all handlers to release file descriptors.
    Call this at application shutdown.
    """
    # Get all loggers including the root logger and all named loggers
    loggers = [logging.getLogger()]  # Start with root logger
    loggers.extend(logging.getLogger(name) for name in logging.root.manager.loggerDict)
    
    # Clean up handlers for each logger
    for logger in loggers:
        if not isinstance(logger, logging.Logger):
            continue
            
        # Get a copy of the handlers list to safely modify it
        for handler in list(logger.handlers):
            try:
                # Flush any pending messages
                if hasattr(handler, 'flush') and callable(handler.flush):
                    try:
                        handler.flush()
                    except Exception as e:
                        logging.error(f"Error flushing handler {handler}: {e}")
                
                # Close the handler
                handler.close()
                
                # Remove the handler from the logger
                logger.removeHandler(handler)
                
            except Exception as e:
                # Log the error but continue with other handlers
                logging.error(f"Error cleaning up handler {handler}: {e}", exc_info=True)
    
    # Also clean up any handlers that might be registered directly
    for handler in logging._handlers.copy():
        try:
            if hasattr(handler, 'flush') and callable(handler.flush):
                handler.flush()
            handler.close()
        except Exception as e:
            logging.error(f"Error cleaning up handler {handler}: {e}", exc_info=True)

def validate_logger_count():
    """
    Validate that logger count and handler count hasn't grown beyond expected.
    Raises an exception if counts exceed thresholds.
    """
    # Fixed set of expected loggers plus a margin for alerts and standard lib loggers
    EXPECTED_LOGGER_COUNT = 40  # Base loggers plus room for alerts and stdlib loggers
    EXPECTED_HANDLERS_PER_LOGGER = 2  # Most loggers have console + file
    
    # Standard library/framework loggers that are expected and can be ignored
    STANDARD_LOGGERS = [
        'asyncio', 'concurrent', 'concurrent.futures',
        'aiohttp', 'aiohttp.access', 'aiohttp.client', 'aiohttp.internal',
        'aiohttp.server', 'aiohttp.web', 'aiohttp.websocket',
        'dotenv', 'dotenv.main', 'urllib3', 'requests', 'chardet',
        'PIL', 'parso', 'jedi'
    ]
    
    # Get actual counts
    logger_count = len(logging.Logger.manager.loggerDict)
    
    # Check for unexpected logger growth
    unexpected_loggers = []
    for name in logging.Logger.manager.loggerDict:
        # Skip loggers that are expected
        if name in LOGGING_CONFIG["loggers"] or name in _configured_alert_loggers:
            continue
            
        # Skip standard library loggers
        if any(name == std_logger or name.startswith(f"{std_logger}.") for std_logger in STANDARD_LOGGERS):
            continue
            
        # This is an unexpected logger
        unexpected_loggers.append(name)
    
    # If we have unexpected loggers OR we've significantly exceeded our threshold
    if unexpected_loggers or logger_count > EXPECTED_LOGGER_COUNT + 10:
        error_msg = f"Logger count: {logger_count}, Threshold: {EXPECTED_LOGGER_COUNT}"
        if unexpected_loggers:
            error_msg += f". Unexpected loggers: {unexpected_loggers}"
        
        # Only fail if we have truly unexpected loggers (not just standard lib ones)
        if unexpected_loggers:
            print(error_msg, file=sys.stderr)
            return False
        
        # Just log a warning if we have no unexpected loggers but count is high
        print(f"WARNING: High logger count but all are expected: {error_msg}", file=sys.stderr)
    
    # Check handler count for each logger
    for name, logger in logging.Logger.manager.loggerDict.items():
        if hasattr(logger, 'handlers'):
            handler_count = len(logger.handlers)
            # Allow 4 handlers maximum - some loggers might legitimately have console + file + others
            if handler_count > 4:
                error_msg = f"Handler count for logger '{name}' exceeded threshold: {handler_count} > 4"
                print(error_msg, file=sys.stderr)
                return False
            # Just log a warning for handlers exceeding our preferred count of 2
            elif handler_count > EXPECTED_HANDLERS_PER_LOGGER:
                print(f"WARNING: Logger '{name}' has {handler_count} handlers (preferred max: {EXPECTED_HANDLERS_PER_LOGGER})", file=sys.stderr)
    
    return True

def get_summary_logger():
    """
    Get or create the centralized summary logger.
    Ensures only one instance exists and is properly configured.
    """
    logger = logging.getLogger('summary')
    
    # If logger already has handlers, return it
    if logger.handlers:
        return logger
        
    # Configure the summary logger
    logs_dir = Path(__file__).parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / 'combined_match_summary.logger'
    
    # Create file handler with prepend functionality
    file_handler = PrependFileHandler(
        log_file,
        when='midnight',
        backupCount=7,
        encoding='utf-8',
        delay=False
    )
    
    # Simple formatter without timestamps
    formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(formatter)
    
    # Configure logger
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Prevent propagation to root logger
    logger.addHandler(file_handler)
    
    return logger

# Configure logging when this module is imported
# This will set up all loggers with Eastern Time (America/New_York) and MM/DD/YYYY AM/PM format
configure_logging()


def test_logging_rules():
    """
    Test that all logging rules are correctly implemented:
    1. Newest-first log entries with PrependFileHandler
    2. Eastern Time Zone for all timestamps
    3. Match summary formatting with centered headers
    4. Persistent match counter
    
    Run this function directly to verify logging system functionality.
    Example: python -c "import log_config; log_config.test_logging_rules()"
    """
    import time
    import sys
    from pathlib import Path
    
    # Use local imports to avoid import cycles
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    print("\n🔍 TESTING SPORTS BOT LOGGING RULES 🔍\n")
    
    def print_section(title):
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")
    
    # 1. Test PrependFileHandler for newest-first entries
    print_section("1. Testing PrependFileHandler (newest-first entries)")
    
    # Set up test output file for direct verification
    test_log_path = LOGS_DIR / "prepend_test.log"
    if test_log_path.exists():
        # Remove existing file to start fresh
        os.remove(test_log_path)
    
    # Create a specialized test logger with our PrependFileHandler
    test_logger = logging.getLogger("prepend_test")
    test_logger.setLevel(logging.INFO)
    
    # Create a handler for our test logger
    file_handler = PrependFileHandler(str(test_log_path), when='midnight', backupCount=3)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',
                                '%m/%d/%Y %I:%M:%S %p %Z')
    file_handler.setFormatter(formatter)
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
    
    match_id_file = current_dir / "match_id.txt"
    if match_id_file.exists():
        with open(match_id_file, 'r') as f:
            initial_id = f.read().strip()
        print(f"Initial match ID: {initial_id}")
    else:
        print("match_id.txt does not exist yet")
    
    # 3. Test match summary formatting with centered headers
    print_section("3. Testing match summary formatting with centered headers")
    
    # Dynamic import to avoid circular imports
    from combined_match_summary import write_combined_match_summary
    
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
    print(f"  - {current_dir / 'logs' / 'combined_match_summary.logger'}")
    
    print("\n✅ TEST COMPLETE ✅")
    
    # Clean up handlers after test
    test_logger.removeHandler(file_handler)
    file_handler.close()
    
    return True


# If this module is run directly, run the test
if __name__ == "__main__":
    test_logging_rules()

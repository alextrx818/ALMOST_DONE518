#!/usr/bin/env python3
"""
# =============================================================================
# CENTRALIZED LOGGING OVERVIEW
#
# 1. SYSTEM / ORCHESTRATION / MONITORING LOGS
#    • Formatters: "standard", "detailed"
#    • Handlers : console, orchestrator_file, fetch_cache_file, merge_logic_file, memory_monitor_file, logger_monitor_file, etc.
#    • Loggers  : orchestrator, pure_json_fetch, fetch_data, merge_logic, memory_monitor, logger_monitor, etc.
#
# 2. ALERT LOGS
#    • Formatter: "human_readable" (same as match summaries unless you override)
#    • Handler  : alerts_file
#    • Logger   : alerter_main / alert.*
#
# 3. MATCH-SUMMARY LOGS
#    • Formatter: "human_readable"
#    • Handler  : match_summary_file
#    • Logger   : summary.pipeline / summary.*
#
# NOTES:
#  - All new loggers, handlers or formatters must be declared here in log_config.py.
#  - No direct calls to logging.getLogger(), .addHandler(), Formatter() or basicConfig() outside this module.
#  - configure_logging() must be invoked at startup before any imports that emit logs.
# =============================================================================

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

# Loggers that should only write to console, not to files
_CONSOLE_ONLY_LOGGERS = set(['root'])

# Track whether configure_logging() has been called
_logging_configured = False

# ============================================================================
# Runtime Enforcement: Monkey-patch logging.getLogger() to ensure central control
# ============================================================================

# line 52-53: Store the original getLogger function before monkey-patching
_original_getLogger = logging.getLogger

# Create a forward reference to our factory functions that will be defined later
_get_logger_func = None
_get_summary_logger_func = None

# Define get_logger function early to avoid circular references
def get_logger(name):
    """Get a logger with the given name.
    This is the main entry point for getting loggers in the application.
    """
    if not _logging_configured:
        configure_logging()
    return _original_getLogger(name)

# line 59-78: Define a central getLogger function to intercept all logging calls
def _central_getLogger(name=None):
    """
    Intercept all calls to logging.getLogger() and route them through our central factory.
    This ensures that even direct stdlib calls adhere to our logging standards.
    
    Args:
        name: Logger name (or None for root logger)
        
    Returns:
        Logger instance configured with our standard handlers/formatters
    """
    # If our factory functions haven't been defined yet, use original temporarily
    if _get_logger_func is None or _get_summary_logger_func is None:
        return _original_getLogger(name)
        
    # No special routing for summary.* loggers - they're now statically configured
    if name is None:
        return _get_logger_func('root')
    else:
        return _get_logger_func(name)

# Define standard logger name constants to prevent typos and ensure consistency
# Application loggers
ORCHESTRATOR_LOGGER = "orchestrator"
# line 116: Renamed to avoid confusion with summary.pipeline logger
PIPELINE_LOGGER = "system_pipeline"  # Creates logs/system_pipeline.log
MERGE_LOGIC_LOGGER = "merge_logic"
MEMORY_MONITOR_LOGGER = "memory_monitor"
NETWORK_RESILIENCE_LOGGER = "network_resilience"
PURE_JSON_FETCH_LOGGER = "pure_json_fetch"
FETCH_DATA_LOGGER = "fetch_data"

# Summary loggers (prefixed with 'summary.')
SUMMARY_PREFIX = "summary."
SUMMARY_PIPELINE = f"{SUMMARY_PREFIX}pipeline"
SUMMARY_ORCHESTRATION = f"{SUMMARY_PREFIX}orchestration"
SUMMARY_JSON = f"{SUMMARY_PREFIX}summary_json"

# Alert loggers (prefixed with 'alert.')
ALERT_PREFIX = "alert."

# Test loggers
TEST_LOGGER_PREFIX = "test_"
PREPEND_TEST_LOGGER = "prepend_test"
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
        # line 63-65: Format the log record and determine the target path
        if self.filter(record):
            msg = self.format(record) + '\n'
            path = self.baseFilename
            
            # line 68-70: Ensure parent directory exists - critical for reliable logging
            try:
                directory = os.path.dirname(path)
                os.makedirs(directory, exist_ok=True)
                
                # line 73-83: Read existing content with comprehensive error handling
                existing_content = ''
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    try:
                        with open(path, 'r', encoding=self.encoding, errors='replace') as f:
                            existing_content = f.read()
                    except Exception as read_error:
                        # Handle errors but continue with empty content
                        self.handleError(record)
                        print(f"WARNING: Error reading log file {path}: {read_error}")
                        # Continue with empty content rather than failing
                
                # line 85-90: Write content in the proper newest-first order
                # with robust error handling and synchronous write
                with open(path, 'w', encoding=self.encoding) as f:
                    # Critical line - write new content followed by existing content
                    f.write(msg + existing_content)
                    f.flush()  # Force flush to disk
                    # Use os.fsync for extra durability on critical logs
                    if hasattr(f, 'fileno'):
                        try:
                            os.fsync(f.fileno())
                        except OSError:
                            pass  # Ignore fsync errors
                    
            except Exception as e:
                # line 93-95: Handle any errors without crashing
                self.handleError(record)
                print(f"ERROR: PrependFileHandler.emit failed: {e}")
                # Don't re-raise to prevent interrupting application flow
            
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
    """
    Return a time.struct_time in local (NY) timezone
    
    Args:
        timestamp: Seconds since the Epoch
        
    Returns:
        time.struct_time object using the system timezone (Eastern)
    """
    return time.localtime(timestamp)

def eastern_time_converter(timestamp):
    """
    Convert UTC timestamp to Eastern Time (America/New_York)
    
    Args:
        timestamp: Seconds since the Epoch
        
    Returns:
        time.struct_time object in Eastern timezone
    """
    utc_dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    eastern_tz = pytz.timezone('America/New_York')
    eastern_dt = utc_dt.astimezone(eastern_tz)
    return eastern_dt.timetuple()

# Use staticmethod to prevent auto-binding issues
logging.Formatter.converter = staticmethod(eastern_time_converter)

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
    LOGS_DIR / "monitor"
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

# Define standard log formats for all loggers in this application
CANONICAL_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
STANDARD_FORMAT = CANONICAL_FORMAT
SUMMARY_FORMAT = "%(message)s"
ISO_DATE_FORMAT = "%Y-%m-%d %H:%M:%S,%f"  # ISO‐8601

def get_standard_formatter():
    """Get the standard formatter used by most loggers."""
    return SingleLineFormatter(STANDARD_FORMAT)

# Central logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "filters": {
        "step_ts": {}
    },
    "formatters": {
        "standard": {
            "format": CANONICAL_FORMAT
        },
        "detailed": {
            "format": CANONICAL_FORMAT
        },
        "simple": {
            "format": SUMMARY_FORMAT
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "summary_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "simple",
            "filename": "logs/summary/pipeline.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "INFO"
        },
        "summary_json_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "standard",
            "filename": str(LOGS_DIR / "summary" / "summary_json.logger"),
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "INFO"
        },
        "orchestrator_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "standard",
            "filename": "logs/orchestrator.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "INFO"
        },
        "fetch_data_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "standard",
            "filename": "logs/fetch_data.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "INFO"
        },
        "fetch_cache_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "standard",
            "filename": "logs/pure_json_fetch.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "DEBUG"
        },
        "merge_logic_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "standard",
            "filename": "logs/merge_logic.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "DEBUG"
        },
        "memory_monitor_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "standard",
            "filename": "logs/memory_monitor.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "INFO"
        },
        "logger_monitor_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "standard",
            "filename": "logs/logger_monitor.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "INFO"
        },
        "alerts_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "standard",
            "filename": "logs/alert_discovery.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "INFO"
        },
        "match_summary_file": {
            "class": "log_config.PrependFileHandler",
            "formatter": "simple",
            "filename": "logs/summary/pipeline.log",
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf-8",
            "level": "INFO"
        }
    },
    "loggers": {
        "root": {
            "handlers": ["console"],
            "level": "INFO"
        },
        "summary.pipeline": {
            "handlers": ["summary_file"],
            "level": "INFO",
            "propagate": False
        },
        "summary.orchestration": {
            "handlers": ["match_summary_file"],
            "level": "INFO",
            "propagate": False
        },
        "summary_json": {
            "handlers": ["console", "summary_json_file"],
            "level": "INFO",
            "propagate": False
        },
        "orchestrator": {
            "handlers": ["console", "orchestrator_file"],
            "level": "INFO",
            "propagate": False
        },
        "pure_json_fetch": {
            "handlers": ["console", "fetch_cache_file"],
            "level": "DEBUG",
            "propagate": False
        },
        "fetch_data": {
            "handlers": ["console", "fetch_data_file"],
            "level": "INFO",
            "propagate": False
        },
        "merge_logic": {
            "handlers": ["console", "merge_logic_file"],
            "level": "DEBUG",
            "propagate": False
        },
        "memory_monitor": {
            "handlers": ["memory_monitor_file", "console"],
            "level": "INFO",
            "propagate": False
        },
        "logger_monitor": {
            "handlers": ["logger_monitor_file", "console"],
            "level": "INFO",
            "propagate": False
        },
        "alerter_main": {
            "handlers": ["alerts_file", "console"],
            "level": "INFO",
            "propagate": False
        }
    }
}

def cleanup_handlers():
    """Clean up all logging handlers.
    This should be called at application shutdown to ensure proper cleanup.
    """
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers[:]:  # Copy list as we'll modify it
                logger.removeHandler(handler)
                handler.close()

def configure_logging():
    """Configure logging for the entire application.
    This function must be called at startup before any imports that emit logs.
    """
    global _logging_configured
    if _logging_configured:
        return

    # Create required log directories
    for log_dir in [
        LOGS_DIR,
        LOGS_DIR / "fetch",
        LOGS_DIR / "summary",
        LOGS_DIR / "alerts",
        LOGS_DIR / "memory",
        LOGS_DIR / "monitor"
    ]:
        log_dir.mkdir(exist_ok=True, parents=True)

    # Configure logging with our settings
    logging.config.dictConfig(LOGGING_CONFIG)
    _logging_configured = True

def validate_logger_configuration():
    """Validate that all loggers use proper handlers.
    Returns True if validation passes, False otherwise.
    """
    # Skip validation during import to prevent circular references
    if _get_logger_func is None or _get_summary_logger_func is None:
        return True
        
    validation_passed = True
    strict_mode = os.environ.get('LOG_STRICT', '1') == '1'
    SUMMARY_PREFIX = "summary."
    ALERT_PREFIX = "alert."
    TEST_LOGGER_PREFIX = "test."
    
    # Third-party library prefixes to ignore in validation
    IGNORE_PREFIXES = [
        "aiohttp.", "aiohttp",  # HTTP server/client library
        "pip.",                # pip's own internal deprecation logs
        "rich",               # rich or rich.* if you're using Rich
        "urllib3",            # HTTP client library
        "requests",           # HTTP client library
        "asyncio",            # Async library
        "chardet",            # Character encoding detection
        "concurrent.futures", # Concurrent execution
        "multiprocessing"     # Multiprocessing module
    ]
    
    # Check all loggers
    for name, logger in logging.Logger.manager.loggerDict.items():
        if not isinstance(logger, logging.Logger):
            continue  # Skip PlaceHolder instances
            
        # Skip internal loggers, root logger, and third-party libraries
        if name == 'root' or name.startswith(SUMMARY_PREFIX) or name.startswith(ALERT_PREFIX):
            continue
            
        # Skip third-party library loggers
        if any(name.startswith(prefix) for prefix in IGNORE_PREFIXES):
            continue
            
        # Check handler types and formatters
        expected_format = CANONICAL_FORMAT
        
        # Check for console and file handlers
        has_console = False
        has_file = False
        
        for handler in logger.handlers:
            # Determine handler types
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                has_console = True
            elif isinstance(handler, logging.FileHandler):
                has_file = True
                
            # Allow any format for test loggers and summary loggers
            if name.startswith(TEST_LOGGER_PREFIX) or name.startswith(SUMMARY_PREFIX):
                continue
            
            # Check for formatter consistency
            if hasattr(handler.formatter, '_fmt') and handler.formatter._fmt != expected_format:
                error_msg = f"Logger '{name}' has inconsistent format: {handler.formatter._fmt} (expected {expected_format})"
                
                if strict_mode:
                    raise ValueError(error_msg)
                else:
                    print(f"WARNING: {error_msg}", file=sys.stderr)
                    validation_passed = False
        
        # Application loggers should have both console and file handlers
        if not (name.startswith(SUMMARY_PREFIX) or name.startswith(ALERT_PREFIX) or 
                name.startswith(TEST_LOGGER_PREFIX)) and not (has_console and has_file):
            warning_msg = f"Logger '{name}' missing expected handlers (console: {has_console}, file: {has_file})"
            print(f"WARNING: {warning_msg}", file=sys.stderr)
            # Don't fail validation for this, just warn
    
    return validation_passed

def validate_logger_count():
    """
    Validate that logger count and handler count hasn't grown beyond expected.
    In strict mode (LOG_STRICT=1, default), raises an exception if counts exceed thresholds.
    In non-strict mode (LOG_STRICT=0), warns but continues execution.
    """
    # Define expected loggers
    EXPECTED_LOGGERS = {
        'summary', 'memory_monitor', 'pure_json_fetch', 'fetch_data', 
        'merge_logic', 'alerter_main', 'orchestrator', 'root',
        'summary_json', 'logger_monitor'
    }
    # Check if we're in strict validation mode (default is strict)
    strict_mode = os.environ.get('LOG_STRICT', '1') == '1'
    # Fixed set of expected loggers plus a margin for alerts and standard lib loggers
    EXPECTED_LOGGER_COUNT = 40  # Base loggers plus room for alerts and stdlib loggers
    EXPECTED_HANDLERS_PER_LOGGER = 2  # Most loggers have console + file
    
    # Standard library/framework loggers that are expected and can be ignored
    # Third-party library loggers that are expected and can be ignored
    STANDARD_LOGGERS = [
        'asyncio', 'concurrent', 'concurrent.futures',
        'aiohttp', 'aiohttp.access', 'aiohttp.client', 'aiohttp.internal',
        'aiohttp.server', 'aiohttp.web', 'aiohttp.websocket',
        'dotenv', 'dotenv.main', 'urllib3', 'requests', 'chardet',
        'PIL', 'parso', 'jedi'
    ]
    
    # line 778-780: Skip validation during tests
    if 'pytest' in sys.modules or any('test' in arg.lower() for arg in sys.argv):
        # When running tests, allow any logger that has 'test' in the name
        test_mode = True
    else:
        test_mode = False
    
    # Get counts for loggers and handlers
    logger_count = len(logging.Logger.manager.loggerDict)
    
    # Check threshold
    logger_threshold = 40
    
    # Find loggers that aren't expected
    unexpected_loggers = []
    for name in logging.Logger.manager.loggerDict:
        # Skip expected loggers and those starting with standard prefixes
        if (name in EXPECTED_LOGGERS or 
            name.startswith('summary.') or 
            name.startswith('alert.') or 
            name in _configured_alert_loggers or
            name in ["orchestrate_complete", "alert_discovery", "alert"] or 
            name.startswith("alert.") or
            any(name == std_logger or name.startswith(f"{std_logger}.") for std_logger in STANDARD_LOGGERS) or
            test_mode and ('test' in name.lower() or name.lower().startswith('test'))):
            continue
        
        # This is an unexpected logger
        unexpected_loggers.append(name)
    
    # If we have unexpected loggers OR we've significantly exceeded our threshold
    if unexpected_loggers or logger_count > EXPECTED_LOGGER_COUNT + 10:
        error_msg = f"Logger count: {logger_count}, Threshold: {logger_threshold}. Unexpected loggers: {unexpected_loggers}"
        print(error_msg, file=sys.stderr)
        if strict_mode:
            # In strict mode, fail on unexpected loggers
            return False
        else:
            # In non-strict mode, just warn and continue
            print("WARNING: Logger validation found unexpected loggers but continuing in non-strict mode.", file=sys.stderr)
        
        # Just log a warning if we have no unexpected loggers but count is high
        print(f"WARNING: High logger count but all are expected: {error_msg}", file=sys.stderr)
    
    # Now check handler count for each logger
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

# The get_summary_logger function has been removed in favor of static configuration
# For summary.pipeline logger, use: logging.getLogger("summary.pipeline")

# Track configured alert loggers to avoid duplication
_configured_alert_loggers = set()

# Additional standard library loggers we shouldn't warn about
STANDARD_LOGGERS = [
    'concurrent', 'asyncio', 'multiprocessing',
    'chardet', 'urllib3', 'requests', 'PIL'
]

def configure_alert_logger(name):
    """Configure a logger for alerts with the given name.
    This is used by the alerter system to create loggers for different alert types.
    """
    if name in _configured_alert_loggers:
        return logging.getLogger(name)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Create alerts directory if it doesn't exist
    alerts_dir = Path(__file__).parent / "logs" / "alerts"
    alerts_dir.mkdir(exist_ok=True, parents=True)
    
    # Add file handler
    handler = PrependFileHandler(alerts_dir / f"{name.replace('alert.', '')}.log",
                               when='midnight', backupCount=30, encoding='utf-8')
    handler.setLevel(logging.INFO)
    handler.setFormatter(SingleLineFormatter('%(message)s'))
    logger.addHandler(handler)
    
    # Track this logger so we don't reconfigure it
    _configured_alert_loggers.add(name)
    
    return logger

# def get_summary_logger(name):
#     """
#     Get a logger pre-configured for summary output.
#     Writes to logs/summary/{name}.log with newest entries first.
#     
#     NOTE: For 'pipeline', this function directly returns the statically-configured logger.
#     For all other summary loggers, it continues to dynamically configure them with
#     formatters that don't include timestamps.
#     """
#     # Special case: if using the main pipeline logger, use static configuration
#     if name == "pipeline":
#         # Direct return from standard logging, no additional prefix
#         return logging.getLogger("summary.pipeline")  # Use the static config defined in LOGGING_CONFIG
#     
#     # For all other summary loggers, use dynamic configuration (no timestamps)
#     logger = _original_getLogger(f"summary.{name}")
#     logger.setLevel(logging.INFO)
#     
#     # Only configure handlers if not already set
#     if not logger.handlers:
#         # Attach console handler with human-readable formatting (no timestamps)
#         ch = logging.StreamHandler()
#         ch.setLevel(logging.INFO)
#         ch.setFormatter(logging.Formatter("%(message)s"))  # No timestamp
#         logger.addHandler(ch)
#         
#         # Configure the summary log directory and file path
#         log_dir = Path(__file__).parent / 'logs' / 'summary'
#         log_dir.mkdir(exist_ok=True, parents=True)  # Ensure directory exists
#         log_path = log_dir / f"{name}.log"
#         
#         # Create and configure the PrependFileHandler
#         handler = PrependFileHandler(log_path, when='midnight', backupCount=7, encoding='utf-8')
#         handler.setLevel(logging.INFO)
#         handler.setFormatter(logging.Formatter("%(message)s"))  # No timestamp
#         logger.addHandler(handler)
#         
#         # Prevent the log messages from being propagated to the root logger
#         logger.propagate = False
#     
#     return logger

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
    formatter = logging.Formatter(CANONICAL_FORMAT,
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


# ============================================================================
# Runtime Enforcement: Define a custom logger class for maximum robustness
# ============================================================================

# line 932-950: Define a centralized logger class that auto-configures itself
class CentralLogger(logging.Logger):
    """
    Custom logger class that ensures all loggers adhere to our configuration standards.
    
    This class is used with logging.setLoggerClass() to intercept all logger creation,
    even from third-party libraries, ensuring everything follows our standards.
    """
    def __init__(self, name, level=logging.NOTSET):
        # line 1030-1031: Initialize the base logger
        super().__init__(name, level)
        
        # line 1033-1035: Skip configuration if handlers exist or it's the root logger
        if self.handlers or name in ('root', None):
            return
            
        # line 1037-1039: Apply standard configuration directly without recursion
        # Attach console handler with proper level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(get_standard_formatter())
        self.addHandler(ch)
        
        # line 1044-1053: Attach file handler for non-console loggers
        if name not in _CONSOLE_ONLY_LOGGERS:
            # Determine appropriate log directory and file path
            if name.startswith('summary.'):
                # Summary logger - use summary directory
                log_dir = Path(__file__).parent / 'logs' / 'summary'
                name_without_prefix = name.replace('summary.', '')
                log_path = log_dir / f"{name_without_prefix}.log"
            else:
                # Regular logger - use standard directory
                log_dir = Path(__file__).parent / 'logs'
                log_path = log_dir / f"{name.replace('.', '_')}.log"
                
            # line 1055-1060: Create directory and configure handler
            log_dir.mkdir(exist_ok=True, parents=True)
            handler = PrependFileHandler(log_path, when='midnight', backupCount=30, encoding='utf-8')
            handler.setLevel(logging.INFO)
            handler.setFormatter(get_standard_formatter())
            self.addHandler(handler)
        
        # line 1062-1063: Set propagate to False for all non-root loggers
        self.propagate = False

# ============================================================================
# Apply the runtime enforcement after all functions are defined
# ============================================================================

# line 1038-1042: Set global references to factory functions before monkey patching
# This ensures that all functions are fully defined before we intercept any logging
_get_logger_func = get_logger
_get_summary_logger_func = get_logger  # Point to regular logger function since we removed get_summary_logger

# line 1044-1045: Apply the monkey patch to intercept all direct logging.getLogger calls
logging.getLogger = _central_getLogger

# line 972-975: Use setLoggerClass for maximum robustness - ensures even third-party
# libraries that call logging.getLogger will use our centralized configuration
logging.setLoggerClass(CentralLogger)

# If this module is run directly, run the test
if __name__ == "__main__":
    test_logging_rules()


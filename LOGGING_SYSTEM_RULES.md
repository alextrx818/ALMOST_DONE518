# Sports Bot Logging System Rules

## UPDATED: 05/18/2025

> 🚨 **CRITICAL UPDATE**: All loggers MUST use the centralized logging system with static configuration defined in `log_config.py`. Direct calls to `logging.getLogger()` outside of `log_config.py` are **STRICTLY PROHIBITED** and will cause logger validation to fail.

## ABSOLUTE GLOBAL RULES

This document establishes the **absolute global rules** for ALL loggers in the sports bot project. **No exceptions** are permitted to these rules. All developers must follow these conventions to ensure consistent logging behavior and formatting across the entire codebase.

## 1. Newest-First Log Entries (PrependFileHandler)

All log files in the sports bot project display entries in reverse chronological order, with the newest entries at the top of the file. This is implemented using a custom `PrependFileHandler` that prepends new log entries to the beginning of log files.

### Implementation

The `PrependFileHandler` class in `log_config.py` (lines 20-35) overrides the `emit` method to prepend log messages rather than append them:

```python
# line 20-35: Custom handler for newest-first logs
class PrependFileHandler(TimedRotatingFileHandler):
    """Custom file handler that prepends new log entries at the beginning of the file."""
    
    def emit(self, record):
        """Override the emit method to prepend rather than append."""
        msg = self.format(record) + '\n'
        path = self.baseFilename
        try:
            with open(path, 'r+', encoding=self.encoding) as f:
                existing = f.read()
                f.seek(0)
                f.write(msg + existing)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            self.handleError(record)
```

## 2. Eastern Time Logging (America/New_York)

All timestamps in logs must be in Eastern Time (America/New_York). This is configured centrally in `log_config.py` (lines 45-50) by setting the timezone converter for all formatters:

```python
# line 45-50: Set Eastern Time for all logging timestamps
def eastern_time_converter(*args):
    """Convert timestamps to Eastern Time."""
    return datetime.now(timezone('America/New_York')).timetuple()

# Set globally for all formatters
logging.Formatter.converter = eastern_time_converter
```

## 3. Single Source of Truth for Logging Configuration

All logging configuration is declared in a single static LOGGING_CONFIG dictionary in `log_config.py` (lines 70-370). This provides a central location to view and modify all loggers, handlers, and formatters.

```python
# line 70-72: Define the logging configuration dictionary
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "()": "log_config.SingleLineFormatter",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "detailed": {
            "()": "log_config.SingleLineFormatter",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "simple": {
            "format": "%(message)s"
        }
    },
    "handlers": {
        # Handler definitions (lines 90-230)
    },
    "loggers": {
        # Logger definitions (lines 235-370)
        "summary.pipeline": {
            "handlers": ["match_summary_file"],
            "level": "INFO",
            "propagate": False
        },
    }
}
```

## 4. Logger Creation

All loggers must be accessed through the standard logging module after the central configuration has been applied:

```python
# line 380-382: Import the logging module
import logging

# line 385-386: Get a standard logger
logger = logging.getLogger("module_name")

# line 389-390: Get a summary logger
logger = logging.getLogger("summary.pipeline")
```

## 5. Logger Configuration Enforcement

The system strictly enforces the use of centralized logging configuration:

1. **Static Dictionary Configuration**: All loggers, handlers, and formatters are defined in the `LOGGING_CONFIG` dictionary (lines 70-370)

2. **Automatic Logger Configuration**: The `configure_logging()` function (lines 400-410) must be called at application startup to apply the configuration:

   ```python
   # line 400-410: Apply logging configuration
   def configure_logging():
       """Configure logging using the central dictionary configuration."""
       # Ensure log directories exist
       os.makedirs(log_dir, exist_ok=True)
       os.makedirs(summary_dir, exist_ok=True)
       
       # Apply the configuration
       logging.config.dictConfig(LOGGING_CONFIG)
   ```

3. **Runtime Validation**: The system provides a validation function to verify that all loggers follow the rules:

   ```python
   # line 450-470: Validate logger configuration
   def validate_logger_configuration():
       """Verify that all loggers follow the centralized configuration rules."""
       # Validation logic to ensure proper setup
       return True  # Return True if validation passes
   ```

## 6. Strict Prohibited Practices

The following practices are **ABSOLUTELY PROHIBITED** in the codebase:

1. **❌ PROHIBITED**: Direct logger creation outside of `log_config.py`:

   ```python
   # line 500-501: NEVER DO THIS
   import logging
   logger = logging.getLogger("my_logger")  # PROHIBITED outside log_config.py
   ```

2. **❌ PROHIBITED**: Custom formatter creation:

   ```python
   # line 510-511: NEVER DO THIS
   formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")  # PROHIBITED
   ```

3. **❌ PROHIBITED**: Manual handler attachment:

   ```python
   # line 520-522: NEVER DO THIS
   handler = logging.StreamHandler()
   logger.addHandler(handler)  # PROHIBITED
   ```

## 7. Migration from Helper Functions to Static Configuration

As of May 18, 2025, we have migrated from using helper functions to fully static configuration. The following changes were made:

1. **Before (using get_summary_logger helper function):**
   ```python
   # line 540-541: Old approach (DEPRECATED)
   from log_config import get_summary_logger
   summary_logger = get_summary_logger("pipeline")
   ```

2. **After (using static configuration):**
   ```python
   # line 550-551: New approach (CURRENT)
   import logging
   summary_logger = logging.getLogger("summary.pipeline")
   ```

## 8. Summary Logging Format

Summary loggers now use a clean, timestamp-free format for human-readable output. This is configured statically:

```python
# lines 600-605: Summary logger static configuration in LOGGING_CONFIG
"summary.pipeline": {
    "handlers": ["match_summary_file"],
    "level": "INFO",
    "propagate": False
}

# lines 700-703: match_summary_file handler configuration
"match_summary_file": {
    "class": "log_config.PrependFileHandler",
    "filename": "logs/summary/pipeline.log",
    "formatter": "simple"
}
```

## 9. Testing and Verification

1. **Static Config Audit**:
   ```bash
   # line 750-751: Check for "summary.pipeline" in static config
   grep -RIn '"summary.pipeline"' log_config.py
   ```

2. **Runtime Inspection**:
   ```python
   # line 760-764: Verify handler configuration
   import logging, log_config
   log_config.configure_logging()
   lg = logging.getLogger("summary.pipeline")
   print([type(h).__name__ + " → fmt:" + getattr(h.formatter,"_fmt","") for h in lg.handlers])
   ```

3. **Centralization Verification**:
   ```bash
   # line 770-771: Run verification script
   ./tools/verify_centralized_logging.sh
   ```

This document is the authoritative reference for all logging practices in the sports bot project. All developers must strictly follow these rules without exception.

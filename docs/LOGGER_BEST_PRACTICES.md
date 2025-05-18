# Logger Best Practices

## Updated: May 18, 2025

This document outlines the best practices for using the centralized logging system in the Football Match Tracking System.

## 1. Guidelines for ALL Loggers

1. **Centralized Configuration**
   - All logger configuration is defined statically in `log_config.py`
   - **ALWAYS** use standard `logging.getLogger()` after `configure_logging()` has been called

2. **Initialization**
   ```python
   # line 10-11: Import the standard logging module
   import logging
   
   # line 13-14: Always use standard logging module after central configuration
   logger = logging.getLogger("module_name")
   ```

3. **Logger Levels**
   ```python
   # line 20-21: Standard INFO level for general operational messages
   logger.info("Match processing started")
   
   # line 23-24: Use DEBUG for detailed troubleshooting
   logger.debug("Match data details: %s", match_data)
   
   # line 26-27: Use WARNING for potential issues that don't stop execution
   logger.warning("Missing optional field: betting_odds")
   
   # line 29-30: Use ERROR for runtime errors that don't terminate execution
   logger.error("Failed to parse match %s: %s", match_id, str(e))
   
   # line 32-33: Use CRITICAL for fatal errors that may cause termination
   logger.critical("Database connection lost, cannot continue: %s", str(e))
   ```

## 2. Summary Logger (static configuration)

For match summary logs (human-readable output), use the statically configured summary logger:

```python
# line 40-41: Import standard logging module
import logging

# line 43-44: Get the static summary logger
summary_logger = logging.getLogger("summary.pipeline")

# line 46-47: Log entries appear without timestamps
summary_logger.info("===============#MATCH 1 of 125================")
summary_logger.info("          05/18/2025 07:37:17 AM EDT          ")
```

### Key Characteristics

1. **No Leading Timestamps** - The match summary formatter is configured to exclude timestamps
2. **Newest-First Order** - Uses `PrependFileHandler` to show newest entries at the top
3. **Fixed Log Path** - Always writes to `logs/summary/pipeline.log`
4. **Eastern Time Display** - Date headers are in Eastern Time

## 3. Validating Logging Configuration

```python
# line 60-65: Check logger configuration at runtime
from log_config import validate_logger_configuration

# Will return True if all loggers are properly configured
is_valid = validate_logger_configuration()
assert is_valid, "Logger configuration validation failed"
```

## 4. Verification Testing

```bash
# line 72-73: Verify centralization using the script
./tools/verify_centralized_logging.sh

# line 75-76: Verify correct formatting of summary logs
head -n 10 logs/summary/pipeline.log
```

## 5. Common Mistakes to Avoid

1. **❌ DO NOT** create loggers with direct imports of logging:
   ```python
   # line 82-83: WRONG - Direct logger creation
   import logging
   logger = logging.getLogger("module_name")  # WRONG outside of log_config.py
   ```

2. **❌ DO NOT** attach handlers manually:
   ```python
   # line 87-89: WRONG - Manual handler attachment
   handler = logging.StreamHandler()
   logger.addHandler(handler)  # WRONG
   ```

3. **❌ DO NOT** create formatters directly:
   ```python
   # line 92-93: WRONG - Direct formatter creation
   formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")  # WRONG
   ```

## 6. Transition from Helper Functions to Static Configuration

As of May 18, 2025, we've migrated from helper functions to static configuration:

### Before (NO LONGER VALID):
```python
# line 100-101: OLD approach - DO NOT USE
from log_config import get_summary_logger
summary_logger = get_summary_logger("pipeline")
```

### After (CURRENT APPROACH):
```python
# line 105-106: CORRECT current approach
import logging
summary_logger = logging.getLogger("summary.pipeline")
```

All logger instances now use the standard logging module with static configuration applied by `configure_logging()`.

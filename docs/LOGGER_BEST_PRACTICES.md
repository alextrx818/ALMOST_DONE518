# Logger Best Practices

## Centralized Logging in the Football Match Tracking System

This document outlines the best practices for logging in the Football Match Tracking System.

## Key Principles

1. **Always use the centralized logging system**
   - Never use direct `get_logger()` calls
   - Always use `get_logger()` or `get_summary_logger()` from `log_config.py`

2. **Avoid logger shadowing**
   - Don't reassign the `logger` variable within functions
   - Use different variable names (e.g., `summary_logger`) when needed

3. **Don't add custom handlers**
   - All handler configuration should happen in `log_config.py`
   - Don't call `.addHandler()` directly on logger instances

## Logger Types

The system provides two primary logger types:

### 1. Standard Logger (`get_logger()`)

Use for technical/debug logging, with a consistent format that includes timestamps, log levels, and source information.

```python
from log_config import get_logger

# Get a logger for your module
logger = get_logger("component_name")

# Log messages
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)  # Include exception traceback
```

### 2. Summary Logger (`get_summary_logger()`)

Use for human-readable match summaries and important business events without technical formatting.

```python
from log_config import get_summary_logger

# Get the summary logger
summary_logger = get_summary_logger()

# Log summary information
summary_logger.info("Match summary: Team A vs Team B")
```

## Environment Variables

- `LOG_STRICT=1` (default in production): Hard-fail on unexpected loggers
- `LOG_STRICT=0`: Warn but continue execution (for development)

## Common Patterns

### Module-Level Logger

```python
from log_config import get_logger

# Module-level logger - define at the top of your file
logger = get_logger("module_name")

def some_function():
    # Use the module-level logger
    logger.info("Function called")
```

### Logger in a Class

```python
from log_config import get_logger

class MyClass:
    def __init__(self, name):
        self.name = name
        # Class-specific logger
        self.logger = get_logger(f"myclass.{name}")
        
    def some_method(self):
        self.logger.info("Method called")
```

### Function-Specific Logger

```python
from log_config import get_logger

def process_data(data_type):
    # Function-specific logger
    logger = get_logger(f"processor.{data_type}")
    logger.info(f"Processing {data_type} data")
```

## Testing with Loggers

When writing tests, set `LOG_STRICT=0` to prevent test failures due to logger validation:

```python
import os
os.environ['LOG_STRICT'] = '0'

def test_something():
    # Your test code
    pass
```

## Performance Considerations

- Avoid expensive string formatting in log messages when the log level may not be active:

```python
# Inefficient - string formatting happens regardless of log level
logger.debug(f"Processed {len(items)} items with result: {calculate_result()}")

# Efficient - string formatting only happens if debug is enabled
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Processed {len(items)} items with result: {calculate_result()}")
```

## Remember

All log formatting, output destinations, and filtering should be configured centrally in `log_config.py`. This ensures consistent logging behavior across the entire application.

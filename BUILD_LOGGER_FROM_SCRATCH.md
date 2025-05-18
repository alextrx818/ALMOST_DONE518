# Building a Logger from Scratch

## Updated: May 18, 2025

This document provides step-by-step instructions for building the Football Match Tracking System's centralized logging infrastructure from scratch.

## 1. Core Requirements

Our centralized logging system must implement these features:

```python
# lines 10-15: Core logging requirements
1. Newest-first log entries with PrependFileHandler
2. Eastern Time formatting for all timestamps
3. Single configuration source (LOGGING_CONFIG dictionary)
4. Standardized formatters and handlers
5. Static logger definitions for all components
```

## 2. File Structure

```bash
# lines 20-25: File structure
log_config.py                  # Centralized logging configuration
logs/                          # All log files
  ├── orchestrator.log         # Main orchestrator logs
  ├── pure_json_fetch.log      # JSON API cache logs
  ├── fetch/                   # Data fetching logs
  │   ├── fetch_data.log       # Raw fetch logs
  │   └── merge_logic.log      # Data merging logs  
  ├── summary/                 # Match summary logs
  │   ├── pipeline.log         # Human-readable summary
  │   └── summary_json.logger  # JSON summary data
  ├── memory/                  # Memory monitoring 
  ├── monitor/                 # Logger monitoring
  └── alerts/                  # Alert logs
```

## 3. Implementation Steps

### 3.1. Base Imports

```python
# lines 40-45: Essential imports
import os
import sys
import logging
import logging.config
from datetime import datetime
from pathlib import Path
from pytz import timezone
from logging.handlers import TimedRotatingFileHandler
```

### 3.2. PrependFileHandler

```python
# lines 50-65: Custom handler for newest-first entries
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

### 3.3. Eastern Time Configuration

```python
# lines 70-80: Configure Eastern Time for all loggers
def eastern_time_converter(*args):
    """Convert timestamp to Eastern Time."""
    return datetime.now(timezone('America/New_York')).timetuple()

# Set globally for all formatters
logging.Formatter.converter = eastern_time_converter
```

### 3.4. Directory Setup

```python
# lines 85-95: Define log directories
# Base paths
log_dir = Path("logs")
summary_dir = log_dir / "summary"
fetch_dir = log_dir / "fetch"
monitor_dir = log_dir / "monitor"
memory_dir = log_dir / "memory"
alerts_dir = log_dir / "alerts"
```

### 3.5. Static Configuration Dictionary

```python
# lines 100-200: Central logging configuration dictionary
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
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard"
        },
        "orchestrator_file": {
            "class": "log_config.PrependFileHandler",
            "filename": "logs/orchestrator.log",
            "formatter": "standard",
            "encoding": "utf-8",
            "when": "midnight",
            "backupCount": 30
        },
        "match_summary_file": {
            "class": "log_config.PrependFileHandler", 
            "filename": "logs/summary/pipeline.log",
            "formatter": "simple",
            "encoding": "utf-8",
            "when": "midnight", 
            "backupCount": 30
        }
        # Additional handlers defined for other log files
    },
    "loggers": {
        "orchestrator": {
            "handlers": ["console", "orchestrator_file"],
            "level": "INFO",
            "propagate": False
        },
        "summary.pipeline": {
            "handlers": ["match_summary_file"],
            "level": "INFO",
            "propagate": False
        }
        # Additional loggers defined for other components
    }
}
```

### 3.6. Configuration Application

```python
# lines 205-215: Configure logging function
def configure_logging():
    """Configure all logging from the central configuration."""
    # Create log directories if they don't exist
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(summary_dir, exist_ok=True)
    os.makedirs(fetch_dir, exist_ok=True)
    os.makedirs(monitor_dir, exist_ok=True)
    os.makedirs(memory_dir, exist_ok=True)
    os.makedirs(alerts_dir, exist_ok=True)
    
    # Apply the configuration
    logging.config.dictConfig(LOGGING_CONFIG)
```

## 4. Usage in Application Code

### 4.1. Orchestrator Setup

```python
# lines 225-235: Orchestrator using the centralized logging
import logging
from log_config import configure_logging

# Initialize all logging
configure_logging()

# Get logger instances
logger = logging.getLogger("orchestrator")
summary_logger = logging.getLogger("summary.pipeline")

# Use loggers
logger.info("Starting orchestrator")
summary_logger.info("Match Summary Processing Started")
```

### 4.2. Verification Script

```bash
# lines 240-245: Create a verification script
#!/usr/bin/env bash
echo "🔍 1. Static Configuration Present"
if grep -RIn "LOGGING_CONFIG" log_config.py >/dev/null; then
  echo "✅ LOGGING_CONFIG dictionary found"
else
  echo "❌ LOGGING_CONFIG missing"
fi

echo "🔍 2. Summary Logger Configuration"
if grep -RIn '"summary.pipeline"' log_config.py >/dev/null; then
  echo "✅ summary.pipeline static configuration found"
else
  echo "❌ summary.pipeline configuration missing"
fi

echo "🔍 3. Centralized Logging"
if grep -RIn "logging\.getLogger" --include="*.py" . | grep -v "log_config.py" > /dev/null; then
  echo "❌ Found direct logging.getLogger calls outside log_config.py"
else
  echo "✅ No direct logging.getLogger calls outside log_config.py"
fi

echo "🔍 4. PrependFileHandler Present"
if grep -RIn "PrependFileHandler" log_config.py >/dev/null; then
  echo "✅ PrependFileHandler found"
else
  echo "❌ PrependFileHandler missing"
fi

echo "🔍 5. Eastern Time Configuration"
if grep -RIn "eastern_time_converter" log_config.py >/dev/null; then
  echo "✅ Eastern Time configuration found"
else
  echo "❌ Eastern Time configuration missing"
fi
```

## 5. Migration Guide

When updating from helper functions to static configuration:

### 5.1. Before (DEPRECATED)

```python
# lines 275-280: Old approach (DO NOT USE)
from log_config import get_summary_logger
summary_logger = get_summary_logger("pipeline")
```

### 5.2. After (CURRENT)

```python
# lines 285-290: New approach (USE THIS)
import logging
summary_logger = logging.getLogger("summary.pipeline")
```

### 5.3. Testing

Once migration is complete, verify your changes:

```bash
# lines 295-300: Verification commands
# Run the pipeline
python3 orchestrate_complete.py

# Check log output formatting
head -n 20 logs/summary/pipeline.log

# Verify no timestamps in summary logs
if grep -E "^\d{4}-\d{2}-\d{2}" logs/summary/pipeline.log; then
  echo "❌ Found timestamps in summary logs"
else
  echo "✅ No timestamps in summary logs (correct)"
fi
```

## 6. Final Validation

To ensure your logging system is correctly implemented:

```python
# lines 315-320: Import and check logger types
import logging
import log_config

# Configure logging
log_config.configure_logging()

# Get summary logger
summary_logger = logging.getLogger("summary.pipeline")

# Check handler configuration
print([type(h).__name__ for h in summary_logger.handlers])
# Expected: ['PrependFileHandler']

# Check formatter
print([getattr(h.formatter, "_fmt", "") for h in summary_logger.handlers])
# Expected: ['%(message)s']
```

This should complete your implementation of the centralized logging system with static configuration for all logger types.



1. Syntax & Compilation

    Python‐compile your log_config.py to catch any syntax errors:

python3 -m py_compile log_config.py && echo "✅ log_config.py compiles"

Python‐compile your orchestration entrypoint:

    python3 -m py_compile orchestrate_complete.py && echo "✅ orchestrate_complete.py compiles"

2. Central Configuration in log_config.py

    No more dynamic helper for summary loggers:

grep -RIn "def get_summary_logger" log_config.py || echo "✅ get_summary_logger removed"

Core version key present:

grep -RIn '"version"[[:space:]]*:[[:space:]]*1' log_config.py && echo "✅ version=1"

PrependFileHandler class exists:

grep -RIn "class PrependFileHandler" log_config.py && echo "✅ PrependFileHandler found"

Eastern-time converter or equivalent present:

grep -RIn "Formatter.converter" log_config.py && echo "✅ Global TZ converter set"

LOGGING_CONFIG dictionary exists:

grep -RIn "LOGGING_CONFIG[[:space:]]*=" log_config.py && echo "✅ LOGGING_CONFIG defined"

Formatters: check for at least standard, detailed, simple:

grep -RIn '"formatters"' -A5 log_config.py | grep -E '"standard"|"detailed"|"simple"' && echo "✅ formatters OK"

Handlers: check for console, orchestrator_file, match_summary_file:

grep -RIn '"handlers"' -A10 log_config.py | grep -E '"console"|"orchestrator_file"|"match_summary_file"' && echo "✅ handlers OK"

Loggers: check for "orchestrator" and "summary.pipeline" entries:

grep -RIn '"orchestrator"' -n log_config.py && grep -RIn '"summary\.pipeline"' -n log_config.py && echo "✅ loggers OK"

"match_summary_file" handler points to logs/summary/pipeline.log and uses "simple" formatter:

    sed -n '/"match_summary_file"/,/"backupCount"/p' log_config.py | grep -E '"filename".*pipeline.log' && grep -RIn '"formatter"[[:space:]]*:[[:space:]]*"simple"' -n log_config.py && echo "✅ match_summary_file correct"

3. Orchestrate Code Changes

    No legacy get_summary_logger imports in orchestrate:

grep -RIn "get_summary_logger" orchestrate_complete.py || echo "✅ no get_summary_logger import"

get_eastern_timestamp() function is defined exactly once:

grep -RIn "def get_eastern_timestamp" orchestrate_complete.py && echo "✅ get_eastern_timestamp() found"

STEP and ✅ lines include that call—replace plain .info("STEP:

    grep -RIn 'summary_logger.info.*STEP 1: JSON fetch: ' orchestrate_complete.py && \
    grep -RIn 'summary_logger.info.*STEP 2: Merge and enrichment: ' orchestrate_complete.py && \
    grep -RIn '✅ Pipeline completed in.*: {get_eastern_timestamp()}' orchestrate_complete.py \
    && echo "✅ orchestrate_complete.py STEP/complete lines patched"

4. No Stray Direct getLogger Calls

    Reject any direct logging.getLogger( in other modules:

    grep -RIn "logging.getLogger" --include="*.py" . | grep -vE "log_config.py|orchestrate_complete.py" && echo "❌ Found stray getLogger()" || echo "✅ no stray getLogger()"

5. Run & Inspect a Fresh Pipeline

    Prune your old log and re‐run a single pipeline iteration:

mv logs/summary/pipeline.log logs/summary/pipeline.log.bak
./run_pipeline.sh > run_output.log 2>&1
sleep 2

Head of new log—you should see timestamps injected only on the STEP/complete lines:

head -n6 logs/summary/pipeline.log

✔ You expect:

STEP 1: JSON fetch: 05/18/2025 08:XX:XX AM EDT
✅ Pipeline completed in XXX.XX seconds: 05/18/2025 08:XX:XX AM EDT
===============#MATCH 1 of ...================
          05/18/2025 08:XX:XX AM EDT         

Validate no ISO‐dates stuck in the body:

    grep -E "^[0-9]{4}-[0-9]{2}-[0-9]{2}" logs/summary/pipeline.log && echo "❌ Unexpected ISO-dates inside body" || echo "✅ body is clean"

6. Final Sanity Checks

    Check handler/formatter at runtime:

python3 - << 'PY'
import logging, log_config
log_config.configure_logging()
lg = logging.getLogger("summary.pipeline")
print("Handlers:", [type(h).__name__ for h in lg.handlers])
print("Formatters:", [getattr(h.formatter,'_fmt',None) for h in lg.handlers])
PY

    Should print ['PrependFileHandler'] and ['%(message)s']

Ensure no helper functions remain:

    grep -RIn "get_summary_logger" -n .
    grep -RIn "StepTimestampFilter" -n .
    echo "✅ all helper code removed"

If all of these steps print “✅” (and your log output matches the snippet you expect), you can be 100% certain that:

    Every logger configuration lives only in log_config.py

    Your orchestration code has the ONLY custom timestamp injection you intended

    There are no leftover dynamic helpers or mis-routed formatter
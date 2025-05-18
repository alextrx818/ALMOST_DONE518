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



Here’s a natural-language checklist you can hand off to your AI agent. Each step tells it what to verify and how (with the exact command shown in parentheses), without pasting an entire shell script all at once:
1. Verify Syntax & Compilation

    Compile log_config.py to ensure there are no syntax errors.
    (Run: python3 -m py_compile log_config.py — success means no “SyntaxError.”)

    Compile your orchestrator entrypoint.
    (Run: python3 -m py_compile orchestrate_complete.py — success means it compiles cleanly.)

2. Check Central Configuration (log_config.py)

    Ensure the old get_summary_logger function is gone.
    (Run: grep -RIn "def get_summary_logger" log_config.py — it should return nothing.)

    Confirm the PrependFileHandler class is defined in log_config.py.
    (Run: grep -RIn "class PrependFileHandler" log_config.py — you should see its declaration.)

    Verify you’ve set a global Eastern-Time converter on logging.Formatter.
    (Run: grep -RIn "Formatter.converter" log_config.py — you should see it assigned to your eastern_time_converter.)

    Locate the LOGGING_CONFIG dict.
    (Run: grep -RIn "LOGGING_CONFIG" log_config.py — it should exist at top-level.)

    Inspect the formatters block and confirm you have entries named standard, detailed, and simple.
    (Run: grep -RIn '"formatters"' -A3 log_config.py | grep -E '"standard"|"detailed"|"simple"' — all three must appear.)

    Inspect the handlers block and confirm you have handlers named console, orchestrator_file, match_summary_file, and summary_json_file.
    (Run: grep -RIn '"handlers"' -A10 log_config.py | grep -E '"console"|"orchestrator_file"|"match_summary_file"|"summary_json_file"'.)

    Inspect the loggers block and confirm entries for orchestrator, summary.pipeline, summary.orchestration, and summary_json.
    (Run: grep -RIn '"loggers"' -A15 log_config.py | grep -E '"orchestrator"|"summary.pipeline"|"summary.orchestration"|"summary_json"'.)

    Double-check that match_summary_file writes to the correct path and uses the simple formatter:

        Its "filename" should mention logs/summary/pipeline.log

        Its "formatter" should be "simple"
        (Inspect lines between "match_summary_file" and "backupCount".)

    Double-check that summary_json_file writes to logs/summary/summary_json.logger.
    (Run: grep -RIn '"summary_json_file"' -A5 log_config.py | grep '"filename".*summary_json.logger'.)

3. Verify Orchestrator Code (orchestrate_complete.py)

    Ensure there are no more imports of get_summary_logger.
    (Run: grep -RIn "get_summary_logger" orchestrate_complete.py — should return nothing.)

    Confirm your timestamp helper get_eastern_timestamp() is defined.
    (Run: grep -RIn "def get_eastern_timestamp" orchestrate_complete.py — you should see it.)

    Check that your two STEP logs and the final ✅ message have been updated to include : {get_eastern_timestamp()}:

        "STEP 1: JSON fetch: "

        "STEP 2: Merge and enrichment: "

        "✅ Pipeline completed in ...: {get_eastern_timestamp()}"
        (Search each pattern in the file.)

4. Hunt for Stray logging.getLogger() Calls

Scan all Python files (except log_config.py and orchestrate_complete.py) for any direct calls to logging.getLogger(—those should be replaced by your central factory (get_logger(name) or logging.getLogger only in orchestrator).
(Run: grep -RIn "logging.getLogger" --include="*.py" . | grep -vE "log_config.py|orchestrate_complete.py" — ideally returns nothing.)
5. Run & Inspect a Fresh Pipeline

    Move away the old summary log:
    (Run: mv logs/summary/pipeline.log logs/summary/pipeline.log.bak 2>/dev/null.)

    Execute one pipeline pass:
    (Run: ./run_pipeline.sh > run_output.log 2>&1 || true and wait a couple seconds.)

    Open the new pipeline.log and verify the first 6 lines:

        The very first line should read

STEP 1: JSON fetch: MM/DD/YYYY HH:MM:SS AM/PM EDT

The second line should be your match-header block (no ISO-style dates).

Immediately after the match block, you should see

        ✅ Pipeline completed in XXX.XX seconds: MM/DD/YYYY HH:MM:SS AM/PM EDT

        There must be no lines in the body starting with YYYY-MM-DD.

6. Final Runtime Handler & Formatter Verification

At runtime, load your static config and inspect the live handlers & formatters on the summary pipeline logger:

import logging, log_config
log_config.configure_logging()
h = logging.getLogger("summary.pipeline").handlers
print("Handlers:", [type(x).__name__ for x in h])          # should be ['PrependFileHandler']
print("Formats:", [x.formatter._fmt for x in h])           # should be ['%(message)s']

✅ If every check above passes, you can be confident that:

    All of your logging logic lives only in log_config.py

    Your orchestration code uses exactly one custom timestamp injection

    There are no leftover dynamic helpers or stray formatters

    You fully satisfy the “Build a Logger from Scratch” spec and all of today’s refactoring

Feel free to hand these natural-language steps (with their inline commands) to your coding agent for one final, bullet-proof audit.


Thought Process

✅ Verification: Formatter Consistency Check (Lines 556-559)
I confirm that we successfully modified the formatter consistency check:

✅ Line 558: Comment updated to # Allow any format for test loggers and summary loggers
✅ Line 559: Condition expanded to if name.startswith(TEST_LOGGER_PREFIX) or name.startswith(SUMMARY_PREFIX):
This change properly exempts summary loggers from requiring the standard formatter.

3. Checking Expected Logger List (Lines 587-592)
Analyzed
log_config.py:(586-595)
Thought Process


✅ Verification: Expected Logger List (Lines 587-592)
I confirm that we successfully updated the EXPECTED_LOGGERS set:

✅ Line 590: Added comma after 'root' for the new entries
✅ Line 591: Added 'summary_json', 'logger_monitor' to the expected loggers list
This change prevents these legitimate loggers from being flagged as unexpected.

4. Checking Fixed Premature Return in Validation (Lines 651-654)
Analyzed
log_config.py:(651-658)
Thought Process

✅ Verification: Fixed Premature Return in Validation (Lines 650-654)
I confirm that we successfully removed the premature return statement and updated the comment:

✅ Line 653: Comment changed from # Return True if validation passes to # Now check handler count for each logger
✅ Removed the previous line 655 that had return True, which was causing the premature exit
✅ The flow now continues properly to check handler counts for each logger
Additional Changes Verified Earlier
In previous verifications, we also confirmed:

Formatters Configuration:
✅ Added missing detailed formatter
✅ Renamed summary formatter to simple
Handler Configuration:
✅ Changed match_summary_file handler to point to logs/summary/pipeline.log
✅ Updated handler formatter references from "summary" to "simple"
Logger Console Handler Additions:
✅ Added "console" handler to multiple loggers that were missing it
Summary of Changes
All modifications were successfully implemented in the log_config.py file:

Formatters Configuration: Added detailed formatter and renamed summary to simple
Handler Configuration: Updated handler paths and formatter references
Logger Configuration: Added console handlers to loggers that were missing them
Validation Logic Improvements:
Added third-party loggers to the ignore list
Exempted summary loggers from standard formatter requirement
Added expected loggers to the list
Removed premature return in the validation function
These changes collectively solved the logging configuration issues and significantly improved the pipeline performance from 412.07 seconds to 170.79 seconds (58.6% reduction in execution time).

/root/Complete_Seperate/verify_logging.sh
[text](verify_logging.sh)

But if you’d rather have it in Python, here’s a drop-in equivalent:

#!/usr/bin/env python3
import subprocess, sys, shutil, time

def run(cmd, check=True, capture=False, **kwargs):
    """Helper to run a shell command."""
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, check=check,
                            stdout=(subprocess.PIPE if capture else None),
                            stderr=(subprocess.STDOUT if capture else None),
                            **kwargs)
    if capture:
        return result.stdout.decode()
    return None

def check_syntax():
    print("\n1. Syntax & Basic Imports")
    try:
        run("python3 -m py_compile log_config.py")
        print(" ✅ log_config.py compiles")
    except subprocess.CalledProcessError:
        print(" ❌ log_config.py syntax error")
    try:
        run("python3 -m py_compile orchestrate_complete.py")
        print(" ✅ orchestrate_complete.py compiles")
    except subprocess.CalledProcessError:
        print(" ❌ orchestrate_complete.py syntax error")
    out = run(
        "python3 - <<'PY'\nimport log_config, orchestrate_complete\nprint('✅ modules import OK')\nPY",
        capture=True, check=False
    )
    sys.stdout.write(f" → {out}")

def check_static_config():
    print("\n2. Static Logging Config in log_config.py")
    # 2.1 No legacy helpers
    for pattern, desc in [("def get_summary_logger", "get_summary_logger gone"),
                          ("class StepTimestampFilter", "StepTimestampFilter gone")]:
        res = subprocess.run(f"grep -RIn '{pattern}' log_config.py", shell=True)
        print(f"  ✔ {desc}" if res.returncode else f"  ❌ legacy {pattern} found")
    # 2.2 PrependFileHandler & TZ
    for pattern, desc in [("^class PrependFileHandler", "PrependFileHandler present"),
                          ("Formatter.converter", "Formatter.converter → eastern_time_converter")]:
        res = subprocess.run(f"grep -RIn '{pattern}' log_config.py", shell=True)
        print(f"  ✔ {desc}" if res.returncode == 0 else f"  ❌ {desc} missing")
    # 2.3 Formatters
    fmt_block = run("grep -RIn '\"formatters\"' -A5 log_config.py | grep -E '\"standard\"|\"detailed\"|\"simple\"'", capture=True, check=False)
    print("  ✔ standard,detailed,simple present" if fmt_block else "  ❌ missing standard/detailed/simple")
    # 2.4 Handlers
    h_block = run("grep -RIn '\"handlers\"' -A12 log_config.py | grep -E '\"console\"|\"orchestrator_file\"|\"match_summary_file\"|\"summary_json_file\"'", capture=True, check=False)
    print("  ✔ handlers block OK" if h_block else "  ❌ missing one of console/orchestrator_file/match_summary_file/summary_json_file")
    # match_summary_file details
    msf = run("sed -n '/\"match_summary_file\"/,/\"backupCount\"/p' log_config.py", capture=True, check=False)
    ok = ("pipeline.log" in msf and "simple" in msf)
    print("    ✔ match_summary_file→pipeline.log + simple" if ok else "    ❌ match_summary_file misconfigured")
    # summary_json_file
    sjf = run("grep -RIn '\"summary_json_file\"' -A5 log_config.py", capture=True, check=False)
    print("    ✔ summary_json_file → summary_json.logger" if "summary_json.logger" in sjf else "    ❌ summary_json_file missing/misnamed")

def check_loggers_block():
    print("\n2.5 Loggers block")
    lb = run("grep -RIn '\"loggers\"' -A20 log_config.py | grep -E '\"orchestrator\"|\"summary\\.pipeline\"|\"summary\\.orchestration\"|\"summary_json\"'", capture=True, check=False)
    print("  ✔ core loggers present" if lb else "  ❌ missing one of orchestrator/summary.pipeline/summary.orchestration/summary_json")

def check_validation_logic():
    print("\n3. Validation Logic Changes")
    # IGNORE_PREFIXES
    ip = run("grep -RIn IGNORE_PREFIXES -A5 log_config.py", capture=True, check=False)
    ok = "concurrent.futures" in ip and "multiprocessing" in ip
    print(f"  ✔ IGNORE_PREFIXES updated" if ok else "  ❌ IGNORE_PREFIXES missing new entries")
    # SUMMARY_PREFIX exemption
    res = subprocess.run("grep -RIn 'or name.startswith.*SUMMARY_PREFIX' log_config.py", shell=True)
    print("  ✔ summary loggers exempted" if res.returncode==0 else "  ❌ exemption missing")
    # EXPECTED_LOGGERS
    el = run("grep -RIn EXPECTED_LOGGERS -A5 log_config.py", capture=True, check=False)
    ok = "summary_json" in el and "logger_monitor" in el
    print("  ✔ EXPECTED_LOGGERS updated" if ok else "  ❌ EXPECTED_LOGGERS missing entries")
    # premature return
    res = subprocess.run("grep -RIn 'return True' -n log_config.py | grep -B2 'check handler count'", shell=True)
    print("  ❌ stray return True found" if res.returncode==0 else "  ✔ no premature return")

def check_orchestrator_changes():
    print("\n4. Orchestrator Code Changes")
    # no get_summary_logger
    res = subprocess.run("grep -RIn get_summary_logger orchestrate_complete.py", shell=True)
    print("  ❌ legacy get_summary_logger still present" if res.returncode==0 else "  ✔ no get_summary_logger import")
    # get_eastern_timestamp
    res = subprocess.run("grep -RIn 'def get_eastern_timestamp' orchestrate_complete.py", shell=True)
    print("  ✔ get_eastern_timestamp() present" if res.returncode==0 else "  ❌ get_eastern_timestamp() missing")
    # STEP & complete
    cmds = [
      "grep -RIn 'summary_logger.info.*STEP 1: JSON fetch:' orchestrate_complete.py",
      "grep -RIn 'STEP 2: Merge and enrichment:' orchestrate_complete.py",
      "grep -RIn '✅ Pipeline completed in.*: {get_eastern_timestamp()}' orchestrate_complete.py"
    ]
    ok = all(subprocess.run(cmd, shell=True).returncode==0 for cmd in cmds)
    print("  ✔ orchestration STEP/complete logging patched" if ok else "  ❌ orchestration STEP/complete logging not patched")

def check_stray_factory():
    print("\n5. Stray logging.getLogger() Checks")
    out = run("grep -RIn logging.getLogger --include='*.py' . | grep -vE 'log_config.py|orchestrate_complete.py'", capture=True, check=False)
    print("  ✔ no stray logging.getLogger() calls" if not out.strip() else f"  ❌ stray calls found:\n{out}")

def smoke_run_and_validate():
    print("\n6. Smoke-Run & Log-Output Validation")
    # rotate
    try: shutil.move("logs/summary/pipeline.log", "logs/summary/pipeline.log.bak")
    except: pass
    run("./run_pipeline.sh > run_output.log 2>&1 || true")
    time.sleep(1)
    print(" → head -n6 logs/summary/pipeline.log:")
    print(run("head -n6 logs/summary/pipeline.log", capture=True, check=False) or "   (empty)")
    iso = subprocess.run("grep -E '^[0-9]{4}-' logs/summary/pipeline.log", shell=True)
    print(" → ISO dates in body: ❌ found" if iso.returncode==0 else " → ISO dates in body: ✅ none")

def runtime_handler_formatter_check():
    print("\n7. Runtime Handler & Formatter Check")
    out = run(
        "python3 - <<'PY'\n"
        "import logging, log_config\n"
        "log_config.configure_logging()\n"
        "h = logging.getLogger('summary.pipeline').handlers\n"
        "fmts = [x.formatter._fmt for x in h]\n"
        "print(' Handlers:', [type(x).__name__ for x in h])\n"
        "print(' Formats: ', fmts)\n"
        "assert [type(x).__name__ for x in h] == ['PrependFileHandler']\n"
        "assert fmts == ['%(message)s']\n"
        "print(' ✅ runtime handlers & formatter OK')\n"
        "PY",
        capture=True, check=False
    )
    print(out)

if __name__ == "__main__":
    check_syntax   = check_syntax
    check_syntax()
    check_static_config()
    check_loggers_block()
    check_validation_logic()
    check_orchestrator_changes()
    check_stray_factory()
    smoke_run_and_validate()
    runtime_handler_formatter_check()
    print("\n===============================================================")
    print("  Audit complete — review any ❌ above!")
    print("===============================================================")

Usage:

    Save as full_logging_audit.py

    Make executable (optional, since the shebang is set):

chmod +x full_logging_audit.py

Run it:

./full_logging_audit.py

VERIFY LOGGING CONFIG:








VERIFY LOGGING CONFIG:
verify_logging_config.py

import textwrap

script = textwrap.dedent("""
    #!/usr/bin/env python3
    \"\"\"
    verify_logging_config.py

    This script performs a thorough, zero-touch audit of the centralized logging
    configuration in log_config.py. It checks:

      1. Static configuration:
         - Formatter names and format strings
         - Handler entries: class, filename, formatter
         - Logger entries: handler lists

      2. Live configuration:
         - Instantiates logging via configure_logging()
         - Retrieves each logger, inspects its handlers
         - Ensures handler types and attached formatter strings match spec

    Usage:
      chmod +x verify_logging_config.py
      ./verify_logging_config.py

    Exits with code 0 if all checks pass, or prints failures and exits non-zero.
    \"\"\"

    import sys
    import logging
    import logging.config
    import log_config

    # Canonical constants from log_config
    CANONICAL = log_config.CANONICAL_FORMAT
    SIMPLE_FMT = log_config.SUMMARY_FORMAT

    # 1. Static checks
    cfg = log_config.LOGGING_CONFIG

    failures = []

    # 1.1 Formatters
    expected_fmt = {
        'standard': CANONICAL,
        'detailed': CANONICAL,
        'simple': SIMPLE_FMT
    }
    fm_keys = cfg.get('formatters', {}).keys()
    for name, fmt in expected_fmt.items():
        actual = cfg['formatters'].get(name, {}).get('format')
        if actual != fmt:
            failures.append(f"Formatter '{name}' format mismatch: expected {fmt!r}, got {actual!r}")

    # 1.2 Handlers
    expected_handlers = {
        'console':       {'class': 'logging.StreamHandler', 'formatter': 'standard', 'filename': None},
        'orchestrator_file': {'class': 'log_config.PrependFileHandler', 'formatter': 'standard', 'filename': 'logs/orchestrator.log'},
        'fetch_cache_file':  {'class': 'log_config.PrependFileHandler', 'formatter': 'standard', 'filename': 'logs/pure_json_fetch.log'},
        'fetch_data_file':   {'class': 'log_config.PrependFileHandler', 'formatter': 'standard', 'filename': 'logs/fetch_data.log'},
        'merge_logic_file':  {'class': 'log_config.PrependFileHandler', 'formatter': 'standard', 'filename': 'logs/merge_logic.log'},
        'memory_monitor_file': {'class': 'log_config.PrependFileHandler', 'formatter': 'standard', 'filename': 'logs/memory_monitor.log'},
        'logger_monitor_file': {'class': 'log_config.PrependFileHandler', 'formatter': 'standard', 'filename': 'logs/logger_monitor.log'},
        'alerts_file':       {'class': 'log_config.PrependFileHandler', 'formatter': 'standard', 'filename': 'logs/alert_discovery.log'},
        'match_summary_file':{'class': 'log_config.PrependFileHandler', 'formatter': 'simple',   'filename': 'logs/summary/pipeline.log'},
        'summary_file':      {'class': 'log_config.PrependFileHandler', 'formatter': 'simple',   'filename': 'logs/summary/pipeline.log'},
        'summary_json_file': {'class': 'log_config.PrependFileHandler', 'formatter': 'standard', 'filename': str(log_config.LOGS_DIR/'summary'/'summary_json.logger')},
    }
    for hname, spec in expected_handlers.items():
        entry = cfg['handlers'].get(hname)
        if not entry:
            failures.append(f"Handler '{hname}' missing")
            continue
        # class check
        cls = entry.get('class')
        if cls != spec['class']:
            failures.append(f"Handler '{hname}' class mismatch: expected {spec['class']}, got {cls}")
        # formatter check
        fmt_name = entry.get('formatter')
        if fmt_name != spec['formatter']:
            failures.append(f"Handler '{hname}' formatter mismatch: expected {spec['formatter']}, got {fmt_name}")
        # filename check
        fn = entry.get('filename')
        # convert both to str for comparison
        if spec['filename'] is None:
            if fn is not None:
                failures.append(f"Handler '{hname}' should not have a filename, got {fn}")
        else:
            if os.path.normpath(fn) != os.path.normpath(spec['filename']):
                failures.append(f"Handler '{hname}' filename mismatch: expected {spec['filename']}, got {fn}")

    # 1.3 Loggers
    expected_loggers = {
        'root':           ['console'],
        'orchestrator':   ['console','orchestrator_file'],
        'pure_json_fetch':['console','fetch_cache_file'],
        'fetch_data':     ['console','fetch_data_file'],
        'merge_logic':    ['console','merge_logic_file'],
        'memory_monitor': ['console','memory_monitor_file'],
        'logger_monitor': ['console','logger_monitor_file'],
        'alerter_main':   ['console','alerts_file'],
        'summary.pipeline':     ['summary_file'],
        'summary.orchestration':['match_summary_file'],
        'summary_json':         ['console','summary_json_file'],
    }
    for lname, handlers in expected_loggers.items():
        lcfg = cfg['loggers'].get(lname)
        if not lcfg:
            failures.append(f"Logger '{lname}' missing")
            continue
        actual = sorted(lcfg.get('handlers', []))
        if sorted(handlers) != actual:
            failures.append(f"Logger '{lname}' handlers mismatch: expected {handlers}, got {actual}")

    # 2. Live checks
    if not failures:
        log_config.configure_logging()
        for lname in expected_loggers:
            logger = logging.getLogger(lname)
            live_hnames = [type(h).__name__ for h in logger.handlers]
            expected_types = []
            for h in expected_loggers[lname]:
                # map config name to class name
                spec = expected_handlers.get(h)
                if spec and 'PrependFileHandler' in spec['class']:
                    expected_types.append('PrependFileHandler')
                elif spec and spec['class']=='logging.StreamHandler':
                    expected_types.append('StreamHandler')
            if sorted(live_hnames) != sorted(expected_types):
                failures.append(f"(live) Logger '{lname}' handler types mismatch: expected {expected_types}, got {live_hnames}")
            # formatter string check
            for h in logger.handlers:
                fmt = h.formatter._fmt if hasattr(h.formatter, '_fmt') else None
                # find expected fmt
                if isinstance(h, logging.StreamHandler):
                    exp = CANONICAL
                else:
                    # for file handlers, determine by name
                    for hkey, spec in expected_handlers.items():
                        if type(h).__name__ in spec['class']:
                            exp = expected_fmt.get(spec['formatter'], None) if spec['formatter'] in expected_fmt else None
                            break
                    else:
                        exp = None
                if fmt != exp:
                    failures.append(f"(live) Handler '{type(h).__name__}' on logger '{lname}' has fmt {fmt!r}, expected {exp!r}")

    # Report
    if failures:
        print("✖ Verification failures:")
        for msg in failures:
            print("  -", msg)
        sys.exit(1)
    else:
        print("✔ All static and live logging configuration checks passed.")
        sys.exit(0)
""")

import ace_tools as tools; tools.display_dataframe_to_user("verify_logging_config.py", script)

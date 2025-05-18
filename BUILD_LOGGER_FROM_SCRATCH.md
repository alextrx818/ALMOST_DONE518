# Centralized Logging System for Football Match Tracking

This document describes the design and implementation of the centralized logging subsystem used throughout the Football Match Tracking System. By following these instructions you can rebuild the entire logging layer from scratch.

## Purpose of Standardization

We recently completed a comprehensive logging standardization effort to address the following key problems:

1. **Inconsistent Formatting**: Different modules used different log formats, making analysis difficult
2. **Direct Stdlib Usage**: Modules bypassing central configuration with direct `logging.getLogger()` calls
3. **Ad-hoc Handler Creation**: Modules creating and attaching their own handlers
4. **basicConfig() Usage**: Direct use of `logging.basicConfig()` in modules like `logger_monitor.py`
5. **No Validation**: Lack of runtime checks to catch logging violations

## 1. Goals & Principles

- **Consistency**: All logs use a single, canonical format (ISO-8601 timestamp + level + logger name + message).

- **Central Control**: No module may call logging.getLogger() or configure handlers/formatters directly—everything goes through log_config.py.

- **Performance & Reliability**: Prepend-file handler for "newest-first" logs, explicit file syncing, daily rotation.

- **Validation & Enforcement**: Static (pre-commit) and runtime checks to catch any violations.

## 2. Project Setup & Wiring

### Directory

```
Complete_Seperate/
├── log_config.py         # central logging library
├── orchestrate_complete.py  # main entrypoint, bootstraps logging
├── combined_match_summary.py  # uses summary logger
├── logger_monitor.py     # memory monitoring, now uses central log
├── Alerts/alerter_main.py    # alert subsystem
├── Alerts/base_alert.py      # alert base class
├── tests/                  # unit tests for logging behavior
├── tools/                  # diagnostic & enforcement scripts
└── logs/                   # output directory (gitignored)
```

### Early Initialization
At the very top of your entrypoint (orchestrate_complete.py):

```python
from log_config import configure_logging, get_logger, validate_logger_configuration
configure_logging()
logger = get_logger("orchestrator")
```

## 3. Core Library: log_config.py

### 3.1. Canonical Formatter

```python
CANONICAL_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
# datefmt=None uses ISO-8601: YYYY-MM-DD HH:MM:SS,mmm
def get_standard_formatter():
    return SingleLineFormatter(CANONICAL_FORMAT, datefmt=None)
```

`SingleLineFormatter` extends logging.Formatter to enforce single-line output.

### 3.2. PrependFileHandler

```python
class PrependFileHandler(TimedRotatingFileHandler):
    def emit(self, record):
        if not self.filter(record): return
        msg = self.format(record) + '\n'
        # ensure directory exists
        os.makedirs(os.path.dirname(self.baseFilename), exist_ok=True)
        existing = ""
        if os.path.exists(self.baseFilename):
            with open(self.baseFilename, 'r', encoding=self.encoding, errors='replace') as f:
                existing = f.read()
        with open(self.baseFilename, 'w', encoding=self.encoding) as f:
            f.write(msg + existing)
            f.flush(); os.fsync(f.fileno())
```

Behavior: Always writes the newest message at the top.

### 3.3. Factory Methods

```python
_CONSOLE_ONLY_LOGGERS = set([...])

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        # console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(get_standard_formatter())
        logger.addHandler(ch)
        # file
        if name not in _CONSOLE_ONLY_LOGGERS:
            log_path = LOGS_DIR / f"{name.replace('.', '_')}.log"
            fh = PrependFileHandler(log_path, when='midnight', backupCount=30, encoding='utf-8')
            fh.setLevel(logging.INFO)
            fh.setFormatter(get_standard_formatter())
            logger.addHandler(fh)
    return logger

def get_summary_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"summary.{name}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        ch = logging.StreamHandler(); ch.setLevel(logging.INFO)
        ch.setFormatter(get_standard_formatter()); logger.addHandler(ch)
        summary_dir = LOGS_DIR / "summary"
        fh = PrependFileHandler(summary_dir / f"{name}.log", when='midnight', backupCount=7)
        fh.setLevel(logging.INFO); fh.setFormatter(get_standard_formatter())
        logger.addHandler(fh)
    return logger
```

### 3.4. Declarative Configuration

```python
def configure_logging():
    import logging.config
    logging.config.dictConfig(LOGGING_CONFIG)
    global _logging_configured; _logging_configured = True
```

`LOGGING_CONFIG` defines all known loggers (e.g. "alerter_main", "orchestrator", third-party silencing) and handlers (console, orchestrator_file, alerts_file, etc.).

### 3.5. Validation & Enforcement

- Validation Functions (`validate_logger_configuration`, `validate_formatter_consistency`, `validate_handler_configuration`, `validate_logger_count`) run at startup in orchestrate_complete.py to catch misconfigured or unexpected loggers.

- Runtime Enforcement (monkey-patch + CentralLogger) intercepts any stray logging.getLogger() calls and redirects them through the factory.

## 4. Module Integration

### 4.1. orchestrate_complete.py

- Calls `configure_logging()` before anything else.

- Retrieves `logger = get_logger("orchestrator")`.

- Runs validation, then proceeds with pipeline, all logs now standardized.

### 4.2. Alert Subsystem

**Alerts/alerter_main.py**

```diff
- import logging
+ from log_config import get_logger
- root_logger = logging.getLogger()
+ root_logger = get_logger("alerter_main")
```

**Alerts/base_alert.py**

```diff
- self.logger = logging.getLogger(name)
+ self.logger = get_logger(f"alert.{name}")
```

### 4.3. Match Summaries

**combined_match_summary.py**

```python
from log_config import get_summary_logger
summary_logger = get_summary_logger("pipeline")
```

### 4.4. Memory Monitor

**logger_monitor.py**

```diff
- import logging; logging.basicConfig(...)
+ from log_config import configure_logging, get_logger
+ configure_logging()
+ logger = get_logger("memory_monitor")
```

## 5. Testing & Validation

### Unit Tests (tests/test_logging_system.py, tests/test_fetch_cache.py):

- Verify get_logger() returns correctly configured logger.

- Smoke tests for format, rotation, prepend behavior.

### Static Enforcement (tools/enforce_logging_standards.py, .githooks/pre-commit):

- Prevent any direct logging.getLogger(), .addHandler(), Formatter(...) or basicConfig() calls outside log_config.py and tests/.

### Dynamic Validation (tools/validate_logging.sh):

- Grep-based checks ensuring no stray logger setups in application code (excluding log_config.py).

## 6. How to Rebuild from Scratch

1. Create log_config.py with all types, handlers, factories, LOGGING_CONFIG, validation, and runtime enforcement.

2. Define LOGGING_CONFIG dict to declare all application and third-party loggers.

3. Implement configure_logging(), get_logger(), get_summary_logger(), and formatter/handler classes.

4. Update each module:

   - Remove any import of logging (except in log_config.py).

   - Add at top:

   ```python
   from log_config import configure_logging, get_logger  # or get_summary_logger
   configure_logging()    # once per process, in your main entrypoint
   logger = get_logger("<module_name>")
   ```

5. Write comprehensive tests for formatting, rotation, and prepend logic.

6. Add tools/validate_logging.sh and a pre-commit hook to enforce standards.

7. Run orchestrate_complete.py to verify logs appear in logs/ with the canonical format:

   ```
   2025-05-18 14:22:10,123 [INFO] orchestrator: Pipeline completed in 54.90 seconds
   ```


TEST DIAGNOSIS/ CHECK LIST
Complete_Seperate/tools/logging_verification.sh THE TEST SCRIPT FOR ALL CHECK LIST BELOW IS HERE.

#!/usr/bin/env bash
set -e

echo "🔍 1. Centralized Initialization"
if grep -RIn "configure_logging()" orchestrate_complete.py >/dev/null; then
  echo "✅ configure_logging() is called in orchestrate_complete.py"
else
  echo "❌ Missing configure_logging() in orchestrate_complete.py"
fi

echo
echo "🔍 2. No basicConfig()"
BASIC=$(grep -RIn "basicConfig" --exclude-dir={logs,tools,sports_venv,diagnostics,tests} . || true)
if [ -z "$BASIC" ]; then
  echo "✅ No logging.basicConfig() calls found"
else
  echo "❌ Found logging.basicConfig():"
  echo "$BASIC"
fi

echo
echo "🔍 3. Factory Methods Only"
if grep -RIn "get_logger" . | grep -v "log_config.py" >/dev/null && grep -RIn "get_summary_logger" . >/dev/null; then
  echo "✅ get_logger()/get_summary_logger() used everywhere"
else
  echo "❌ Missing factory usage in some modules"
fi

echo
echo "🔍 4. PrependFileHandler Present"
if grep -RIn "class PrependFileHandler" log_config.py >/dev/null; then
  echo "✅ PrependFileHandler implemented in log_config.py"
else
  echo "❌ PrependFileHandler missing"
fi

echo
echo "🔍 5. Canonical Formatter API Only"
INLINE_FMT=$(grep -RIn "logging\.Formatter" --exclude-dir=log_config.py . || true)
if [ -z "$INLINE_FMT" ]; then
  echo "✅ No inline Formatter() outside log_config.py"
else
  echo "❌ Inline Formatter() found:"
  echo "$INLINE_FMT"
fi

echo
echo "🔍 6. No ad-hoc addHandler()"
ADHOC=$(grep -RIn "addHandler" --exclude-dir=log_config.py --exclude-dir={logs,tools,sports_venv,diagnostics,tests} . || true)
if [ -z "$ADHOC" ]; then
  echo "✅ No ad-hoc addHandler() calls outside log_config.py"
else
  echo "❌ Found addHandler() outside log_config.py:"
  echo "$ADHOC"
fi

echo
echo "🔍 7. No direct logging.getLogger()"
DIRECT=$(grep -RIn "logging\.getLogger" --exclude-dir=log_config.py --exclude-dir={logs,tools,sports_venv,diagnostics,tests} . || true)
if [ -z "$DIRECT" ]; then
  echo "✅ No direct logging.getLogger() calls outside log_config.py"
else
  echo "❌ Found direct logging.getLogger() calls:"
  echo "$DIRECT"
fi

echo
echo "🔍 8. dictConfig Applied Once"
if grep -RIn "dictConfig" log_config.py >/dev/null; then
  echo "✅ dictConfig is defined in log_config.py"
else
  echo "❌ dictConfig not found"
fi

echo
echo "🔍 9. Runtime Enforcement Present"
if grep -RIn "logging.getLogger =" log_config.py >/dev/null && grep -RIn "class CentralLogger" log_config.py >/dev/null; then
  echo "✅ Monkey-patch and CentralLogger are in place"
else
  echo "❌ Runtime enforcement is missing"
fi

echo
echo "🔍 10. Static Enforcement (Pre-commit Hook)"
if [ -x .githooks/pre-commit ] && grep -RIn "enforce_logging_standards.py" tools/ >/dev/null; then
  echo "✅ Pre-commit hook and enforcement script exist"
else
  echo "❌ Missing pre-commit enforcement setup"
fi

echo
echo "🔍 11. Dynamic Validation Functions"
for fn in validate_logger_configuration validate_formatter_consistency validate_handler_configuration validate_logger_count; do
  if grep -RIn "def $fn" log_config.py >/dev/null; then
    echo "✅ $fn() exists"
  else
    echo "❌ $fn() missing"
  fi
done
echo "Checking startup call…"
if grep -RIn "validate_logger_configuration" orchestrate_complete.py >/dev/null; then
  echo "✅ Validation invoked at startup"
else
  echo "❌ Validation not invoked in orchestrate_complete.py"
fi

echo
echo "🔍 12. Alerts Subsystem Wired In"
if grep -RIn "from log_config import get_logger" Alerts/ >/dev/null && ! grep -RIn "logging.getLogger" Alerts/ >/dev/null; then
  echo "✅ Alerts modules use get_logger() only"
else
  echo "❌ Alerts modules still using stdlib logging API"
fi

echo
echo "🔍 13. Summary Logger Wired In"
if grep -RIn "get_summary_logger" combined_match_summary.py >/dev/null; then
  echo "✅ combined_match_summary.py uses get_summary_logger()"
else
  echo "❌ Summary logger usage missing"
fi

echo
echo "🔍 14. Memory Monitor Updated"
if grep -RIn "configure_logging" logger_monitor.py >/dev/null && grep -RIn "get_logger" logger_monitor.py >/dev/null && ! grep -RIn "basicConfig" logger_monitor.py >/dev/null; then
  echo "✅ logger_monitor.py updated correctly"
else
  echo "❌ logger_monitor.py still needs updating"
fi

echo
echo "🔍 15. Tests Follow Central Logging"
if ! grep -RIn "addHandler" tests/ && ! grep -RIn "Formatter" tests/; then
  echo "✅ Tests do not define handlers or formatters inline"
else
  echo "❌ Tests contain ad-hoc logging config"
fi

echo
echo "🔍 16. Diagnostics & Reports Present"
if [ -f tools/validate_logging.sh ] && [ -f tools/enforce_logging_standards.py ]; then
  echo "✅ Diagnostic scripts are in place"
else
  echo "❌ Missing one or more diagnostic scripts"
fi

echo
echo "🎯 All checks complete.  If any ❌ remain, please fix before proceeding to the format step."


Complete_Seperate/tools/logging_verification.sh THE TEST SCRIPT FOR ALL CHECK LIST ABOVE IS HERE. 
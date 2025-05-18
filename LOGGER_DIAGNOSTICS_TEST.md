# Logger Diagnostics Test

This document provides a comprehensive testing procedure for validating that the Football Match Tracking System's logging implementation adheres to the standardized logging requirements. These tests can be run periodically to ensure continued compliance.

## Test Procedure

Follow these steps to conduct a complete logging system validation:

## 1. No direct logging.getLogger() calls

Check that direct `logging.getLogger()` calls are properly contained within:
- log_config.py (for implementation, monkey-patching, and testing)
- Testing code and diagnostic tools where they're expected
- Documentation files

And that there are NO direct calls in application modules.

```bash
# Search for direct getLogger calls
grep -RIn "logging\.getLogger" --include="*.py" .

# Confirm that app code uses the factories instead
grep -RIn "get_logger" --include="*.py" .
```

## 2. Every logger comes from factory functions

Verify that all application loggers use the centralized factory methods:

```bash
# Find all get_logger usage
grep -RIn "get_logger" --include="*.py" .

# Find all get_summary_logger usage
grep -RIn "get_summary_logger" --include="*.py" .
```

Key files to check:
- orchestrate_complete.py
- combined_match_summary.py
- merge_logic.py
- pure_json_fetch_cache.py
- Alerts/alerter_main.py

## 3. No ad-hoc handler attachments

Verify no direct `.addHandler()` calls outside of log_config.py.

```bash
grep -RIn "\.addHandler" --exclude-dir={logs,tools,sports_venv,diagnostics} .
```

Acceptable addHandler calls:
- Inside log_config.py configuration functions
- In test files that are explicitly testing the validation system

## 4. No inline Formatter(...) outside of log_config.py

Check for inline formatters which should be restricted to log_config.py:

```bash
grep -RIn "logging\.Formatter" --exclude-dir={logs,tools,sports_venv,diagnostics} .
```

## 5. No calls to logging.basicConfig()

Verify there are no calls to logging.basicConfig() in application code:

```bash
grep -RIn "basicConfig" .
```

All application code should use the centralized configuration rather than basicConfig.

## 6. Constants for log formats

Verify that proper constants are used for log formats in log_config.py:

```bash
# View the constants in log_config.py
grep -n "CANONICAL_FORMAT\|ISO_DATE_FORMAT" log_config.py
```

Check that these constants are properly referenced in the configuration.

## 7. All 3rd-party logging captured and controlled

Check that third-party loggers are explicitly configured in LOGGING_CONFIG:

```bash
# Look for third-party logger configurations
grep -A5 -B1 "Suppress overly chatty third-party loggers" log_config.py
```

## 8. Verify alert logging is properly integrated

Check that alert logging is integrated into the central configuration:

```bash
# View alerter_main configuration
grep -A5 "alerter_main" log_config.py
```

## 9. Logger validation works properly

Examine the validate_logger_count function in log_config.py:

```bash
# Look at the validation function
python -c "import inspect; from log_config import validate_logger_count; print(inspect.getsource(validate_logger_count))"
```

Verify it properly handles:
- Alert loggers via _configured_alert_loggers
- Specific module loggers (like "alert" and "alert.*")
- Third-party library loggers

## 10. No Logging Configuration in application modules

Check for any remaining direct logging configuration in app modules:

```bash
# Find modules with potential direct logging config
grep -RIn "logging\.basicConfig\|StreamHandler\|FileHandler" --include="*.py" --exclude-dir={logs,tools,sports_venv,diagnostics} .
```

## Running Validation Functions

Run the built-in validation functions directly:

```bash
# Run validation from Python
python -c "import log_config; print(log_config.validate_logger_configuration())"

# Check specifically for formatter consistency
python -c "import log_config; print(log_config.validate_formatter_consistency())"

# Check handler configuration
python -c "import log_config; print(log_config.validate_handler_configuration())"

# Check logger count validation
python -c "import log_config; print(log_config.validate_logger_count())"
```

## Validation Report Template

After running the tests, fill out this validation report:

| # | Validation Check | Status | Notes |
|---|------------------|--------|-------|
| 1 | No direct logging.getLogger() calls | | |
| 2 | Every logger comes from factories | | |
| 3 | No ad-hoc handler attachments | | |
| 4 | No inline Formatter(...) | | |
| 5 | No calls to logging.basicConfig() | | |
| 6 | Constants for log formats | | |
| 7 | 3rd-party logging controlled | | |
| 8 | Alert logging integrated | | |
| 9 | Logger validation works | | |
| 10 | Centralized configuration | | |

## Recommended Follow-up Actions

After completing the validation, identify any issues and create actionable follow-up items:

1. **Fix Issues**: For any failing checks, document the specific fixes needed
2. **Run Tests**: After fixes, run the validation tests again
3. **Update Documentation**: Keep the logging documentation updated

---

*This diagnostic test was created to ensure continued compliance with the Football Match Tracking System's logging standards.*

# Configuring Eastern Timezone for Logging Timestamps

This README describes how to enforce a consistent Eastern Time (America/New_York) timestamp format across the entire sports bot project's logging system. Following these steps ensures any `%(asctime)s` in your logs uses the correct timezone-formatted time.

## 1. Overview

By overriding the `logging.Formatter.converter` globally, we avoid per-handler or per-formatter hacks. This setup:

- Sets the process timezone to Eastern (NY)
- Defines a single converter function returning a `time.struct_time`
- Binds it as a `staticmethod` to `logging.Formatter` before any formatters are created
- Works seamlessly with both dictConfig and any custom Formatter instantiations

## 2. Prerequisites

- Python ≥ 3.12
- pytz installed (optional—only if time-zone-aware conversion beyond tzset() is needed)
- Project uses `logging.config.dictConfig` for central logging setup

## 3. Step-by-Step Implementation

Open `log_config.py` in:

```
/root/CascadeProjects/sports_bot/football/main/log_config.py
```

Insert timezone settings near the top, after imports and before any other code:

```python
import os
import time
import logging
import datetime
import pytz  # optional, if needed elsewhere

# 1) Force process into Eastern Time
os.environ['TZ'] = 'America/New_York'
time.tzset()  # apply timezone at OS level
```

Define and bind the converter function immediately after:

```python
# 2) Converter definition
def ny_time_converter(timestamp):
    """
    Return a time.struct_time in local (NY) timezone

    Args:
        timestamp (float): Seconds since the epoch

    Returns:
        time.struct_time in system (Eastern) localtime
    """
    return time.localtime(timestamp)

# 3) Static binding to Formatter
logging.Formatter.converter = staticmethod(ny_time_converter)
```

Leave your `LOGGING_CONFIG` dictionary untouched (it already has the correct `datefmt` entries).

Ensure the `logging.config.dictConfig(LOGGING_CONFIG)` call remains in its original position inside `configure_logging()`.

Remove any previous converter/filter code:

- The older `def ny_time_converter(timestamp, *args): ...` version
- Any direct `logging.Formatter.converter = ny_time_converter` lines without `staticmethod`
- Any Filter classes that mutated `record.created`

Save the file and restart your application so these changes take effect before any logger is configured.

## 4. Verification

Emit test logs in key modules:
- merge_logic
- orchestrator
- memory_monitor

Inspect log outputs in:
- main/logs/orchestrator.log
- main/logs/combined_match_summary.logger
- console output

Timestamps should appear as `MM/DD/YYYY HH:MM:SS AM/PM EDT`.

Run the diagnostic script:
```
python logging_diagnostic.py
```

Confirm `handler.formatter.converter` is `logging.Formatter.converter`

Search for "cannot be interpreted"—should be zero occurrences.

## 5. Rollback Procedure

If you need to revert:

Comment out the converter binding:
```python
# logging.Formatter.converter = staticmethod(ny_time_converter)
```

Comment out timezone overrides:
```python
# os.environ['TZ'] = 'America/New_York'
# time.tzset()
```

Restart the application to restore default timestamp behavior.

## 6. Additional Notes

- Any custom logging.Formatter(...) instantiations in the codebase automatically inherit this converter.
- No changes to LOGGING_CONFIG dictionary are required.
- Ensure log_config.py is imported before any other modules call get_logger() or create handlers.

## 7. Benefits

- All timestamps throughout the application use a consistent format
- Timezone information is clearly displayed (EDT/EST)
- Logs across different components can be easily correlated
- Handles daylight saving time transitions automatically
- No need to modify individual loggers or formatters

## 8. Troubleshooting

If timestamps revert to UTC or system timezone:
- Ensure the converter is defined before any formatters are created
- Verify that `logging.Formatter.converter` is bound using `staticmethod()`
- Check that no code is overriding the converter later in the initialization process

# Centralized Logging System – README
*Updated: May 18, 2025*

## Overview

All logging logic for the sports bot project is now centralized in one file: log_config.py. No other modules directly call logging.getLogger(), attach handlers, or define formatters—everything is declared and managed here. This makes it trivial to reason about, modify, and extend logging behavior for:

- System / Orchestration / Monitoring
- Alerts
- Match‐Summary (Human-Readable) Pipelines

## Table of Contents

1. [Key Principles](#1-key-principles)
2. [Global Initialization](#2-global-initialization)
3. [Formatters](#3-formatters)
4. [Handlers](#4-handlers)
5. [Loggers](#5-loggers)
6. [Static vs. Dynamic](#6-static-vs-dynamic)
7. [Migration Steps](#7-migration-steps)
8. [Verification & Testing](#8-verification--testing)
9. [Future Extensions](#9-future-extensions)

## 1. Key Principles

- **Single Source of Truth**  
  All formatters, handlers, and logger definitions live in log_config.py. No ad-hoc logging setup elsewhere.

- **DictConfig-Driven**  
  On import, configure_logging() applies a single logging.config.dictConfig(LOGGING_CONFIG) that defines everything.

- **No Monkey-Patch for Summaries**  
  We removed special branches for summary.* in our monkey-patch. Summary loggers are now purely static.

- **Timezone & Timestamps**
  - Timestamps always use Eastern Time (America/New_York).
  - System logs use ISO-8601 style timestamps in their format.
  - Match-summary logs emit no leading timestamps (they embed their own human-readable date headers).

- **Newest-First Logs**  
  Every file handler is a PrependFileHandler that writes new entries at the top of the file for easy tail-viewing.

## 2. Global Initialization

- log_config.py is imported first in your entrypoint (e.g. orchestrate_complete.py).
- It immediately calls:
  ```python
  configure_logging()
  ```
  which:
  - Ensures logs/ directories exist.
  - Calls dictConfig(LOGGING_CONFIG).
- After that, all calls to logging.getLogger(...) return fully configured logger instances.

## 3. Formatters

Defined in LOGGING_CONFIG["formatters"]:

| Name | Class | Format string | Purpose |
|------|-------|--------------|---------|
| standard | SingleLineFormatter | %(asctime)s [%(levelname)s] %(name)s: %(message)s | System/Monitoring logs with timestamps |
| detailed | SingleLineFormatter | Same as standard | Debug-level system logs |
| simple | built-in logging.Formatter | %(message)s | Raw message only (used by summary file handler) |
| human_readable¹ | SingleLineFormatter | %(message)s | (Optional alias for simple) human-readable logs |

¹ We recommend aliasing simple as human_readable for clarity.

All formatters inherit a global logging.Formatter.converter that converts UTC timestamps into Eastern Time.

## 4. Handlers

Every file handler is a prepend handler (PrependFileHandler) with:

- Rotation: midnight, backupCount=30
- Encoding: UTF-8
- Flush + fsync semantics to guarantee durability.

| Handler Name | Formatter | Filename | Usage |
|--------------|-----------|----------|-------|
| console | standard | n/a (stdout) | All INFO+ system logs |
| orchestrator_file | standard | logs/orchestrator.log | Orchestrator |
| fetch_cache_file | detailed | logs/pure_json_fetch.log | JSON cache |
| fetch_data_file | detailed | logs/fetch/fetch_data.log | Data fetching |
| merge_logic_file | detailed | logs/fetch/merge_logic.log | Merging logic |
| summary_json_file | standard | logs/summary/summary_json.logger | JSON summaries |
| memory_monitor_file | standard | logs/memory/memory_monitor.log | Memory usage monitor |
| logger_monitor_file | detailed | logs/monitor/logger_monitor.log | Logger introspection |
| alerts_file | standard | logs/alerts/alerter_main.log | Global alerts |
| match_summary_file | simple¹ | logs/summary/pipeline.log | Human-readable match summaries |

¹ No leading timestamps; the summary module prints its own centered date header.

## 5. Loggers

All static logger entries live in LOGGING_CONFIG["loggers"]. Key types:

### A. System / Orchestration / Monitoring

- **Names**: orchestrator, pure_json_fetch, fetch_data, merge_logic, memory_monitor, logger_monitor, etc.
- **Handlers**: console + respective file handler
- **Level**: INFO (or DEBUG for detailed logs)

### B. Alerts

- **Name**: alerter_main (plus any alert.<name> configured via configure_alert_logger)
- **Handlers**: alerts_file, console
- **Formatter**: standard
- **Custom per-alert**: can call configure_alert_logger("my_alert") if needed.

### C. Match-Summary (Human-Readable)

- **Name**: summary.pipeline (plus summary.orchestration, summary.summary_json)
- **Handlers**: match_summary_file (no console by default)
- **Formatter**: simple (or alias human_readable)
- **Level**: INFO
- **Access via**:
  ```python
  import logging
  logger = logging.getLogger("summary.pipeline")
  ```

## 6. Static vs. Dynamic

- **Static‐only approach (current recommendation)**:  
  All loggers declared in LOGGING_CONFIG; no helper functions required.  
  — This ensures consistency, prevents helper drift, and makes config fully visible in one place.

- **Dynamic helpers (retired for summary)**:  
  We removed get_summary_logger() and the special branch in _central_getLogger.

- **Fallback for unknown names**:  
  Any logging.getLogger("anything_else") still gets a console + prepend-file handler via get_logger().

## 7. Migration Steps

- **Static Configuration**
  - Added "summary.pipeline" to LOGGING_CONFIG["loggers"]
  - Pointed its handler to match_summary_file with formatter simple.

- **Remove Helpers**
  - Commented out or deleted get_summary_logger()
  - Removed the elif name.startswith("summary."): branch in _central_getLogger.

- **Update Call Sites**
  ```diff
  - from log_config import get_summary_logger
  - logger = get_summary_logger("pipeline")
  + import logging
  + logger = logging.getLogger("summary.pipeline")
  ```

- **Clean Up**
  - Deleted unused "summary_formatter" entry if not used elsewhere.
  - Ensured match_summary_file's filename matches the actual logs/summary/pipeline.log path.

- **Restart & Verify**
  ```bash
  python3 orchestrate_complete.py
  head -n 5 logs/summary/pipeline.log
  ```
  — new entries appear without leading timestamps, only the centered human date header and match details.

## 8. Verification & Testing

- **Static config audit**:
  ```bash
  grep -RIn '"summary.pipeline"' log_config.py
  grep -RIn '"match_summary_file"' log_config.py
  ```

- **Runtime introspection**:
  ```python
  import logging, log_config
  log_config.configure_logging()
  lg = logging.getLogger("summary.pipeline")
  print([type(h).__name__ + " → fmt:" + getattr(h.formatter,"_fmt","") for h in lg.handlers])
  ```

- **Live output check**:
  ```python
  lg.info("🚀 TEST")
  head -n2 logs/summary/pipeline.log
  # Expect: "🚀 TEST" with no timestamp prefix.
  ```

## 9. Future Extensions

- **Alert-specific formatters**: introduce "alert_formatter" in LOGGING_CONFIG["formatters"] for color-coded alerts.
- **Per-alert files**: use configure_alert_logger("my_alert") to spin up logs/alerts/my_alert.log.
- **Additional static loggers**: add new entries to LOGGING_CONFIG["loggers"]—no code churn elsewhere.

That's it!

With everything centralized in one place, you can tweak any aspect of your logging—raw message formatting, timestamp style, rotation policies, handler targets—just by editing log_config.py. No more hunting through dozens of modules for stray .addHandler() calls or inline Formatter() instantiations.

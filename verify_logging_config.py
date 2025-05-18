#!/usr/bin/env python3
"""
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
"""

import sys
import os
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
            # Find expected format based on logger and handler type
            if lname.startswith('summary.'):
                # Special case: summary loggers always use simple format
                exp = SIMPLE_FMT
            elif isinstance(h, logging.StreamHandler):
                exp = CANONICAL
            else:
                # For file handlers, determine by handler name
                found = False
                for hkey, spec in expected_handlers.items():
                    # Match by handler type and the handler in logger's handlers list
                    if type(h).__name__ in spec['class'] and hkey in expected_loggers.get(lname, []):
                        # Get formatter from the handler spec
                        formatter_name = spec.get('formatter')
                        exp = expected_fmt.get(formatter_name, CANONICAL)
                        found = True
                        break
                if not found:
                    # Default fallback
                    exp = CANONICAL
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

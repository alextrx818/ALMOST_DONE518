# Logger Usage Analysis Report
Generated on: 2025-05-18 01:26:30
Total files analyzed: 38

## Summary
- Direct logging.getLogger calls: 18
- Custom get_logger calls: 14
- Logger variable shadowing: 3
- Custom handler setup: 13
- Wildcard imports: 0

## Files with Direct logging.getLogger Calls

### /root/Complete_Seperate/logging_diagnostic.py
- Line 61 at module level: get_logger(None)

### /root/Complete_Seperate/memory_monitor.py
- Line 32 at module level: get_logger(memory_monitor)

### /root/Complete_Seperate/log_config.py
- Line 337 in get_logger: get_logger(name)
- Line 358 in create_custom_logger: get_logger(name)
- Line 410 in configure_alert_logger: get_logger(alert_name)
- Line 427 in configure_alert_logger: get_logger(alert_name)
- Line 449 in cleanup_handlers: get_logger(None)
- Line 450 in cleanup_handlers: get_logger(name)
- Line 562 in get_summary_logger: get_logger(summary)
- Line 631 in test_logging_rules: get_logger(prepend_test)

### /root/Complete_Seperate/pure_json_fetch_cache.py
- Line 86 in _setup_logger: get_logger(pure_json_fetch)
- Line 107 in _setup_logger: get_logger(fetch_data)

### /root/Complete_Seperate/merge_logic.py
- Line 26 in setup_logger: get_logger(merge_logic)

### /root/Complete_Seperate/test_logging_rules.py
- Line 47 at module level: get_logger(prepend_test)

### /root/Complete_Seperate/Alerts/alerter_main.py
- Line 87 at module level: get_logger(None)
- Line 480 in _initialize_alert: get_logger(file_base)

### /root/Complete_Seperate/Alerts/base_alert.py
- Line 65 in __init__: get_logger(name)

### /root/Complete_Seperate/tests/test_logging_system.py
- Line 38 in test_strict_mode_validation: get_logger(unexpected_test_logger)

## Files with Logger Shadowing

### /root/Complete_Seperate/combined_match_summary.py
- Line 77 in function test_header_alignment: shadows module-level logger
- Line 209 in function write_combined_match_summary: shadows module-level logger

### /root/Complete_Seperate/orchestrate_complete.py
- Line 271 in function timed: shadows module-level logger

## Files with Custom Handler Setup

### /root/Complete_Seperate/logging_diagnostic.py
- Line 84 at module level: test_logger.addHandler()

### /root/Complete_Seperate/memory_monitor.py
- Line 50 at module level: monitor_logger.addHandler()
- Line 51 at module level: monitor_logger.addHandler()

### /root/Complete_Seperate/log_config.py
- Line 639 in test_logging_rules: test_logger.addHandler()

### /root/Complete_Seperate/pure_json_fetch_cache.py
- Line 103 in _setup_logger: log.addHandler()
- Line 104 in _setup_logger: log.addHandler()
- Line 118 in _setup_logger: fetch_logger.addHandler()

### /root/Complete_Seperate/merge_logic.py
- Line 43 in setup_logger: log.addHandler()
- Line 44 in setup_logger: log.addHandler()

### /root/Complete_Seperate/test_logging_rules.py
- Line 56 at module level: test_logger.addHandler()

### /root/Complete_Seperate/Alerts/alerter_main.py
- Line 91 at module level: root_logger.addHandler()

### /root/Complete_Seperate/Alerts/base_alert.py
- Line 76 in __init__: None.addHandler()

### /root/Complete_Seperate/tests/test_logging_system.py
- Line 104 in test_timestamp_formatting: test_logger.addHandler()
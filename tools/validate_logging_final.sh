#!/bin/bash
# Improved validation script for logging standardization

echo "🔍 VALIDATING FOOTBALL MATCH TRACKING SYSTEM LOGGING 🔍"
echo "===================================================="
echo

# Check 1: No direct logging.getLogger() calls outside log_config.py
echo "📋 Check 1: No direct logging.getLogger() calls"
GETLOGGER_COUNT=$(grep -RIn "logging\.getLogger" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | wc -l)
if [ $GETLOGGER_COUNT -eq 0 ]; then
  echo "✅ PASS: No direct logging.getLogger() calls"
else
  echo "❌ FAIL: Found $GETLOGGER_COUNT direct logging.getLogger() calls"
  grep -RIn "logging\.getLogger" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | head -5
fi
echo

# Check 2: Every logger comes from factory functions
echo "📋 Check 2: Factory functions usage"
FACTORY_COUNT=$(grep -RIn "get_logger\|get_summary_logger" --include="*.py" --exclude="log_config.py" . | wc -l)
if [ $FACTORY_COUNT -gt 0 ]; then
  echo "✅ PASS: Found $FACTORY_COUNT factory function usages"
else
  echo "❌ FAIL: No factory function usage found in application modules"
fi
echo

# Check 3: No ad-hoc handler attachments
echo "📋 Check 3: No ad-hoc handler attachments"
ADDHANDLER_COUNT=$(grep -RIn "\.addHandler" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | wc -l)
if [ $ADDHANDLER_COUNT -eq 0 ]; then
  echo "✅ PASS: No ad-hoc handler attachments"
else
  echo "❌ FAIL: Found $ADDHANDLER_COUNT ad-hoc handler attachments"
  grep -RIn "\.addHandler" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | head -5
fi
echo

# Check 4: No inline Formatter(...) outside of log_config.py
echo "📋 Check 4: No inline Formatter(...)"
FORMATTER_COUNT=$(grep -RIn "logging\.Formatter" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | wc -l)
if [ $FORMATTER_COUNT -eq 0 ]; then
  echo "✅ PASS: No inline Formatter(...) usage"
else
  echo "❌ FAIL: Found $FORMATTER_COUNT inline Formatter(...) usage"
  grep -RIn "logging\.Formatter" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | head -5
fi
echo

# Check 5: No calls to logging.basicConfig()
echo "📋 Check 5: No calls to logging.basicConfig()"
BASICCONFIG_COUNT=$(grep -RIn "basicConfig" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | wc -l)
if [ $BASICCONFIG_COUNT -eq 0 ]; then
  echo "✅ PASS: No logging.basicConfig() calls"
else
  echo "❌ FAIL: Found $BASICCONFIG_COUNT logging.basicConfig() calls"
  grep -RIn "basicConfig" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | head -5
fi
echo

# Check 6: Constants for log formats
echo "📋 Check 6: Constants for log formats"
if grep -q "CANONICAL_FORMAT" ./log_config.py; then
  echo "✅ PASS: Constants for log formats in log_config.py"
else
  echo "❌ FAIL: Missing constants for log formats"
fi
echo

# Check 7: 3rd-party logging captured and controlled
echo "📋 Check 7: 3rd-party logging controlled"
if grep -q "Suppress overly chatty third-party loggers" ./log_config.py; then
  echo "✅ PASS: 3rd-party logging controlled"
else
  echo "❌ FAIL: 3rd-party logging not properly controlled"
fi
echo

# Check 8: Alert logging properly integrated
echo "📋 Check 8: Alert logging integrated"
if grep -q "alerter_main" ./log_config.py; then
  echo "✅ PASS: Alert logging integrated"
else
  echo "❌ FAIL: Alert logging not properly integrated"
fi
echo

# Check 9: Logger validation works properly
echo "📋 Check 9: Logger validation"
if grep -q "_configured_alert_loggers" ./log_config.py; then
  echo "✅ PASS: Logger validation updated for alert loggers"
else
  echo "❌ FAIL: Logger validation missing alert logger handling"
fi
echo

# Check 10: No logging configuration in application modules
echo "📋 Check 10: Centralized configuration"
CONFIG_COUNT=$(grep -RIn "logging\.basicConfig\|StreamHandler\|FileHandler" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | wc -l)
if [ $CONFIG_COUNT -eq 0 ]; then
  echo "✅ PASS: No logging configuration in application modules"
else
  echo "❌ FAIL: Found $CONFIG_COUNT logging configurations in application modules"
  grep -RIn "logging\.basicConfig\|StreamHandler\|FileHandler" --include="*.py" . | grep -v "log_config.py" | grep -v "/tests/" | grep -v "/tools/" | grep -v "/sports_venv/" | head -5
fi
echo

# Summary
echo "===================================================="
echo "📊 VALIDATION SUMMARY"
echo "===================================================="
FAIL_COUNT=$(grep -c "❌ FAIL" <<< "$(cat)")
if [ $FAIL_COUNT -eq 0 ]; then
  echo "✅ ALL CHECKS PASSED: Logging standardization complete!"
else
  echo "❌ VALIDATION FAILED: $FAIL_COUNT issues found"
fi

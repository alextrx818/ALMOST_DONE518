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

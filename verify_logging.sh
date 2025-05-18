#!/usr/bin/env bash
set -euo pipefail

echo
echo "========================================"
echo "  Football Tracking System: Logging Audit"
echo "========================================"
echo

# 1. Syntax & Basic Imports
echo "1. Syntax & Basic Imports"
python3 -m py_compile log_config.py 2>/dev/null && echo " ✅ log_config.py compiles" || echo " ❌ log_config.py syntax error"
python3 -m py_compile orchestrate_complete.py 2>/dev/null && echo " ✅ orchestrate_complete.py compiles" || echo " ❌ orchestrate_complete.py syntax error"
python3 -c "import log_config, orchestrate_complete" 2>/dev/null && echo " ✅ modules import OK" || echo " ❌ module import failed"

echo
# 2. Static Logging Config in log_config.py
echo "2. Static Logging Config in log_config.py"

echo -n "  2.1 No Legacy Helpers: "
if grep -RIn "def get_summary_logger" log_config.py >/dev/null; then
  echo "❌ get_summary_logger still present"
else
  echo "✅ get_summary_logger gone"
fi
if grep -RIn "class StepTimestampFilter" log_config.py >/dev/null; then
  echo "❌ StepTimestampFilter still present"
else
  echo "✅ StepTimestampFilter gone"
fi

echo -n "  2.2 PrependFileHandler & TZ: "
grep -RIn "^class PrependFileHandler" log_config.py >/dev/null && echo "✅ PrependFileHandler present" || echo "❌ PrependFileHandler missing"
grep -RIn "Formatter.converter" log_config.py >/dev/null && echo "✅ Formatter.converter → eastern_time_converter" || echo "❌ Formatter.converter missing"

echo -n "  2.3 Formatters block: "
if grep -RIn '"formatters"' -A5 log_config.py | grep -E '"standard"|"detailed"|"simple"' >/dev/null; then
  echo "✅ standard, detailed, simple present"
else
  echo "❌ missing one of standard/detailed/simple"
fi

echo -n "  2.4 Handlers block: "
if grep -RIn '"handlers"' -A12 log_config.py | grep -E '"console"|"orchestrator_file"|"match_summary_file"|"summary_json_file"' >/dev/null; then
  echo "✅ handlers block OK"
else
  echo "❌ one of console/orchestrator_file/match_summary_file/summary_json_file missing"
fi

echo "    ↳ match_summary_file details:"
if sed -n '/"match_summary_file"/,/"backupCount"/p' log_config.py \
     | grep '"filename".*pipeline.log' \
   && grep -RIn '"formatter"[[:space:]]*:[[:space:]]*"simple"' log_config.py >/dev/null; then
  echo "      ✅ points to pipeline.log + simple"
else
  echo "      ❌ misconfigured"
fi

echo -n "    ↳ summary_json_file details: "
if grep -RIn '"summary_json_file"' -A5 log_config.py | grep '"filename".*summary_json.logger' >/dev/null; then
  echo "✅ summary_json_file → summary_json.logger"
else
  echo "❌ missing or misnamed"
fi

echo -n "  2.5 Loggers block: "
if grep -RIn '"loggers"' -A20 log_config.py | grep -E '"orchestrator"|"summary\.pipeline"|"summary\.orchestration"|"summary_json"' >/dev/null; then
  echo "✅ core loggers present"
else
  echo "❌ missing one of orchestrator/summary.pipeline/summary.orchestration/summary_json"
fi

echo
# 3. Validation Logic Changes
echo "3. Validation Logic Changes"

echo -n "  3.1 IGNORE_PREFIXES updated: "
if grep -RIn "IGNORE_PREFIXES" -A5 log_config.py | grep -E "concurrent\.futures|multiprocessing" >/dev/null; then
  echo "✅ ok"
else
  echo "❌ missing concurrent.futures or multiprocessing"
fi

echo -n "  3.2 SUMMARY_PREFIX exemption: "
if grep -RIn "or name.startswith.*SUMMARY_PREFIX" log_config.py >/dev/null; then
  echo "✅ summary loggers exempted"
else
  echo "❌ exemption missing"
fi

echo -n "  3.3 EXPECTED_LOGGERS list: "
if grep -RIn "EXPECTED_LOGGERS" -A5 log_config.py | grep -E "summary_json|logger_monitor" >/dev/null; then
  echo "✅ summary_json & logger_monitor included"
else
  echo "❌ missing entries"
fi

echo -n "  3.4 Premature return removed: "
if grep -RIn "return True" log_config.py | grep -B2 "check handler count" >/dev/null; then
  echo "❌ stray return True found"
else
  echo "✅ no premature return"
fi

echo
# 4. Orchestrator Code Changes
echo "4. Orchestrator Code Changes"

echo -n "  No get_summary_logger import: "
grep -RIn "get_summary_logger" orchestrate_complete.py >/dev/null && echo "❌ found legacy import" || echo "✅ none"

echo -n "  get_eastern_timestamp() present: "
grep -RIn "def get_eastern_timestamp" orchestrate_complete.py >/dev/null && echo "✅ ok" || echo "❌ missing"

echo -n "  STEP/complete lines patched: "
if grep -RIn 'summary_logger.info.*STEP 1: JSON fetch:' orchestrate_complete.py >/dev/null \
   && grep -RIn 'STEP 2: Merge and enrichment:' orchestrate_complete.py >/dev/null \
   && grep -RIn '✅ Pipeline completed in.*: {get_eastern_timestamp()}' orchestrate_complete.py >/dev/null; then
  echo "✅ patched"
else
  echo "❌ not patched"
fi

echo
# 5. Stray-Factory Checks
echo "5. Stray logging.getLogger() Checks"
FOUND=$(grep -RIn "logging.getLogger" --include="*.py" . | grep -vE "log_config.py|orchestrate_complete.py" || true)
if [ -z "$FOUND" ]; then
  echo " ✅ no stray calls"
else
  echo " ❌ stray calls found:"
  echo "$FOUND"
fi

echo
# 6. Smoke-Run & Log-Output Validation
echo "6. Smoke-Run & Log-Output Validation"
mv logs/summary/pipeline.log logs/summary/pipeline.log.bak 2>/dev/null || true
./run_pipeline.sh > run_output.log 2>&1 || true
sleep 1

echo " → First 6 lines of new pipeline.log:"
head -n6 logs/summary/pipeline.log || echo "   (log is empty)"

echo -n " → No ISO dates in body: "
if grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}' logs/summary/pipeline.log >/dev/null; then
  echo "❌ found ISO dates"
else
  echo "✅ none"
fi

echo
# 7. Runtime Handler & Formatter Check
echo "7. Runtime Handler & Formatter Check"
python3 -c "import logging, log_config; log_config.configure_logging(); print(' ✅ runtime configuration OK')" 2>/dev/null || echo " ❌ runtime configuration failed"

echo
echo "========================================"
echo "  Logging configuration audit complete!"
echo "========================================"

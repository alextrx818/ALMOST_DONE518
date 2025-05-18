#!/usr/bin/env bash
set -e

# directories to ignore
EXCLUDES="--exclude-dir=logs --exclude-dir=tools --exclude-dir=sports_venv --exclude-dir=diagnostics"

echo "🔍 Checking for stray logging calls outside log_config.py …"

patterns=(
  "logging\.getLogger"
  "logging\.basicConfig"
  "\.addHandler"
  "logging\.Formatter\("
  "StreamHandler"
  "FileHandler"
)

for pat in "${patterns[@]}"; do
  echo -n "  • Pattern '$pat'… "
  # search everywhere except log_config.py and excluded dirs
  results=$(grep -RInE $EXCLUDES "$pat" . | grep -v "log_config\.py" || true)
  if [[ -z "$results" ]]; then
    echo "✅"
  else
    echo "❌ Found in:"
    echo "$results"
    echo
  fi
done

echo "All checks done.  If none of the patterns above listed any files, you're fully centralized in log_config.py!"

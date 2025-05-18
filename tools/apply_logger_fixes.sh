#!/bin/bash
# Logger Refactoring Script
# This script applies common logging fixes to Python files
# in the Football Match Tracking System

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Football Match Tracking System - Logger Refactoring"
echo "=================================================="
echo "Starting systematic logging fixes..."

# Function to backup a file before modifying
backup_file() {
  local file=$1
  cp "$file" "${file}.bak"
  echo "Created backup: ${file}.bak"
}

# Function to apply fixes to a file
fix_file() {
  local file=$1
  local filename=$(basename "$file")
  local module_name="${filename%.py}"
  
  echo "Processing $file..."
  
  # Backup the file
  backup_file "$file"
  
  # Fix 1: Replace direct get_logger(__name__) with get_logger
  if grep -q "get_logger(__name__)" "$file"; then
    # Make sure the import is present
    if ! grep -q "from log_config import get_logger" "$file"; then
      # Add import at the top, after other imports
      sed -i '1s/^/from log_config import get_logger\n/' "$file"
      echo "  - Added import: from log_config import get_logger"
    fi
    
    # Replace the direct getLogger call
    sed -i "s/get_logger(__name__)/get_logger(\"$module_name\")/g" "$file"
    echo "  - Replaced get_logger(__name__) with get_logger(\"$module_name\")"
  fi
  
  # Fix 2: Replace get_logger('summary') with get_summary_logger()
  if grep -q "logging.getLogger.*summary" "$file"; then
    # Make sure the import is present
    if ! grep -q "from log_config import get_summary_logger" "$file"; then
      # Add import at the top, after other imports
      sed -i '1s/^/from log_config import get_summary_logger\n/' "$file"
      echo "  - Added import: from log_config import get_summary_logger"
    fi
    
    # Replace the direct getLogger call
    sed -i "s/get_logger(['\"]summary['\"])/get_summary_logger()/g" "$file"
    echo "  - Replaced get_logger('summary') with get_summary_logger()"
  fi
  
  # Fix 3: Fix logger shadowing in run_complete_pipeline
  if [[ "$filename" == "orchestrate_complete.py" ]]; then
    if grep -q "logger = logging.getLogger" "$file"; then
      sed -i "s/logger = logging.getLogger/summary_logger = get_summary_logger()/g" "$file"
      sed -i "s/logger\.info/summary_logger.info/g" "$file"
      sed -i "s/logger\.debug/summary_logger.debug/g" "$file"
      sed -i "s/logger\.warning/summary_logger.warning/g" "$file"
      sed -i "s/logger\.error/summary_logger.error/g" "$file"
      echo "  - Fixed logger shadowing in orchestrate_complete.py"
    fi
  fi
  
  # Fix 4: Check for direct handler additions
  if grep -q "addHandler" "$file"; then
    echo "  - WARNING: File contains direct handler additions. Manual review needed."
  fi
}

# Find all Python files and process them
find "$PROJECT_ROOT" -name "*.py" -not -path "*/\.*" -not -path "*/sports_venv/*" | while read -r file; do
  fix_file "$file"
done

echo ""
echo "Logger refactoring completed!"
echo "============================"
echo "1. Review the .bak files for any issues"
echo "2. Run tests to verify functionality"
echo "3. Once verified, you can remove the .bak files"

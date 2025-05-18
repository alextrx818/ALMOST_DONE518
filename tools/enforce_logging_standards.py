#!/usr/bin/env python3
"""
enforce_logging_standards.py - Script to enforce logging standardization rules

This script runs a series of diagnostic checks to ensure all logging adheres to
the centralized configuration standards. It will fail (non-zero exit code) if
any violations are detected. Designed to be run as part of CI/pre-commit hooks.

Usage:
    python enforce_logging_standards.py [--fix]

Options:
    --fix    Attempt to automatically fix some common violations
"""

import os
import sys
import re
import subprocess
import json
from pathlib import Path

# Ensure we can import from the parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import core logging configuration for validation
from log_config import validate_logger_configuration, LOGGING_CONFIG

# Define constants for the diagnostic checks
DIAGNOSTICS_DIR = Path(__file__).parent.parent / "diagnostics"

# Production code checks should exclude these patterns
EXCLUDE_DIRS = [
    "--exclude-dir=logs", 
    "--exclude-dir=sports_venv", 
    "--exclude-dir=diagnostics",
    "--exclude-dir=.git",
    "--exclude-dir=tools",   # Diagnostic tools have special logging needs
    "--exclude-dir=tests",  # Test files often need special logging
    "--exclude=*test_*.py", # Skip all test files
    "--exclude=*_test.py",  # Skip test files with suffix
    "--exclude=*.bak", 
    "--exclude=*.pyc",
    "--exclude=*.md",
    "--exclude=*.log",
    "--exclude=*.txt",
    "--exclude=*logger_*.py" # Logger diagnostic utils
]

# Files/directories where direct logging access is allowed
ALLOWED_DIRECT_ACCESS = [
    "log_config.py",         # Central logging configuration
    "logging_diagnostic.py", # Diagnostic script
    "logger_monitor.py",     # Monitoring script
    "tools/",               # Special tools for logging
    "tests/"                # Test files
]

PROJECT_ROOT = Path(__file__).parent.parent

# Create diagnostics directory if it doesn't exist
DIAGNOSTICS_DIR.mkdir(exist_ok=True)


def run_diagnostic(cmd, output_file, name, allowed_in=None):
    """Run a diagnostic command and capture its output to a file.
    
    Args:
        cmd: Command to run as a list of strings
        output_file: Path to write output to
        name: Human-readable name for this check
        allowed_in: List of files where violations are allowed (e.g., log_config.py itself)
    
    Returns:
        tuple: (success, report)
            - success: Boolean indicating if no violations were found
            - report: Text report describing violations, if any
    """
    # line 44-46: Run the command and capture output
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout

    # line 49-56: Remove allowed exceptions
    if output:
        filtered_lines = []
        for line in output.splitlines():
            # Check both explicitly provided allowed_in and global ALLOWED_DIRECT_ACCESS
            is_allowed = False
            
            # Check if line matches any allowed pattern
            if allowed_in:
                is_allowed = any(allowed_file in line for allowed_file in allowed_in)
                
            if not is_allowed:
                is_allowed = any(allowed_file in line for allowed_file in ALLOWED_DIRECT_ACCESS)
                
            if not is_allowed:
                filtered_lines.append(line)
                
        output = "\n".join(filtered_lines)

    # line 57-58: Write filtered output to file
    output_path = DIAGNOSTICS_DIR / output_file
    with open(output_path, "w") as f:
        f.write(output)

    # line 62-71: Prepare report
    if output.strip():
        # Violations detected
        report = f"❌ {name} check failed. Violations found:\n"
        for i, line in enumerate(output.splitlines()[:10]):  # Limit to first 10 violations
            report += f"   {i+1}. {line}\n"
        if len(output.splitlines()) > 10:
            report += f"   ... and {len(output.splitlines()) - 10} more violations\n"
        report += f"   See {output_path} for full details\n"
        return False, report
    else:
        # No violations
        return True, f"✅ {name} check passed\n"


def clean_old_diagnostics():
    """Clean up any existing diagnostic files to prevent nested references"""
    # line 120-125: Remove any existing diagnostic files to prevent recursion
    for diag_file in DIAGNOSTICS_DIR.glob('*.txt'):
        try:
            os.remove(diag_file)
        except Exception:
            pass
    return True

def main():
    """Run all diagnostic checks and report results."""
    # line 134-135: Clean old diagnostic files
    clean_old_diagnostics()
    
    # line 137-138: Optionally clean up backup files
    if '--clean-backups' in sys.argv:
        for backup_file in Path('.').glob('**/*.bak'):
            try:
                os.remove(backup_file)
                print(f"Removed backup file: {backup_file}")
            except Exception as e:
                print(f"Could not remove {backup_file}: {e}")
    
    # line 146-147: Prepare for checking
    all_passed = True
    report = ["# Logging Standards Compliance Report\n"]
    
    # line 87-105: Check 1 - Direct use of stdlib logging.getLogger
    success, check_report = run_diagnostic(
        ["grep", "-RIn", "logging\\.getLogger", "."] + EXCLUDE_DIRS,
        "01_direct_getLogger.txt",
        "Direct stdlib API usage",
        allowed_in=["log_config.py", "tests/", "tools/"]
    )
    all_passed = all_passed and success
    report.append(check_report)
    
    # line 108-125: Check 2 - Verify use of central factory methods
    success, check_report = run_diagnostic(
        ["grep", "-RInE", "get_logger|get_summary_logger", "."],
        "02_central_factory_usage.txt",
        "Central factory method usage",
    )
    # This is an informational check, not a failure case
    report.append(f"ℹ️ {len(open(DIAGNOSTICS_DIR / '02_central_factory_usage.txt').readlines())} "
                  f"instances of factory methods found\n")
    
    # line 128-138: Check 3 - Ad-hoc handler attachments
    success, check_report = run_diagnostic(
        ["grep", "-RIn", "\\.addHandler", "."] + EXCLUDE_DIRS,
        "03_direct_addHandler.txt",
        "Ad-hoc handler attachments",
        allowed_in=["log_config.py", "tests/"]
    )
    all_passed = all_passed and success
    report.append(check_report)
    
    # line 141-151: Check 4 - Inline formatter definitions
    success, check_report = run_diagnostic(
        ["grep", "-RIn", "logging\\.Formatter", "."],
        "04_inline_Formatter.txt",
        "Inline formatter definitions",
        allowed_in=["log_config.py", "tests/"]
    )
    all_passed = all_passed and success
    report.append(check_report)
    
    # line 154-164: Check 5 - basicConfig usage
    success, check_report = run_diagnostic(
        ["grep", "-RIn", "basicConfig", "."],
        "05_basicConfig.txt",
        "basicConfig usage",
        allowed_in=["tests/"]
    )
    all_passed = all_passed and success
    report.append(check_report)
    
    # line 167-182: Check 6 - Configure logging invocation
    success, check_report = run_diagnostic(
        ["grep", "-RIn", "configure_logging", "orchestrate_complete.py"],
        "06_entrypoint_configure.txt",
        "Entry point configuration"
    )
    # This check passes if configure_logging appears at least once
    entrypoint_file = DIAGNOSTICS_DIR / "06_entrypoint_configure.txt"
    entrypoint_check = os.path.exists(entrypoint_file) and os.path.getsize(entrypoint_file) > 0
    if not entrypoint_check:
        report.append("❌ Entry point not calling configure_logging()\n")
        all_passed = False
    else:
        report.append("✅ Entry point properly configures logging\n")
    
    # line 185-213: Check 7 - Runtime logger validation
    try:
        # Import the logging configuration without affecting existing loggers
        from log_config import validate_logger_configuration
        validation_result = validate_logger_configuration()
        
        if validation_result:
            report.append("✅ Runtime logger validation passed\n")
        else:
            report.append("❌ Runtime logger validation failed\n")
            all_passed = False
    except Exception as e:
        report.append(f"❌ Runtime logger validation check failed with error: {str(e)}\n")
        all_passed = False
    
    # line 216-227: Print summary and exit with appropriate code
    print("\n".join(report))
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL LOGGING STANDARDS CHECKS PASSED\n")
        return 0
    else:
        print("❌ LOGGING STANDARDS VIOLATIONS DETECTED\n")
        print("Run with --fix to attempt automatic fixes (not yet implemented)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

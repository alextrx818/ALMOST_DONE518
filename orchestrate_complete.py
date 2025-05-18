#!/usr/bin/env python3
"""
NOTE: All logging configuration is centralized in log_config.py
      Do not add new loggers directly - use get_logger() or get_summary_logger()

orchestrate_complete.py - Main orchestration script for the sports betting data pipeline

IMPORTANT:
- This script MUST ONLY be started via the run_pipeline.sh shell script located in the same directory.
- The run_pipeline.sh script is the ONLY supported startup method for the sports bot project.
- run_pipeline.sh will activate the required external Python virtual environment (./sports_venv/) before running this script.
- Manual or direct invocation of orchestrate_complete.py (e.g., python3 orchestrate_complete.py) is NOT supported and may result in improper operation.

VIRTUAL ENVIRONMENT:
- The required Python virtual environment is located at ./sports_venv/.
- All dependencies must be installed in this environment.
- run_pipeline.sh will ensure the environment is activated before execution.

Please refer to the README.md for further details.
"""

"""
=================================================================================
COMPLETE SPORTS BOT PROJECT STRUCTURE AND DATA FLOW
=================================================================================

Project Architecture
-------------------
The sports bot in this folder is a modular football match data processing pipeline
with two parallel output branches working on the same underlying data.

Main Components & Data Flow
-------------------------
1. orchestrate_complete.py: Core orchestration engine that controls the workflow
2. run_pipeline.sh: Shell wrapper script that executes the orchestration engine
3. pure_json_fetch_cache.py: Fetches & caches API data → outputs to full_match_cache.json
4. merge_logic.py: Combines and enriches match data → outputs to merge_logic.json

Complete Execution Pipeline
-------------------------
STEP 1: JSON fetch via pure_json_fetch_cache.py
   ↓
STEP 2: Prepare data for merge (unpack from cache)
   ↓
STEP 3: Run merge logic via merge_logic.py (creates enriched match data)
   ↓
STEP 4: Save output files (merge_logic.json, complete_cache_output.json)
   ↓
STEP 4.25: Generate summary JSON via summary_json_generator.py (creates summary_data.json)
   ↓
   ├────────────────────┐
   ↓                    ↓
STEP 4.5: Alert scan   STEP 5: Print summaries
   ↓                    ↓
AlerterMain system     combined_match_summary.py
   ↓                    ↓
OU3.py detection       complete_summary.logger
   ↓
OU3.logger

Key Fork in Processing Pipeline
----------------------------
After data is fetched, merged and saved, the pipeline splits into two parallel branches:

Branch 1: Alert System (STEP 4.5)
- Purpose: Monitor matches for high Over/Under betting lines (≥3.0)
- Key Files: 
  - Alerts/alerter_main.py: Alert orchestration system
  - Alerts/OU3.py: Over/Under line detection module
  - Alerts/*.logger: Alert log files
- Output: Alerts logged and potentially sent as notifications

Branch 2: Summary Generation (STEP 5)
- Purpose: Generate human-readable formatted match summaries
- Key Files:
  - combined_match_summary.py: Formats match data for human readability
  - complete_summary.logger: Stores formatted match summaries
- Output: Comprehensive match summaries with formatted sections

Data Files & Outputs
------------------
- full_match_cache.json - Raw API data from fetch operation
- merge_logic.json - Enriched match data after processing
- summary_data.json - Structured JSON with summary fields
- complete_summary.logger - Human-readable match summaries

Log Files:
- orchestrator.log - Main orchestration process log
- summary_json.logger - Log of summary JSON generation
- OU3.logger - Log of Over/Under alerts

This architecture provides clear separation of concerns, making the system
modular and maintainable while allowing both alert and summary generation
to work independently on the same underlying data.
"""

import asyncio
import gc
import json
import logging
import os
import psutil
import pytz

def get_eastern_timestamp():
    """Generate an Eastern Time timestamp for log messages."""
    from datetime import datetime
    return datetime.now(pytz.timezone("America/New_York")).strftime("%m/%d/%Y %I:%M:%S %p %Z")

import signal
import subprocess
import sys
import datetime
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Import memory monitoring tool
sys.path.append(str(Path(__file__).parent))
import memory_monitor
import logger_monitor

# Setup logging before other imports to ensure proper configuration
from log_config import get_logger, validate_logger_configuration, cleanup_handlers, configure_logging, validate_logger_count

# Explicitly configure logging at application startup
configure_logging()

# Module-level logger initialized via centralized logging system
# Using get_logger() ensures proper handler setup and validation

class Timer:
    """Context manager for timing code blocks."""
    def __init__(self, name=None):
        self.name = name or "block"
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        # Use the module-level logger
        get_logger("orchestrate_complete").info(f"⏱️  {self.name} took {elapsed:.2f} seconds")
        return False

# Define custom exception for pipeline errors
class PipelineError(Exception):
    """Custom exception for pipeline errors that require immediate abort."""
    pass

# Cache the timezone object at module scope
TZ = pytz.timezone("America/New_York")

# Import fetch and merge modules
sys.path.append(Path(__file__).parent.as_posix())
import pure_json_fetch_cache
from merge_logic import merge_all_matches
from combined_match_summary import write_combined_match_summary
from combined_match_summary import get_status_description

# Import summary JSON generator
from summary_json_generator import write_summary_json

# Import the alert system
from Alerts.alerter_main import AlerterMain
from Alerts.base_alert import Alert  # Base class for all alerts

# Define the complete status_id sequence in logical order:
DESIRED_STATUS_ORDER = ["1","2","3","4","5","6","7","8","9","10","11","12","13","14"]

def sort_by_status(matches):
    """
    Sort matches by status_id according to DESIRED_STATUS_ORDER.
    This is the central sorting function used by all components that need match ordering.
    
    Args:
        matches: List of match dictionaries with status_id keys
        
    Returns:
        Sorted list of matches
    """
    return sorted(
        matches,
        key=lambda m: (
            DESIRED_STATUS_ORDER.index(m.get("status_id")) 
            if m.get("status_id") in DESIRED_STATUS_ORDER 
            else len(DESIRED_STATUS_ORDER)
        )
    )

# Constants
BASE_DIR = Path(__file__).parent
FULL_CACHE_FILE = BASE_DIR / "full_match_cache.json"
OUTPUT_FILE = BASE_DIR / "complete_cache_output.json"
MERGE_OUTPUT_FILE = BASE_DIR / "merge_logic.json"
SUMMARY_SCRIPT = BASE_DIR / "combined_match_summary.py"

# Get pre-configured logger from centralized configuration
logger = get_logger("orchestrator")

if __name__ == "__main__":
    # Enforce running through run_pipeline.sh
    import sys
    import os
    
    # Check if we're running in the virtual environment
    venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sports_venv')
    is_in_venv = hasattr(sys, 'real_prefix') or \
                 (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or \
                 os.environ.get('VIRTUAL_ENV') is not None
    
    if not is_in_venv:
        print("ERROR: This script must be run through run_pipeline.sh to ensure proper environment setup.")
        print("Please use: ./run_pipeline.sh")
        sys.exit(1)
    
    # Set timezone to Eastern

# Import the centralized logging configuration
import logging
from log_config import cleanup_handlers
import atexit

# Get the centralized summary logger
# Use static configuration for summary loggers
summary_logger = logging.getLogger("summary.orchestration")

# Register cleanup function to be called on program exit
atexit.register(cleanup_handlers)

# Import and run logging validation to ensure all loggers comply with standards
if __name__ == "__main__":
    try:
        # First run the enhanced internal validation that comes with log_config
        logger.info("Performing comprehensive logging system validation...")
        config_valid = validate_logger_configuration()
        
        # Then run the external validation module for additional checks
        from tools.validate_logging import validate_logging_compliance
        compliance_valid = validate_logging_compliance(strict_mode=False)
        
        # Log the combined results
        if config_valid and compliance_valid:
            logger.info("✅ Logging system validation passed completely")
        elif config_valid:
            logger.warning("⚠️ Logging configuration valid but compliance check found issues")
        elif compliance_valid:
            logger.warning("⚠️ Logging compliance checks passed but configuration validation found issues")
        else:
            logger.warning("⚠️ Multiple logging validation issues found. See output above.")
    except Exception as e:
        logger.warning(f"⚠️ Logging validation encountered an error: {str(e)}")
        logger.debug(f"Validation error details: {traceback.format_exc()}")


def get_eastern_time():
    # Use the cached timezone object for better performance
    now = datetime.now(TZ)
    return now.strftime("%m/%d/%Y %I:%M:%S %p %Z")

# Prepending logic moved to wrapper script

def unpack_full_cache(full_cache: dict):
    live = {"results": []}
    details = {}
    odds = {}
    team_cache = {}
    comp_cache = {}
    country_map = {}

    for m in full_cache.get("matches", []):
        mid = m.get("match_id")
        basic = m.get("basic_info", {})
        live["results"].append(basic)
        details[mid] = m.get("details", {})
        odds[mid] = m.get("odds", {})

        # teams
        for role in ("home_team", "away_team"):
            t = m.get("enriched", {}).get(role, {})
            tid = t.get("id")
            if tid:
                team_cache[tid] = t

        # competition
        comp = m.get("enriched", {}).get("competition", {})
        cid = comp.get("id")
        if cid:
            comp_cache[cid] = comp

        # country
        country_id = comp.get("country_id")
        country_name = m.get("metadata", {}).get("country_name")
        if country_id and country_name:
            country_map[country_id] = country_name

    return live, details, odds, team_cache, comp_cache, country_map

def timeit(method):
    """Decorator to time functions."""
    async def timed(*args, **kw):
        # Get logger from the module with a non-shadowing name
        timer_logger = get_logger("orchestrate_complete")
        ts = time.time()
        result = await method(*args, **kw)
        te = time.time()
        timer_logger.info(f"⏱️  {method.__name__} took {te-ts:.2f} seconds")
        return result
    return timed

@timeit
async def run_complete_pipeline():
    """Run the complete pipeline consisting of all steps."""
    start_time = time.time()
    
    # Log cache sizes and memory stats
    memory_monitor.log_cache_sizes()
    memory_monitor.check_file_descriptor_count()
    
    with Timer("Full pipeline"):
        # STEP 1: Fetch data
        with Timer("JSON fetch"):
            # line 311: Updated to use required name parameter
            summary_logger = logging.getLogger("summary.pipeline")
            summary_logger.info(f"STEP 1: JSON fetch: {get_eastern_timestamp()}")
            match_ids = await pure_json_fetch_cache.main()
        
        # STEP 2: Process and merge data
        with Timer("Merge and enrichment"):
            summary_logger.info(f"STEP 2: Merge and enrichment: {get_eastern_timestamp()}")
            # Test error handling by forcing a file not found error
            test_error_handling = False  # Set to True to test error handling
            if test_error_handling:
                error_msg = "TEST ERROR: Simulating missing file for error handling verification"
                summary_logger.error(error_msg)
                summary_logger.error("This is a test of the pipeline error handling system.")
                raise PipelineError(error_msg)
                
            try:
                # Use faster JSON parsing if available
                try:
                    import orjson
                    full_cache = orjson.loads(FULL_CACHE_FILE.read_bytes())
                except ImportError:
                    full_cache = json.loads(FULL_CACHE_FILE.read_text())
            except FileNotFoundError:
                error_msg = f"Missing file: {FULL_CACHE_FILE}"
                summary_logger.error(error_msg)
                summary_logger.error("Cannot proceed without the full cache file. Aborting pipeline.")
                raise PipelineError(error_msg)
            except (json.JSONDecodeError, ValueError) as e:
                error_msg = f"Invalid JSON in {FULL_CACHE_FILE}: {e}"
                summary_logger.error(error_msg)
                summary_logger.error("The full cache file contains invalid JSON. Aborting pipeline.")
                raise PipelineError(error_msg)
            
            # Process data
            live_data, details_by_id, odds_by_id, team_cache, comp_cache, country_map = unpack_full_cache(full_cache)
            
            with Timer("merge_all_matches"):
                merged_data = merge_all_matches(
                    live_data, details_by_id, odds_by_id,
                    team_cache, comp_cache, country_map
                )
            
            merged_data = [{"created_at": get_eastern_time(), **m} for m in merged_data]
            merged_data = sort_by_status(merged_data)
            
            summary_logger.debug(f"Merged {len(merged_data)} records")
        
        # STEP 3: Write match summaries
        with Timer("Writing match summaries"):
            summary_logger.debug("STEP 3: Writing match summaries")
            try:
                from combined_match_summary import format_match_summary
                
                # Prepare all summaries first
                reversed_matches = list(reversed(merged_data))
                summaries = []
                
                for idx, match in enumerate(reversed_matches, 1):
                    summary = format_match_summary(match, idx, len(reversed_matches))
                    if not summary.startswith("Error"):
                        summaries.append(summary)
                
                # Write all summaries in one go
                if summaries:
                    summary_logger.info("\n\n".join(summaries) + "\n")
                    
            except Exception as e:
                # Use the module-level logger for error reporting
                summary_logger.error(f"Error in batch writing match summaries: {e}")
                import traceback
                summary_logger.error(traceback.format_exc())
        
        # STEP 4: Generate summary JSON
        with Timer("Generate summary JSON"):
            summary_logger.debug("STEP 4: Generate summary JSON")
            summary_json = write_summary_json(merged_data)
        
        # STEP 5: Run alerters
        with Timer("Running alerters"):
            summary_logger.debug("STEP 5: Run alerters")
            await run_alerters(summary_json, match_ids)
        
        # Final stats
        total_time = time.time() - start_time
        summary_logger.info(f"✅ Pipeline completed in {total_time:.2f} seconds: {get_eastern_timestamp()}")
        
        # Dump garbage collection stats
        memory_monitor.dump_gc_stats()

# NOTE FOR AI BOT:
# This is the single entry point for alerts in the main pipeline.
# Do not invoke AlerterMain.run() here—always call run_alerters(summary_json, match_ids).

async def run_alerters(summary_json, match_ids=None):
    """
    Process matches through all registered alerts and handle notifications.
    
    Args:
        summary_json: Dictionary containing match data to process
        match_ids: Optional list of match IDs to process. If None, processes all matches.
    """
    # Create AlerterMain instance with auto-discovery of all Alert subclasses
    try:
        from Alerts.alerts_config import ALERT_PARAMS as alert_params
    except ImportError:
        logger.warning("Could not import alerts_config.py, using default parameters")
        alert_params = {
            "OverUnderAlert": {"threshold": 3.0}  # Default fallback configuration
        }
    
    alerter = AlerterMain(auto_discover=True, alert_params=alert_params)
    
    # Process all matches with AlerterMain
    summary_logger.info(f"Processing {len(summary_json['matches'])} matches through AlerterMain")
    summary_logger.info(f"Using {len(alerter.alerts)} auto-discovered alerts")
    
    # Filter matches if match_ids is provided
    matches_to_process = summary_json['matches']
    if match_ids:
        matches_to_process = [
            m for m in matches_to_process 
            if (m.get("match_id") or m.get("id") or "") in match_ids
        ]
        summary_logger.info(f"Filtered to {len(matches_to_process)} matches based on match_ids")
    
    # Process each match through all alerts
    for match in matches_to_process:
        # Ensure we have a match_id in the expected format
        match_id = str(match.get("match_id") or match.get("id") or "")
        if not match_id:
            continue
            
        # Check each registered alert
        for alert in alerter.alerts:
            # Get the file base ID for this alert for deduplication
            file_base_id = alerter.alert_file_bases[id(alert)]
            
            # Skip if we've already processed this match for this alert
            if match_id in alerter.seen_ids[file_base_id]:
                continue
                
            # Check if this alert triggers for the current match
            notice = alert.safe_check(match)
            
            if notice:
                # Format and process the alert
                try:
                    # Format the alert message using AlerterMain's formatter
                    message = alerter.format_alert(match, notice, alert.name)
                    
                    # Log the alert
                    summary_logger.debug(f"Alert {alert.name} triggered for match {match_id}")
                    alert.logger.info(message)
                    
                    # Send notification through the alerter's notification system
                    alerter.send_notification(message)
                    
                    # Mark as seen for deduplication
                    alerter.seen_ids[file_base_id].add(match_id)
                    alerter._save_seen(file_base_id)
                    
                except Exception as e:
                    summary_logger.error(
                        f"Error processing alert {alert.name} for match {match_id}: {str(e)}",
                        exc_info=True
                    )

def print_instructions():
    """Print instructions for scheduling the pipeline using cron"""
    logger.info("""
=== SCHEDULING INSTRUCTIONS ===

To run this pipeline every 30 seconds using cron:

1. Create a shell script wrapper (run_pipeline.sh):
   #!/bin/bash
   cd /root/CascadeProjects/sports_bot/football/main
   python orchestrate_complete.py

2. Make it executable: chmod +x run_pipeline.sh

3. Add to crontab (every minute, it will handle its own rate limiting):
   * * * * * /root/CascadeProjects/sports_bot/football/main/run_pipeline.sh

Alternatively, use a simple while loop in a shell script:
   while true; do
     python orchestrate_complete.py
     sleep 30
   done
""")

if __name__ == "__main__":
    # Enforce running through run_pipeline.sh by checking if virtual environment is active
    if not os.getenv("VIRTUAL_ENV"):
        print("ERROR: Please launch via run_pipeline.sh")
        logger.error("ERROR: Script was launched directly without activating virtual environment")
        logger.error("This script MUST be launched via run_pipeline.sh to ensure proper environment setup")
        sys.exit(1)
    
    # Initialize process and memory monitoring
    proc = psutil.Process(os.getpid())
    start_mem = proc.memory_info().rss / (1024*1024)
    logger.info(f"Starting memory: {start_mem:.1f} MB")
    
    # Check for open file descriptors
    try:
        fd_count = len(os.listdir(f"/proc/{proc.pid}/fd"))
        logger.info(f"Initial FD count: {fd_count}")
    except Exception as e:
        logger.warning(f"Could not check file descriptors: {e}")
    
    # Validate initial logger and handler counts if not disabled
    logger.info("Validating initial logger and handler counts...")
    if os.environ.get('DISABLE_LOGGER_VALIDATION') != '1':
        if not validate_logger_count():
            logger.error("Logger validation failed! Exiting to prevent memory leaks.")
            sys.exit(1)
    else:
        logger.warning("Logger validation is disabled via DISABLE_LOGGER_VALIDATION=1")
    
    logger.info(f"Initial logger count: {len(logging.Logger.manager.loggerDict)}")
    logger.info("Initial logger validation passed.")
    
    try:
        # Set up single run mode for production/cron use
        logger.info("\n===== RUNNING PIPELINE =====")
        
        # Start memory monitoring
        memory_monitor.start_cycle_monitoring()
        
        # Run the pipeline
        asyncio.run(run_complete_pipeline())
        
        # End memory monitoring
        memory_monitor.end_cycle_monitoring()
        
        # Print current memory usage after pipeline run
        curr_mem = proc.memory_info().rss / (1024*1024)
        delta_mem = curr_mem - start_mem
        logger.info(f"Current memory: {curr_mem:.1f} MB ({delta_mem:+.1f} MB from start)")
        
        # Validate logger and handler counts after run if not disabled
        logger.info("Validating logger and handler counts after run...")
        if os.environ.get('DISABLE_LOGGER_VALIDATION') != '1':
            if not validate_logger_count():
                summary_logger.error("Logger validation failed after run! Exiting to prevent memory leaks.")
                sys.exit(1)
        else:
            summary_logger.warning("Logger validation is disabled via DISABLE_LOGGER_VALIDATION=1")
            
        logger.info(f"Current logger count: {len(logging.Logger.manager.loggerDict)}")
        
        # Count top types of objects with performance measurement
        import time
        t0 = time.perf_counter()
        objs = gc.get_objects()
        t1 = time.perf_counter()
        logger.info(f"[DIAG] GC introspection: {len(objs)} objects in {t1-t0:.2f}s")
        
        # Only analyze in detail if it's reasonably fast
        if t1-t0 < 0.5:  # Only process if taking less than 0.5 seconds
            counts = {}
            for obj in objs:
                obj_type = type(obj).__name__
                if obj_type not in counts:
                    counts[obj_type] = 0
                counts[obj_type] += 1
            
            # Log top 10 most common object types
            top_types = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
            summary_logger.debug(f"Top 10 object types: {top_types}")
        else:
            summary_logger.warning(f"[DIAG] Skipping detailed object analysis as GC introspection took {t1-t0:.2f}s")
            # Use sampling instead
            import itertools
            sample_counts = {}
            for obj in itertools.islice(objs, 1000):  # Sample first 1000 objects
                obj_type = type(obj).__name__
                if obj_type not in sample_counts:
                    sample_counts[obj_type] = 0
                sample_counts[obj_type] += 1
            
            # Log sampled object types
            sampled_types = sorted(sample_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            summary_logger.debug(f"Top 10 object types (sampled): {sampled_types}")
        
        logger.info("\n===== ALL CYCLES COMPLETE =====")
        logger.info("Memory monitoring complete. Check logs/memory/memory_monitor.log for detailed results.")
        
        # Log final logger count
        logger.info(f"Final logger count: {len(logging.Logger.manager.loggerDict)}")
    
    except PipelineError as e:
        logger.error(f"CRITICAL PIPELINE ERROR: {e}")
        logger.error("Pipeline aborted due to critical error.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error during pipeline execution: {e}")
    
    finally:
        # Always perform cleanup of all handlers
        logger.info("[DIAG] About to cleanup handlers")
        cleanup_handlers()
        logger.info("[DIAG] Finished cleanup handlers")
        
        # Count top types of objects with performance measurement
        import time
        t0 = time.perf_counter()
        objs = gc.get_objects()
        t1 = time.perf_counter()
        logger.info(f"[DIAG] GC introspection: {len(objs)} objects in {t1-t0:.2f}s")
        
        # Only proceed with object counting if it's reasonably fast
        if t1-t0 < 0.5:  # Only process if taking less than 0.5 seconds
            counts = {}
            for obj in objs:
                t = type(obj).__name__
                counts[t] = counts.get(t, 0) + 1
            for t, cnt in sorted(counts.items(), key=lambda x: -x[1])[:5]:
                summary_logger.debug(f"  {t}: {cnt}")
        else:
            summary_logger.warning(f"[DIAG] Skipping detailed object analysis as GC introspection took {t1-t0:.2f}s")
            # Use sampling instead
            import itertools
            sample_counts = {}
            for obj in itertools.islice(objs, 1000):  # Sample first 1000 objects
                t = type(obj).__name__
                sample_counts[t] = sample_counts.get(t, 0) + 1
            summary_logger.debug("[DIAG] Top 5 object types (from 1000-object sample):")
            for t, cnt in sorted(sample_counts.items(), key=lambda x: -x[1])[:5]:
                summary_logger.debug(f"  {t}: {cnt} (sampled)")

#!/usr/bin/env python3
"""
memory_monitor.py - Comprehensive memory monitoring for the sports_bot system.

This module provides functions to track memory usage, cache sizes, logger instances,
file descriptors, and object counts during execution of the orchestrate_complete
pipeline. It's designed to help identify memory leaks and growth patterns.

Usage:
    1. Import this module in orchestrate_complete.py
    2. Call start_cycle_monitoring() at the beginning of each processing cycle
    3. Call end_cycle_monitoring() at the end of each cycle
    4. Call log_cache_sizes() after caches are loaded or updated
    5. Use dump_gc_stats() to analyze garbage collection at key points

Author: Sports Bot Team
Date: 2025-05-15
"""

import os
import sys
import gc
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import psutil

# Create a dedicated logger for memory monitoring
# Use centralized logging configuration
from log_config import get_logger

# Get properly configured logger
monitor_logger = get_logger("memory_monitor")
monitor_logger.setLevel(logging.INFO)

# Global variables to track state
_cycle_start_time = None
_cycle_start_rss = None
_cycle_count = 0
_baseline_loggers = set()
_baseline_objects = {}

def _initialize_baselines():
    """Capture initial state of loggers and objects to detect growth."""
    global _baseline_loggers, _baseline_objects
    
    # Capture initial logger set
    _baseline_loggers = set(logging.Logger.manager.loggerDict.keys())
    monitor_logger.info(f"Baseline loggers: {len(_baseline_loggers)}")
    
    # Capture initial object counts
    _baseline_objects = {}
    for obj in gc.get_objects():
        t = type(obj).__name__
        _baseline_objects[t] = _baseline_objects.get(t, 0) + 1
    
    monitor_logger.info(f"Baseline object types: {len(_baseline_objects)}")
    for t, cnt in sorted(_baseline_objects.items(), key=lambda x: -x[1])[:5]:
        monitor_logger.info(f"  {t}: {cnt}")

def start_cycle_monitoring():
    """Call at the beginning of each processing cycle to start monitoring."""
    global _cycle_start_time, _cycle_start_rss, _cycle_count
    
    # Initialize baselines on first run
    if _cycle_count == 0:
        _initialize_baselines()
    
    # Get current process
    proc = psutil.Process()
    
    # Record start time and RSS
    _cycle_start_time = time.time()
    _cycle_start_rss = proc.memory_info().rss / (1024*1024)
    
    # Log cycle start
    monitor_logger.info(f"[CYCLE {_cycle_count}] ===== CYCLE START =====")
    monitor_logger.info(f"[CYCLE {_cycle_count}] Start RSS: {_cycle_start_rss:.1f} MB")
    
    # Check file descriptors
    try:
        fd_count = len(os.listdir(f"/proc/{proc.pid}/fd"))
        monitor_logger.info(f"[CYCLE {_cycle_count}] Start FD count: {fd_count}")
    except (FileNotFoundError, PermissionError) as e:
        monitor_logger.warning(f"[CYCLE {_cycle_count}] Cannot check FDs: {e}")

def end_cycle_monitoring():
    """Call at the end of each processing cycle to log memory stats."""
    global _cycle_start_time, _cycle_start_rss, _cycle_count
    
    if _cycle_start_time is None:
        monitor_logger.warning("end_cycle_monitoring() called without start_cycle_monitoring()")
        return
    
    # Get current process
    proc = psutil.Process()
    
    # Calculate cycle duration
    duration = time.time() - _cycle_start_time
    
    # Get end RSS and calculate delta
    end_rss = proc.memory_info().rss / (1024*1024)
    delta_rss = end_rss - _cycle_start_rss
    
    # Log cycle completion stats
    monitor_logger.info(f"[CYCLE {_cycle_count}] ===== CYCLE END =====")
    monitor_logger.info(f"[CYCLE {_cycle_count}] Duration: {duration:.2f} seconds")
    monitor_logger.info(f"[CYCLE {_cycle_count}] End RSS: {end_rss:.1f} MB")
    monitor_logger.info(f"[CYCLE {_cycle_count}] Delta RSS: {delta_rss:+.1f} MB")
    
    # Check file descriptors
    try:
        fd_count = len(os.listdir(f"/proc/{proc.pid}/fd"))
        monitor_logger.info(f"[CYCLE {_cycle_count}] End FD count: {fd_count}")
    except (FileNotFoundError, PermissionError) as e:
        monitor_logger.warning(f"[CYCLE {_cycle_count}] Cannot check FDs: {e}")
    
    # Check for new loggers
    current_loggers = set(logging.Logger.manager.loggerDict.keys())
    new_loggers = current_loggers - _baseline_loggers
    if new_loggers:
        monitor_logger.warning(f"[CYCLE {_cycle_count}] New loggers: {len(new_loggers)}")
        monitor_logger.warning(f"[CYCLE {_cycle_count}] New logger names: {sorted(new_loggers)[:10]}")
    
    monitor_logger.info(f"[CYCLE {_cycle_count}] Total loggers: {len(current_loggers)}")
    
    # Dump GC stats at the end of each cycle
    dump_gc_stats(cycle=_cycle_count)
    
    # Increment cycle count for next run
    _cycle_count += 1
    
    # Reset start time
    _cycle_start_time = None

def log_cache_sizes(teams_cache=None, comp_cache=None, country_map=None, custom_caches=None):
    """Log the sizes of various cache structures.
    
    Args:
        teams_cache: Team cache dictionary/TTLCache
        comp_cache: Competition cache dictionary/TTLCache
        country_map: Country mapping dictionary
        custom_caches: Dictionary of {cache_name: cache_object} for additional caches
    """
    if teams_cache is not None:
        monitor_logger.info(f"Teams cache size: {len(teams_cache)} entries")
    
    if comp_cache is not None:
        monitor_logger.info(f"Competitions cache size: {len(comp_cache)} entries")
    
    if country_map is not None:
        monitor_logger.info(f"Country map size: {len(country_map)} entries")
    
    if custom_caches:
        for name, cache in custom_caches.items():
            if hasattr(cache, "__len__"):
                monitor_logger.info(f"{name} cache size: {len(cache)} entries")
            else:
                monitor_logger.info(f"{name} cache: Unable to determine size")

def dump_logger_stats():
    """Dump statistics about logger instances."""
    loggers = list(logging.Logger.manager.loggerDict.keys())
    monitor_logger.info(f"Active loggers: {len(loggers)}")
    if loggers:
        monitor_logger.info(f"Logger names (first 10): {sorted(loggers)[:10]}")
    
    # Check for handlers that might buffer data
    memory_handlers = []
    for name, logger in logging.Logger.manager.loggerDict.items():
        if not hasattr(logger, "handlers"):
            continue
        
        for handler in logger.handlers:
            handler_type = type(handler).__name__
            if "MemoryHandler" in handler_type or "Buffer" in handler_type:
                memory_handlers.append((name, handler_type))
    
    if memory_handlers:
        monitor_logger.warning(f"Found potential memory-buffering handlers: {memory_handlers}")

def dump_gc_stats(cycle=None):
    """Dump garbage collection statistics and top object counts."""
    # Force garbage collection
    collected = gc.collect()
    
    # Get counts of objects by type
    counts = {}
    for obj in gc.get_objects():
        t = type(obj).__name__
        counts[t] = counts.get(t, 0) + 1
    
    # Compare with baseline
    object_deltas = {}
    for t, count in counts.items():
        baseline = _baseline_objects.get(t, 0)
        delta = count - baseline
        if delta != 0:
            object_deltas[t] = delta
    
    # Log the top object types
    prefix = f"[CYCLE {cycle}] " if cycle is not None else ""
    monitor_logger.info(f"{prefix}GC collected {collected} objects")
    monitor_logger.info(f"{prefix}Top 5 object types by count:")
    for t, cnt in sorted(counts.items(), key=lambda x: -x[1])[:5]:
        monitor_logger.info(f"{prefix}  {t}: {cnt}")
    
    # Log the top growing object types
    monitor_logger.info(f"{prefix}Top 5 growing object types:")
    for t, delta in sorted(object_deltas.items(), key=lambda x: -abs(x[1]))[:5]:
        if delta > 0:
            monitor_logger.warning(f"{prefix}  {t}: +{delta}")
        else:
            monitor_logger.info(f"{prefix}  {t}: {delta}")
    
    return counts

def check_file_descriptor_count():
    """Check the number of open file descriptors for the current process."""
    proc = psutil.Process()
    try:
        fd_count = len(os.listdir(f"/proc/{proc.pid}/fd"))
        monitor_logger.info(f"Open file descriptors: {fd_count}")
        return fd_count
    except (FileNotFoundError, PermissionError) as e:
        monitor_logger.warning(f"Cannot check file descriptors: {e}")
        return None

if __name__ == "__main__":
    """When run directly, show current memory usage."""
    monitor_logger.info("=== Memory Monitor Test ===")
    proc = psutil.Process()
    rss = proc.memory_info().rss / (1024*1024)
    monitor_logger.info(f"Current RSS: {rss:.1f} MB")
    
    check_file_descriptor_count()
    dump_logger_stats()
    dump_gc_stats()
    
    monitor_logger.info("To use this module, import it in orchestrate_complete.py")
    monitor_logger.info("and add calls to start_cycle_monitoring() and end_cycle_monitoring()")

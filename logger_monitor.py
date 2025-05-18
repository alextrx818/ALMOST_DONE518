#!/usr/bin/env python3
"""
logger_monitor.py - Monitor logger and handler counts during orchestration cycles

This utility tracks the growth of loggers and handlers over multiple cycles to identify
memory leaks in the logging system.
"""

from log_config import configure_logging, get_logger
import json
import os
from pathlib import Path
import time
from datetime import datetime

# Ensure central logging is configured before any logger is retrieved
configure_logging()

# Use the central factory to get your module‐level logger
logger = get_logger("memory_monitor")

class LoggerMonitor:
    """Tracks logger and handler counts across multiple orchestration cycles."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.results_path = self.base_dir / "logs" / "monitor" / "logger_monitor_results.json"
        self.results_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Initialize results dictionary
        self.results = {
            "cycles": [],
            "summary": {}
        }
    
    def capture_logger_state(self, cycle_number=None):
        """Capture the current state of all loggers in the system."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get current logger dictionary
        loggers_dict = logging.Logger.manager.loggerDict
        
        # Track total logger count
        total_loggers = len(loggers_dict)
        
        # Track handler count for each logger
        logger_handlers = {}
        total_handlers = 0
        
        for name, logger in loggers_dict.items():
            # Some entries in loggerDict might be PlaceHolders, not actual loggers
            handler_count = len(getattr(logger, 'handlers', []))
            logger_handlers[name] = handler_count
            total_handlers += handler_count
        
        # Get detailed info for loggers with handlers
        loggers_with_handlers = {}
        for name, logger in loggers_dict.items():
            handlers = getattr(logger, 'handlers', [])
            if handlers:
                handler_info = []
                for handler in handlers:
                    handler_type = type(handler).__name__
                    file_path = getattr(handler, 'baseFilename', 'N/A') if hasattr(handler, 'baseFilename') else 'N/A'
                    handler_info.append({
                        "type": handler_type,
                        "file_path": file_path,
                        "level": logging.getLevelName(handler.level) if hasattr(handler, 'level') else 'N/A'
                    })
                loggers_with_handlers[name] = handler_info
        
        state = {
            "timestamp": timestamp,
            "cycle_number": cycle_number,
            "total_loggers": total_loggers,
            "total_handlers": total_handlers,
            "logger_handlers": logger_handlers,
            "loggers_with_handlers": loggers_with_handlers
        }
        
        return state
    
    def start_monitoring(self, num_cycles=10, interval_seconds=0):
        """Monitor logger state over multiple cycles."""
        logging.info(f"Starting logger monitoring for {num_cycles} cycles")
        
        # Capture initial state
        initial_state = self.capture_logger_state(cycle_number=0)
        self.results["cycles"].append(initial_state)
        logging.info(f"Initial state: {initial_state['total_loggers']} loggers, {initial_state['total_handlers']} handlers")
        
        # Set initial state as baseline
        baseline_loggers = set(initial_state["logger_handlers"].keys())
        baseline_handlers = initial_state["total_handlers"]
        
        for cycle in range(1, num_cycles + 1):
            if interval_seconds > 0:
                logging.info(f"Waiting {interval_seconds} seconds before cycle {cycle}")
                time.sleep(interval_seconds)
            
            # Run whatever would normally run in a cycle
            # (In this case we're just monitoring existing loggers)
            
            # Capture state after cycle
            state = self.capture_logger_state(cycle_number=cycle)
            self.results["cycles"].append(state)
            
            # Calculate delta from baseline
            current_loggers = set(state["logger_handlers"].keys())
            new_loggers = current_loggers - baseline_loggers
            handler_delta = state["total_handlers"] - baseline_handlers
            
            # Log differences
            logging.info(f"Cycle {cycle}: {state['total_loggers']} loggers ({len(new_loggers)} new), {state['total_handlers']} handlers ({handler_delta:+d})")
            
            if new_loggers:
                logging.info(f"  New loggers: {sorted(new_loggers)}")
            
            # Check for handler count changes
            for name, count in state["logger_handlers"].items():
                prev_count = initial_state["logger_handlers"].get(name, 0)
                if count != prev_count:
                    logging.warning(f"  Logger '{name}' handler count changed: {prev_count} → {count}")
        
        # Generate summary
        self.results["summary"] = {
            "start_time": self.results["cycles"][0]["timestamp"],
            "end_time": self.results["cycles"][-1]["timestamp"],
            "cycles_monitored": num_cycles,
            "initial_logger_count": initial_state["total_loggers"],
            "final_logger_count": self.results["cycles"][-1]["total_loggers"],
            "initial_handler_count": initial_state["total_handlers"],
            "final_handler_count": self.results["cycles"][-1]["total_handlers"],
            "new_loggers": list(set(self.results["cycles"][-1]["logger_handlers"].keys()) - baseline_loggers),
            "loggers_with_handler_growth": []
        }
        
        # Find loggers with handler growth
        for name in self.results["cycles"][-1]["logger_handlers"]:
            initial_count = initial_state["logger_handlers"].get(name, 0)
            final_count = self.results["cycles"][-1]["logger_handlers"][name]
            if final_count > initial_count:
                self.results["summary"]["loggers_with_handler_growth"].append({
                    "name": name,
                    "initial_count": initial_count,
                    "final_count": final_count,
                    "growth": final_count - initial_count
                })
        
        # Save results to file
        with open(self.results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logging.info(f"Logger monitoring complete. Results saved to {self.results_path}")
        
        # Print summary
        if self.results["summary"]["new_loggers"]:
            logging.warning(f"New loggers created: {self.results['summary']['new_loggers']}")
        
        if self.results["summary"]["loggers_with_handler_growth"]:
            logging.warning("Loggers with handler growth detected:")
            for logger_info in self.results["summary"]["loggers_with_handler_growth"]:
                logging.warning(f"  {logger_info['name']}: {logger_info['initial_count']} → {logger_info['final_count']} ({logger_info['growth']:+d})")
        
        handler_growth = self.results["summary"]["final_handler_count"] - self.results["summary"]["initial_handler_count"]
        logging.info(f"Total handler growth: {handler_growth:+d}")
        
        return self.results

def integrate_with_orchestrate():
    """Create code to integrate this monitor with orchestrate_complete.py"""
    integration_code = """
# Add this at the top of orchestrate_complete.py after other imports
import logger_monitor

# Add this before the main loop in orchestrate_complete.py
monitor = logger_monitor.LoggerMonitor()
initial_state = monitor.capture_logger_state(cycle_number=0)
print(f"Initial logger count: {initial_state['total_loggers']}")
print(f"Initial handler count: {initial_state['total_handlers']}")

# Add this after each cycle in the loop
cycle_state = monitor.capture_logger_state(cycle_number=cycle_count)
print(f"Cycle {cycle_count} logger count: {cycle_state['total_loggers']}")
print(f"Cycle {cycle_count} handler count: {cycle_state['total_handlers']}")
"""
    print(integration_code)

def patch_alerter_main():
    """Create code to fix handler accumulation in alerter_main.py"""
    fix_code = """
# Inside AlerterMain.run() method, replace the alerter_logger creation with:
from log_config import get_logger

# Use centralized logger factory to get properly configured logger
alert_logger = get_logger(self.alert_file_bases[id(alert)])

# Optional: If you need to use a specific formatter for this logger
# you can still customize it, but the basic handlers are already attached
# REMOVED inline Formatter – use get_standard_formatter()

# Note: No need to manually create and attach handlers - get_logger() does this automatically
# with standardized formatting and consistent behavior across the application
"""
    print(fix_code)

if __name__ == "__main__":
    # Run standalone monitoring
    monitor = LoggerMonitor()
    results = monitor.start_monitoring(num_cycles=5, interval_seconds=1)
    
    # Display integration code
    print("\nTo integrate with orchestrate_complete.py:")
    integrate_with_orchestrate()
    
    # Display patch for alerter_main.py
    print("\nTo fix handler accumulation in alerter_main.py:")
    patch_alerter_main()

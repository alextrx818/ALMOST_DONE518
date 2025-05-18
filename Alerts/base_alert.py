#!/usr/bin/env python3
# base_alert.py - Abstract base class for all alert satellites
#
# IMPORTANT: Before modifying this file or creating new alerts, refer to:
#   /Alerts/README_ALERT_SUBSYSTEM.md for complete architecture documentation
"""
This module defines the abstract base class that all alert satellites must extend.

Key features:
1. Standardized interface for all alerts through the abstract check() method
2. Centralized error handling via the safe_check() wrapper
3. Consistent logging through auto-configured loggers
4. Integration with the global timezone and status ordering rules

To create a new alert satellite:
1. Create a new file in the Alerts directory (e.g., my_alert.py)
2. Define a class that extends Alert 
3. Implement the required check(match) method
4. The alert will be auto-discovered and integrated into the pipeline

Example:
    class MyNewAlert(Alert):
        def __init__(self, some_param=default_value):
            super().__init__(name="MyAlert")
            self.some_param = some_param
            
        def check(self, match):
            # Your alert logic here
            if condition_met:
                return {"type": "MyAlert", "value": some_value}
            return None
"""

# NOTE FOR AI BOT:
# To create a new alert scanner, simply drop a .py file in this Alerts/ folder,
# define a class that subclasses Alert, and implement check(match). No other
# files need touching—you'll be auto‐discovered.


import abc
import traceback
from typing import Dict, Optional, Union, Any

# Use the central logger factory instead of direct logging
from log_config import get_logger


class Alert(abc.ABC):
    """
    Abstract base class that all alert satellites must extend.
    
    This class enforces a standard interface for all alerts and provides
    common error handling through the safe_check wrapper.
    """
    
    def __init__(self, name: str, debug: bool = False):
        """
        Initialize a new alert with a human-readable name.
        
        Args:
            name: Human-readable name for this alert type
            debug: Whether to enable detailed debug logging to a file
        """
        from pathlib import Path
        
        self.name = name
        # Use standardized logger name convention for alerts
        self.logger = get_logger(f"alert.{name}")
        
        # Set debug level if requested
        if debug:
            self.logger.setLevel(logging.DEBUG)
    
    @abc.abstractmethod
    def check(self, match: Dict[str, Any]) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Check if the match meets this alert's criteria.
        
        This method must be implemented by all subclasses.
        
        Args:
            match: A dictionary containing the match data
            
        Returns:
            None if no alert is triggered, or a payload (string or dict) if criteria are met
        """
        pass
    
    def safe_check(self, match: Dict[str, Any]) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Safely execute the check method with error handling.
        
        This wrapper ensures that exceptions in satellite alerts won't crash the
        entire pipeline.
        
        Args:
            match: Match data dictionary
            
        Returns:
            None if no alert or if an error occurred, otherwise the alert payload
        """
        match_id = match.get("match_id", match.get("id", "unknown"))
        
        try:
            return self.check(match)
        except Exception as e:
            # Log detailed error info but continue processing
            error_msg = f"Error in {self.name} alert checking match {match_id}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            return None

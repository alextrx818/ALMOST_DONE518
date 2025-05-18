#!/usr/bin/env python3
# alerter_main.py - Main alerter interface
#
# IMPORTANT: Before modifying this file or creating new alerts, refer to:
#   /Alerts/README_ALERT_SUBSYSTEM.md for complete architecture documentation

############################################################################
# TEMPORARY DEVELOPER NOTE - ARCHITECTURAL CHANGES (2025-05-15)            #
############################################################################
# Recent changes to the alerting system:                                   #
#                                                                          #
# 1. SEPARATION OF CONCERNS:                                               #
#    - Individual alerters (like OU3.py) now ONLY handle detection logic   #
#    - They return raw data (as dict) instead of formatted messages        #
#    - AlerterMain now handles ALL formatting through format_alert()       #
#                                                                          #
# 2. ALERT DATA FORMAT:                                                    #
#    - Alerters now return structured data like:                           #
#      {                                                                   #
#        "type": "OU3",                                                   #
#        "value": 3.5,                                                    #
#        "threshold": 3.0,                                                #
#        "detail": "Over/Under Line: 3.50"                                #
#      }                                                                   #
#                                                                          #
# 3. CONSISTENT FORMATTING:                                                #
#    - All alerts now use format_match_summary() from format_utils         #
#    - This ensures consistent pretty-printing across all alert types      #
#    - The formatting matches combined_match_summary.logger                #
#                                                                          #
# 4. BACKWARD COMPATIBILITY:                                               #
#    - format_alert() can handle both new dict-based and old string alerts #
#    - This allows gradual migration of other alerters to the new pattern  #
#                                                                          #
############################################################################

import os
import sys
import json
import time
import inspect
import importlib
import importlib.util
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Type, Optional

# Use the central logger factory instead of direct logging
from log_config import get_logger

# Import our base alert class to enable discovery of subclasses
try:
    from .base_alert import Alert
except ImportError:
    # Fallback if importing from relative path fails
    sys.path.append(str(Path(__file__).parent.parent))
    from Alerts.base_alert import Alert
from zoneinfo import ZoneInfo

# Add the parent directory to sys.path to ensure imports work correctly
sys.path.append(str(Path(__file__).parent.parent))
from log_config import configure_alert_logger
from pure_json_fetch_cache import fetch_and_cache
from merge_logic import merge_all_matches

# Local imports with relative path
from .OU3 import OverUnderAlert

# Import specific formatting functions from combined_match_summary
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our custom formatting utilities
try:
    from .format_utils import format_match_summary
except ImportError:
    # Fallback if importing from relative path fails
    from Alerts.format_utils import format_match_summary
    
from combined_match_summary import (
    get_eastern_time, 
    format_odds_display, 
    summarize_environment,
    get_status_description,
    transform_odds,
    API_DATETIME_FORMAT
)

# Use the central logger factory for consistent logging
root_logger = get_logger("alerter_main")
root_logger.setLevel(logging.INFO)

# Telegram configuration with hardcoded credentials from telegram_config.py
TELEGRAM_TOKEN = "7764953908:AAHMpJsw5vKQYPiJGWrj0PgDkztiIgY_dko"
CHAT_ID = "6128359776"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


def send_notification(message: str):
    """Send a Telegram notification."""
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(TELEGRAM_URL, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to send notification: {e}")


def format_match_summary(match):
    """Format match data exactly like combined_match_summary.py does.
    This is a direct duplicate of the formatting code from combined_match_summary.py
    to ensure consistent pretty-printing throughout the system.
    
    Args:
        match: The enriched match object from merge_logic
        
    Returns:
        List of formatted strings representing the match summary
    """
    lines = []
    
    # Headers and basic info
    lines.append("\n----- MATCH SUMMARY -----")
    lines.append("-------------------------")
    lines.append("")
    lines.append(f"Timestamp: {get_eastern_time().strftime(API_DATETIME_FORMAT)}")
    
    # Try both ID formats
    match_id = match.get('id') or match.get('match_id', 'Unknown')
    lines.append(f"Match ID: {match_id}")
    
    # Competition info - handle both string format and object format
    competition = match.get('competition', {})
    comp_id = None
    comp_name = None
    comp_country = None
    
    if isinstance(competition, str):
        # Direct string format
        comp_name = competition
        comp_id = match.get('competition_id', 'Unknown')
        comp_country = match.get('country', 'Unknown Country')
    elif isinstance(competition, dict):
        # Object format
        comp_id = competition.get('id')
        comp_name = competition.get('name')
        comp_country = competition.get('country')
    else:
        # Alternative key formats
        comp_id = match.get('competition_id')
        comp_name = match.get('competition_name')
        comp_country = match.get('country') or match.get('competition_country')
    
    # Apply defaults if still missing
    comp_id = comp_id or 'Unknown'
    comp_name = comp_name or 'Unknown'
    comp_country = comp_country or 'Unknown Country'
    
    lines.append(f"Competition ID: {comp_id}")
    lines.append(f"Competition: {comp_name} ({comp_country})")
    
    # Team names with fallbacks for different structures
    home_team = None
    away_team = None
    
    # String access
    home_team = match.get('home_team')
    away_team = match.get('away_team')
    
    # Object structure access
    if not isinstance(home_team, str) and match.get('home_team', {}).get('name'):
        home_team = match.get('home_team', {}).get('name')
    if not isinstance(away_team, str) and match.get('away_team', {}).get('name'):
        away_team = match.get('away_team', {}).get('name')
    
    # Alternate keys
    home_team = home_team or match.get('home', 'Unknown')
    away_team = away_team or match.get('away', 'Unknown')
    
    lines.append(f"Match: {home_team} vs {away_team}")
    
    # Score handling for both object and array structures
    home_live = 0
    home_ht = 0
    away_live = 0
    away_ht = 0
    
    # Object structure
    score = match.get('score', {})
    if isinstance(score, dict):
        home_live = score.get('home', 0) 
        away_live = score.get('away', 0)
        home_ht = score.get('home_ht', 0)
        away_ht = score.get('away_ht', 0)
    # Array structure (from original data source)
    elif isinstance(score, list) and len(score) > 3:
        hs, as_ = score[2], score[3]
        if isinstance(hs, list) and len(hs) > 1:
            home_live, home_ht = hs[0], hs[1]
        if isinstance(as_, list) and len(as_) > 1:
            away_live, away_ht = as_[0], as_[1]
    
    lines.append(f"Score: {home_live} - {away_live} (HT: {home_ht} - {away_ht})")
    
    # Status with rich description
    status_id = match.get('status_id')
    status = match.get('status', get_status_description(status_id))
    lines.append(f"Status: {status} (Status ID: {status_id})")
    
    # Betting Odds section
    lines.append("\n--- MATCH BETTING ODDS ---")
    lines.append("--------------------------")
    lines.append("")
    odds_data = match.get('odds', {})
    
    # Handle both market array and object structures
    ml_market = None
    spread_market = None
    ou_market = None
    minute = "4"
    
    # Extract markets by type
    markets = odds_data.get('markets', [])
    if markets:
        for market in markets:
            market_type = market.get('type')
            if market_type == 'MONEYLINE':
                ml_market = market
            elif market_type == 'SPREAD':
                spread_market = market
            elif market_type == 'OVER_UNDER':
                ou_market = market
                
        # Format exactly as in example
        odds_lines = []
        
        # Moneyline odds
        if ml_market:
            home = ml_market.get('home', 0)
            draw = ml_market.get('draw', 0)
            away = ml_market.get('away', 0)
            
            # Format to match +130 style
            home_str = f"{int(float(home) * 100):+d}" if home else "+0"
            draw_str = f"{int(float(draw) * 100):+d}" if draw else "+0"
            away_str = f"{int(float(away) * 100):+d}" if away else "+0"
            
            ml_line = f"│ Home  : {home_str} │ Draw  : {draw_str} │ Away  : {away_str} │ (@{minute}')"
            odds_lines.append(ml_line)
        
        # Spread odds
        if spread_market:
            home = spread_market.get('home', 0)
            handicap = spread_market.get('handicap', 0)
            away = spread_market.get('away', 0)
            
            # Format to match -133 style
            home_str = f"{int(float(home) * 100):+d}" if home else "+0"
            handicap_str = f"{float(handicap):.1f}" if handicap else "0.0"
            away_str = f"{int(float(away) * 100):+d}" if away else "+0"
            
            spread_line = f"│ Home  : {home_str} │ Hcap  : {handicap_str} │ Away  : {away_str} │ (@{minute}')"
            odds_lines.append(spread_line)
        
        # Over/Under odds
        if ou_market:
            over = ou_market.get('over', 0)
            line = ou_market.get('line', 0)
            under = ou_market.get('under', 0)
            
            # Format to match -111 style
            over_str = f"{int(float(over) * 100):+d}" if over else "+0"
            line_str = f"{float(line):.1f}" if line else "0.0"
            under_str = f"{int(float(under) * 100):+d}" if under else "+0"
            
            ou_line = f"│ Over  : {over_str} │ Line  : {line_str} │ Under : {under_str} │ (@{minute}')"
            odds_lines.append(ou_line)
            
        # Add all odds lines
        if odds_lines:
            lines.extend(odds_lines)
        else:
            lines.append("No betting odds available")
    else:
        # Try format_odds_display as fallback for any other odds format
        formatted_odds = {
            "ML": transform_odds(odds_data.get("eu", []), "eu"),
            "SPREAD": transform_odds(odds_data.get("asia", []), "asia"),
            "Over/Under": transform_odds(odds_data.get("bs", []), "bs")
        }
        odds_display = format_odds_display(formatted_odds)
        lines.append(odds_display)
    
    # Environment data
    lines.append("\n--- MATCH ENVIRONMENT ---")
    lines.append("-------------------------")
    lines.append("")
    env_data = match.get('environment', {})
    
    # Format environment exactly as in the example
    if isinstance(env_data, dict):
        weather = env_data.get('weather', {})
        if isinstance(weather, dict):
            # Temperature
            if 'temperature' in weather:
                try:
                    temp_c = float(weather['temperature'])
                    temp_f = temp_c * 9/5 + 32
                    lines.append(f"Temperature: {temp_f:.1f}°F")
                except (ValueError, TypeError):
                    pass
            
            # Humidity
            if 'humidity' in weather:
                try:
                    humidity = int(weather['humidity'])
                    lines.append(f"Humidity: {humidity}%")
                except (ValueError, TypeError):
                    pass
            
            # Wind
            if 'wind_speed' in weather:
                try:
                    wind = float(weather['wind_speed'])
                    lines.append(f"Wind: {wind:.1f} mph")
                except (ValueError, TypeError):
                    pass
        else:
            # Fallback to summarize_environment if needed
            env_lines = summarize_environment(env_data)
            lines.extend(env_lines)
    
    return lines


class FutureAlert:
    """Placeholder for future alert logic."""
    def check(self, match: dict) -> str | None:
        # TODO: implement when needed
        return None


class AlerterMain:
    """Orchestrates satellite alerts, manages per-alert state, logging, and dispatches notifications without duplicates."""
    
    # NOTE FOR AI BOT:
    # This method auto‐discovers all subclasses of Alert—you never need to
    # manually import or list them. If you drop a new scanner here, it'll be
    # picked up automatically.
    @classmethod
    def discover_alerts(cls, alert_params=None):
        """
        Auto-discover all Alert subclasses in the Alerts directory.
        
        We auto-discover all BaseAlert subclasses here, instantiate them with any
        provided parameters, and return them for use in the alerter system.
        
        Args:
            alert_params: Optional dict mapping alert class names to init parameters.
                          Example: {"OverUnderAlert": {"threshold": 3.5}}
        
        Returns:
            List of instantiated Alert objects
        """
        alerts_dir = Path(__file__).parent
        alert_classes = {}
        alert_params = alert_params or {}
        discovered_alerts = []
        
        # Use project's logging system for discovery process
        logger = configure_alert_logger("alert_discovery")
        
        # Scan all .py files in the Alerts directory
        for file_path in alerts_dir.glob("*.py"):
            if file_path.name.startswith("__") or file_path.name == "alerter_main.py" or file_path.name == "base_alert.py":
                continue
                
            module_name = file_path.stem
            try:
                # Import the module dynamically
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find all classes in the module that inherit from Alert
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, Alert) and obj != Alert:
                            logger.info(f"Discovered alert class: {name} in {file_path.name}")
                            alert_classes[name] = obj
            except Exception as e:
                logger.error(f"Error importing {file_path.name}: {e}")
        
        # Instantiate each discovered alert with appropriate parameters
        for class_name, alert_class in alert_classes.items():
            try:
                # Get default parameters from class if available
                default_params = getattr(alert_class, 'DEFAULT_PARAMS', {})
                
                # Get parameters for this alert class from config
                config_params = alert_params.get(class_name, {})
                
                # Merge defaults with config params (config takes precedence)
                merged_params = {**default_params, **config_params}
                
                # Instantiate with merged parameters
                alert_instance = alert_class(**merged_params)
                discovered_alerts.append(alert_instance)
                logger.info(f"Instantiated {class_name} with params: {merged_params}")
            except Exception as e:
                logger.error(f"Error instantiating {class_name}: {e}")
                # Continue with other alerts rather than crashing
        
        return discovered_alerts
    
    def __init__(self, alerts=None, auto_discover=True, alert_params=None):
        # NOTE FOR AI BOT:
        # After discovery, we must initialize each alert: set up per‐alert log files
        # and load its <AlertName>.seen.json state. See _initialize_alert() below.
        
        # Auto-discover alerts if requested
        if auto_discover:
            self.alerts = self.discover_alerts(alert_params)
            if alerts:  # Add any explicitly provided alerts
                self.alerts.extend(alerts)
        else:
            self.alerts = alerts or []
            
        self.seen_ids = {}
        # Create Alerts directory path for logs and state files
        self.alerts_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Store file_base mappings for alerts
        self.alert_file_bases = {}
        
        # Initialize each alert with file bases and seen IDs
        for alert in self.alerts:
            self._initialize_alert(alert)
            
    def _initialize_alert(self, alert):
        """Initialize file base, logging, and state for a single alert.
        
        Sets up per-alert logger and loads seen ID state from disk. This encapsulates
        the mapping between alert instance and its corresponding file basis.
        
        Args:
            alert: An instance of a subclass of Alert
        """
        # Determine appropriate alert name for logging and state files
        # Import path may contain slashes, get just the filename
        module_name = alert.__class__.__name__
        # Find the actual .py file that contains this class
        py_file = None
        for file in os.listdir(self.alerts_dir):
            if file.endswith('.py') and not file.startswith('__'):
                # Check if the class is in this file
                file_path = os.path.join(self.alerts_dir, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                    if f'class {module_name}' in content:
                        py_file = file
                        break
        
        # Use the Python filename for logs (without .py extension)
        if py_file:
            file_base = os.path.splitext(py_file)[0]
        else:
            # Fallback to class name if file not found
            file_base = module_name
            
        # Store the file_base mapping for this alert
        self.alert_file_bases[id(alert)] = file_base
            
        # Use the central logger factory with standardized naming convention
        logger = get_logger(f"alert.{file_base}")
        logger.setLevel(logging.INFO)
        # Use same file_base for seen IDs storage
        # Load seen IDs from disk - stored in Alerts directory with file base name
        seen_file = os.path.join(self.alerts_dir, f"{file_base}.seen.json")
        if os.path.exists(seen_file):
            try:
                with open(seen_file, 'r') as f:
                    ids = json.load(f)
                self.seen_ids[file_base] = set(ids)
            except Exception:
                self.seen_ids[file_base] = set()
        else:
            self.seen_ids[file_base] = set()

    def _save_seen(self, file_base: str):
        """Persist seen IDs for an alert to disk."""
        # Store seen files in the Alerts directory with file base name
        seen_file = os.path.join(self.alerts_dir, f"{file_base}.seen.json")
        try:
            with open(seen_file, 'w') as f:
                json.dump(list(self.seen_ids[file_base]), f)
        except Exception as e:
            print(f"Failed to save seen IDs for {file_base}: {e}")
    
    def format_alert(self, match, alert_data, alert_type):
        """Format an alert with pretty-printing similar to combined_match_summary.
        
        This centralized format function ensures all alerts look consistent.
        
        Args:
            match: The match data that triggered the alert
            alert_data: The alert data returned by the alerter (string or dict)
            alert_type: The type of alert (e.g., 'OU3', 'GOAL', etc.)
            
        Returns:
            str: A formatted alert message
        """
        # Get the pretty-printed match summary
        formatted_lines = format_match_summary(match)
        
        # Add our custom alert header
        alert_header = [
            "\n=====================================",
            f"🔔 {alert_type.upper()} ALERT 🔔",
            "=====================================\n"
        ]
        
        # Handle different alert data formats based on the alert type
        if isinstance(alert_data, dict):
            # New structured alert data format
            
            # Handle OU3 alert type
            if alert_type.upper() == "OU3":
                if "value" in alert_data and "threshold" in alert_data:
                    # Format the O/U value with highlighting
                    formatted_lines.insert(1, f"Over/Under Line: *{alert_data['value']:.2f}* (Threshold: {alert_data['threshold']})")
                elif "detail" in alert_data:
                    # Use the provided detail field
                    formatted_lines.insert(1, f"{alert_data['detail']}")
            
            # Handle other alert types as they're added
            # elif alert_type.upper() == "ANOTHER_TYPE":
            #    Handle specific formatting for that alert type
            
            else:
                # Generic handling for unknown alert types
                # Just add any details found in the alert data
                for key, value in alert_data.items():
                    if key not in ["type"]:
                        formatted_lines.insert(1, f"{key.capitalize()}: {value}")
        
        elif isinstance(alert_data, str) and ":" in alert_data:
            # Legacy string format - try to extract details
            try:
                # Find content between first * pair - this often contains key alert details
                import re
                detail_match = re.search(r'\*(.+?)\*', alert_data)
                if detail_match:
                    detail = detail_match.group(1)
                    formatted_lines.insert(1, f"{alert_type} Alert Detail: *{detail}*")
                else:
                    # Just add the raw alert message
                    formatted_lines.insert(1, f"Alert: {alert_data}")
            except Exception:
                # If extraction fails, just insert the raw alert message
                formatted_lines.insert(1, f"Alert: {alert_data}")
        
        # Join all lines into a complete match summary
        return "\n".join(alert_header + formatted_lines)

    def run(self):
        """[DEPRECATED] Run the alerter to check for any alerts.
        
        This method is deprecated. Use run_alerters() from orchestrate_complete.py instead.
        
        Fetches the latest data, processes each match against registered alerts,
        and saves alerts to log files.
        """
        import warnings
        warnings.warn(
            "AlerterMain.run() is deprecated. Use run_alerters() from orchestrate_complete.py instead.",
            DeprecationWarning,
            stacklevel=2
        )
        raw_data = fetch_and_cache()
        
        # Extract necessary components from raw_data for merge_all_matches
        live_data = raw_data.get('matches', [])
        details_by_id = {}
        odds_by_id = {}
        team_cache = {}
        competition_cache = {}
        country_map = {}
        
        # For simplified integration, we'll work directly with the matches
        # rather than go through the merge process again
        merged_matches = raw_data.get('matches', [])
        
        # Process each match
        for match in merged_matches:
            # Get the match ID - could be 'match_id' or 'id' depending on the data source
            match_id = match.get("match_id") or match.get("id")
            for alert in self.alerts:
                # Use module name for consistency
                module_name = alert.__class__.__module__.split('.')[-1]
                notice = alert.check(match)
                # Only proceed if alert triggers and not already seen
                if notice and match_id and match_id not in self.seen_ids[self.alert_file_bases[id(alert)]]:
                    # Format the alert with pretty-printing
                    formatted_alert = self.format_alert(match, notice, self.alert_file_bases[id(alert)])
                    
                    # Send alert to Telegram
                    send_notification(formatted_alert)
                    
                    # Generate pretty match summary for console display
                    print("\n" + "=" * 80)
                    print(f"ALERT TRIGGERED: {self.alert_file_bases[id(alert)]}")
                    print("=" * 80)
                    print(formatted_alert)
                    
                    # Add to seen match IDs to prevent duplicate alerts
                    self.seen_ids[self.alert_file_bases[id(alert)]].add(match_id)
                    self._save_seen(self.alert_file_bases[id(alert)])
                    
                    # Get logger for this specific alert type using centralized configuration
                    alert_name = self.alert_file_bases[id(alert)]
                    alert_logger = configure_alert_logger(alert_name)
                    
                    # Log the formatted alert
                    if alert_logger and formatted_alert:
                        alert_logger.info(formatted_alert)
                    
                # Save home_team, away_team, and status for logger entry
                home_team = match.get('home_team', {}).get('name', match.get('home', 'Unknown'))
                away_team = match.get('away_team', {}).get('name', match.get('away', 'Unknown'))
                score = match.get('score', {})
                home_score = score.get('home', 0)
                away_score = score.get('away', 0)
                status_id = match.get('status_id')
                status = match.get('status', get_status_description(status_id))


if __name__ == "__main__":
    # Register satellite alerts here
    alerts = [
        OverUnderAlert(threshold=3.0),  # O/U ≥ 3.00
        FutureAlert(),                  # Future alert stub
    ]
    manager = AlerterMain(alerts=alerts)
    manager.run()
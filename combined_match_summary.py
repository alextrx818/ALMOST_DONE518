#!/usr/bin/env python3
"""
NOTE: All logging configuration is centralized in log_config.py
      Do not add new loggers directly - use get_logger() or get_summary_logger()
"""
# combined_match_summary.py
import json
from datetime import datetime
import pytz
import sys
import logging
from pathlib import Path
import logging
from log_config import cleanup_handlers
import atexit

# Initialize our summary logger using static configuration
summary_logger = logging.getLogger("summary.pipeline")  # to match the name used in orchestrate_complete.py

# Register cleanup function to be called on program exit
atexit.register(cleanup_handlers)

def get_combined_summary_logger():
    """
    Get the centralized summary logger.
    This function is maintained for backward compatibility.
    """
    return summary_logger

# Setup diagnostic logging at the module level
logger = get_combined_summary_logger()
logger.debug("Loaded combined_match_summary module")

from zoneinfo import ZoneInfo
import functools
import signal
import os

# --- Prevent BrokenPipeError when piping into head, etc. ---
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Implement conversion functions directly instead of importing from live.py
def hk_to_american(hk_odds):
    """Convert Hong Kong odds to American odds (int value)"""
    try:
        hk_odds = float(hk_odds)
        if hk_odds >= 1:
            return int(round(hk_odds * 100))
        else:
            return int(round(-100 / hk_odds))
    except (ValueError, ZeroDivisionError):
        return 0

def decimal_to_american(decimal_odds):
    """Convert decimal odds to American odds (int value)"""
    try:
        decimal_odds = float(decimal_odds)
        if decimal_odds == 0:
            return 0
        
        if decimal_odds >= 2.0:
            return int(round((decimal_odds - 1) * 100))
        else:
            return int(round(-100 / (decimal_odds - 1)))
    except (ValueError, ZeroDivisionError):
        return 0

API_DATETIME_FORMAT = "%m/%d/%Y %I:%M:%S %p %Z"

# Match numbering system
MATCH_COUNTER_FILE = "match_counters.json"
MATCH_HEADER_WIDTH = 80

# Test the header formatting with different match numbers
def test_header_alignment():
    """Test function to verify header alignment"""
    test_numbers = [(1, 10), (5, 25), (10, 100), (100, 100)]
    logger = get_combined_summary_logger()
    
    for match_num, total in test_numbers:
        match_str = f"#MATCH {match_num} of {total}"
        ts_str = get_eastern_time().strftime(API_DATETIME_FORMAT)
        
        base = max(len(match_str), len(ts_str))
        width = base + 20  # Add padding
        
        # Ensure width - len(ts_str) is even for perfect centering
        if (width - len(ts_str)) % 2 != 0:
            width += 1
            
        match_line = match_str.center(width, '=')
        ts_line = ts_str.center(width, ' ')
        
        print(f"\nTest {match_num}/{total}:")
        print(match_line)
        print(ts_line)

def get_eastern_time():
    return datetime.now(ZoneInfo("America/New_York"))
    
# Global match counter with file-based persistence
_MATCH_COUNTER = None

def _get_next_match_id():
    """Get the next match ID with file-based persistence."""
    global _MATCH_COUNTER
    
    if _MATCH_COUNTER is None:
        match_id_file = Path(__file__).parent / "match_id.txt"
        try:
            with open(match_id_file, 'r') as f:
                content = f.read().strip()
                _MATCH_COUNTER = int(content) if content else 0
        except (FileNotFoundError, ValueError):
            _MATCH_COUNTER = 0
    
    _MATCH_COUNTER += 1
    
    # Write back to file in a non-blocking way
    def _write_counter():
        with open(match_id_file, 'w') as f:
            f.write(str(_MATCH_COUNTER))
    
    import threading
    threading.Thread(target=_write_counter, daemon=True).start()
    
    return _MATCH_COUNTER

def format_match_summary(match, match_num=None, total_matches=None):
    """Format a match summary without any I/O operations."""
    try:
        # Use provided match_num if given, otherwise use the counter
        if match_num is None:
            match_num = _get_next_match_id()
        
        # Set total_matches to match_num if not provided
        if total_matches is None:
            total_matches = match_num
            
        # Get eastern timestamp with the API format
        ts_str = get_eastern_time().strftime(API_DATETIME_FORMAT)
        
        # Create compact match label
        match_str = f"#MATCH {match_num} of {total_matches}"
        
        # Compute target width for perfect centering
        base = max(len(match_str), len(ts_str))
        width = base + 20  # Add padding
        
        # Ensure width - len(ts_str) is even for perfect centering
        if (width - len(ts_str)) % 2 != 0:
            width += 1
            
        # Center both lines
        match_line = match_str.center(width, '=')
        ts_line = ts_str.center(width, ' ')
        
        # Basic match info
        competition = f"{match.get('competition', 'N/A')} ({match.get('country', 'N/A')})"
        teams = f"{match.get('home_team', 'Home')} vs {match.get('away_team', 'Away')}"
        
        # Score
        home_live = home_ht = away_live = away_ht = 0
        sd = match.get("score", [])
        if isinstance(sd, list) and len(sd) > 3:
            hs, as_ = sd[2], sd[3]
            if isinstance(hs, list) and len(hs) > 1:
                home_live, home_ht = hs[0], hs[1]
            if isinstance(as_, list) and len(as_) > 1:
                away_live, away_ht = as_[0], as_[1]
        score = f"Score: {home_live} - {away_live} (HT: {home_ht} - {away_ht})"
        
        # Status
        sid = match.get("status_id", 0)
        status = f"Status: {get_status_description(sid)} (Status ID: {sid})"
        
        # Betting Odds - with error handling
        try:
            odds_data = match.get("odds", {})
            formatted_odds = {
                "ML": transform_odds(odds_data.get("eu", []), "eu"),
                "SPREAD": transform_odds(odds_data.get("asia", []), "asia"),
                "Over/Under": transform_odds(odds_data.get("bs", []), "bs")
            }
            odds_display = format_odds_display(formatted_odds)
        except Exception as e:
            odds_display = "Error formatting odds: " + str(e)
        
        # Environment
        try:
            env_lines = summarize_environment(match.get("environment", {}))
            env_summary = "\n".join(env_lines)
        except Exception as e:
            env_summary = f"Error getting environment: {str(e)}"
        
        # Extract IDs
        competition_id = match.get('competition_id', 'N/A')
        match_id = match.get('id', 'N/A')
        
        # Consolidate everything into a single multi-line message
        return f"{match_line}\n{ts_line}\n\nMatch ID: {match_id}\nCompetition ID: {competition_id}\nCompetition: {competition}\nMatch: {teams}\n{score}\n{status}\n\n--- MATCH BETTING ODDS ---\n{odds_display}\n\n--- MATCH ENVIRONMENT ---\n{env_summary}\n\n{'-' * 60}"
    except Exception as e:
        return f"Error formatting match: {str(e)}\n{traceback.format_exc()}"

def write_combined_match_summary(match, match_num=None, total_matches=None):
    """Write a formatted match summary to the logger file.
    
    This is a backward-compatibility wrapper around format_match_summary.
    """
    logger = get_combined_summary_logger()
    try:
        summary = format_match_summary(match, match_num, total_matches)
        if summary.startswith("Error"):
            logger.error(summary)
            return False
        logger.info(summary)
        return True
    except Exception as e:
        logger.error(f"Error in write_combined_match_summary: {e}")
        logger.error(traceback.format_exc())
        return False

def format_american_odds(raw_value, market):
    """Format American odds with consistent sign display, using appropriate conversion."""
    try:
        # Ensure valid input
        if raw_value is None or raw_value == "" or raw_value == 0:
            return "+0"
            
        if market in ("SPREAD", "Over/Under"):
            amd = hk_to_american(raw_value)
        else:
            amd = decimal_to_american(raw_value)
            
        # Check for valid conversion result
        if amd == 0:
            return "+0"
            
        return f"{amd:+d}"
    except Exception as e:
        return "+0"

@functools.lru_cache(maxsize=32)
def get_status_description(status_id):
    status_mapping = {
        "1": "Not started", "2": "First half", "3": "Half-time break",
        "4": "Second half", "5": "Extra time", "6": "Penalty shootout",
        "7": "Finished", "8": "Finished", "9": "Postponed",
        "10": "Canceled", "11": "To be announced", "12": "Interrupted",
        "13": "Abandoned", "14": "Suspended"
    }
    return status_mapping.get(str(status_id), f"Unknown (ID: {status_id})")

def pick_best_entry(entries):
    """Select the best entry from available odds, preferring minutes 4-6"""
    if not entries:
        return {}
        
    # Sort entries by time (numeric values first, then non-numeric)
    entries.sort(key=lambda e: int(e["time_of_match"]) if e.get("time_of_match","").isdigit() else 1000)
    
    # Target minutes are 4, 5, and 6
    target_minutes = ["4", "5", "6"]
    
    # First try to find an entry within target minutes
    best_entry = next((e for e in entries if e.get("time_of_match", "") in target_minutes), None)
    
    # If no entry found in target minutes, use the first available entry
    if not best_entry and entries:
        best_entry = entries[0]
        
    return best_entry or {}

def transform_odds(raw_odds, odds_type=None):
    """
    Transform raw odds data from the merged format to the format expected by the formatter
    
    Raw format: List of arrays with numeric/timestamp values
    Expected: List of dictionaries with named keys
    
    odds_type: One of 'asia' (SPREAD), 'eu' (ML), or 'bs' (Over/Under)
    """
    if not raw_odds or not isinstance(raw_odds, list):
        return []
        
    transformed = []
    for odds_entry in raw_odds:
        if not isinstance(odds_entry, list) or len(odds_entry) < 5:
            continue
            
        entry = {
            "time_of_match": str(odds_entry[1]) if len(odds_entry) > 1 else "0",
        }
        
        # Use odds_type parameter to determine the structure
        if odds_type == "asia":
            # SPREAD odds
            entry["home_win"] = odds_entry[2]
            entry["handicap"] = odds_entry[3]
            entry["away_win"] = odds_entry[4]
        elif odds_type == "eu":
            # ML odds
            entry["home_win"] = odds_entry[2]
            entry["draw"]     = odds_entry[3]
            entry["away_win"] = odds_entry[4]
        elif odds_type == "bs":
            # Over/Under odds
            entry["over"]     = odds_entry[2]
            entry["handicap"] = odds_entry[3]
            entry["under"]    = odds_entry[4]
        
        transformed.append(entry)
        
    return transformed

def summarize_environment(env):
    """Format environment data for display"""
    lines = []
    
    # Check if there's any data
    if not env:
        return ["No environment data available"]
        
    # Weather condition mapping
    weather_conditions = {
        "1": "Sunny",
        "2": "Partly Cloudy",
        "3": "Cloudy",
        "4": "Overcast",
        "5": "Foggy",
        "6": "Light Rain",
        "7": "Rain",
        "8": "Heavy Rain",
        "9": "Snow",
        "10": "Thunder"
    }
    
    # Weather
    if "weather" in env and env["weather"]:
        weather_code = str(env["weather"])
        weather_desc = weather_conditions.get(weather_code, f"Unknown ({weather_code})")
        lines.append(f"Weather: {weather_desc}")
    
    # Temperature
    temp = env.get("temperature")
    if temp:
        try:
            # Check if it has °C marker
            if "\u00b0C" in temp:
                temp_val = float(temp.replace("\u00b0C", ""))
                temp_f = temp_val * 9/5 + 32
            else:
                # Try to extract numeric value
                temp_val = float(''.join(c for c in temp if c.isdigit() or c == '.'))
                # Assume Celsius if not specified
                temp_f = temp_val * 9/5 + 32 if env.get("temperature_unit") == "C" or "\u00b0C" in temp else temp_val
            
            lines.append(f"Temperature: {temp_f:.1f}°F")
        except (ValueError, TypeError):
            # If parsing fails, show the raw value
            lines.append(f"Temperature: {temp}")
    
    # Humidity 
    humidity = env.get("humidity")
    if humidity:
        try:
            # Handle if it's already a string with % sign
            if isinstance(humidity, str) and "%" in humidity:
                lines.append(f"Humidity: {humidity}")
            else:
                lines.append(f"Humidity: {int(float(humidity))}%")
        except (ValueError, TypeError):
            lines.append(f"Humidity: {humidity}")
    
    # Wind 
    wind = env.get("wind")
    if wind:
        try:
            if isinstance(wind, str) and wind.endswith("m/s"):
                ms = float(wind.rstrip("m/s"))
                mph = ms * 2.237
                
                # Add wind strength descriptor
                if mph < 1:
                    strength = "Calm"
                elif mph < 4:
                    strength = "Light Air"
                elif mph < 8:
                    strength = "Light Breeze"
                elif mph < 13:
                    strength = "Gentle Breeze"
                elif mph < 19:
                    strength = "Moderate Breeze"
                elif mph < 25:
                    strength = "Fresh Breeze"
                elif mph < 32:
                    strength = "Strong Breeze"
                elif mph < 39:
                    strength = "Near Gale"
                elif mph < 47:
                    strength = "Gale"
                elif mph < 55:
                    strength = "Strong Gale"
                elif mph < 64:
                    strength = "Storm"
                elif mph < 73:
                    strength = "Violent Storm"
                else:
                    strength = "Hurricane"
                
                lines.append(f"Wind: {strength}, {mph:.1f} mph")
            else:
                lines.append(f"Wind: {wind}")
        except (ValueError, TypeError):
            lines.append(f"Wind: {wind}")
            
    # Note: We're explicitly not including pressure as requested
    return lines or ["No environment data available"]

# ────────────────────────────────────────────────────────────────────────────────
# Unified betting odds display function with precise alignment of numeric values:

def format_odds_display(formatted_odds):
    """
    Return perfectly aligned betting-odds rows:
       │ Market │ Col1    │ Col2    │ Col3   │ Stamp  │
    """
    rows = []
    label_map = {"ML":"ML:", "SPREAD":"Spread:", "Over/Under":"O/U:"}

    for market in ("ML", "SPREAD", "Over/Under"):
        entry = pick_best_entry(formatted_odds.get(market, []))
        if not entry:
            continue
            
        time = entry.get("time_of_match", "0")
        stamp = f"(@{time}')"
        lab = label_map[market]
        
        if market == "ML":
            home_odds = format_american_odds(entry.get('home_win', 0), market)
            draw_odds = format_american_odds(entry.get('draw', 0), market)
            away_odds = format_american_odds(entry.get('away_win', 0), market)
            
            rows.append((lab, f"Home: {home_odds}", f"Draw: {draw_odds}", f"Away: {away_odds}", stamp))
            
        elif market == "SPREAD":
            home_odds = format_american_odds(entry.get('home_win', 0), market)
            handicap = entry.get('handicap', 0)
            away_odds = format_american_odds(entry.get('away_win', 0), market)
            
            rows.append((lab, f"Home: {home_odds}", f"Hcap: {handicap}", f"Away: {away_odds}", stamp))
            
        else:  # Over/Under
            over_odds = format_american_odds(entry.get('over', 0), market)
            line = entry.get('handicap', 0)
            under_odds = format_american_odds(entry.get('under', 0), market)
            
            rows.append((lab, f"Over: {over_odds}", f"Line: {line}", f"Under: {under_odds}", stamp))
    
    if not rows:
        return "No betting odds available"
    
    # Process each column element to extract labels and values for precise alignment
    processed_rows = []
    
    for market, col1, col2, col3, stamp in rows:
        # Extract label and value from each column
        col1_parts = col1.split(": ", 1)
        col2_parts = col2.split(": ", 1)
        col3_parts = col3.split(": ", 1)
        
        if len(col1_parts) == 2 and len(col2_parts) == 2 and len(col3_parts) == 2:
            # Labels
            col1_label = col1_parts[0] + ":"
            col2_label = col2_parts[0] + ":"
            col3_label = col3_parts[0] + ":"
            
            # Values
            col1_value = col1_parts[1]
            col2_value = col2_parts[1]
            col3_value = col3_parts[1]
            
            processed_rows.append((market, col1_label, col1_value, col2_label, col2_value, col3_label, col3_value, stamp))
    
    if not processed_rows:
        return "No betting odds available"
    
    # Calculate max widths for precise alignment
    market_width = max(len(row[0]) for row in processed_rows)
    col1_label_width = max(len(row[1]) for row in processed_rows)
    col1_value_width = max(len(row[2]) for row in processed_rows)
    col2_label_width = max(len(row[3]) for row in processed_rows)
    col2_value_width = max(len(row[4]) for row in processed_rows)
    col3_label_width = max(len(row[5]) for row in processed_rows)
    col3_value_width = max(len(row[6]) for row in processed_rows)
    stamp_width = max(len(row[7]) for row in processed_rows)
    
    # Format rows with precise alignment of numeric values
    lines = []
    for market, c1_label, c1_val, c2_label, c2_val, c3_label, c3_val, stamp in processed_rows:
        # Format with precise right-alignment of values for perfect odds alignment
        line = f"│ {market:<{market_width}} │ {c1_label:<{col1_label_width}} {c1_val:>{col1_value_width}} │ "
        line += f"{c2_label:<{col2_label_width}} {c2_val:>{col2_value_width}} │ "
        line += f"{c3_label:<{col3_label_width}} {c3_val:>{col3_value_width}} │ {stamp}"
        lines.append(line)
    
    return "\n".join(lines)

# ────────────────────────────────────────────────────────────────────────────────

def get_match_count():
    """
    Get and update the match count for the day.
    
    Returns:
        tuple: (current_match_number, total_matches_today)
    """
    # Get current date as string
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Initialize counters if they don't exist
    base_dir = os.path.dirname(os.path.abspath(__file__))
    counter_file = os.path.join(base_dir, MATCH_COUNTER_FILE)
    
    # Load existing counters or initialize
    counters = {}
    if os.path.exists(counter_file):
        try:
            with open(counter_file, 'r') as f:
                counters = json.load(f)
        except Exception:
            # If file is corrupted, start fresh
            counters = {}
    
    # Initialize for today if needed
    if today not in counters:
        counters[today] = {"total": 0, "current": 0}
    
    # Increment total matches for today
    counters[today]["total"] += 1
    total_matches = counters[today]["total"]
    
    # Increment current match counter
    counters[today]["current"] += 1
    current_match = counters[today]["current"]
    
    # Save updated counters
    try:
        with open(counter_file, 'w') as f:
            json.dump(counters, f)
    except Exception:
        # If we can't save, just continue without error
        pass
        
    return (current_match, total_matches)


if __name__ == "__main__":
    from pathlib import Path
    BASE_DIR = Path(__file__).parent
    MERGE_OUTPUT_FILE = BASE_DIR / "merge_logic.json"
    
    with open(MERGE_OUTPUT_FILE) as f:
        matches = json.load(f)
    
    for match in matches:
        # Get match number and total matches
        match_num, total_matches = get_match_count()
        
        write_combined_match_summary(match, match_num, total_matches)
        print(f"Competition: {match.get('competition')} ({match.get('country')})")
        print(f"Match: {match.get('home_team')} vs {match.get('away_team')}")
        
        # Score
        home_live = home_ht = away_live = away_ht = 0
        sd = match.get("score", [])
        if isinstance(sd, list) and len(sd) > 3:
            hs, as_ = sd[2], sd[3]
            if isinstance(hs, list) and len(hs) > 1:
                home_live, home_ht = hs[0], hs[1]
            if isinstance(as_, list) and len(as_) > 1:
                away_live, away_ht = as_[0], as_[1]
        print(f"Score: {home_live} - {away_live} (HT: {home_ht} - {away_ht})")
        
        # Status
        sid = match.get("status_id")
        print(f"Status: {get_status_description(sid)} (Status ID: {sid})")
        
        # Betting Odds
        print("\n--- MATCH BETTING ODDS ---")
        odds_data = match.get("odds", {})
        formatted_odds = {
            "ML": transform_odds(odds_data.get("eu", []), "eu"),
            "SPREAD": transform_odds(odds_data.get("asia", []), "asia"),
            "Over/Under": transform_odds(odds_data.get("bs", []), "bs")
        }
        print(format_odds_display(formatted_odds))
        
        # Environment
        print("\n--- MATCH ENVIRONMENT ---")
        for line in summarize_environment(match.get("environment", {})):
            print(line)
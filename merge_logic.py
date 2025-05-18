#!/usr/bin/env python3
from typing import Any, Dict, List, Tuple, Optional
import logging, os
from datetime import datetime
import pytz

# Import extract_ids from pure_json_fetch_cache
from pure_json_fetch_cache import extract_ids

# ─── LOGGER SETUP ──────────────────────────────────────────────────────────
# Use centralized logging configuration
from log_config import get_logger

# Initialize logger using the centralized logger factory
_log = get_logger("merge_logic")
_log.setLevel(logging.DEBUG)

# ─── HELPERS ────────────────────────────────────────────────────────────────
def unwrap_results(obj: Dict[str, Any], ctx: str) -> Dict[str, Any]:
    """Extract first item from results array, with logging for missing data."""
    res = obj.get("results")
    if res is None:
        _log.warning(f"[{ctx}] missing 'results'; falling back to empty dict")
        return {}
    if isinstance(res, list):
        return res[0] if res else {}
    return res


def extract_team_name(team_obj: dict) -> str:
    """Pull out the team’s name field (fallback if missing)."""
    return team_obj.get("name", "Unknown Team")

def extract_competition_info(comp_obj: dict) -> Tuple[str, Any]:
    """
    Return a tuple of (competition_name, country_id).
    Falls back if keys are missing.
    """
    return (
        comp_obj.get("name", "Unknown Competition"),
        comp_obj.get("country_id")
    )

def format_match_odds(odds_obj: dict) -> dict:
    """
    Massage the raw odds structure into your desired output.
    Here’s a simple example pulling out the latest “asia” odds:
    """
    results = odds_obj.get("results", {})
    # pick odds type “2” → asia, or empty
    return {
        "asia": results.get("2", {}).get("asia", []),
        "eu":   results.get("2", {}).get("eu",   []),
        "bs":   results.get("2", {}).get("bs",   []),
        "cr":   results.get("2", {}).get("cr",   []),
    }

def get_status_description(status_id: Any) -> str:
    """Map numeric status codes to human-readable text."""
    return {
        1: "Not started",
        2: "Live",
        3: "Finished",
    }.get(status_id, "Unknown status")

# ─── MERGE UTILS ────────────────────────────────────────────────────────────

def merge_match_data(
    live: Dict[str, Any],
    detail: Dict[str, Any],
    odds: Dict[str, Any],
    team_cache: Dict[str, Any],
    competition_cache: Dict[str, Any],
    country_map: Dict[Any, str],
    home_id: str,
    away_id: str,
    comp_id: str
) -> Dict[str, Any]:
    """
    Merge a single match's live, detail, odds, team and competition data
    into one unified record.
    """
    # Get match ID for logging context
    match_id = live.get('id', 'unknown')
    
    # 1) Use the new unwrap_results helper to extract data safely
    det = unwrap_results(detail, match_id)
    merged = {**det, **live}
    
    # Add match_id and competition_id to the merged data
    merged['id'] = match_id  # Ensure match ID is included
    merged['competition_id'] = comp_id  # Add competition ID
    
    _log.debug(f"Base merge complete for match {match_id}")
    _log.debug(f"Included competition_id: {comp_id} in match data")

    # 2) Team names with improved logging - use IDs passed in from extract_ids
    # Note: We use the IDs passed in (which may come from details if live doesn't have them)
    if home_id not in team_cache:
        _log.debug(f"[{match_id}] home_team_id '{home_id}' not in team_cache")
    merged["home_team"] = extract_team_name(team_cache.get(home_id, {}))
    
    if away_id not in team_cache:
        _log.debug(f"[{match_id}] away_team_id '{away_id}' not in team_cache")
    merged["away_team"] = extract_team_name(team_cache.get(away_id, {}))

    # 3) Competition and country with improved logging - use comp_id passed in from extract_ids
    if comp_id not in competition_cache:
        _log.debug(f"[{match_id}] competition_id '{comp_id}' not in competition_cache")
    
    comp_name, country_id = extract_competition_info(competition_cache.get(comp_id, {}))
    merged["competition"] = comp_name
    
    if country_id is None:
        _log.debug(f"[{match_id}] competition cache had no country_id")
    merged["country"] = country_map.get(country_id, "Unknown Country")
    
    _log.debug(f"Added competition '{comp_name}' and country info for match {match_id}")

    # 4) Odds formatting
    merged["odds"] = format_match_odds(odds)

    # 5) Status description
    status_id = merged.get("status_id")
    merged["status"] = get_status_description(status_id)
    
    _log.debug(f"Completed merging match {match_id} (status: {merged['status']})")
    return merged


def merge_all_matches(
    live_data: Dict[str, Any],
    details_by_id: Dict[str, Dict[str, Any]],
    odds_by_id: Dict[str, Dict[str, Any]],
    team_cache: Dict[str, Any],
    competition_cache: Dict[str, Any],
    country_map: Dict[Any, str]
) -> List[Dict[str, Any]]:
    """
    For each match in live_data['results'], merge its detail and odds data
    into a single record. Returns a list of merged match records.
    """
    _log.info(f"Merging {len(live_data.get('results', []))} matches with details and odds")
    merged_records: List[Dict[str, Any]] = []
    
    for match in live_data.get("results", []):
        mid = match.get("id")
        
        # Validate inputs with clear logging for missing data
        if mid not in details_by_id:
            _log.warning(f"No detail entry for match {mid}")
        detail = details_by_id.get(mid, {})
        
        if mid not in odds_by_id:
            _log.warning(f"No odds entry for match {mid}")
        odds = odds_by_id.get(mid, {})  # Renamed from 'odd' to 'odds' for clarity
        
        _log.debug(f"Merging match {mid} with {len(detail)} detail keys and {len(odds)} odds keys")
        
        # Extract team and competition IDs using both match and details data
        home_id, away_id, comp_id = extract_ids(match, detail)
        _log.debug(f"Using IDs home={home_id}, away={away_id}, comp={comp_id}")
        
        merged = merge_match_data(match, detail, odds,
                                  team_cache,
                                  competition_cache,
                                  country_map,
                                  home_id, away_id, comp_id)
        merged_records.append(merged)
        
    _log.info(f"Successfully merged {len(merged_records)} complete match records")
    return merged_records

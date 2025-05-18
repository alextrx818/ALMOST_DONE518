#!/usr/bin/env python3
# pure_json_fetch_cache.py - Enhanced API fetcher with TTL caching
#
# Requirements:
# - Python 3.7+ (for full async/await and type hint support)
# - Network: Outbound HTTPS access required for API communication
# - Optional: aiofiles package for true async disk I/O (pip install aiofiles)

import aiohttp, asyncio, random, time, json, os, logging, pickle, hashlib, traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union, Tuple
from pathlib import Path

# --- NEW LIBRARIES ---
from dotenv import load_dotenv
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential
import aiofiles
from pydantic import BaseModel, ValidationError, Extra
import pytz

# Return US Eastern formatted time with timezone
def get_eastern_time():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    return now.strftime('%m/%d/%Y %I:%M:%S %p %Z')

# Helper for JSON serialization of Pydantic models

def serialize_for_json(obj):
    """Helper for JSON serialization of Pydantic models or nested structures"""
    if isinstance(obj, BaseModel):
        # Handle both Pydantic v1 and v2 APIs
        return obj.model_dump() if hasattr(obj, 'model_dump') else obj.dict()
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    return obj

# Load .env for secrets
load_dotenv()

# --- END NEW LIBRARIES ---


# ─── credentials & retry settings ───────────────────────────────────────────────
USER = os.getenv("API_USER", "thenecpt")
SECRET = os.getenv("API_SECRET", "0c55322e8e196d6ef9066fa4252cf386")
MAX_RETRIES = 3  # Used by tenacity retry decorator
RETRY_BACKOFF = 1.2

# ─── API ENDPOINTS ─────────────────────────────────────────────────────────────
_BASE = "https://api.thesports.com/v1/football"
_URLS = {
    "live":         f"{_BASE}/match/detail_live",
    "details":      f"{_BASE}/match/recent/list",
    "odds":         f"{_BASE}/odds/history",
    "team":         f"{_BASE}/team/additional/list",
    "competition":  f"{_BASE}/competition/additional/list",
    "country":      f"{_BASE}/country/list",
}

# File paths for output
BASE_DIR = Path(__file__).parent
MATCH_CACHE_PATH = BASE_DIR / "full_match_cache.json"
SAMPLE_CACHE_PATH = BASE_DIR / "sample_match_cache.json"

# ─── LOGGER ─────────────────────────────────────────────────────────────────────
import time
# Custom formatter for standardized timestamp format across all logs
class StandardTimestampFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Always use Eastern time with MM/DD/YYYY II:MM:SS AM/PM EDT format
        eastern = pytz.timezone('US/Eastern')
        dt = datetime.fromtimestamp(record.created).astimezone(eastern)
        return dt.strftime("%m/%d/%Y %I:%M:%S %p %Z")

def _setup_logger():
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Get logger using centralized logger factory
    from log_config import get_logger
    log = get_logger("pure_json_fetch")
    log.setLevel(logging.DEBUG)
    
    # Get detailed fetch logger using centralized logger factory
    fetch_logger = get_logger("fetch_data")
    fetch_logger.setLevel(logging.DEBUG)
    
    return log, fetch_logger

# Initialize both loggers
_log, _fetch_log = _setup_logger()

# ─── DATA LOGGING HELPERS ─────────────────────────────────────────────────────────
def log_match_summary(matches_data):
    """Log a detailed summary of fetched match data"""
    if not isinstance(matches_data, dict) or "results" not in matches_data:
        _fetch_log.warning("Invalid match data format for logging")
        return
        
    matches = matches_data["results"]
    if not matches:
        _fetch_log.info("No live matches available")
        return
        
    _fetch_log.info(f"==== MATCH SUMMARY: {len(matches)} live matches ====")
    
    # Group matches by competition if possible
    competitions = {}
    for i, match in enumerate(matches[:20]):  # Limit to first 20 for brevity
        comp_id = match.get("competition_id", "unknown")
        if comp_id not in competitions:
            competitions[comp_id] = []
        competitions[comp_id].append(match)
    
    # Log summary by competition
    _fetch_log.info(f"Matches from {len(competitions)} different competitions")
    
    # Log individual matches (limited to first 20)
    for i, match in enumerate(matches[:20]):
        home = match.get("home_team_name", "Unknown")
        away = match.get("away_team_name", "Unknown")
        match_id = match.get("id", "unknown")
        status = match.get("status_id", "?") 
        # Get score if available
        score_str = "?"
        if "score" in match and isinstance(match["score"], list) and len(match["score"]) >= 2:
            score_str = f"{match['score'][0]}-{match['score'][1]}"
            
        _fetch_log.info(f"Match {i+1}: [{match_id}] {home} vs {away} ({score_str}) [Status: {status}]")
        
    if len(matches) > 20:
        _fetch_log.info(f"... and {len(matches) - 20} more matches")

def log_match_details(match_id, details_data):
    """Log detailed information about a specific match"""
    _fetch_log.info(f"==== MATCH DETAILS: {match_id} ====")
    
    if not isinstance(details_data, dict) or "results" not in details_data:
        _fetch_log.warning("Invalid match details format for logging")
        return
        
    results = details_data["results"]
    if isinstance(results, list) and results:
        detail = results[0]
        _fetch_log.info(f"Competition: {detail.get('competition_name', 'Unknown')}")
        _fetch_log.info(f"Teams: {detail.get('home_team_name', 'Unknown')} vs {detail.get('away_team_name', 'Unknown')}")
        _fetch_log.info(f"Status: {detail.get('status_name', 'Unknown')} ({detail.get('status_id', '?')})")
        
        # Log timeline events if available
        if "timeline" in detail and detail["timeline"]:
            _fetch_log.info("Match timeline events:")
            for event in detail["timeline"][:5]:  # Limit to first 5 events
                _fetch_log.info(f"  - {event}")
            if len(detail["timeline"]) > 5:
                _fetch_log.info(f"  ... and {len(detail['timeline']) - 5} more events")

def log_odds_summary(match_id, odds_data):
    """Log a summary of odds data for a match"""
    _fetch_log.info(f"==== ODDS SUMMARY: {match_id} ====")
    
    if not isinstance(odds_data, dict) or "odds" not in odds_data:
        _fetch_log.warning("Invalid odds data format for logging")
        return
    
    odds = odds_data.get("odds", {})
    if not odds:
        _fetch_log.info("No odds data available")
        return
        
    # Log available odds types
    odds_types = list(odds.keys())
    _fetch_log.info(f"Available odds types: {', '.join(odds_types)}")
    
    # Log sample of odds entries for each type (limited)
    for odds_type in odds_types:
        entries = odds[odds_type]
        if isinstance(entries, list) and entries:
            _fetch_log.info(f"Odds type {odds_type}: {len(entries)} entries")
            # Log a few sample entries
            for i, entry in enumerate(entries[:3]):
                _fetch_log.info(f"  Sample {i+1}: {entry}")
            if len(entries) > 3:
                _fetch_log.info(f"  ... and {len(entries) - 3} more entries")

def log_cache_metrics(force=False):
    """Log metrics about cache hits and misses"""
    global _metrics_last_logged
    
    now = time.time()
    if not force and (now - _metrics_last_logged) < _METRICS_LOG_INTERVAL:
        return  # Don't spam logs with metrics
        
    _metrics_last_logged = now
    
    _fetch_log.info("==== CACHE METRICS ====")
    for cache_type, metrics in _cache_metrics.items():
        total = metrics["hits"] + metrics["misses"]
        hit_rate = (metrics["hits"] / total * 100) if total > 0 else 0
        
        # Special handling for country cache which has 'permanent' instead of 'disk_hits'
        if cache_type == "country":
            _fetch_log.info(f"{cache_type.title()} cache: {metrics['hits']} hits, {metrics['misses']} misses, {metrics['permanent']} permanent ({hit_rate:.1f}% hit rate)")
        else:
            _fetch_log.info(f"{cache_type.title()} cache: {metrics['hits']} hits, {metrics['misses']} misses, {metrics.get('disk_hits', 0)} disk hits ({hit_rate:.1f}% hit rate)")

def log_cache_stats():
    """Log statistics about the cache usage"""
    _fetch_log.info("==== CACHE STATISTICS ====")
    _fetch_log.info(f"Teams cached: {len(_team_cache)}")
    _fetch_log.info(f"Competitions cached: {len(_comp_cache)}")
    _fetch_log.info(f"Countries cached: {len(_country_map)}")
    
    # Log metrics too
    log_cache_metrics(force=True)
    
    if _ENABLE_DISK_CACHE and os.path.exists(_CACHE_DIR):
        # Count disk cache files
        team_files = len([f for f in os.listdir(_CACHE_DIR) if f.startswith("team_")])
        comp_files = len([f for f in os.listdir(_CACHE_DIR) if f.startswith("comp_")])
        country_files = len([f for f in os.listdir(_CACHE_DIR) if f.startswith("country_")])
        
        _fetch_log.info("==== DISK CACHE STATISTICS ====")
        _fetch_log.info(f"Team files: {team_files}")
        _fetch_log.info(f"Competition files: {comp_files}")
        _fetch_log.info(f"Country files: {country_files}")
        
        # Calculate total cache size
        total_size = sum(os.path.getsize(os.path.join(_CACHE_DIR, f)) for f in os.listdir(_CACHE_DIR))
        _fetch_log.info(f"Total cache size: {total_size / 1024:.2f} KB")

# ─── ASYNC FETCH + RETRY ────────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1.2, min=1, max=10))
async def _fetch_json(session: aiohttp.ClientSession, url: str, params: Dict[str,Any], name: str) -> Dict[str,Any]:
    try:
        async with session.get(url, params=params) as r:
            _log.debug(f"[{name}] Status {r.status}")
            r.raise_for_status()
            return await r.json()
    except aiohttp.ClientResponseError as e:
        # HTTP error responses (4xx, 5xx)
        _log.error(f"HTTP error fetching {name}: HTTP {e.status} - {e.message}")
        raise  # Let @retry handle retry logic
    except aiohttp.ClientError as e:
        # Connection errors, timeouts, etc.
        _log.error(f"Connection error fetching {name}: {str(e)}")
        raise  # Let @retry handle retry logic
    except json.JSONDecodeError as e:
        # Invalid JSON response - don't retry these
        _log.error(f"Invalid JSON from {name}: {e}")
        return {"error": f"Invalid JSON: {str(e)}", "results": []}
    except Exception as e:
        # Catch-all for any other exceptions
        _log.error(f"Unexpected error fetching {name}: {e}")
        raise  # Let @retry handle retry logic

# ─── PUBLIC ASYNC FUNCTIONS ────────────────────────────────────────────────────
async def fetch_live_matches(session: aiohttp.ClientSession) -> Dict[str,Any]:
    return await _fetch_json(session, _URLS["live"],        {"user":USER,"secret":SECRET}, "live")

async def fetch_match_details(session: aiohttp.ClientSession, mid: str) -> Dict[str,Any]:
    return await _fetch_json(session, _URLS["details"],     {"user":USER,"secret":SECRET,"uuid":mid}, f"details[{mid}]")

async def fetch_match_odds(session: aiohttp.ClientSession, mid: str) -> Dict[str,Any]:
    return await _fetch_json(session, _URLS["odds"],        {"user":USER,"secret":SECRET,"uuid":mid}, f"odds[{mid}]")

# ─── TTL CACHING FOR TEAM / COMPETITION / COUNTRY ──────────────────────────────
# Cache storage (using cachetools.TTLCache for in-memory TTL cache)
# TTLCache handles automatic expiration, so we don't need manual timestamp tracking
# TTL in seconds - default 86400 seconds (24 hours)
_TTL = int(os.getenv("CACHE_TTL", 86400))  

# Initialize caches with TTL
_team_cache = TTLCache(maxsize=10000, ttl=_TTL)  # Should be plenty for team caching
_comp_cache = TTLCache(maxsize=1000, ttl=_TTL)   # ~1000 competitions worldwide

# Permanent dictionary for country data - these values don't change
# This eliminates the need for API calls for country data
_PERMANENT_COUNTRY_MAP = {
    # Major countries
    "ENG": "England",
    "ESP": "Spain",
    "ITA": "Italy",
    "GER": "Germany",
    "FRA": "France",
    "NED": "Netherlands",
    "POR": "Portugal",
    "BRA": "Brazil",
    "ARG": "Argentina",
    "USA": "United States",
    "MEX": "Mexico",
    "JPN": "Japan",
    "KOR": "South Korea",
    "AUS": "Australia",
    "CHN": "China",
    "RUS": "Russia",
    "TUR": "Turkey",
    "BEL": "Belgium",
    "SUI": "Switzerland",
    "AUT": "Austria",
    "SCO": "Scotland",
    "WAL": "Wales",
    "IRE": "Ireland",
    "DEN": "Denmark",
    "SWE": "Sweden",
    "NOR": "Norway",
    "FIN": "Finland",
    "GRE": "Greece",
    "CRO": "Croatia",
    "SRB": "Serbia",
    "UKR": "Ukraine",
    "POL": "Poland",
    "CZE": "Czech Republic",
    "HUN": "Hungary",
    "ROM": "Romania",
    "BUL": "Bulgaria",
    "ISR": "Israel",
    "EGY": "Egypt",
    "SAU": "Saudi Arabia",
    "QAT": "Qatar",
    "UAE": "United Arab Emirates",
    "CAN": "Canada",
    "COL": "Colombia",
    "PER": "Peru",
    "CHI": "Chile",
    "ECU": "Ecuador",
    "URU": "Uruguay",
    "PAR": "Paraguay",
    "BOL": "Bolivia",
    "VEN": "Venezuela",
    # International
    "INT": "International",
    "WOR": "World",
    "EUR": "Europe",
    "AFC": "Asia",
    "CAF": "Africa",
    "SAM": "South America",
    "CCA": "North/Central America",
    "OCE": "Oceania",
}

# Map of country ID to name (no TTL)
_country_map = _PERMANENT_COUNTRY_MAP.copy()

# Lock for thread safety in async context
_team_lock = asyncio.Lock()
_comp_lock = asyncio.Lock()
_country_lock = asyncio.Lock()

# Flags/options
_ENABLE_DISK_CACHE = True
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

# Metrics for cache hits/misses
_cache_metrics = {
    "team": {"hits": 0, "disk_hits": 0, "misses": 0},
    "comp": {"hits": 0, "disk_hits": 0, "misses": 0},
    "country": {"hits": 0, "misses": 0, "permanent": 0},
}
_metrics_last_logged = 0.0
_METRICS_LOG_INTERVAL = 300  # Log cache metrics every 5 minutes

# Disk cache settings
_ENABLE_DISK_CACHE = True  # Enable disk-backed persistence by default
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')

# Initialize disk cache directory
if _ENABLE_DISK_CACHE:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    _log.info(f"Disk cache enabled at {_CACHE_DIR}")

# Helper functions for disk cache
def _get_cache_path(cache_type: str, item_id: str = "") -> str:
    """Generate a file path for a cache item"""
    if item_id:
        # For team and competition caches
        filename = f"{cache_type}_{hashlib.md5(item_id.encode()).hexdigest()}.cache"
    else:
        # For country cache
        filename = f"{cache_type}_all.cache"
    return os.path.join(_CACHE_DIR, filename)

async def _save_to_disk(cache_type: str, item_id: str, data: Any, timestamp: float) -> None:
    """Save a cache item to disk"""
    if not _ENABLE_DISK_CACHE:
        return
    
    try:
        cache_path = _get_cache_path(cache_type, item_id)
        cache_data = {
            "data": data,
            "timestamp": timestamp
        }
        
        # Write asynchronously using aiofiles if available, fall back to synchronous if not
        try:
            import aiofiles
            async with aiofiles.open(cache_path, 'wb') as f:
                await f.write(pickle.dumps(cache_data))
        except ImportError:
            with open(cache_path, 'wb') as f:
                f.write(pickle.dumps(cache_data))
                
        _log.debug(f"Saved {cache_type} cache for {item_id} to disk")
    except Exception as e:
        _log.warning(f"Failed to save {cache_type} cache to disk: {e}")

async def _load_from_disk(cache_type: str, item_id: str) -> Tuple[Any, float, bool]:
    """Load a cache item from disk
    
    Returns:
        tuple: (data, timestamp, success)
    """
    if not _ENABLE_DISK_CACHE:
        return None, 0, False
    
    try:
        cache_path = _get_cache_path(cache_type, item_id)
        if not os.path.exists(cache_path):
            return None, 0, False
        
        # Read asynchronously using aiofiles if available, fall back to synchronous if not
        try:
            import aiofiles
            async with aiofiles.open(cache_path, 'rb') as f:
                cache_data = pickle.loads(await f.read())
        except ImportError:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.loads(f.read())
                
        _log.debug(f"Loaded {cache_type} cache for {item_id} from disk")
        return cache_data["data"], cache_data["timestamp"], True
    except Exception as e:
        _log.warning(f"Failed to load {cache_type} cache from disk: {e}")
        return None, 0, False

# Define permissive Pydantic models for API responses

class MatchDetails(BaseModel, extra=Extra.allow):
    """Model for match details response"""
    pass

class OddsData(BaseModel, extra=Extra.allow):
    """Model for odds data response"""
    pass

class CountryData(BaseModel, extra=Extra.allow):
    """Model for country data response"""
    pass

class TeamData(BaseModel, extra=Extra.allow):
    """Model for team information response"""
    pass

class CompetitionData(BaseModel, extra=Extra.allow):
    """Model for competition information response"""
    pass

# Validate API responses using Pydantic models
async def fetch_match_details(session: aiohttp.ClientSession, mid: str) -> MatchDetails:
    data = await _fetch_json(session, _URLS["details"], {"user": USER, "secret": SECRET, "uuid": mid}, f"details[{mid}]")
    try:
        return MatchDetails.model_validate(data) if hasattr(MatchDetails, 'model_validate') else MatchDetails.parse_obj(data)
    except (ValidationError, Exception) as e:
        _log.error(f"Validation error for MatchDetails: {e}")
        return data

async def fetch_match_odds(session: aiohttp.ClientSession, mid: str) -> OddsData:
    data = await _fetch_json(session, _URLS["odds"],        {"user":USER,"secret":SECRET,"uuid":mid}, f"odds[{mid}]")
    try:
        return OddsData.model_validate(data) if hasattr(OddsData, 'model_validate') else OddsData.parse_obj(data)
    except ValidationError as e:
        _log.error(f"Validation error for OddsData: {e}")
        return data

async def fetch_country_data(session: aiohttp.ClientSession) -> CountryData:
    data = await _fetch_json(session, _URLS["country"],     {"user":USER,"secret":SECRET},       "country")
    try:
        return CountryData.model_validate(data) if hasattr(CountryData, 'model_validate') else CountryData.parse_obj(data)
    except ValidationError as e:
        _log.error(f"Validation error for CountryData: {e}")
        return data

# Define fetch_team_info and fetch_competition_info using the same pattern
async def fetch_team_info(session: aiohttp.ClientSession, tid: str) -> TeamData:
    data = await _fetch_json(session, _URLS["team"], {"user": USER, "secret": SECRET, "uuid": tid}, f"team[{tid}]")
    try:
        return TeamData.model_validate(data) if hasattr(TeamData, 'model_validate') else TeamData.parse_obj(data)
    except (ValidationError, Exception) as e:
        _log.error(f"Validation error for TeamData: {e}")
        return data

async def fetch_competition_info(session: aiohttp.ClientSession, cid: str) -> CompetitionData:
    data = await _fetch_json(session, _URLS["competition"], {"user": USER, "secret": SECRET, "uuid": cid}, f"comp[{cid}]")
    try:
        return CompetitionData.model_validate(data) if hasattr(CompetitionData, 'model_validate') else CompetitionData.parse_obj(data)
    except (ValidationError, Exception) as e:
        _log.error(f"Validation error for CompetitionData: {e}")
        return data

# Helper function to extract team and competition IDs from match data
def extract_ids(match: dict, details: dict = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (home_id, away_id, comp_id) picking from match first, else details."""
    home_id = match.get("home_team_id") or match.get("home", {}).get("id")
    away_id = match.get("away_team_id") or match.get("away", {}).get("id")
    comp_id = match.get("competition_id")
    
    # fallback to details API if any missing
    if details:
        det = details.get("results", [])
        if isinstance(det, list) and det:
            det = det[0]
            home_id = home_id or det.get("home_team_id")
            away_id = away_id or det.get("away_team_id")
            comp_id = comp_id or det.get("competition_id")
    
    _log.debug(f"extract_ids → home:{home_id}, away:{away_id}, comp:{comp_id}")
    return home_id, away_id, comp_id

# ─── ASYNC HELPERS TO BUILD YOUR CACHES ─────────────────────────────────────────
async def get_team_cache(session: aiohttp.ClientSession, tid: str) -> Dict[str,Any]:
    _log.debug(f"ENTER get_team_cache({tid})")
    if not tid or tid == "unknown":
        _log.warning(f"Invalid team ID {tid} → skipping cache fetch")
        return {}
        
    # Check for periodic metrics logging
    await asyncio.sleep(0)  # Yield to event loop to avoid blocking
    log_cache_metrics()
    
    # Use async lock to prevent race conditions in concurrent access
    async with _team_lock:
        # Check memory cache first (TTLCache handles expiration automatically)
        if tid in _team_cache:
            _log.debug(f"Memory cache hit for team {tid}")
            _cache_metrics["team"]["hits"] += 1
            return _team_cache[tid]
        
        # If not in memory but disk cache is enabled, try to load from disk
        if _ENABLE_DISK_CACHE:
            disk_data, disk_ts, success = await _load_from_disk("team", tid)
            if success and (time.time() - disk_ts <= _TTL):
                _log.debug(f"Disk cache hit for team {tid}")
                # Update memory cache
                _team_cache[tid] = disk_data
                _cache_metrics["team"]["disk_hits"] += 1
                return _team_cache[tid]
        
        # Cache miss, fetch from API
        _log.debug(f"Cache miss for team {tid}, fetching from API")
        _cache_metrics["team"]["misses"] += 1
        
        try:
            # Fetch from API
            data = await fetch_team_info(session, tid)
            
            # Ensure we have dictionary format, not Pydantic model
            data_dict = serialize_for_json(data) if data else {}
            
            # Debug the API response
            _log.debug(f"fetch_team_info returned: {data_dict.get('results', [])}")
            
            # Extract the team data
            res = data_dict.get("results") or []
            team_data = res[0] if isinstance(res, list) and res else {}
            
            # Validate we got useful data
            if not team_data:
                _log.warning(f"No team data returned for ID={tid}")
            
            # Update memory cache (TTLCache handles expiration)
            _team_cache[tid] = team_data
            
            # Asynchronously save to disk cache
            if _ENABLE_DISK_CACHE:
                now = time.time()
                asyncio.create_task(_save_to_disk("team", tid, team_data, now))
                
            return _team_cache[tid]
        except Exception as e:
            _log.error(f"Error fetching team {tid}: {str(e)}")
            return {}

async def get_comp_cache(session: aiohttp.ClientSession, cid: str) -> Dict[str,Any]:
    _log.debug(f"ENTER get_comp_cache({cid})")
    if not cid or cid == "unknown":
        _log.warning(f"Invalid competition ID {cid} → skipping cache fetch")
        return {}
    
    # Check for periodic metrics logging
    await asyncio.sleep(0)  # Yield to event loop to avoid blocking
    log_cache_metrics()
    
    # Use async lock to prevent race conditions in concurrent access
    async with _comp_lock:
        if cid in _comp_cache:
            _log.debug(f"Memory cache hit for competition {cid}")
            _cache_metrics["comp"]["hits"] += 1
            return _comp_cache[cid]
        
        # If not in memory but disk cache is enabled, try to load from disk
        if _ENABLE_DISK_CACHE:
            disk_data, disk_ts, success = await _load_from_disk("comp", cid)
            if success and (time.time() - disk_ts <= _TTL):
                _log.debug(f"Disk cache hit for competition {cid}")
                _comp_cache[cid] = disk_data
                _cache_metrics["comp"]["disk_hits"] += 1
                return _comp_cache[cid]
        
        # Cache miss, fetch from API
        _log.debug(f"Cache miss for competition {cid}, fetching from API")
        _cache_metrics["comp"]["misses"] += 1
        
        try:
            # Fetch from API
            data = await fetch_competition_info(session, cid)
            
            # Ensure we have dictionary format, not Pydantic model
            data_dict = serialize_for_json(data) if data else {}
            
            # Debug the API response
            _log.debug(f"fetch_competition_info returned: {data_dict.get('results', [])}")
            
            # Extract the competition data
            res = data_dict.get("results") or []
            comp_data = res[0] if isinstance(res, list) and res else {}
            
            # Validate we got useful data
            if not comp_data:
                _log.warning(f"No competition data returned for ID={cid}")
            
            # Update memory cache
            _comp_cache[cid] = comp_data
            
            # Asynchronously save to disk cache
            if _ENABLE_DISK_CACHE:
                now = time.time()
                asyncio.create_task(_save_to_disk("comp", cid, comp_data, now))
            
            return _comp_cache[cid]
        except Exception as e:
            _log.error(f"Error fetching competition {cid}: {str(e)}")
            return {}

async def get_country_map_cache(session: aiohttp.ClientSession) -> Dict[Any,str]:
    """Get country mapping, prioritizing our permanent map with common countries.
    
    Since country IDs and names rarely change, this function uses a permanent dictionary
    of common countries as the base, then supplements with API data only if necessary.
    
    Args:
        session: aiohttp session for making API requests if needed
        
    Returns:
        Dictionary mapping country IDs to country names
    """
    # We always have a permanent map of common countries
    global _country_map
    
    # Always increment permanent hit counter
    _cache_metrics["country"]["permanent"] += 1
    
    # Check if we already have more than just the permanent countries
    # This would indicate we've already fetched from the API
    if len(_country_map) > len(_PERMANENT_COUNTRY_MAP):
        _log.debug("Using existing country map with %d entries", len(_country_map))
        _cache_metrics["country"]["hits"] += 1
        return _country_map
    
    _log.info("Using permanent country map with %d entries", len(_PERMANENT_COUNTRY_MAP))
    
    # Try to supplement with API data, but don't block on it
    try:
        async with _country_lock:  # thread safety for async
            # We have the basic permanent map, but try to supplement with API data
            # for additional countries - this is non-critical and can fail gracefully
            _cache_metrics["country"]["misses"] += 1
            data = await fetch_country_data(session)
            
            # Handle potential Pydantic model or dictionary
            if hasattr(data, "results"):
                # It's a Pydantic model
                results = data.results if hasattr(data, "results") else []
            else:
                # It's a dictionary
                results = data.get("results", [])
            
            # Convert results to {id: name} mapping
            new_countries = 0
            for result in results:
                result_id = result.get("id")
                result_name = result.get("name")
                if result_id and result_name and result_id not in _country_map:
                    _country_map[result_id] = result_name
                    new_countries += 1
            
            if new_countries > 0:
                _log.info(f"Added {new_countries} additional countries from API")
            else:
                _log.debug("No new countries found from API")
                
    except Exception as e:
        # Non-critical - we can continue with just the permanent map
        _log.warning(f"Failed to fetch country data from API: {e}")
        _log.debug(f"Using only permanent country map with {len(_PERMANENT_COUNTRY_MAP)} entries")
    
    return _country_map

# ─── CACHE MANAGEMENT ───────────────────────────────────────────────────────
async def prewarm_caches(session: aiohttp.ClientSession, team_ids: list = None, comp_ids: list = None):
    """Pre-load caches in parallel to avoid first-hit latency
    
    Args:
        session: The aiohttp ClientSession to use for API calls
        team_ids: List of team IDs to pre-cache
        comp_ids: List of competition IDs to pre-cache
    """
    tasks = []
    
    # Always pre-load country data since it's small and used frequently
    _log.info("Prewarming country cache...")
    country_task = asyncio.create_task(get_country_map_cache(session))
    tasks.append(country_task)
    
    # Optionally prewarm team cache
    if team_ids and len(team_ids) > 0:
        _log.info(f"Prewarming {len(team_ids)} team caches...")
        for tid in team_ids:
            if tid and tid != "unknown":
                task = asyncio.create_task(get_team_cache(session, tid))
                tasks.append(task)
    
    # Optionally prewarm competition cache
    if comp_ids and len(comp_ids) > 0:
        _log.info(f"Prewarming {len(comp_ids)} competition caches...")
        for cid in comp_ids:
            if cid and cid != "unknown":
                task = asyncio.create_task(get_comp_cache(session, cid))
                tasks.append(task)
    
    # Wait for all prewarm tasks to complete
    if tasks:
        await asyncio.gather(*tasks)
        _log.info(f"Cache prewarming complete ({len(tasks)} items)")

async def cleanup_disk_cache():
    """Remove expired items from disk cache"""
    if not _ENABLE_DISK_CACHE or not os.path.exists(_CACHE_DIR):
        return
        
    now = time.time()
    count = 0
    
    for filename in os.listdir(_CACHE_DIR):
        try:
            filepath = os.path.join(_CACHE_DIR, filename)
            with open(filepath, 'rb') as f:
                cache_data = pickle.loads(f.read())
                
            # Remove if expired
            if now - cache_data["timestamp"] > _TTL:
                os.remove(filepath)
                count += 1
        except Exception as e:
            _log.warning(f"Error cleaning up cache file {filename}: {e}")
            
    _log.info(f"Removed {count} expired cache files")

# ─── MAIN FUNCTION ───────────────────────────────────────────────────────
async def main():
    """
    Main function to run the cache-enabled API fetcher.
    
    This demonstrates how to:
    1. Fetch live matches
    2. Get detailed match data
    3. Use the caching system for team/competition/country data
    4. Prewarm caches for efficient operation
    """
    _log.info("=== Starting API Fetch with Caching ===")
    
    # Start timer for performance metrics
    start_time = time.time()
    
    # Create a ClientSession that will be used for all requests
    connection_timeout = aiohttp.ClientTimeout(total=30) # 30s timeout
    async with aiohttp.ClientSession(timeout=connection_timeout) as session:
        try:
            # Periodically clean up disk cache if enabled
            if _ENABLE_DISK_CACHE:
                _log.info("Running disk cache cleanup...")
                await cleanup_disk_cache()
                
            # Fetch live matches
            _log.info("Fetching live matches...")
            matches_data = await fetch_live_matches(session)
            
            # Log sample match keys and structure for debugging
            if matches_data.get("results"):
                sample = matches_data["results"][0]
                _log.debug("LIVE sample keys: %s", list(sample.keys()))
                _log.debug("IDs in live: home=%r, away=%r, comp=%r",
                          sample.get("home_team_id"), sample.get("away_team_id"), sample.get("competition_id"))
            
            # Process and log the summary of matches
            log_match_summary(matches_data)
            
            # Extract all team and competition IDs for prewarming
            team_ids = set()
            comp_ids = set()
            
            if "results" in matches_data and matches_data["results"]:
                for match in matches_data["results"]:
                    # Extract team IDs
                    if "home" in match and match["home"] and "id" in match["home"]:
                        team_ids.add(match["home"]["id"])
                    elif "home_team_id" in match and match["home_team_id"] != "unknown":
                        team_ids.add(match["home_team_id"])
                        
                    if "away" in match and match["away"] and "id" in match["away"]:
                        team_ids.add(match["away"]["id"])
                    elif "away_team_id" in match and match["away_team_id"] != "unknown":
                        team_ids.add(match["away_team_id"])
                    
                    # Extract competition IDs
                    if "competition_id" in match and match["competition_id"] != "unknown":
                        comp_ids.add(match["competition_id"])
            
            # If matches exist, process them
            if "results" in matches_data and matches_data["results"]:
                matches = matches_data["results"]
                _log.info(f"Found {len(matches)} live matches")
                
                # Debug: Examine the structure of the first match to determine ID locations
                _sample = matches[0]
                _log.debug("SAMPLE KEYS: %s", list(_sample.keys()))
                _log.debug("home_team_id fields: %r / %r",
                          _sample.get("home_team_id"),
                          _sample.get("home", {}).get("id"))
                _log.debug("away_team_id fields: %r / %r",
                          _sample.get("away_team_id"),
                          _sample.get("away", {}).get("id"))
                _log.debug("competition_id     : %r", _sample.get("competition_id"))
                
                # Use permanent country map for lookups (with API fallback if needed)
                _log.info("Using permanent country map for enrichment")
                countries = await get_country_map_cache(session)
                _log.info(f"Using country map with {len(countries)} entries")
            
                # Process all matches with enrichment
                all_processed_matches = []
                match_count = 0
                
                for match in matches:
                    match_count += 1
                    match_id = match.get("id")
                    
                    if match_count % 10 == 0 or match_count == 1:
                        _log.info(f"Processing match {match_count}/{len(matches)} - ID: {match_id}")
                    
                    # First, fetch match details
                    match_details = await fetch_match_details(session, match_id)
                    match_details_dict = serialize_for_json(match_details)
                    
                    # Now extract IDs from live OR details
                    home_team_id, away_team_id, competition_id = extract_ids(
                        match, match_details_dict
                    )
                    
                    _log.debug(f"Using IDs home={home_team_id}, away={away_team_id}, comp={competition_id}")
                    
                    # Fetch odds after ID extraction
                    match_odds = await fetch_match_odds(session, match_id)
                    match_odds_dict = serialize_for_json(match_odds)
                    
                    # Get team and competition data for enrichment
                    team_home = {}
                    team_away = {}
                    competition = {}
                    
                    # Fetch home team data if we have a valid ID
                    if home_team_id:
                        _log.debug(f"Fetching home team data for ID: {home_team_id}")
                        team_home = await get_team_cache(session, home_team_id)
                        if not team_home:
                            _log.warning(f"No data returned for home team ID={home_team_id} in match {match_id}")
                    
                    # Fetch away team data if we have a valid ID
                    if away_team_id:
                        _log.debug(f"Fetching away team data for ID: {away_team_id}")
                        team_away = await get_team_cache(session, away_team_id)
                        if not team_away:
                            _log.warning(f"No data returned for away team ID={away_team_id} in match {match_id}")
                    
                    # Fetch competition data if we have a valid ID
                    if competition_id:
                        _log.debug(f"Fetching competition data for ID: {competition_id}")
                        competition = await get_comp_cache(session, competition_id)
                        if not competition:
                            _log.warning(f"No data returned for competition ID={competition_id} in match {match_id}")
                    
                    # Get country name from country mapping
                    country_id = competition.get("country_id")
                    country_name = "Unknown Country"
                    if country_id and country_id in countries:
                        country_name = countries.get(country_id)
                    
                    # Build enriched match data
                    match_data = {
                        "match_id": match_id,
                        "basic_info": match,
                        "details": match_details_dict,
                        "odds": match_odds_dict,
                        "enriched": {
                            "home_team": {"id": home_team_id, **team_home},
                            "away_team": {"id": away_team_id, **team_away}, 
                            "competition": {"id": competition_id, **competition}
                        },
                        "metadata": {
                            "country_name": country_name,
                            "country_id": country_id,
                            "fetch_time": get_eastern_time()
                        }
                    }
                    
                    # Add to collection
                    all_processed_matches.append(match_data)
                
                # Log cache statistics and metrics
                log_cache_stats()
                
                # Save ALL match data
                _log.info(f"\nSaving all {len(all_processed_matches)} matches to {MATCH_CACHE_PATH}")
                
                # Build output with all matches and global metadata
                output_data = {
                    "matches": all_processed_matches,
                    "metadata": {
                        "total_matches": len(all_processed_matches),
                        "fetch_time": get_eastern_time(),
                        "cache_stats": {
                            "teams_cached": len(_team_cache),
                            "competitions_cached": len(_comp_cache),
                            "countries_cached": len(_country_map)
                        },
                        "cache_metrics": _cache_metrics
                    }
                }
                
                # Also save the first match as sample for compatibility
                if all_processed_matches:
                    _log.info(f"Also saving first match as {SAMPLE_CACHE_PATH} for compatibility")
                    await write_json_file(SAMPLE_CACHE_PATH, serialize_for_json(all_processed_matches[0]))
                
                # Write full dataset with all matches
                await write_json_file(MATCH_CACHE_PATH, serialize_for_json(output_data))
                _log.info(f"Successfully wrote data to {MATCH_CACHE_PATH}")
            else:
                _log.warning("No live matches found or unexpected response format")
        except Exception as e:
            _log.exception(f"Error during API fetch: {str(e)}")
            _log.error(traceback.format_exc())
        finally:
            # Always show runtime stats
            runtime = time.time() - start_time
            _log.info(f"Total runtime: {runtime:.2f} seconds")
    
    _log.info("=== API Fetch Complete ===")

# Helper function to write JSON to file asynchronously
async def write_json_file(file_path: Path, data: Any) -> None:
    """Write data to a JSON file asynchronously."""
    try:
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2))
    except Exception as e:
        _log.error(f"Error writing to {file_path}: {str(e)}")
        raise

# Function to fetch and cache data - used by the alert system
def fetch_and_cache():
    """Fetch the latest match data or load from cache.
    
    This function is used by the alert system to retrieve the latest match data.
    It returns the data directly from the cache file to avoid running a new async fetch.
    
    Returns:
        dict: The full match data including all matches and metadata
    """
    try:
        # Read directly from the cache file
        if not MATCH_CACHE_PATH.exists():
            _log.warning(f"Cache file {MATCH_CACHE_PATH} does not exist, alert system may not work properly")
            return {"matches": [], "metadata": {}}
            
        with open(MATCH_CACHE_PATH, 'r') as f:
            cache_data = json.load(f)
            _log.info(f"Loaded {len(cache_data.get('matches', []))} matches from cache for alert processing")
            return cache_data
    except Exception as e:
        _log.error(f"Error loading cache for alerts: {e}")
        return {"matches": [], "metadata": {}}


# Run the main function when script is executed directly
if __name__ == "__main__":
    asyncio.run(main())
    
    # Quick sanity check
    import json
    try:
        with open("sample_match_cache.json") as f:
            sample = json.load(f)
            print("\n==== ENRICHED SAMPLE CHECK ====")
            print(f"Home Team: {sample.get('home_team', 'MISSING')}")
            print(f"Away Team: {sample.get('away_team', 'MISSING')}")
            print(f"Competition: {sample.get('competition', 'MISSING')}")
            print(f"Country: {sample.get('country', 'MISSING')}")
            print("===============================")
            
            # Check for any 'Unknown' values
            has_unknown = False
            for field in ['home_team', 'away_team', 'competition', 'country']:
                if sample.get(field, '').startswith('Unknown'):
                    has_unknown = True
                    print(f"WARNING: {field} is {sample.get(field)}")
            
            if not has_unknown:
                print("✅ All fields are properly enriched!")
            else:
                print("❌ Some fields are still not enriched properly.")
    except Exception as e:
        print(f"Error in sanity check: {e}")

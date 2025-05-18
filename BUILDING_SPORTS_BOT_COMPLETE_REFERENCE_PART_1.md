# Building Sports Bot: Complete Reference
## Part 1: Project Setup & Data Fetching

This guide provides step-by-step instructions for setting up the foundation of the Football Match Tracking System with detailed explanations and code examples, focusing specifically on the project structure and data fetching components.

## 1. Project Directory Structure
```bash
# lines 1-3: Create project directory and initialize git repository
mkdir Complete_Seperate
cd Complete_Seperate
git init

# lines 5-7: Create organized project subdirectories
mkdir -p Alerts core docs logs tests tools
touch README.md DATA_FLOW.md LOGGING_SYSTEM_RULES.md
```

### Directory Organization:
- `/Alerts`: Alert modules and implementations
- `/core`: Primary pipeline modules
- `/docs`: Technical documentation
- `/logs`: Log output directory (added to .gitignore)
- `/tests`: Test suite
- `/tools`: Diagnostic and utility scripts

## 2. Virtual Environment Setup
```bash
# lines 10-12: Create and activate virtual environment
python3 -m venv sports_venv
source sports_venv/bin/activate

# lines 14-15: Install required dependencies
pip install aiohttp cachetools tenacity psutil pytest
pip freeze > requirements.txt  # Save exact versions for reproducibility
```

**Technical Note**: The virtual environment (`sports_venv`) enables isolation of our project dependencies from the system Python, ensuring consistent behavior across different environments and preventing conflicts with other Python applications.

## 3. Core Fetch Module Implementation

The fetch module (`pure_json_fetch_cache.py`) is responsible for retrieving live match data from the sports API and caching it to avoid unnecessary API calls.

```python
# lines 20-35: Core imports for the fetch module
import aiohttp
import asyncio
import json
import os
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, Any, Optional, List

# lines 37-40: Initialize logging using centralized configuration
from log_config import get_logger
logger = get_logger('fetch')

# lines 42-47: Cache directory configuration
CACHE_DIR = os.environ.get('SPORTS_CACHE_DIR', 'cache')
CACHE_TTL = int(os.environ.get('SPORTS_CACHE_TTL', 60))  # Seconds
os.makedirs(CACHE_DIR, exist_ok=True)
```

### Retry-Capable HTTP Client (lines 50-80)
```python
class SportsFetcher:
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        # lines 52-55: Initialize fetcher with configuration
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.session = None
    
    async def _ensure_session(self):
        # lines 58-60: Lazily create HTTP session when needed
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        # lines 64-79: Fetch data with retry logic
        await self._ensure_session()
        cache_key = self._generate_cache_key(endpoint, params)
        cached_data = self._check_cache(cache_key)
        
        if cached_data:
            logger.info(f"Cache hit for {endpoint}")
            return cached_data
        
        logger.info(f"Fetching {endpoint} from API")
        async with self.session.get(
            f"{self.base_url}/{endpoint}",
            params={**(params or {}), 'api_key': self.api_key}
        ) as response:
            response.raise_for_status()
            data = await response.json()
            self._save_to_cache(cache_key, data)
            return data
```

### Cache Management (lines 82-115)
```python
    def _generate_cache_key(self, endpoint: str, params: Dict = None) -> str:
        # lines 83-88: Create unique cache key based on endpoint and parameters
        params_str = json.dumps(params or {}, sort_keys=True)
        hash_input = f"{endpoint}:{params_str}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        # lines 90-92: Generate filesystem path for cache item
        return Path(CACHE_DIR) / f"{cache_key}.json"
    
    def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        # lines 94-105: Check if valid cache exists and return it if not expired
        cache_path = self._get_cache_path(cache_key)
        if not cache_path.exists():
            return None
        
        # Check if cache has expired
        mtime = cache_path.stat().st_mtime
        if time.time() - mtime > CACHE_TTL:
            logger.debug(f"Cache expired for {cache_key}")
            return None
        
        try:
            with cache_path.open('r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        # lines 107-115: Save API response to cache file
        cache_path = self._get_cache_path(cache_key)
        try:
            with cache_path.open('w') as f:
                json.dump(data, f)
            logger.debug(f"Saved to cache: {cache_key}")
        except IOError as e:
            logger.error(f"Cache write error: {e}")
```

### Main Fetch Function (lines 118-145)
```python
async def fetch_live_matches() -> List[Dict[str, Any]]:
    # lines 118-124: Configure API credentials from environment
    api_key = os.environ.get('SPORTS_API_KEY') 
    if not api_key:
        logger.error("No API key provided via SPORTS_API_KEY environment variable")
        return []
    
    base_url = os.environ.get('SPORTS_API_URL', 'https://api.thesports.com/v1/football')
    fetcher = SportsFetcher(base_url, api_key)
    
    try:
        # lines 127-131: Fetch live matches data
        logger.info("Starting live match data fetch")
        start_time = time.time()
        matches_data = await fetcher.fetch('match/detail_live')
        
        # lines 133-136: Process and log results
        matches = matches_data.get('results', [])
        fetch_time = time.time() - start_time
        logger.info(f"Fetched {len(matches)} live matches in {fetch_time:.2f} seconds")
        
        return matches
    except Exception as e:
        # lines 139-142: Handle and log errors
        logger.error(f"Error fetching live matches: {e}")
        return []
    finally:
        # lines 144-145: Clean up session
        if fetcher.session:
            await fetcher.session.close()
```

### Synchronous Entry Point (lines 148-160)
```python
def fetch_matches() -> List[Dict[str, Any]]:
    # lines 148-159: Provide synchronous interface for async function
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Create new event loop if none exists
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(fetch_live_matches())
    finally:
        # Don't close the loop as it might be used elsewhere
        pass
```

## 4. Setting Up Robust Command-line Entry Point

Create a shell script (`run_pipeline.sh`) that handles virtual environment activation and proper logging:

```bash
# lines 163-184: Shell script for running the pipeline
#!/usr/bin/env bash
# This is the ONLY supported way to start the sports bot pipeline.
# It activates the virtual environment and runs the orchestrator.

# Fail on any error
set -e

# Get absolute path to script directory
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ensure logs directory exists with absolute paths
mkdir -p "$BASE_DIR/logs"

# Log start timestamp and PID
echo "$(date) STARTING pipeline (PID $$)" >> "$BASE_DIR/logs/cron.log"

# Activate virtual environment
source "$BASE_DIR/sports_venv/bin/activate"

# Run the orchestrator with proper error handling
python "$BASE_DIR/orchestrate_complete.py" || {
    echo "$(date) ERROR: Pipeline failed with code $?" >> "$BASE_DIR/logs/cron.log"
    exit 1
}

echo "$(date) SUCCESS: Pipeline completed" >> "$BASE_DIR/logs/cron.log"
```

Make the script executable:
```bash
# line 187: Make run script executable
chmod +x run_pipeline.sh
```

## 5. Testing the Fetch Module

Create a test file to verify the fetch functionality works correctly:

```python
# lines 190-220: Test file for fetch module (tests/test_fetch_cache.py)
import os
import json
import pytest
from unittest.mock import patch, AsyncMock
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pure_json_fetch_cache import fetch_matches, SportsFetcher

@pytest.fixture
def mock_response():
    mock = AsyncMock()
    mock.json.return_value = {
        "results": [
            {"match_id": "123", "status": "live"},
            {"match_id": "456", "status": "live"}
        ]
    }
    mock.__aenter__.return_value = mock
    mock.raise_for_status = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_fetch_live_matches(mock_response):
    with patch('aiohttp.ClientSession.get', return_value=mock_response):
        with patch.dict('os.environ', {"SPORTS_API_KEY": "test_key"}):
            fetcher = SportsFetcher("https://api.test.com", "test_key")
            data = await fetcher.fetch("match/detail_live")
            
            assert "results" in data
            assert len(data["results"]) == 2
            assert data["results"][0]["match_id"] == "123"
```

## 6. Next Steps

In Part 2, we'll cover:
- Implementing the `merge_logic.py` module
- Creating the summary generation component
- Developing the central orchestrator
- Integrating with the alerts subsystem

## Key Takeaways

- **Structured Project Layout**: Clear directory organization keeps the codebase manageable as it grows
- **Virtual Environment**: Ensures reproducible builds with consistent dependencies
- **Cached API Access**: Reduces API calls and improves performance while providing fallback during API outages
- **Typed Code**: Using Python type hints improves code quality and documentation
- **Error Handling**: Robust retry logic and proper error logging
- **Testability**: Designing components that can be easily tested in isolation

# Football Match Tracking System: Logging Flow

**Documentation Created: May 18, 2025 10:21 AM EDT**

## Example Log Output

```
STEP 1: JSON fetch: 05/18/2025 10:19:45 AM EDT
✅ Pipeline completed in 373.19 seconds: 05/18/2025 10:19:26 AM EDT
===============#MATCH 1 of 278================
          05/18/2025 10:19:24 AM EDT          

Match ID: 318q66hw9y87qo9
Competition ID: yl5ergphd2r8k0o
Competition: Moldova Division 2 (Moldova)
Match: Saxan Ceadir Lunga vs FC Ursidos Stauceni
Score: 1 - 1 (HT: 0 - 1)
Status: Finished (Status ID: 8)

--- MATCH BETTING ODDS ---
No betting odds available

--- MATCH ENVIRONMENT ---
No environment data available

------------------------------------------------------------
```

## Core Log Files

### 1. Primary Summary Logs

- **`logs/summary/pipeline.log`**
  - **Purpose**: Contains the main match summaries with detailed information
  - **Logger**: `summary.pipeline` 
  - **Handler**: `summary_file`
  - **Content**: Match details, IDs, competition info, scores, betting odds, and completion messages

- **`logs/summary/orchestration.log`**
  - **Purpose**: Logs orchestration-related events and alerts processing
  - **Logger**: `summary.orchestration`
  - **Handler**: `match_summary_file`
  - **Content**: Alerts processing, orchestration errors, and validation messages

- **`logs/summary/summary_json.logger`**
  - **Purpose**: Stores raw JSON data for matches
  - **Logger**: `summary_json`
  - **Handler**: `summary_json_file`
  - **Content**: Large JSON structures with all match data (36MB+)

### 2. Component-Specific Logs

- **`logs/orchestrator.log`**
  - **Purpose**: Main orchestration process logs
  - **Logger**: `orchestrator`
  - **Handler**: `orchestrator_file` and `console`
  - **Content**: Core pipeline events, validation results, memory usage

- **`logs/fetch/fetch_data.log`**
  - **Purpose**: Records data fetching operations
  - **Logger**: `fetch_data`
  - **Handler**: `fetch_data_file`
  - **Content**: API calls, data retrieval events, HTTP responses

- **`logs/fetch/merge_logic.log`**
  - **Purpose**: Documents data merging and processing
  - **Logger**: `merge_logic`
  - **Handler**: `merge_logic_file`
  - **Content**: Data transformation, enrichment operations

- **`logs/pure_json_fetch.log`**
  - **Purpose**: Raw fetch operations without processing
  - **Logger**: `pure_json_fetch`
  - **Handler**: `fetch_cache_file`
  - **Content**: Raw API responses, cache hits/misses

### 3. Monitoring Logs

- **`logs/memory/memory_monitor.log`**
  - **Purpose**: Tracks memory usage throughout pipeline execution
  - **Logger**: `memory_monitor`
  - **Handler**: `memory_monitor_file` and `console`
  - **Content**: Memory usage statistics, leak detection

- **`logs/monitor/logger_monitor.log`**
  - **Purpose**: Monitors logger behavior itself
  - **Logger**: `logger_monitor`
  - **Handler**: `logger_monitor_file` and `console`
  - **Content**: Logger creation, handler registration, logging overhead

- **`logs/alerts/alerter_main.log`**
  - **Purpose**: Alert system activity and triggers
  - **Logger**: `alerter_main`
  - **Handler**: `alerts_file` and `console`
  - **Content**: Alert conditions, notifications, rule processing

## Logging Flow

1. **Pipeline Initiation**
   - When the pipeline starts, `orchestrator` logger records startup and configuration
   - Memory and logger monitors begin tracking system resources

2. **Data Fetching**
   - `summary.pipeline` logs "STEP 1: JSON fetch" with timestamp
   - `pure_json_fetch` records raw API responses
   - `fetch_data` logs transformation of raw data

3. **Data Processing**
   - `summary.pipeline` logs "STEP 2: Merge and enrichment" with timestamp
   - `merge_logic` records data enrichment operations

4. **Match Summary Generation**
   - Match details are logged to `pipeline.log` via `summary.pipeline`
   - Complete JSON data is written to `summary_json.logger`

5. **Alert Processing**
   - `alerter_main` processes matches against alert rules
   - Results sent to `summary.orchestration` for logging

6. **Completion**
   - Pipeline completion with timing is logged to `pipeline.log`
   - Final memory usage and resource stats are recorded

## Configuration Structure

The entire logging system is centrally configured in `log_config.py` through the `LOGGING_CONFIG` dictionary, which defines:

1. **Formatters**: Define how log messages are formatted
   - `standard` - Used for console/detailed logs
   - `summary` - Used for match summary logs

2. **Handlers**: Define where logs are sent
   - File handlers (using `PrependFileHandler` for newest-first ordering)
   - Console handlers for interactive feedback

3. **Loggers**: Define named logging channels with specific behaviors
   - Each component has its own logger with appropriate handlers
   - Propagation is set to False to prevent duplicate logs

## Key Design Features

1. **Centralized Configuration**: All logging settings defined in `log_config.py`
2. **Eastern Timezone**: All timestamps use Eastern time zone (EDT/EST)
3. **Newest-First Ordering**: `PrependFileHandler` ensures newest logs appear at the top of files
4. **File Rotation**: All log files rotate at midnight with configurable retention (30 days default)
5. **Separation of Concerns**: Each component has dedicated loggers and handlers

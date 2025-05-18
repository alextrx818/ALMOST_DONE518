# Football Match Tracking System

## FIRST TIME SETUP (MANDATORY)

**After cloning this repository, you MUST run the setup script to configure logging enforcement:**

```bash
# line 10-12: Run this command immediately after cloning
./setup_hooks.sh
```

This script:
- Configures Git to use the `.githooks` directory for hooks
- Sets up automatic enforcement of logging standards on commit
- Ensures all code changes follow the standardized logging approach

**Without running this script, logging standards will not be enforced, which can lead to inconsistent logging behavior.**

## STARTUP INSTRUCTIONS (MANDATORY)

**This project can ONLY be started using the provided shell script:**

```bash
# line 28-30: Always use the run script, never call Python directly
run_pipeline.sh
```

This script:
- Activates the externally managed Python virtual environment
- Runs the orchestrate_complete.py pipeline

**Manual or direct invocation of orchestrate_complete.py is NOT supported. Always use run_pipeline.sh to start the system.**

## Standardized Logging System

This project implements a comprehensive standardized logging system. All logging operations must follow these standards:

### 1. Use Centralized Logging Configuration

All loggers must be created using the standard logging module, with configuration centralized in `log_config.py`:

```python
# line 37-38: Import the standard logging module
import logging

# line 40-41: Create a standardized logger
logger = logging.getLogger("module_name")

# line 43-44: For summary loggers, use the static configuration
import logging
logger = logging.getLogger("summary.pipeline")
```

### 2. Prohibited Practices

The following logging practices are strictly prohibited and will be caught by the pre-commit hook:

```python
# ❌ PROHIBITED: Custom formatter creation
formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")  # Will fail validation

# ❌ PROHIBITED: Manual handler attachment
handler = logging.StreamHandler()
logger.addHandler(handler)  # Will fail validation
```

### 3. Runtime Validation

The system includes runtime validation to ensure log consistency:

```python
# line 120-123: Configuration must be called at application startup
from log_config import configure_logging
configure_logging()

# line 222-223: Log validation can be run explicitly
from log_config import validate_logger_configuration
result = validate_logger_configuration()  # Should return True
```

### 4. Testing Logging in Different Modes

To verify logging in strict and non-strict modes:

```bash
# line 1-2: Run the validator test script
python3 tools/test_logging_modes.py
```

For more detailed information, see the [LOGGING_SYSTEM_RULES.md](LOGGING_SYSTEM_RULES.md) file.

---

## Virtual Environment
- The virtual environment is located at:
  ```
  /root/CascadeProjects/sports_bot/football/main/sports_venv/
  ```
- This environment must be initialized and activated by the `run_pipeline.sh` script before starting the orchestrator.

---

## Project Overview
The Football Match Tracking System is designed to monitor live football matches, process match data, generate human-readable summaries, and send alerts based on specific match conditions.

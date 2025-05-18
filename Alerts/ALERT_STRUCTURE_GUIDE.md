# Alert Skeleton Structure Creation

This README outlines the high-level notes to embed into your code and the natural-language commands to instruct your AI coding agent to implement each step of the alert subsystem.

---

## 1. In `Alerts/base_alert.py`

**Note to insert at the very top (under the docstring):**

```python
# NOTE FOR AI BOT:
# To create a new alert scanner, simply drop a .py file in this Alerts/ folder,
# define a class that subclasses Alert, and implement check(match). No other
# files need touching—you'll be auto‑discovered.
```

**Command to your coding agent:**

```
"In Alerts/base_alert.py, add the above NOTE FOR AI BOT comment under the module docstring."
```

---

## 2. In `Alerts/alerter_main.py`

**Note to insert in the `discover_alerts` docstring (or immediately above it):**

```python
# NOTE FOR AI BOT:
# This method auto‑discovers all subclasses of Alert—you never need to
# manually import or list them. If you drop a new scanner here, it'll be
# picked up automatically.
```

**Note to insert at the top of `__init__`:**

```python
# NOTE FOR AI BOT:
# After discovery, we must initialize each alert: set up per‑alert log files
# and load its <AlertName>.seen.json state. See _initialize_alert() below.
```

**Command to your coding agent:**

```
"In alerter_main.py, add the two NOTE FOR AI BOT comments—one above discover_alerts() and one at the top of __init__(). Then implement a private helper _initialize_alert(self, alert) that encapsulates the old file‑base / seen‑IDs logic, and call _initialize_alert(alert) for each alert immediately after instantiation in __init__. Keep the rest of the constructor intact."
```

---

## 3. In `orchestrate_complete.py`

**Note to insert just above the call to `run_alerters(...)`:**

```python
# NOTE FOR AI BOT:
# This is the single entry point for alerts in the main pipeline.
# Do not invoke AlerterMain.run() here—always call run_alerters(summary_json, match_ids).
```

**Note to insert just above the `alert_params = {...}` block:**

```python
# NOTE FOR AI BOT:
# Alert parameters come from Alerts/alerts_config.py.
# Load them here instead of hard‑coding values.
```

**Command to your coding agent:**

```
"In orchestrate_complete.py, add those two NOTE FOR AI BOT comments. Then replace the hard‑coded alert_params = {...} literal by importing a new alerts_config.py (or .json) from the Alerts folder and using its ALERT_PARAMS mapping. Remove any direct references to AlerterMain.run(), leaving only run_alerters(). Ensure run_alerters() still passes through the loaded config."
```

---

## 4. Create `Alerts/alerts_config.py`

**File contents sketch:**

```python
# alerts_config.py – Centralized alert parameters

# Example:
ALERT_PARAMS = {
    "OverUnderAlert": {"threshold": 3.0},
    # Add other alerts here as you create them:
    # "MyNewAlert": {"paramA": "foo", "paramB": 42},
}
```

**Command to your coding agent:**

```
"Add a new file Alerts/alerts_config.py containing an ALERT_PARAMS dict. Then update discover_alerts() to merge each class's optional DEFAULT_PARAMS with ALERT_PARAMS.get(class_name, {}), instantiating each alert with those merged settings—skipping or logging any instantiation errors without crashing."
```

---

## 5. Enhance `Alert` base class for optional debug logging

**Pseudocode to add in `base_alert.py` constructor:**

```python
def __init__(self, name: str, debug: bool = False):
    self.name = name
    self.logger = get_logger(name)
    if debug:
        handler = logging.FileHandler(Path(__file__).parent / f"{name}_debug.log")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
```

**Command to your coding agent:**

```
"Modify the Alert.__init__ signature to accept debug=False. If debug is true, add a DEBUG‑level file handler named <AlertName>_debug.log with a standard timestamped formatter. Do not change any satellite code except to pass debug=True where needed."
```

---

### Final Integration Checklist

1. **Insert Notes**: Embed each "NOTE FOR AI BOT" comment in the three code files above.
2. **\_initialize\_alert Helper**: Create and call this to restore per‑alert file‑base & seen‑IDs logic.
3. **Deprecate run()**: Remove or mark `AlerterMain.run()` as deprecated, keeping only `run_alerters()`.
4. **Config File**: Add `Alerts/alerts_config.py` and wire it into `discover_alerts()`.
5. **Debug Handler**: Update `base_alert.py` to accept a `debug` flag and optionally attach a file handler.

Follow these commands in order to set up a robust, self‑documenting, auto‑discovering alert skeleton for your AI coding agent. Happy coding!

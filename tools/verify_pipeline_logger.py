import sys
from pathlib import Path
import os

# Add the parent directory to Python path to allow importing log_config
sys.path.append(str(Path(__file__).parent.parent))

import log_config
# 1. Initialize the central config:
log_config.configure_logging()

# 2. Grab both the regular pipeline logger and summary.pipeline logger:
pipeline_logger = log_config.get_logger(log_config.PIPELINE_LOGGER)
summary_pipeline_logger = logging.getLogger("summary.pipeline")

# 3. Introspect the regular pipeline logger handlers & formatters:
print("\n=== REGULAR PIPELINE LOGGER ===")
print("Logger name:", pipeline_logger.name)
print("HANDLERS:", [type(h).__name__ for h in pipeline_logger.handlers])
print("FORMATS:", [h.formatter._fmt for h in pipeline_logger.handlers])

# 4. Introspect the summary.pipeline logger handlers & formatters:
print("\n=== SUMMARY.PIPELINE LOGGER ===")
print("Logger name:", summary_pipeline_logger.name)
print("HANDLERS:", [type(h).__name__ for h in summary_pipeline_logger.handlers]) 
print("FORMATS:", [h.formatter._fmt for h in summary_pipeline_logger.handlers])
print("LOG FILES:", [getattr(h, 'baseFilename', 'N/A') for h in summary_pipeline_logger.handlers])

# 5. Emit test messages to both
print("\n=== SENDING TEST MESSAGES ===")
pipeline_logger.info("🚀 TEST_PIPELINE_LOGGER")
summary_pipeline_logger.info("🚀 TEST_SUMMARY_PIPELINE_LOGGER")
print("Test messages sent!")

#!/usr/bin/env python3
# Diagnostic script to analyze active loggers at runtime
import logging
import sys

print("=== ACTIVE LOGGER ANALYSIS ===")
print(f"Total loggers in manager.loggerDict: {len(logging.Logger.manager.loggerDict)}")
print("\nActive loggers and their handler counts:")

for name, logger in sorted(logging.Logger.manager.loggerDict.items()):
    if isinstance(logger, logging.Logger):
        print(f"{name!r}: handlers={len(logger.handlers)}")

# Check root logger configuration
root_logger = get_logger()
print(f"\nRoot Logger: level={logging.getLevelName(root_logger.level)}, handlers={len(root_logger.handlers)}")

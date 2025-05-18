#!/usr/bin/env python3
# inspect_handlers.py - Diagnostic tool for logging system analysis
import logging
import sys
from pathlib import Path

# Add project root to path to ensure imports work
sys.path.append(str(Path(__file__).parent.parent))

# First print general stats
print(f"Total loggers in manager.loggerDict: {len(logging.Logger.manager.loggerDict)}")
print("\n=== ACTIVE LOGGERS AND THEIR CONFIGURATIONS ===")

# Examine all loggers
for name, logger in sorted(logging.Logger.manager.loggerDict.items()):
    if isinstance(logger, logging.Logger):
        # Get handler count and formatter info
        handler_count = len(logger.handlers)
        
        # Format and formatter information
        fmt_strings = []
        handler_types = []
        for h in logger.handlers:
            handler_type = h.__class__.__name__
            handler_types.append(handler_type)
            
            if hasattr(h, 'formatter') and h.formatter:
                if hasattr(h.formatter, '_fmt'):
                    fmt_strings.append(h.formatter._fmt)
                else:
                    fmt_strings.append("No _fmt attribute")
            else:
                fmt_strings.append("No formatter")
                
        # Print details
        print(f"\nLogger: {name!r}")
        print(f"  Level: {logging.getLevelName(logger.level)}")
        print(f"  Propagate: {logger.propagate}")
        print(f"  Handlers: {handler_count}")
        
        # Show handlers and formatters
        if handler_count > 0:
            print(f"  Handler Types: {handler_types}")
            print(f"  Format Strings: {fmt_strings}")
        else:
            print("  No handlers attached")

# Check root logger too
root_logger = get_logger()
root_handlers = len(root_logger.handlers)
root_fmt_strings = [
    h.formatter._fmt if (hasattr(h, 'formatter') and h.formatter and hasattr(h.formatter, '_fmt')) 
    else "No formatter" 
    for h in root_logger.handlers
]
print(f"\nRoot Logger:")
print(f"  Level: {logging.getLevelName(root_logger.level)}")
print(f"  Handlers: {root_handlers}")
if root_handlers > 0:
    print(f"  Format Strings: {root_fmt_strings}")

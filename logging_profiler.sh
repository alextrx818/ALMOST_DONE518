#!/bin/bash
# line 1-2: Profiling script to measure logging overhead
# Creates precise timing measurements for logging operations

# line 4-5: Create output file for timing metrics
mkdir -p /root/Complete_Seperate/logs
LOG_FILE="/root/Complete_Seperate/logs/logging_overhead.log"
echo "Logging overhead profiling started at $(date)" > $LOG_FILE

# line 8-12: First test - with systemd-cat logging
echo "=== TEST WITH SYSTEMD-CAT LOGGING ===" >> $LOG_FILE
cp /root/Complete_Seperate/service_wrapper.sh.original /root/Complete_Seperate/service_wrapper.sh
chmod +x /root/Complete_Seperate/service_wrapper.sh
START=$(date +%s%N)
/root/Complete_Seperate/service_wrapper.sh
END=$(date +%s%N)
WITH_LOGGING_MS=$(( ($END - $START) / 1000000 ))
echo "Runtime with logging: $WITH_LOGGING_MS ms" >> $LOG_FILE

# line 15-19: Second test - without systemd-cat logging
echo "=== TEST WITHOUT SYSTEMD-CAT LOGGING ===" >> $LOG_FILE
sed -i.bak "/systemd-cat -t football_bot/d; /logger -t football_bot/d" /root/Complete_Seperate/service_wrapper.sh
START=$(date +%s%N)
/root/Complete_Seperate/service_wrapper.sh
END=$(date +%s%N)
WITHOUT_LOGGING_MS=$(( ($END - $START) / 1000000 ))
echo "Runtime without logging: $WITHOUT_LOGGING_MS ms" >> $LOG_FILE

# line 21-24: Calculate and report overhead
OVERHEAD_MS=$(( $WITH_LOGGING_MS - $WITHOUT_LOGGING_MS ))
OVERHEAD_PCT=$(( $OVERHEAD_MS * 100 / $WITHOUT_LOGGING_MS ))
echo "Logging overhead: $OVERHEAD_MS ms ($OVERHEAD_PCT%)" >> $LOG_FILE
echo "Logging overhead: $OVERHEAD_MS ms ($OVERHEAD_PCT%)"

# line 26-27: Restore original script
cp /root/Complete_Seperate/service_wrapper.sh.original /root/Complete_Seperate/service_wrapper.sh

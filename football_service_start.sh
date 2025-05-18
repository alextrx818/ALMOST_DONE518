#!/bin/bash
# lines 1-2: Football service launcher with clean environment setup

# line 4-5: Activate virtual environment with absolute path
cd /root/Complete_Seperate
source /root/Complete_Seperate/sports_venv/bin/activate

# line 8-9: Set environment variables
export VIRTUAL_ENV=/root/Complete_Seperate/sports_venv
export PATH="$VIRTUAL_ENV/bin:$PATH"

# line 12-13: Run service wrapper in a loop
while true; do 
  /root/Complete_Seperate/service_wrapper.sh
  sleep 15
done

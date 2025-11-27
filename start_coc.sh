#!/bin/bash

# Change to the correct directory
cd /home/tnv/Desktop/ClashOfClansWarTracker/

# Start a detached screen session named COC and run the Python command inside it
# We use the venv's Python path directly to skip 'source activate'
/usr/bin/screen -dmS COC /home/tnv/Desktop/ClashOfClansWarTracker/venv/bin/python3 run_production.py
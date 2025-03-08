#!/bin/bash

# Change to the application directory
cd /home/pi/chromecast

# Activate the virtual environment
source venv/bin/activate

# Start the application
python3 main.py --web --port=80 
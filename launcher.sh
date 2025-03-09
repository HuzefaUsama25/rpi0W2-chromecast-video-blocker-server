#!/bin/bash

# Define error handling
handle_error() {
    echo "ERROR: $1"
    exit 1
}

# Change to the application directory
cd /home/pi/chromecast || handle_error "Failed to change to application directory"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    handle_error "Virtual environment not found. Please run the installer first."
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || handle_error "Failed to activate virtual environment"

# Check for required files
if [ ! -f "main.py" ] || [ ! -f "web_server.py" ]; then
    handle_error "Required files missing. Please reinstall the application."
fi

echo "Starting Chromecast Content Blocker with web interface on port 8080..."
echo "Access the web interface at: http://$(hostname -I | awk '{print $1}'):8080 or http://pi.local:8080"

# Start the application
python3 main.py --web --port=8080

# Capture exit code
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "Application exited with error code $EXIT_CODE"
    exit $EXIT_CODE
fi 
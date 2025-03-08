#!/bin/bash

# Make sure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Define install directory
INSTALL_DIR=/home/pi/chromecast

# Create directory structure if it doesn't exist
mkdir -p $INSTALL_DIR/templates
mkdir -p $INSTALL_DIR/static

# Install dependencies
echo "Installing dependencies..."
pip3 install pychromecast flask

# Copy files to install directory
echo "Copying files to $INSTALL_DIR..."
cp main.py $INSTALL_DIR/
cp web_server.py $INSTALL_DIR/
cp templates/index.html $INSTALL_DIR/templates/
cp -r static/* $INSTALL_DIR/static/ 2>/dev/null || :

# Set execution permissions
chmod +x $INSTALL_DIR/main.py
chmod +x $INSTALL_DIR/web_server.py

# Install systemd service
echo "Installing systemd service..."
cp chromecast-blocker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable chromecast-blocker.service
systemctl start chromecast-blocker.service

echo "Installation complete!"
echo "The Chromecast Content Blocker is now running and will start automatically on boot."
echo "You can access the web interface at: http://pi.local/"
echo ""
echo "Service status:"
systemctl status chromecast-blocker.service 
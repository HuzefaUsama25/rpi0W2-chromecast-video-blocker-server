#!/bin/bash

# Make sure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Define install directory
INSTALL_DIR=/home/pi/chromecast
VENV_DIR=$INSTALL_DIR/venv

# Create directory structure if it doesn't exist
mkdir -p $INSTALL_DIR/templates
mkdir -p $INSTALL_DIR/static

# Make sure required packages for virtual environment are installed
echo "Installing system dependencies..."
apt-get update
apt-get install -y python3-venv python3-pip

# Set up virtual environment
echo "Setting up virtual environment..."
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Install dependencies in the virtual environment
echo "Installing Python dependencies in virtual environment..."
$VENV_DIR/bin/pip install pychromecast flask

# Copy files to install directory
echo "Copying files to $INSTALL_DIR..."
cp main.py $INSTALL_DIR/
cp web_server.py $INSTALL_DIR/
cp templates/index.html $INSTALL_DIR/templates/
cp -r static/* $INSTALL_DIR/static/ 2>/dev/null || :

# Set execution permissions
chmod +x $INSTALL_DIR/main.py
chmod +x $INSTALL_DIR/web_server.py

# Create a wrapper script to run with the virtual environment
echo "Creating launcher script..."
cat > $INSTALL_DIR/launcher.sh << 'EOF'
#!/bin/bash
cd /home/pi/chromecast
source venv/bin/activate
python3 main.py --web --port=8080
EOF

chmod +x $INSTALL_DIR/launcher.sh

# Update the service file to use the launcher
echo "Updating systemd service..."
cat > /etc/systemd/system/chromecast-blocker.service << 'EOF'
[Unit]
Description=Chromecast Content Blocker with Web Interface
After=network.target

[Service]
ExecStart=/home/pi/chromecast/launcher.sh
WorkingDirectory=/home/pi/chromecast
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Reload and start service
systemctl daemon-reload
systemctl enable chromecast-blocker.service
systemctl restart chromecast-blocker.service

echo "Installation complete!"
echo "The Chromecast Content Blocker is now running and will start automatically on boot."
echo "You can access the web interface at: http://pi.local/"
echo ""
echo "Service status:"
systemctl status chromecast-blocker.service 
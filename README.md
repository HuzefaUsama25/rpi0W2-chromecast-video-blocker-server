# Chromecast Content Blocker

A web-enabled application to monitor and block content on Chromecast devices.

## Features

-   Web interface accessible from any device on your local network
-   Customizable keywords to block specific content
-   Option to block all content (empty keywords list)
-   Automatic startup on Raspberry Pi boot
-   Simple start/stop controls

## Requirements

-   Raspberry Pi (any model with WiFi)
-   Python 3.6+
-   Internet connection
-   Chromecast device on the same network

## Installation

### Automatic Installation (recommended)

1. Clone this repository to your Raspberry Pi:

    ```
    git clone https://github.com/yourusername/chromecast-blocker.git
    cd chromecast-blocker
    ```

2. Make the installation script executable and run it as root:

    ```
    chmod +x install.sh
    sudo ./install.sh
    ```

3. Access the web interface at: `http://pi.local/`

The installer will:
- Create a Python virtual environment in `/home/pi/chromecast/venv`
- Install all dependencies in the virtual environment
- Set up a systemd service to run the application at startup
- Launch the web interface

### Manual Installation

1. Create a virtual environment and install required packages:

    ```
    mkdir -p ~/chromecast/templates ~/chromecast/static
    cd ~/chromecast
    python3 -m venv venv
    source venv/bin/activate
    pip install pychromecast flask
    ```

2. Copy the files to your installation directory:

    ```
    cp /path/to/source/main.py web_server.py ~/chromecast/
    cp /path/to/source/templates/index.html ~/chromecast/templates/
    ```

3. Create a launcher script:

    ```
    cat > ~/chromecast/launcher.sh << 'EOF'
    #!/bin/bash
    cd /home/pi/chromecast
    source venv/bin/activate
    python3 main.py --web --port=80
    EOF
    
    chmod +x ~/chromecast/launcher.sh
    ```

4. Create and install the systemd service:

    ```
    sudo nano /etc/systemd/system/chromecast-blocker.service
    # Paste the contents of chromecast-blocker.service
    
    sudo systemctl daemon-reload
    sudo systemctl enable chromecast-blocker.service
    sudo systemctl start chromecast-blocker.service
    ```

## Usage

1. Open a web browser and navigate to `http://pi.local/`
2. Enter keywords to block in the text field (comma-separated)
3. Leave the keywords field empty to block all content
4. Click "Start Blocker" to begin monitoring
5. Click "Stop Blocker" to pause monitoring
6. Click "Update Keywords" to change the block list without restarting

## Troubleshooting

### Can't access the web interface

-   Make sure your device is on the same network as the Raspberry Pi
-   Try accessing by IP address instead of hostname (e.g., `http://192.168.1.100/`)
-   Check if the service is running: `sudo systemctl status chromecast-blocker.service`

### Service won't start

-   Check service logs: `sudo journalctl -u chromecast-blocker.service`
-   Verify the virtual environment is correctly set up: `ls -l /home/pi/chromecast/venv/bin/python`
-   Check if the launcher script is executable: `ls -l /home/pi/chromecast/launcher.sh`
-   Try running the launcher script manually to see any errors: `sudo /home/pi/chromecast/launcher.sh`
-   If port 80 fails (requires root), try modifying the port in launcher.sh to 8080

### Can't install dependencies

-   Modern Raspberry Pi OS versions use externally managed Python environments
-   Always use a virtual environment as shown in the installation instructions
-   If pip still fails, ensure you have python3-venv installed: `sudo apt install python3-venv`

## License

This project is open source and available under the [MIT License](LICENSE).

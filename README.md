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

2. Run the installation script as root:

    ```
    sudo ./install.sh
    ```

3. Access the web interface at: `http://pi.local/`

### Manual Installation

1. Install required packages:

    ```
    pip3 install pychromecast flask
    ```

2. Copy the files to your desired location:

    ```
    mkdir -p ~/chromecast/templates
    mkdir -p ~/chromecast/static
    cp main.py web_server.py ~/chromecast/
    cp templates/index.html ~/chromecast/templates/
    ```

3. Make the scripts executable:

    ```
    chmod +x ~/chromecast/main.py
    chmod +x ~/chromecast/web_server.py
    ```

4. To run manually:

    ```
    cd ~/chromecast
    python3 main.py --web
    ```

5. To set up as a service:
    ```
    sudo cp chromecast-blocker.service /etc/systemd/system/
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
-   Ensure Python dependencies are installed: `pip3 install pychromecast flask`
-   Make sure port 80 is available (not used by another service)

## License

This project is open source and available under the [MIT License](LICENSE).

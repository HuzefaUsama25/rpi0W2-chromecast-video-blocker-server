#!/usr/bin/env python3

import time
import pychromecast
import logging
import re
import threading
import argparse
import signal
import sys
from pychromecast.controllers.youtube import YouTubeController  # Import directly

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Default keywords to detect in app display name, titles, or any text
DEFAULT_MINECRAFT_KEYWORDS = [
    'minecraft', 'minecraf', 'miecraft', 'creeper', 'steve', 'enderman',
    'ender dragon', 'skeleton', 'zombie', 'mojang'
]

# Global flag to control monitoring loop
monitoring_active = True

# Global variables for chromecast and browser to allow clean shutdown
active_chromecast = None
active_browser = None


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM signals for clean shutdown"""
    global monitoring_active, active_chromecast, active_browser
    print("\nReceived shutdown signal, cleaning up...")
    monitoring_active = False

    # Clean up chromecast connection
    if active_chromecast:
        try:
            active_chromecast.disconnect()
            print("Disconnected from Chromecast")
        except Exception as e:
            print(f"Error during disconnect: {e}")

    # Clean up browser
    if active_browser:
        try:
            active_browser.stop_discovery()
            print("Stopped discovery service")
        except Exception as e:
            print(f"Error stopping discovery: {e}")

    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def find_chromecast():
    """Discover and return the first Chromecast found on the network."""
    global active_browser

    print("Discovering Chromecasts on the network...")
    chromecasts, browser = pychromecast.get_chromecasts()
    active_browser = browser  # Save for clean shutdown

    # Wait for at least one Chromecast to be discovered
    attempt = 0
    max_attempts = 10
    while not chromecasts and attempt < max_attempts:
        attempt += 1
        print(f"No Chromecasts found. Retrying ({attempt}/{max_attempts})...")
        time.sleep(5)
        chromecasts, browser = pychromecast.get_chromecasts()
        active_browser = browser  # Update browser reference

    if not chromecasts:
        raise Exception("No Chromecasts discovered after multiple attempts")

    print(f"Found {len(chromecasts)} Chromecast(s)")

    # Return the first Chromecast found
    chromecast = chromecasts[0]
    print(f"Selected Chromecast: {chromecast.name}")

    # Store reference to the chromecast for clean shutdown
    global active_chromecast
    active_chromecast = chromecast

    # Return both the Chromecast and browser to prevent garbage collection
    return chromecast, browser


def reconnect_chromecast(chromecast):
    """
    Attempt to reconnect to a Chromecast if connection seems stale.
    Returns True if reconnected successfully or connection was already good.
    """
    try:
        # Test if connection is still active by accessing status
        chromecast.status
        return True
    except Exception as e:
        print(f"Connection appears stale, attempting to reconnect: {e}")
        try:
            chromecast.disconnect()
            time.sleep(1)
            # Start worker thread and wait for cast device to be ready
            chromecast.wait()
            print(f"Reconnected to {chromecast.name}")
            return True
        except Exception as reconnect_error:
            print(f"Failed to reconnect: {reconnect_error}")
            return False


def is_minecraft_related(text, keywords=None):
    """Check if the given text is related to Minecraft using a set of keywords."""
    if not text:
        return False

    # If no keywords provided, use the default ones or get from web server if available
    if keywords is None:
        # Try to get keywords from web server if available
        try:
            from web_server import get_keywords
            keywords_from_server = get_keywords()
            if keywords_from_server:
                keywords = keywords_from_server
            else:
                keywords = DEFAULT_MINECRAFT_KEYWORDS
        except (ImportError, AttributeError):
            keywords = DEFAULT_MINECRAFT_KEYWORDS

    text = text.lower()
    return any(keyword in text for keyword in keywords)


def monitor_and_control_chromecast(chromecast):
    """Monitor the Chromecast and mute it when Minecraft content is detected or suspected."""
    global monitoring_active

    try:
        # Connect to the Chromecast and wait for it to be ready
        print(f"Connecting to {chromecast.name}...")

        # Start worker thread and wait for cast device to be ready
        chromecast.wait()
        print(f"Connected to {chromecast.name}")

        # Register a YouTube controller for additional detection capability
        try:
            yt = YouTubeController()  # Use the imported YouTubeController
            chromecast.register_handler(yt)
            print("Registered YouTube controller")
        except Exception as e:
            print(f"Warning: Could not register YouTube controller: {e}")
            print("Will continue without YouTube-specific controls")

        print(f"Now monitoring {chromecast.name} for content...")
        print(f"Will mute when filtered content is detected...")

        # Keep track of last refresh time
        last_reconnect_time = time.time()
        reconnect_interval = 10  # Reconnect every 10 seconds to keep connection fresh

        # Track muting status to avoid excessive muting commands
        currently_muted = False
        last_mute_time = 0
        mute_duration = 600  # Keep muted for 10 minutes by default

        # Track detection to avoid excessive logging
        last_detection_log = 0
        detection_log_interval = 10  # Log detection details every 10 seconds

        # Keep track of recent apps seen for better detection
        recent_app_ids = set()
        last_app_id = None
        last_title = None

        # Force periodic muting check intervals
        force_mute_check_interval = 5  # Check every 5 seconds regardless of detection
        last_forced_check = time.time()

        # Set monitoring_active to True when starting
        monitoring_active = True

        # Import keywords function if web server is available
        try:
            from web_server import get_keywords
            get_keywords_func = get_keywords
            print("Using keywords from web interface")
        except (ImportError, AttributeError):
            def get_keywords_func(): return DEFAULT_MINECRAFT_KEYWORDS
            print("Using default keywords (web interface not available)")

        print(f"Monitoring active: {monitoring_active}")

        while monitoring_active:
            try:
                current_time = time.time()

                # Check if we should still be running - additional check
                if not monitoring_active:
                    print("Monitoring has been stopped by external request")
                    # Make sure we unmute before exiting
                    try:
                        if currently_muted:
                            chromecast.set_volume_muted(False)
                            print("Unmuted Chromecast before stopping")
                    except Exception as e:
                        print(f"Error unmuting before exit: {e}")
                    break

                # Get current keywords
                current_keywords = get_keywords_func()

                # If empty, use cautious mode (block all)
                cautious_mode = len(current_keywords) == 0
                if cautious_mode and current_time - last_detection_log > detection_log_interval:
                    print("Running in cautious mode - will block all content")

                # Periodically reconnect to keep connection fresh
                if current_time - last_reconnect_time > reconnect_interval:
                    print(
                        "Performing periodic reconnection to keep connection fresh...")
                    reconnect_chromecast(chromecast)
                    last_reconnect_time = current_time

                # Check if it's time to unmute after the mute duration
                if currently_muted and current_time - last_mute_time > mute_duration:
                    print(
                        f"Mute duration ({mute_duration/60:.1f} minutes) expired, unmuting...")
                    try:
                        chromecast.set_volume_muted(False)
                        currently_muted = False
                        print("Unmuted Chromecast")
                    except Exception as e:
                        print(f"Failed to unmute: {e}")

                # Get current app information
                current_app_id = None
                app_display_name = None
                title = None
                player_state = None
                minecraft_detected = False
                detection_reason = ""

                # Get app ID and display name
                try:
                    if chromecast.status:
                        current_app_id = chromecast.status.app_id
                        if current_app_id:
                            recent_app_ids.add(current_app_id)

                        # Try to get app display name
                        app_display_name = getattr(
                            chromecast.status, 'display_name', None)
                        if app_display_name:
                            # Check if app name contains filtered keywords
                            if not cautious_mode and is_minecraft_related(app_display_name, current_keywords):
                                minecraft_detected = True
                                detection_reason = f"App name: {app_display_name}"
                            elif cautious_mode:
                                minecraft_detected = True
                                detection_reason = "Cautious mode - blocking all content"
                except Exception as app_error:
                    print(f"Error getting app info: {app_error}")

                # Check if app has changed
                if current_app_id != last_app_id:
                    if current_app_id:
                        print(
                            f"App changed to: {current_app_id} ({app_display_name or 'Unknown'})")
                    else:
                        print("No app currently running")
                    last_app_id = current_app_id

                # Try to get media information
                try:
                    if hasattr(chromecast, 'media_controller') and chromecast.media_controller.status:
                        # Try to get title from media metadata
                        if chromecast.media_controller.status.media_metadata:
                            title = chromecast.media_controller.status.media_metadata.get(
                                'title', '')
                            if title and title != last_title:
                                print(f"Media title: {title}")
                                last_title = title

                            # Check title for filtered keywords
                            if not cautious_mode and title and is_minecraft_related(title, current_keywords):
                                minecraft_detected = True
                                detection_reason = f"Title: {title}"
                            elif cautious_mode and title:
                                minecraft_detected = True
                                detection_reason = "Cautious mode - blocking all content"

                        # Check player state
                        player_state = chromecast.media_controller.status.player_state
                        if player_state in ('PLAYING', 'BUFFERING'):
                            # If YouTube is playing or another app right after YouTube was seen,
                            # and we don't have a title to check, be cautious
                            if cautious_mode or (not title and ('YouTube' in recent_app_ids or current_app_id == 'YouTube')):
                                minecraft_detected = True
                                detection_reason = "Cautious approach - blocking unknown content"
                except Exception as media_error:
                    # Errors are common here, only log them periodically
                    if current_time - last_detection_log > detection_log_interval:
                        print(f"Note: Media detection partial or unavailable")

                # Force periodic mute check for any active media
                if current_time - last_forced_check > force_mute_check_interval:
                    last_forced_check = current_time
                    try:
                        # Check volume
                        volume_level = chromecast.status.volume_level if chromecast.status else 0
                        is_muted = chromecast.status.volume_muted if chromecast.status else False

                        if current_time - last_detection_log > detection_log_interval:
                            print(
                                f"Periodic check - Volume: {volume_level}, Currently muted: {is_muted}")

                        # If volume is up and there's an app running, do a cautious mute check
                        if cautious_mode and volume_level > 0 and not is_muted and current_app_id:
                            print(
                                "Active media detected in periodic check - applying cautious muting")
                            minecraft_detected = True
                            detection_reason = "Periodic cautious check for active media"

                        # Update currently_muted status to match device
                        currently_muted = is_muted
                    except Exception as volume_error:
                        print(f"Error during volume check: {volume_error}")

                # Log detection details periodically to avoid console spam
                if current_time - last_detection_log > detection_log_interval:
                    last_detection_log = current_time
                    if minecraft_detected:
                        print(
                            f"⚠️ Content blocked! Reason: {detection_reason}")
                    else:
                        # Only log this periodically
                        print(f"No content to block detected at this time")

                # Take action if filtered content is detected or suspected
                if minecraft_detected and not currently_muted:
                    print(
                        f"⚠️ Muting Chromecast due to detection: {detection_reason}")
                    try:
                        # First try to pause if it's playing
                        if player_state in ('PLAYING', 'BUFFERING'):
                            try:
                                chromecast.media_controller.pause()
                                print("Media paused")
                                time.sleep(0.5)
                            except Exception as pause_error:
                                print(f"Failed to pause: {pause_error}")

                        # Then always mute as well
                        chromecast.set_volume_muted(True)
                        print("✅ Chromecast muted")
                        currently_muted = True
                        last_mute_time = current_time
                    except Exception as mute_error:
                        print(f"Failed to mute: {mute_error}")

                # Keep recent app list manageable
                if len(recent_app_ids) > 5:
                    recent_app_ids = set(list(recent_app_ids)[-5:])

            except Exception as e:
                print(f"Error during monitoring: {e}")
                # If we have critical errors, attempt to reconnect
                reconnect_chromecast(chromecast)
                last_reconnect_time = time.time()

                # Also check if we should exit
                if not monitoring_active:
                    print("Monitoring stopping after error recovery")
                    break

            # Check again before sleeping
            if not monitoring_active:
                print("Monitoring stopping before sleep")
                break

            # Wait before checking again
            time.sleep(2)

        print("Monitoring function exiting")
        return

    except Exception as e:
        print(f"Unexpected error in monitor_and_control_chromecast: {e}")
        monitoring_active = False
        return


def main():
    parser = argparse.ArgumentParser(description='Chromecast Content Blocker')
    parser.add_argument('--web', action='store_true',
                        help='Run with web interface')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for web interface')
    args = parser.parse_args()

    try:
        if args.web:
            # Import the web server and set up the blocker function
            try:
                import web_server
                import threading
                import time
                import socket

                print(f"Finding Chromecast...")
                # First find the Chromecast
                chromecast, browser = find_chromecast()

                # Set up the web server
                web_server.set_blocker_function(monitor_and_control_chromecast)
                web_server.set_chromecast_and_browser(chromecast, browser)

                # Get the host IP for display purposes
                hostname = socket.gethostname()
                try:
                    host_ip = socket.gethostbyname(hostname)
                except:
                    host_ip = "pi.local or IP address"

                # Define a function that will be run in a thread to start the web server
                def run_web_server():
                    print(f"Starting web interface on port {args.port}...")
                    web_server.run_server(port=args.port)

                # Start the web server in a separate thread
                web_thread = threading.Thread(target=run_web_server)
                web_thread.daemon = True
                web_thread.start()

                # Give the web server a moment to start
                print("Waiting for web server to initialize...")
                time.sleep(3)  # Wait 3 seconds for Flask to start

                print(f"Web interface should now be accessible at:")
                print(f"  http://{host_ip}:{args.port}")
                print(f"  http://pi.local:{args.port}")
                print(f"  http://localhost:{args.port}")

                # Continue with normal operation - the web server is running in the background
                # and the blocker will be activated when requested through the web interface
                while True:
                    time.sleep(1)

            except ImportError as e:
                print(
                    f"Web server module not found: {e}, falling back to CLI mode")
                chromecast, browser = find_chromecast()
                monitor_and_control_chromecast(chromecast)

            except Exception as e:
                print(f"Error starting web interface: {e}")
                print("Falling back to CLI mode")
                chromecast, browser = find_chromecast()
                monitor_and_control_chromecast(chromecast)

        else:
            # CLI mode - Monitor and control Chromecast indefinitely
            chromecast, browser = find_chromecast()
            monitor_and_control_chromecast(chromecast)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Cleanup
        try:
            global monitoring_active
            monitoring_active = False

            # Only disconnect if socket client exists and is alive
            print("Cleaning up...")
            if 'chromecast' in locals() and hasattr(chromecast, 'socket_client') and chromecast.socket_client:
                try:
                    chromecast.disconnect()
                    print("Disconnected from Chromecast")
                except Exception as e:
                    print(f"Error during disconnect: {e}")

            # Stop discovery if browser exists
            if 'browser' in locals():
                browser.stop_discovery()
                print("Stopped discovery service")
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")


if __name__ == "__main__":
    main()

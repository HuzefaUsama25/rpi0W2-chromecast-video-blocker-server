#!/usr/bin/env python3

import threading
import time
import json
import os
from flask import Flask, render_template, request, jsonify, send_from_directory
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='static')

# Global variables
blocker_running = False
blocker_thread = None
keywords = []
config_file = 'blocker_config.json'
blocker_stop_event = threading.Event()  # Event to signal thread to stop

# Load configuration if it exists


def load_config():
    global keywords
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                keywords = config.get('keywords', [])
                logger.info(f"Loaded keywords from config: {keywords}")
    except Exception as e:
        logger.error(f"Error loading config: {e}")

# Save configuration


def save_config():
    try:
        with open(config_file, 'w') as f:
            json.dump({
                'keywords': keywords
            }, f)
        logger.info("Config saved")
    except Exception as e:
        logger.error(f"Error saving config: {e}")


# Load config at startup
load_config()

# Placeholder for the blocker function that will be imported from main.py
blocker_function = None
chromecast_instance = None
browser_instance = None


def set_blocker_function(func):
    global blocker_function
    blocker_function = func


def set_chromecast_and_browser(chromecast, browser):
    global chromecast_instance, browser_instance
    chromecast_instance = chromecast
    browser_instance = browser


def blocker_thread_function():
    global blocker_running, chromecast_instance, blocker_stop_event

    logger.info("Blocker thread starting...")

    # Reset the stop event whenever we start a new thread
    blocker_stop_event.clear()

    if blocker_function and chromecast_instance:
        try:
            # Set global running status to true
            blocker_running = True

            # Import the monitoring_active variable from main to control it
            import main
            main.monitoring_active = True

            logger.info("Starting blocker function...")
            blocker_function(chromecast_instance)
            logger.info("Blocker function returned")
        except Exception as e:
            logger.error(f"Error in blocker thread: {e}")
        finally:
            blocker_running = False
            logger.info("Blocker thread ending...")
    else:
        logger.error("Blocker function or Chromecast not set")
        blocker_running = False


@app.route('/')
def index():
    return render_template('index.html',
                           blocker_running=blocker_running,
                           keywords=', '.join(keywords) if keywords else '')


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


@app.route('/templates/<path:path>')
def send_template(path):
    return send_from_directory('templates', path)


@app.route('/api/status')
def get_status():
    global blocker_thread, blocker_running

    # Check if thread is still alive and update status accordingly
    if blocker_thread is not None:
        if not blocker_thread.is_alive():
            blocker_thread = None
            blocker_running = False
            logger.info("Thread is no longer alive, updated status to stopped")

    return jsonify({
        'running': blocker_running,
        'keywords': keywords
    })


@app.route('/api/start', methods=['POST'])
def start_blocker():
    global blocker_thread, blocker_running, blocker_stop_event

    logger.info("Start blocker request received")

    # First check if the thread is actually running
    if blocker_thread is not None:
        if blocker_thread.is_alive():
            if blocker_running:
                return jsonify({'status': 'error', 'message': 'Blocker is already running'})
            else:
                # Thread exists but status says not running - let's fix the inconsistency
                logger.warning(
                    "Thread exists but status says not running - fixing inconsistency")
                blocker_running = True
                return jsonify({'status': 'success', 'message': 'Blocker was already running, fixed status'})
        else:
            # Thread is not alive, we can clean it up
            logger.info(
                "Found dead thread, cleaning up before creating new one")
            blocker_thread = None

    # Update keywords if provided
    if 'keywords' in request.form:
        global keywords
        new_keywords = [k.strip().lower()
                        for k in request.form['keywords'].split(',') if k.strip()]
        keywords = new_keywords
        save_config()
        logger.info(f"Updated keywords: {keywords}")

    try:
        # Create a new thread
        blocker_stop_event.clear()  # Make sure the stop event is cleared

        # Make sure main.monitoring_active is set to True
        try:
            import main
            main.monitoring_active = True
            logger.info("Set main.monitoring_active to True")
        except Exception as e:
            logger.error(f"Failed to update main.monitoring_active: {e}")

        blocker_thread = threading.Thread(target=blocker_thread_function)
        blocker_thread.daemon = True

        # Set global status
        blocker_running = True

        # Start thread
        blocker_thread.start()
        logger.info("Blocker thread started")

        return jsonify({'status': 'success', 'message': 'Blocker started'})
    except Exception as e:
        logger.error(f"Error starting blocker: {e}")
        blocker_running = False
        return jsonify({'status': 'error', 'message': f'Error starting blocker: {e}'})


@app.route('/api/stop', methods=['POST'])
def stop_blocker():
    global blocker_running, chromecast_instance, blocker_thread, blocker_stop_event

    logger.info("Stop blocker request received")

    # If status says not running, update UI but check thread
    if not blocker_running:
        if blocker_thread is not None and blocker_thread.is_alive():
            logger.warning(
                "Status says not running but thread exists - stopping thread anyway")
        else:
            return jsonify({'status': 'error', 'message': 'Blocker is not running'})

    try:
        # Signal the thread to stop via global flag
        blocker_running = False
        blocker_stop_event.set()

        # Set the main.py monitoring_active flag to False to stop the monitoring loop
        try:
            import main
            logger.info("Setting main.monitoring_active to False")
            main.monitoring_active = False
        except Exception as e:
            logger.error(f"Failed to update main.monitoring_active: {e}")

        # Attempt to unmute Chromecast if it was muted
        if chromecast_instance:
            try:
                logger.info("Attempting to unmute Chromecast")
                chromecast_instance.set_volume_muted(False)
                logger.info("Unmuted Chromecast")
            except Exception as e:
                logger.error(f"Failed to unmute: {e}")

        # Give the thread a moment to clean up
        time.sleep(1)

        # If thread still active, wait a bit longer but don't block the response
        if blocker_thread and blocker_thread.is_alive():
            def cleanup_thread():
                try:
                    logger.info("Waiting for blocker thread to finish...")
                    # Wait up to 5 seconds for thread to finish
                    blocker_thread.join(5)
                    if blocker_thread.is_alive():
                        logger.warning("Thread failed to stop within timeout")
                    else:
                        logger.info("Blocker thread successfully stopped")
                except Exception as e:
                    logger.error(
                        f"Error while waiting for thread to finish: {e}")

            # Start a cleanup thread to wait for the main blocker thread
            cleanup = threading.Thread(target=cleanup_thread)
            cleanup.daemon = True
            cleanup.start()
        else:
            logger.info("Blocker thread was not running or already stopped")

        # Reset blocker_thread if it's no longer alive
        if blocker_thread and not blocker_thread.is_alive():
            blocker_thread = None

        logger.info("Blocker stopping")
        return jsonify({'status': 'success', 'message': 'Blocker stopped'})
    except Exception as e:
        logger.error(f"Error stopping blocker: {e}")
        return jsonify({'status': 'error', 'message': f'Error stopping blocker: {e}'})


@app.route('/api/update_keywords', methods=['POST'])
def update_keywords():
    global keywords

    if 'keywords' in request.form:
        new_keywords = [k.strip().lower()
                        for k in request.form['keywords'].split(',') if k.strip()]
        keywords = new_keywords
        save_config()
        return jsonify({'status': 'success', 'message': 'Keywords updated', 'keywords': keywords})

    return jsonify({'status': 'error', 'message': 'No keywords provided'})


def get_keywords():
    return keywords


def run_server(host='0.0.0.0', port=80):
    try:
        app.run(host=host, port=port, threaded=True)
    except Exception as e:
        logger.error(f"Error running server: {e}")
        # If port 80 requires root privileges and fails, try a higher port
        if port == 80:
            logger.info("Attempting to run on port 8080 instead...")
            try:
                app.run(host=host, port=8080, threaded=True)
            except Exception as e2:
                logger.error(f"Error running server on fallback port: {e2}")

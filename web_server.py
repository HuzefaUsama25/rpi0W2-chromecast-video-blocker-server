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
    global blocker_running, chromecast_instance

    if blocker_function and chromecast_instance:
        try:
            blocker_running = True
            blocker_function(chromecast_instance)
        except Exception as e:
            logger.error(f"Error in blocker thread: {e}")
        finally:
            blocker_running = False
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
    return jsonify({
        'running': blocker_running,
        'keywords': keywords
    })


@app.route('/api/start', methods=['POST'])
def start_blocker():
    global blocker_thread, blocker_running

    if blocker_running:
        return jsonify({'status': 'error', 'message': 'Blocker is already running'})

    # Update keywords if provided
    if 'keywords' in request.form:
        global keywords
        new_keywords = [k.strip().lower()
                        for k in request.form['keywords'].split(',') if k.strip()]
        keywords = new_keywords
        save_config()

    try:
        if blocker_thread is None or not blocker_thread.is_alive():
            blocker_thread = threading.Thread(target=blocker_thread_function)
            blocker_thread.daemon = True
            blocker_thread.start()
            logger.info("Blocker thread started")
            return jsonify({'status': 'success', 'message': 'Blocker started'})
        else:
            return jsonify({'status': 'error', 'message': 'Blocker thread already exists'})
    except Exception as e:
        logger.error(f"Error starting blocker: {e}")
        return jsonify({'status': 'error', 'message': f'Error starting blocker: {e}'})


@app.route('/api/stop', methods=['POST'])
def stop_blocker():
    global blocker_running, chromecast_instance

    if not blocker_running:
        return jsonify({'status': 'error', 'message': 'Blocker is not running'})

    try:
        # Signal the thread to stop
        blocker_running = False

        # Attempt to unmute Chromecast if it was muted
        if chromecast_instance:
            try:
                chromecast_instance.set_volume_muted(False)
                logger.info("Unmuted Chromecast")
            except Exception as e:
                logger.error(f"Failed to unmute: {e}")

        logger.info("Blocker stopping")
        return jsonify({'status': 'success', 'message': 'Blocker stopping'})
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

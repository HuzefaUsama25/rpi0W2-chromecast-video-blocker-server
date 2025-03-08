#!/usr/bin/env python3

import pychromecast
import json

# Discover Chromecasts
print("Discovering Chromecasts...")
chromecasts, browser = pychromecast.get_chromecasts()
print(f"Found {len(chromecasts)} Chromecast(s)")

if chromecasts:
    # Take the first Chromecast
    cc = chromecasts[0]

    # Print available properties and methods
    print("\nAvailable properties and methods:")
    for attr in dir(cc):
        if not attr.startswith('_'):  # Skip private attributes
            print(f"- {attr}")

    # Try to get the name
    print("\nChromecast information:")
    print(f"- Object type: {type(cc)}")
    print(f"- String representation: {str(cc)}")

    # Check for name attributes
    print("\nTrying different name attributes:")
    if hasattr(cc, 'name'):
        print(f"- cc.name: {cc.name}")
    else:
        print("- cc.name: Not found")

    if hasattr(cc, 'device_name'):
        print(f"- cc.device_name: {cc.device_name}")
    else:
        print("- cc.device_name: Not found")

    if hasattr(cc, 'model_name'):
        print(f"- cc.model_name: {cc.model_name}")
    else:
        print("- cc.model_name: Not found")

    if hasattr(cc, 'friendly_name'):
        print(f"- cc.friendly_name: {cc.friendly_name}")
    else:
        print("- cc.friendly_name: Not found")

    # Check for a model or info object
    if hasattr(cc, 'model'):
        print(f"- cc.model: {cc.model}")
    else:
        print("- cc.model: Not found")

    if hasattr(cc, 'device'):
        print(f"- cc.device exists")
        device = cc.device
        print(f"  - Type: {type(device)}")

        # Print device attributes
        for attr in dir(device):
            if not attr.startswith('_') and not callable(getattr(device, attr)):
                try:
                    value = getattr(device, attr)
                    print(f"  - {attr}: {value}")
                except:
                    print(f"  - {attr}: <error accessing>")
    else:
        print("- cc.device: Not found")

    # Try to access the cast info
    if hasattr(cc, 'cast_info'):
        print("\nCast info:")
        info = cc.cast_info
        print(f"- Type: {type(info)}")

        # Print cast_info attributes
        if hasattr(info, '__dict__'):
            for key, value in info.__dict__.items():
                if not key.startswith('_'):
                    print(f"  - {key}: {value}")
        else:
            for attr in dir(info):
                if not attr.startswith('_') and not callable(getattr(info, attr)):
                    try:
                        value = getattr(info, attr)
                        print(f"  - {attr}: {value}")
                    except:
                        print(f"  - {attr}: <error accessing>")
    else:
        print("\n- cc.cast_info: Not found")

    # Clean up
    browser.stop_discovery()
else:
    print("No Chromecasts found.")

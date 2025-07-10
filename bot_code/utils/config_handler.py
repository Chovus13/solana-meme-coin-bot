import json
import os
from pathlib import Path

CONFIG_PATH = Path('data/config.json')

def save_config_to_file(config_data):
    """Save config to persistent JSON file"""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {str(e)}")
        return False

def load_config_from_file():
    """Load config from persistent storage"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return None

def initialize_config(default_config):
    """Initialize config file with defaults if not exists"""
    if not CONFIG_PATH.exists():
        save_config_to_file(default_config)
        return default_config
    return load_config_from_file() or default_config

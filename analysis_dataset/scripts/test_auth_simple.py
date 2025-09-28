#!/usr/bin/env python3
"""
Simple LSEG Authentication Test - No Unicode
"""

import requests
import json
from pathlib import Path

def load_config():
    """Load LSEG configuration."""
    config_file = Path("../lseg-data.config.json")
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config['sessions']['platform']['rdp']

def test_auth():
    """Test authentication with takeExclusiveSignOnControl."""
    print("LSEG AUTHENTICATION TEST")
    print("=" * 40)

    config = load_config()
    auth_url = "https://api.refinitiv.com/auth/oauth2/v1/token"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    auth_data = {
        'grant_type': 'password',
        'username': config['username'],
        'password': config['password'],
        'scope': 'trapi',
        'client_id': config['app-key'],
        'takeExclusiveSignOnControl': 'true'  # Force kill existing session
    }

    print(f"Username: {config['username']}")
    print(f"Client ID: {config['app-key'][:20]}...")
    print("Sending authentication request with session control...")

    try:
        response = requests.post(auth_url, data=auth_data, headers=headers, timeout=30)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in')

            print("SUCCESS! Authentication worked!")
            print(f"Access Token: {access_token[:50]}...")
            print(f"Expires In: {expires_in} seconds")

            return access_token
        else:
            print("Authentication failed")
            try:
                error_data = response.json()
                print(f"Error: {error_data}")
            except:
                print(f"Raw response: {response.text}")

            return None

    except Exception as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    access_token = test_auth()

    if access_token:
        print("\nSUCCESS! LSEG API is working!")
        print("You can now proceed with data extraction.")
    else:
        print("\nFAILED! Check credentials or try again.")
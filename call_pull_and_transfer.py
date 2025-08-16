#!/usr/bin/env python3
import requests

def call_route():
    try:
        # Call the pull_and_transfer route
        response = requests.get('http://127.0.0.1:5000/pull_and_transfer')
        print(f"Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    call_route()

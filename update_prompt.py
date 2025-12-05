#!/usr/bin/env python3
"""Script to update ElevenLabs agent system prompt"""
import requests
import json

try:
    print("Calling /api/elevenlabs-agent/update-prompt...")
    response = requests.post(
        'http://localhost:5000/api/elevenlabs-agent/update-prompt',
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    try:
        response_data = response.json()
        print(f"\nResponse JSON:")
        print(json.dumps(response_data, indent=2))
    except:
        print(f"\nResponse Text: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Error: Could not connect to server at http://localhost:5000")
    print("   Make sure the Flask server is running!")
except Exception as e:
    print(f"❌ Error: {str(e)}")

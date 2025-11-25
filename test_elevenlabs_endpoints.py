"""
Script to test different ElevenLabs API endpoints to find the correct one for phone calls
Run this script to discover the correct endpoint
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', '')

if not API_KEY:
    print("ERROR: ELEVENLABS_API_KEY not found in .env file")
    exit(1)

if not AGENT_ID:
    print("ERROR: ELEVENLABS_AGENT_ID not found in .env file")
    exit(1)

headers = {
    'xi-api-key': API_KEY,
    'Content-Type': 'application/json'
}

# Test endpoints to try
endpoints_to_test = [
    # ConvAI/Conversational AI endpoints
    f'https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}/calls',
    f'https://api.elevenlabs.io/v1/conversational-ai/agents/{AGENT_ID}/calls',
    'https://api.elevenlabs.io/v1/convai/calls',
    'https://api.elevenlabs.io/v1/conversational-ai/calls',
    
    # Phone/Telephony endpoints
    f'https://api.elevenlabs.io/v1/convai/phone/calls',
    f'https://api.elevenlabs.io/v1/telephony/calls',
    f'https://api.elevenlabs.io/v1/phone/calls',
    f'https://api.elevenlabs.io/v1/convai/calls/phone',
    f'https://api.elevenlabs.io/v1/agents/{AGENT_ID}/phone/calls',
    
    # Alternative structures
    f'https://api.elevenlabs.io/v1/phone-numbers/calls',
    f'https://api.elevenlabs.io/v1/convai/phone-numbers/calls',
]

# Test payload
test_payload = {
    'agent_id': AGENT_ID,
    'phone_number': '+1234567890',  # Test number
}

print(f"Testing ElevenLabs API endpoints with Agent ID: {AGENT_ID}")
print("=" * 80)

for endpoint in endpoints_to_test:
    try:
        print(f"\nTesting: {endpoint}")
        response = requests.post(endpoint, headers=headers, json=test_payload, timeout=5)
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"  [SUCCESS] This endpoint works!")
            print(f"  Response: {response.text[:200]}")
            break
        elif response.status_code == 404:
            print(f"  [NOT FOUND] Status 404")
        elif response.status_code == 401:
            print(f"  [UNAUTHORIZED] Status 401 - Check API key")
        elif response.status_code == 400:
            print(f"  [BAD REQUEST] Status 400 - Endpoint exists but payload might be wrong")
            print(f"  Response: {response.text[:200]}")
        else:
            print(f"  [STATUS {response.status_code}]: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR]: {str(e)[:100]}")

print("\n" + "=" * 80)
print("\nIf no endpoint worked, check:")
print("1. ElevenLabs API documentation: https://elevenlabs.io/docs")
print("2. Your ElevenLabs dashboard for API endpoints")
print("3. Contact ElevenLabs support for the correct endpoint")

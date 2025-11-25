"""
Test script to find the correct ElevenLabs endpoint for initiating phone calls
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', '')

if not API_KEY or not AGENT_ID:
    print("ERROR: Missing API_KEY or AGENT_ID")
    exit(1)

headers = {
    'xi-api-key': API_KEY,
    'Content-Type': 'application/json'
}

# First, get phone numbers
print("Fetching phone numbers...")
try:
    phone_response = requests.get('https://api.elevenlabs.io/v1/convai/phone-numbers', headers=headers)
    if phone_response.status_code == 200:
        phone_data = phone_response.json()
        print(f"Found {len(phone_data)} phone number(s)")
        if phone_data:
            phone_id = phone_data[0].get('phone_number_id')
            phone_number = phone_data[0].get('phone_number')
            print(f"Phone Number ID: {phone_id}")
            print(f"Phone Number: {phone_number}")
            print(f"Assigned Agent: {phone_data[0].get('assigned_agent', {}).get('agent_name')}")
    else:
        print(f"Error fetching phone numbers: {phone_response.status_code}")
        phone_id = None
except Exception as e:
    print(f"Error: {e}")
    phone_id = None

# Test endpoints with phone_number_id
endpoints_to_test = [
    # Using phone_number_id
    f'https://api.elevenlabs.io/v1/convai/phone-numbers/{phone_id}/calls' if phone_id else None,
    f'https://api.elevenlabs.io/v1/convai/phone-numbers/calls',
    f'https://api.elevenlabs.io/v1/convai/calls',
    
    # Using agent_id
    f'https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}/calls',
]

# Test payloads
payloads_to_test = [
    {
        'to': '+1234567890',
        'from': phone_number if phone_id else None,
    },
    {
        'phone_number': '+1234567890',
        'phone_number_id': phone_id,
    },
    {
        'to_phone_number': '+1234567890',
        'from_phone_number_id': phone_id,
    },
    {
        'agent_id': AGENT_ID,
        'phone_number': '+1234567890',
        'phone_number_id': phone_id,
    },
]

print("\n" + "=" * 80)
print("Testing endpoints...")
print("=" * 80)

for endpoint in endpoints_to_test:
    if not endpoint:
        continue
    
    for i, payload in enumerate(payloads_to_test):
        # Remove None values
        clean_payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            print(f"\nTesting: {endpoint}")
            print(f"  Payload {i+1}: {clean_payload}")
            response = requests.post(endpoint, headers=headers, json=clean_payload, timeout=5)
            print(f"  Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print(f"  [SUCCESS] Endpoint works!")
                print(f"  Response: {response.text[:300]}")
                print(f"\n✅ FOUND CORRECT ENDPOINT: {endpoint}")
                print(f"✅ CORRECT PAYLOAD: {clean_payload}")
                exit(0)
            elif response.status_code == 400:
                print(f"  [BAD REQUEST] Endpoint exists but payload wrong")
                print(f"  Response: {response.text[:300]}")
            elif response.status_code == 401:
                print(f"  [UNAUTHORIZED] Check API key")
            elif response.status_code == 404:
                print(f"  [NOT FOUND]")
            elif response.status_code == 405:
                print(f"  [METHOD NOT ALLOWED] Endpoint exists but wrong method")
            else:
                print(f"  [STATUS {response.status_code}]: {response.text[:200]}")
        except Exception as e:
            print(f"  [ERROR]: {str(e)[:100]}")

print("\n" + "=" * 80)
print("No working endpoint found. Check ElevenLabs documentation or contact support.")


"""
Diagnostic script to test ElevenLabs outbound call API
This will help identify the exact endpoint and payload format needed
"""
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', '')
TEST_PHONE = os.getenv('TEST_PHONE_NUMBER', '+923455233102')  # Replace with test number

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

print("=" * 80)
print("ElevenLabs Outbound Call API Diagnostic")
print("=" * 80)
print(f"Agent ID: {AGENT_ID}")
print(f"Test Phone: {TEST_PHONE}")
print()

# Step 1: Get phone numbers
print("Step 1: Fetching phone numbers...")
try:
    phone_response = requests.get(
        'https://api.elevenlabs.io/v1/convai/phone-numbers',
        headers=headers,
        timeout=10
    )
    
    print(f"Status: {phone_response.status_code}")
    
    if phone_response.status_code == 200:
        phone_data = phone_response.json()
        print(f"Found {len(phone_data)} phone number(s)")
        
        phone_number_id = None
        elevenlabs_phone_number = None
        
        for pn in phone_data:
            print(f"\nPhone Number: {pn.get('phone_number')}")
            print(f"Phone Number ID: {pn.get('phone_number_id')}")
            assigned_agent = pn.get('assigned_agent', {})
            print(f"Assigned Agent ID: {assigned_agent.get('agent_id')}")
            print(f"Assigned Agent Name: {assigned_agent.get('agent_name')}")
            
            if assigned_agent.get('agent_id') == AGENT_ID:
                phone_number_id = pn.get('phone_number_id')
                elevenlabs_phone_number = pn.get('phone_number')
                print("  ✓ This phone number is assigned to your agent!")
        
        if not phone_number_id:
            if phone_data:
                phone_number_id = phone_data[0].get('phone_number_id')
                elevenlabs_phone_number = phone_data[0].get('phone_number')
                print(f"\n⚠ No phone number assigned to agent {AGENT_ID}")
                print(f"Using first available phone number: {elevenlabs_phone_number}")
            else:
                print("\n❌ No phone numbers found!")
                exit(1)
    else:
        print(f"❌ Error: {phone_response.status_code}")
        print(f"Response: {phone_response.text[:500]}")
        exit(1)
        
except Exception as e:
    print(f"❌ Error fetching phone numbers: {e}")
    exit(1)

print()
print("=" * 80)
print("Step 2: Testing outbound call endpoints...")
print("=" * 80)

# Test endpoints - Updated with the correct native Twilio outbound endpoint
endpoints_to_test = [
    {
        'url': 'https://api.elevenlabs.io/v1/convai/twilio/outbound-call',
        'payloads': [
            {
                'agent_id': AGENT_ID,
                'agent_phone_number_id': phone_number_id,
                'to_number': TEST_PHONE,
                'conversation_initiation_client_data': {
                    'test': True,
                    'questions': ['Test question 1', 'Test question 2']
                }
            }
        ]
    },
    # Keep old endpoints for comparison (will likely fail)
    {
        'url': f'https://api.elevenlabs.io/v1/convai/phone-numbers/{phone_number_id}/calls',
        'payloads': [
            {'phone_number': TEST_PHONE, 'agent_id': AGENT_ID},
        ]
    },
    {
        'url': f'https://api.elevenlabs.io/v1/convai/calls',
        'payloads': [
            {'to': TEST_PHONE, 'agent_id': AGENT_ID, 'phone_number_id': phone_number_id},
        ]
    },
]

all_results = []

for endpoint_config in endpoints_to_test:
    endpoint = endpoint_config['url']
    payloads = endpoint_config['payloads']
    
    print(f"\nTesting endpoint: {endpoint}")
    print("-" * 80)
    
    for i, payload in enumerate(payloads, 1):
        print(f"\n  Payload {i}: {json.dumps(payload, indent=4)}")
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            print(f"  Status: {response.status_code}")
            print(f"  Headers: {dict(response.headers)}")
            
            if response.text:
                try:
                    response_json = response.json()
                    print(f"  Response: {json.dumps(response_json, indent=2)}")
                except:
                    print(f"  Response (text): {response.text[:500]}")
            else:
                print("  Response: (empty)")
            
            result = {
                'endpoint': endpoint,
                'payload': payload,
                'status': response.status_code,
                'response': response.text[:1000] if response.text else None,
                'success': response.status_code in [200, 201, 202]
            }
            all_results.append(result)
            
            if response.status_code in [200, 201, 202]:
                print(f"  ✅ SUCCESS! This endpoint and payload format works!")
                print("\n" + "=" * 80)
                print("RECOMMENDED CONFIGURATION:")
                print("=" * 80)
                print(f"Endpoint: {endpoint}")
                print(f"Payload: {json.dumps(payload, indent=2)}")
                exit(0)
            elif response.status_code == 404:
                print(f"  ⚠ Endpoint not found")
            elif response.status_code == 405:
                allowed = response.headers.get('Allow', 'Unknown')
                print(f"  ⚠ Method not allowed. Allowed methods: {allowed}")
            elif response.status_code == 401:
                print(f"  ❌ Unauthorized - check API key permissions")
            elif response.status_code == 403:
                print(f"  ❌ Forbidden - check API key permissions")
            else:
                print(f"  ❌ Failed with status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Network error: {str(e)}")
            all_results.append({
                'endpoint': endpoint,
                'payload': payload,
                'error': str(e),
                'success': False
            })

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Tested {len(all_results)} endpoint/payload combinations")
print(f"Successful: {sum(1 for r in all_results if r.get('success'))}")
print(f"Failed: {sum(1 for r in all_results if not r.get('success'))}")

if not any(r.get('success') for r in all_results):
    print("\n❌ No working endpoint found.")
    print("\nPossible reasons:")
    print("1. ElevenLabs may not support outbound calls via REST API")
    print("2. The endpoint format or payload structure is different")
    print("3. Additional permissions or configuration is required")
    print("4. Outbound calls might require a different approach (e.g., Twilio integration)")
    print("\nRecommendation: Contact ElevenLabs support with these test results.")


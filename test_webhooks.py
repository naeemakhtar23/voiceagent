"""
Test script for webhook endpoints
Tests all API endpoints to ensure they're working correctly
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_health():
    """Test health check endpoint"""
    print_section("Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_dashboard():
    """Test dashboard endpoint"""
    print_section("Testing Dashboard Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"Content Length: {len(response.text)} characters")
        if response.status_code == 200:
            print("[OK] Dashboard is accessible")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_initiate_call():
    """Test call initiation endpoint"""
    print_section("Testing Initiate Call Endpoint")
    try:
        # Test data
        test_data = {
            "phone_number": "+923001234567",  # Example Pakistan number
            "questions": [
                {"text": "Do you have health insurance?"},
                {"text": "Are you taking any medications?"}
            ]
        }
        
        print(f"Sending request with data:")
        print(json.dumps(test_data, indent=2))
        
        response = requests.post(
            f"{BASE_URL}/api/initiate-call",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("[OK] Call initiation endpoint working!")
                print(f"   Call ID: {data.get('call_id')}")
                print(f"   Call SID: {data.get('call_sid')}")
                return True, data.get('call_id')
        
        return False, None
    except Exception as e:
        print(f"Error: {str(e)}")
        return False, None

def test_voice_flow_webhook(call_id=None):
    """Test voice flow webhook (TwiML generation)"""
    print_section("Testing Voice Flow Webhook")
    try:
        if not call_id:
            print("[WARNING] No call_id provided. Creating a test call first...")
            # Create a test call in database would require DB connection
            print("   Skipping - requires database connection")
            return False
        
        url = f"{BASE_URL}/api/voice-flow?call_id={call_id}&q_num=0"
        print(f"Testing URL: {url}")
        
        # Simulate Twilio POST request
        response = requests.post(
            url,
            data={},  # Twilio sends form data
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            print("[OK] Voice flow webhook responding!")
            print(f"TwiML Response (first 500 chars):")
            print(response.text[:500])
            return True
        else:
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_process_answer_webhook(call_id=None):
    """Test process answer webhook"""
    print_section("Testing Process Answer Webhook")
    try:
        if not call_id:
            print("[WARNING] No call_id provided. Skipping...")
            return False
        
        url = f"{BASE_URL}/api/process-answer?call_id={call_id}&q_num=0"
        print(f"Testing URL: {url}")
        
        # Simulate Twilio POST with speech result
        form_data = {
            "SpeechResult": "yes",
            "Confidence": "0.95",
            "Digits": None
        }
        
        response = requests.post(
            url,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            print("[OK] Process answer webhook responding!")
            print(f"TwiML Response (first 500 chars):")
            print(response.text[:500])
            return True
        else:
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_call_status_webhook():
    """Test call status webhook"""
    print_section("Testing Call Status Webhook")
    try:
        # Simulate Twilio status callback
        form_data = {
            "CallSid": "CA1234567890abcdef1234567890abcdef",
            "CallStatus": "ringing",
            "CallDuration": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/call-status",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("[OK] Call status webhook working!")
            return True
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_get_calls():
    """Test get all calls endpoint"""
    print_section("Testing Get All Calls Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/calls")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            calls = response.json()
            print(f"[OK] Retrieved {len(calls)} calls")
            if calls:
                print(f"Sample call: {json.dumps(calls[0], indent=2, default=str)}")
            return True
        else:
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  WEBHOOK ENDPOINT TESTING")
    print("="*60)
    print(f"\nTesting endpoints at: {BASE_URL}\n")
    
    results = {}
    
    # Test basic endpoints
    results['health'] = test_health()
    results['dashboard'] = test_dashboard()
    results['get_calls'] = test_get_calls()
    results['call_status'] = test_call_status_webhook()
    
    # Test call initiation (this will create a real call attempt)
    print("\n[WARNING] Note: Testing call initiation will attempt to make a real call")
    try:
        user_input = input("Do you want to test call initiation? (y/n): ").lower().strip()
    except:
        user_input = 'n'
        print("Skipping call initiation (non-interactive mode)")
    
    if user_input == 'y':
        call_success, call_id = test_initiate_call()
        results['initiate_call'] = call_success
        
        if call_success and call_id:
            # Test webhooks that require call_id
            results['voice_flow'] = test_voice_flow_webhook(call_id)
            results['process_answer'] = test_process_answer_webhook(call_id)
    else:
        print("Skipping call initiation test")
        results['initiate_call'] = None
        results['voice_flow'] = None
        results['process_answer'] = None
    
    # Summary
    print_section("Test Summary")
    for test_name, result in results.items():
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIPPED]"
        print(f"{test_name:20} {status}")
    
    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total and total > 0:
        print("\n[SUCCESS] All tests passed! Webhooks are ready!")
    elif passed > 0:
        print("\n[WARNING] Some tests failed. Check the errors above.")
    else:
        print("\n[ERROR] Tests failed. Check if server is running.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


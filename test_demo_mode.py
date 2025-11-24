"""
Test script for Demo Mode
Tests the demo mode functionality without requiring ngrok or real calls
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000"

def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_health():
    """Test health endpoint"""
    print_section("Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to server. Is Flask running?")
        print("  Start server: cd backend && python app.py")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_demo_call():
    """Test demo mode call simulation"""
    print_section("Testing Demo Mode Call")
    
    test_data = {
        "phone_number": "+923001234567",
        "questions": [
            {"text": "Do you have health insurance?"},
            {"text": "Are you currently taking any medications?"},
            {"text": "Have you visited a doctor in the last 6 months?"}
        ]
    }
    
    print("Sending demo call request:")
    print(json.dumps(test_data, indent=2))
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/initiate-call",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print()
        
        if response.status_code == 200 and data.get('success'):
            if data.get('demo_mode'):
                print("[SUCCESS] Demo mode is working!")
                print(f"  Call ID: {data.get('call_id')}")
                print(f"  Call SID: {data.get('call_sid')}")
                print()
                
                # Check if results are included
                if data.get('results'):
                    results = data['results']
                    print("[SUCCESS] Results generated!")
                    print(f"  Total Questions: {results.get('summary', {}).get('total_questions', 0)}")
                    print(f"  Yes Answers: {results.get('summary', {}).get('yes_count', 0)}")
                    print(f"  No Answers: {results.get('summary', {}).get('no_count', 0)}")
                    print()
                    print("Sample JSON Response:")
                    print(json.dumps(results, indent=2)[:500] + "...")
                    return True, data.get('call_id')
                else:
                    print("[INFO] Results not in response, fetching separately...")
                    return True, data.get('call_id')
            else:
                print("[WARNING] Response received but demo_mode flag not set")
                print("  Check if DEMO_MODE=true in .env file")
                return False, None
        else:
            print(f"[ERROR] Call failed: {data.get('error', 'Unknown error')}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to server. Is Flask running?")
        print("  Start server: cd backend && python app.py")
        return False, None
    except Exception as e:
        print(f"[ERROR] Request failed: {str(e)}")
        return False, None

def test_get_results(call_id):
    """Test getting call results"""
    print_section("Testing Get Call Results")
    
    if not call_id:
        print("[SKIP] No call_id available")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/call-results/{call_id}",
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            results = response.json()
            print("[SUCCESS] Results retrieved!")
            print()
            print("Full JSON Response:")
            print(json.dumps(results, indent=2))
            return True
        else:
            print(f"Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_call_history():
    """Test call history"""
    print_section("Testing Call History")
    
    try:
        response = requests.get(f"{BASE_URL}/api/calls", timeout=5)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            calls = response.json()
            print(f"[SUCCESS] Retrieved {len(calls)} calls")
            if calls:
                print("\nRecent calls:")
                for call in calls[:3]:  # Show first 3
                    print(f"  ID: {call.get('id')}, Phone: {call.get('phone_number')}, Status: {call.get('status')}")
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
    print("  DEMO MODE TESTING")
    print("="*60)
    print(f"\nTesting endpoints at: {BASE_URL}\n")
    print("Make sure:")
    print("  1. Flask server is running (python backend/app.py)")
    print("  2. DEMO_MODE=true in .env file")
    print("  3. Database is accessible (optional for demo mode)\n")
    
    results = {}
    
    # Test health
    results['health'] = test_health()
    
    if not results['health']:
        print("\n[ERROR] Server is not running or not accessible!")
        print("  Please start Flask server first:")
        print("    cd backend")
        print("    python app.py")
        return
    
    # Test demo call
    call_success, call_id = test_demo_call()
    results['demo_call'] = call_success
    
    # Test get results
    if call_id:
        results['get_results'] = test_get_results(call_id)
    
    # Test call history
    results['call_history'] = test_call_history()
    
    # Summary
    print_section("Test Summary")
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:20} {status}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] Demo mode is working perfectly!")
        print("\nNext steps:")
        print("  1. Open browser: http://localhost:5000")
        print("  2. Enter phone number and questions")
        print("  3. Click 'Make Call'")
        print("  4. See results immediately!")
    elif call_success:
        print("\n[SUCCESS] Demo mode is working!")
        print("  Some tests failed but core functionality works.")
    else:
        print("\n[WARNING] Demo mode test failed.")
        print("  Check:")
        print("    - Is DEMO_MODE=true in .env?")
        print("    - Is Flask server running?")
        print("    - Check server logs for errors")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


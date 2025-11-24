"""
Simple webhook endpoint tests (without database dependency)
Tests TwiML generation endpoints that Twilio will call
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoint"""
    print("\n[TEST] Health Check")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def test_dashboard():
    """Test dashboard"""
    print("\n[TEST] Dashboard")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        return response.status_code == 200
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def test_voice_flow_twiml():
    """Test voice flow TwiML generation (simulates Twilio webhook)"""
    print("\n[TEST] Voice Flow Webhook (TwiML Generation)")
    print("  This endpoint generates TwiML that Twilio will use")
    
    # Test with a dummy call_id (will fail DB but test TwiML generation)
    test_call_id = 999
    
    try:
        url = f"{BASE_URL}/api/voice-flow?call_id={test_call_id}&q_num=0"
        print(f"  URL: {url}")
        
        # Simulate Twilio POST request
        response = requests.post(
            url,
            data={},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            print("  [OK] Endpoint responding with TwiML")
            # Check if it's valid XML/TwiML
            if "<?xml" in response.text or "<Response>" in response.text:
                print("  [OK] Valid TwiML format detected")
                print(f"  TwiML Preview (first 300 chars):")
                print("  " + response.text[:300].replace("\n", "\n  "))
            return True
        else:
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def test_process_answer_twiml():
    """Test process answer TwiML generation"""
    print("\n[TEST] Process Answer Webhook (TwiML Generation)")
    
    test_call_id = 999
    
    try:
        url = f"{BASE_URL}/api/process-answer?call_id={test_call_id}&q_num=0"
        print(f"  URL: {url}")
        
        # Simulate Twilio POST with speech result
        form_data = {
            "SpeechResult": "yes",
            "Confidence": "0.95"
        }
        
        response = requests.post(
            url,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            print("  [OK] Endpoint responding with TwiML")
            if "<?xml" in response.text or "<Response>" in response.text:
                print("  [OK] Valid TwiML format detected")
                print(f"  TwiML Preview (first 300 chars):")
                print("  " + response.text[:300].replace("\n", "\n  "))
            return True
        else:
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def test_call_status():
    """Test call status webhook"""
    print("\n[TEST] Call Status Webhook")
    
    try:
        form_data = {
            "CallSid": "CA1234567890abcdef1234567890abcdef",
            "CallStatus": "ringing"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/call-status",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print("  [OK] Status webhook accepting requests")
            print(f"  Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def main():
    """Run webhook tests"""
    print("="*60)
    print("  WEBHOOK ENDPOINT TESTING")
    print("="*60)
    print(f"\nTesting endpoints at: {BASE_URL}\n")
    
    results = {}
    
    results['health'] = test_health()
    results['dashboard'] = test_dashboard()
    results['voice_flow'] = test_voice_flow_twiml()
    results['process_answer'] = test_process_answer_twiml()
    results['call_status'] = test_call_status()
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:20} {status}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All webhook endpoints are working!")
        print("\nNext steps:")
        print("1. Start ngrok: ngrok http 5000")
        print("2. Update WEBHOOK_BASE_URL in .env with ngrok HTTPS URL")
        print("3. Configure webhook URL in Twilio console")
        print("4. Test with a real call!")
    else:
        print("\n[WARNING] Some tests failed.")
        print("Note: Database-dependent endpoints may fail if DB is not set up.")

if __name__ == '__main__':
    main()


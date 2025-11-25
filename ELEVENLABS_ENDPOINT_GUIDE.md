# ElevenLabs API Endpoint Discovery Guide

## Current Status

Based on testing, the endpoint `/v1/convai/phone-numbers/calls` exists (returns 405 Method Not Allowed instead of 404), which means:
- The endpoint path is correct or close
- The HTTP method (POST) might be wrong, OR
- The request format/payload is incorrect

## How to Find the Correct Endpoint

### Method 1: Check ElevenLabs Dashboard

1. **Log into your ElevenLabs account**: https://elevenlabs.io
2. **Go to your Voice Agent settings**
3. **Look for "Phone Numbers" or "Telephony" section**
4. **Check for API documentation or "Make a Call" functionality**
5. **Look for webhook URLs or API endpoints listed there**

### Method 2: Check API Documentation

1. **Visit**: https://elevenlabs.io/docs
2. **Navigate to**: "Agents Platform" → "Phone Numbers" or "Telephony"
3. **Look for REST API endpoints** (not just WebSocket)
4. **Find the endpoint for creating/initiating phone calls**

### Method 3: Use Browser Developer Tools

1. **Log into ElevenLabs dashboard**
2. **Open browser Developer Tools** (F12)
3. **Go to Network tab**
4. **Try to make a call from the dashboard** (if available)
5. **Look at the network requests** to see what endpoint is called
6. **Check the request method, URL, headers, and payload**

### Method 4: Check API Response Headers

When you get a 405 error, the response might include an `Allow` header showing which methods are allowed:

```python
response = requests.post('https://api.elevenlabs.io/v1/convai/phone-numbers/calls', ...)
print(response.headers.get('Allow'))  # Might show: GET, POST, PUT, etc.
```

### Method 5: Contact ElevenLabs Support

If you can't find the endpoint:
1. **Email**: support@elevenlabs.io
2. **Ask for**: 
   - The REST API endpoint to initiate phone calls with a Voice Agent
   - The required request format (method, headers, body)
   - Example request/response

## Possible Endpoint Variations to Try

Based on the 405 response, try these variations:

### Option 1: Different HTTP Method
```python
# Try PUT instead of POST
requests.put('https://api.elevenlabs.io/v1/convai/phone-numbers/calls', ...)

# Try PATCH
requests.patch('https://api.elevenlabs.io/v1/convai/phone-numbers/calls', ...)
```

### Option 2: Different Endpoint Structure
```python
# With agent_id in path
f'https://api.elevenlabs.io/v1/convai/phone-numbers/{agent_id}/calls'

# With phone number in path
f'https://api.elevenlabs.io/v1/convai/phone-numbers/calls/{phone_number}'
```

### Option 3: Different Payload Structure
The payload might need to be structured differently. Check if ElevenLabs expects:
- Form data instead of JSON
- Different field names
- Additional required fields

## Important Note

**ElevenLabs primarily uses WebSockets for voice agent conversations**, not REST API calls. The REST endpoint might be:
- Only for initiating calls (then WebSocket takes over)
- A different service/feature
- Not available in your plan

## Next Steps

1. **Check your ElevenLabs dashboard** for phone number/call functionality
2. **Review the API documentation** at https://elevenlabs.io/docs
3. **Try the variations above** with your actual API key
4. **Contact ElevenLabs support** if needed

## Once You Find the Endpoint

Add it to your `.env` file:
```env
ELEVENLABS_CALL_ENDPOINT=https://api.elevenlabs.io/v1/[correct-endpoint]
```

Then restart your Flask server.


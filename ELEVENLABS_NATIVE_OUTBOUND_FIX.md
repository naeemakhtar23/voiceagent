# ElevenLabs Native Outbound Call Implementation

## ✅ Solution Implemented

The code has been updated to use ElevenLabs' **native Twilio outbound call endpoint** instead of the complex WebSocket bridge approach.

## What Changed

### Before (Old Approach)
- Used Twilio directly to make calls
- Attempted to bridge Twilio Media Streams to ElevenLabs WebSocket
- Complex implementation that wasn't fully working
- Questions weren't reaching the ElevenLabs agent

### After (New Approach)
- Uses ElevenLabs' native endpoint: `/v1/convai/twilio/outbound-call`
- ElevenLabs handles the entire call flow
- Questions are passed via `conversation_initiation_client_data`
- Simpler, more reliable implementation

## Key Changes in Code

**File: `backend/elevenlabs_handler.py`**

1. **Removed**: Twilio direct call creation + WebSocket bridge
2. **Added**: ElevenLabs native outbound call API endpoint
3. **Endpoint**: `POST https://api.elevenlabs.io/v1/convai/twilio/outbound-call`
4. **Payload Structure**:
   ```json
   {
     "agent_id": "your_agent_id",
     "agent_phone_number_id": "phone_number_id_from_elevenlabs",
     "to_number": "+1234567890",
     "conversation_initiation_client_data": {
       "call_id": "12345",
       "questions": [...],
       "questions_text": "...",
       "conversation_context": "..."
     }
   }
   ```

## Prerequisites

Before using this, ensure:

1. ✅ **Twilio Number Imported in ElevenLabs**:
   - Go to ElevenLabs Dashboard → Phone Numbers
   - Click "Add Provider" → Select "Twilio"
   - Enter your Twilio Account SID and Auth Token
   - Import your Twilio phone number
   - Note the `agent_phone_number_id` (this is what the code fetches)

2. ✅ **Phone Number Linked to Agent**:
   - Go to your Agent settings in ElevenLabs
   - Navigate to "Phone Numbers" section
   - Link your imported Twilio number to the agent

3. ✅ **API Key Permissions**:
   - Your API key must have `convai_write` permission
   - Check in ElevenLabs Dashboard → Settings → API Keys

4. ✅ **Agent Configuration**:
   - Your agent should be configured to handle the questions
   - The `conversation_initiation_client_data` will be available to the agent

## How It Works Now

1. **User initiates call** via the frontend
2. **Backend fetches** the ElevenLabs phone number ID assigned to the agent
3. **Backend calls** `/v1/convai/twilio/outbound-call` with:
   - Agent ID
   - Phone number ID (imported Twilio number in ElevenLabs)
   - Destination phone number
   - Questions in `conversation_initiation_client_data`
4. **ElevenLabs handles** the entire call:
   - Makes the call via Twilio
   - Uses your ElevenLabs agent voice
   - Asks the questions
   - Collects responses
5. **Webhook receives** call events (if configured)

## Benefits

✅ **Uses ElevenLabs Agent Voice** - Not Twilio's default voice  
✅ **Questions Passed Correctly** - Via `conversation_initiation_client_data`  
✅ **Simpler Implementation** - No WebSocket bridge needed  
✅ **Better Error Handling** - Specific error messages for different status codes  
✅ **Native Integration** - Uses ElevenLabs' official Twilio integration  

## Testing

1. **Make a test call** using the "ElevenLabs Call" button
2. **Check server logs** for:
   - "Calling ElevenLabs outbound endpoint"
   - "Response status: 200" (or error code)
   - "ElevenLabs outbound call initiated successfully!"
3. **Answer the call** - You should hear the ElevenLabs agent voice
4. **Verify questions** are asked correctly

## Troubleshooting

### Error 401 (Unauthorized)
- Check your API key is correct
- Verify API key has `convai_write` permission

### Error 403 (Forbidden)
- API key doesn't have required permissions
- Contact ElevenLabs support to enable permissions

### Error 404 (Not Found)
- Endpoint URL might be incorrect (should be `/v1/convai/twilio/outbound-call`)
- Check ElevenLabs API documentation for latest endpoint

### Error 422 (Validation Error)
- `agent_id` is incorrect
- `agent_phone_number_id` is incorrect or not linked to agent
- Check that phone number is imported and linked in ElevenLabs dashboard

### Call Doesn't Use ElevenLabs Voice
- Verify phone number is imported in ElevenLabs
- Check phone number is linked to your agent
- Ensure agent voice settings are configured

## Next Steps

1. **Test the implementation** with a real call
2. **Monitor server logs** for any errors
3. **Check ElevenLabs dashboard** for call logs
4. **Verify questions** are being asked correctly
5. **Test answer collection** if webhooks are configured

## Notes

- The old webhook endpoint `/api/elevenlabs-voice-flow` is still in the code but may not be needed anymore
- Call status updates will come via ElevenLabs webhooks (if configured)
- The `conversation_initiation_client_data` allows the agent to access questions dynamically


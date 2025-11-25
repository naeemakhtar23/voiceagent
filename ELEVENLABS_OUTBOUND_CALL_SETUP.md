# ElevenLabs Outbound Call Setup Guide

## Understanding the Issue

The ElevenLabs "talk-to" URL (`https://elevenlabs.io/app/talk-to?agent_id=agent_0701kak95ks9ehstmdpx6mwaaxwd`) is for **web-based testing** where you can talk to your agent through your browser. This is **NOT** for making outbound phone calls.

## How Outbound Calls Work with ElevenLabs

To make outbound phone calls with ElevenLabs, you need:

1. **A phone number assigned to your agent** in the ElevenLabs dashboard
2. **API access** with proper permissions (`convai_write`)
3. **Use the ElevenLabs API** to initiate calls programmatically

## Current Implementation

The system has been updated to use ElevenLabs' direct API for making outbound calls. Here's what happens:

1. **Frontend**: You enter a client phone number in the "Phone Number" field
2. **Backend**: The system:
   - Fetches your ElevenLabs phone numbers
   - Finds the phone number assigned to your agent
   - Makes an API call to ElevenLabs to initiate an outbound call
   - The call goes from your ElevenLabs phone number to the client's number

## Steps to Make Outbound Calls

### 1. Verify Your Setup

Make sure you have:
- ✅ ElevenLabs API key with `convai_write` permission
- ✅ Agent ID configured (agent_0701kak95ks9ehstmdpx6mwaaxwd)
- ✅ A phone number assigned to your agent in ElevenLabs dashboard

### 2. Check Phone Number Assignment

1. Go to https://elevenlabs.io
2. Navigate to your Voice Agent settings
3. Go to "Phone Numbers" section
4. Verify that a phone number is assigned to your agent

### 3. Use the Application

1. Open the application: `http://localhost:5000`
2. You should see the **Phone Number** input field (it's visible on the form)
3. Enter the client's phone number with country code (e.g., `+923001234567`)
4. Add your survey questions
5. Click **"ElevenLabs Call"** button
6. The system will attempt to make the call via ElevenLabs API

## Troubleshooting

### "No phone number found for this agent"

**Solution**: 
- Go to ElevenLabs dashboard → Phone Numbers
- Assign a phone number to your agent
- Make sure the phone number is active

### "Failed to initiate call via ElevenLabs API"

**Possible causes**:
1. **API endpoint not found**: ElevenLabs API endpoints may vary. The code tries multiple endpoints automatically.
2. **Missing permissions**: Your API key needs `convai_write` permission
3. **Phone number not assigned**: Make sure a phone number is assigned to your agent

**Solutions**:
1. Check ElevenLabs dashboard for the correct API endpoint
2. Verify API key permissions in ElevenLabs settings
3. Contact ElevenLabs support if needed

### Phone Number Field Not Visible

The phone number input field should be visible on the form. If you don't see it:
1. Check that you're on the "Initiate Call" section (first tab in sidebar)
2. The field is located at the top of the form, above the questions section
3. Try refreshing the page

### Call Received Instead of Made

If you're receiving calls instead of making them:
- The "talk-to" URL is for **incoming** calls (web-based)
- To make **outbound** calls, use the "ElevenLabs Call" button in the application
- Make sure you're using the application, not the talk-to URL

## API Endpoints Being Tried

The code automatically tries these endpoints in order:
1. `POST /v1/convai/phone-numbers/{phone_number_id}/calls`
2. `POST /v1/convai/calls`
3. `POST /v1/convai/phone-numbers/calls`

If all fail, check the server logs for the specific error message.

## Next Steps

1. **Test the implementation**: Try making a call using the "ElevenLabs Call" button
2. **Check server logs**: Look for any error messages when initiating a call
3. **Verify ElevenLabs dashboard**: Make sure your agent has a phone number assigned
4. **Contact support**: If issues persist, contact ElevenLabs support with:
   - Your agent ID
   - The API endpoint you're trying to use
   - Error messages from the logs

## Important Notes

- The "talk-to" URL is **only for web-based testing**, not for programmatic outbound calls
- Outbound calls require a phone number assigned to your agent
- The API endpoint for outbound calls may vary - the code tries multiple endpoints
- Make sure your API key has the necessary permissions


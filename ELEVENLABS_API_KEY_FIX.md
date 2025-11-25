# ElevenLabs API Key Permission Fix

## Problem

You're getting this error:
```
HTTP 401 error: Unable to create record: Authenticate
"missing_permissions","message":"The API key you used is missing the permission convai_write"
```

## Solution

Your ElevenLabs API key is missing the `convai_write` permission required for Conversational AI (ConvAI) features.

### Step 1: Generate a New API Key with Correct Permissions

1. **Log into ElevenLabs Dashboard**: https://elevenlabs.io
2. **Go to Settings**: Click on your profile → Settings
3. **Navigate to API Keys**: Find the "API Keys" section
4. **Create New API Key**:
   - Click "Create API Key" or "Generate New Key"
   - **Important**: Make sure to enable/select:
     - ✅ **Conversational AI (ConvAI)** permissions
     - ✅ **convai_write** permission (if shown separately)
   - Give it a name like "Voice Agent API Key"
   - Copy the new API key immediately (you won't be able to see it again)

### Step 2: Update Your .env File

Replace your old API key with the new one:

```env
ELEVENLABS_API_KEY=your_new_api_key_here
```

### Step 3: Restart Your Server

After updating the `.env` file, restart your Flask server:

```bash
# Stop the current server (Ctrl+C)
# Then restart:
cd backend
python app.py
```

### Step 4: Test Again

Try making a call using the "ElevenLabs Call" button again.

## Alternative: Check Existing API Key Permissions

If you want to keep your current API key:

1. Go to ElevenLabs Dashboard → Settings → API Keys
2. Find your current API key
3. Check if there's an option to "Edit" or "Update Permissions"
4. Enable "Conversational AI" or "convai_write" permission
5. Save changes

**Note**: Some API keys may not support permission updates. In that case, you'll need to create a new one.

## Verification

After updating, you can verify the API key works by running:

```bash
python -c "import requests; from dotenv import load_dotenv; import os; load_dotenv(); api_key = os.getenv('ELEVENLABS_API_KEY'); agent_id = os.getenv('ELEVENLABS_AGENT_ID'); r = requests.get('https://api.elevenlabs.io/v1/convai/conversation/get-signed-url', headers={'xi-api-key': api_key}, params={'agent_id': agent_id}); print('Status:', r.status_code); print('Response:', r.text[:300])"
```

You should see `Status: 200` instead of `Status: 401`.

## Why This Happens

ElevenLabs API keys have different permission levels:
- **Basic API keys**: Can only use Text-to-Speech
- **Full API keys**: Can use all features including Conversational AI
- **Custom permissions**: Some keys have specific permissions enabled/disabled

For Voice Agent calls, you need the `convai_write` permission which allows:
- Creating conversations
- Initiating calls
- Managing agent interactions

## Still Having Issues?

If you continue to have problems:
1. Make sure you're using the latest API key from your dashboard
2. Check that your ElevenLabs account has access to Conversational AI features
3. Verify your account subscription includes Voice Agent capabilities
4. Contact ElevenLabs support if the issue persists


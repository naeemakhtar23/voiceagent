# Real Twilio Call Setup Guide

## Demo Mode Disabled ✅

Demo mode has been disabled. The system is now configured for **real Twilio calls**.

## Required Configuration

### 1. Twilio Phone Number
Make sure your `.env` file has your Twilio phone number:
```env
TWILIO_PHONE_NUMBER=+1234567890
```
(Replace with your actual Twilio number)

### 2. Webhook URL (CRITICAL for Real Calls)

For real calls to work, Twilio needs to reach your webhooks. You have two options:

#### Option A: Use ngrok (Recommended for Testing)
1. **Start ngrok:**
   ```bash
   ngrok http 5000
   ```

2. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

3. **Update `.env` file:**
   ```env
   WEBHOOK_BASE_URL=https://abc123.ngrok.io
   ```

4. **Restart Flask server**

5. **Configure Twilio:**
   - Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
   - Click your phone number
   - Set webhook: `https://abc123.ngrok.io/api/voice-flow`
   - Method: POST
   - Save

#### Option B: Deploy to Cloud (Production)
- Deploy to Heroku, Railway, or Render
- Use the public URL directly
- No ngrok needed

### 3. Verify Phone Number (Trial Accounts)

If using Twilio trial account:
1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/verified
2. Add your test phone number
3. Verify via SMS/call

## Testing Real Calls

### Step 1: Check Configuration
```bash
# Verify demo mode is off
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DEMO_MODE:', os.getenv('DEMO_MODE'))"
```

### Step 2: Start ngrok (if using)
```bash
ngrok http 5000
```

### Step 3: Update Webhook URL
- Update `.env` with ngrok URL
- Restart Flask server
- Update Twilio webhook

### Step 4: Make a Test Call
1. Open: http://localhost:5000
2. Enter **verified** phone number
3. Add questions
4. Click "Initiate Call"
5. Answer on your phone!

## Important Notes

⚠️ **Without ngrok/webhook:**
- Calls will be initiated
- But Twilio won't be able to ask questions
- Call will fail or hang

✅ **With proper webhook:**
- Calls work perfectly
- Questions are asked
- Answers are collected
- Results stored

## Troubleshooting

**Call connects but no questions asked?**
- Check webhook URL in Twilio console
- Verify ngrok is running
- Check Flask logs for errors

**"Call failed" error?**
- Verify phone number is verified (trial accounts)
- Check Twilio account has credits
- Verify phone number format: +countrycode+number

**Webhook not receiving requests?**
- Ensure ngrok URL matches `.env`
- Check firewall/antivirus
- Verify Twilio webhook URL is correct

## Current Status

- ✅ Demo mode: **DISABLED**
- ✅ Real calls: **ENABLED**
- ⚠️ Webhook: **Needs configuration** (ngrok or cloud deployment)

## Next Steps

1. Set `TWILIO_PHONE_NUMBER` in `.env`
2. Start ngrok: `ngrok http 5000`
3. Update `WEBHOOK_BASE_URL` in `.env`
4. Configure Twilio webhook
5. Restart Flask server
6. Test with real call!


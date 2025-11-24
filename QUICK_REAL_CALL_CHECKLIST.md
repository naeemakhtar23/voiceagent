# Quick Checklist for Real Twilio Calls

## ✅ Current Status

- ✅ Demo mode: **DISABLED**
- ✅ Real calls: **ENABLED**
- ⚠️ Twilio Phone Number: Check `.env` file
- ⚠️ Webhook URL: Needs ngrok or cloud deployment

## Required Steps (5 minutes)

### 1. Verify Twilio Phone Number ✅
Your phone number should be in `.env`:
```env
TWILIO_PHONE_NUMBER=+19043318746
```
(Format: +countrycode+number, no spaces or dashes)

### 2. Start ngrok (REQUIRED)
```bash
ngrok http 5000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 3. Update .env File
```env
WEBHOOK_BASE_URL=https://abc123.ngrok.io
```
(Replace with your actual ngrok URL)

### 4. Restart Flask Server
```bash
# Stop current server (Ctrl+C)
cd backend
python app.py
```

### 5. Configure Twilio Webhook
1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Click your phone number: **+19043318746**
3. In "Voice & Fax" section:
   - **A CALL COMES IN**: `https://your-ngrok-url.ngrok.io/api/voice-flow`
   - **HTTP Method**: POST
4. Click **Save**

### 6. Verify Your Test Phone Number
1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/verified
2. Add your mobile number (the one you'll call)
3. Verify via SMS

### 7. Test!
1. Open: http://localhost:5000
2. Enter your **verified** phone number
3. Add questions
4. Click "Initiate Call"
5. Answer on your phone!

## Troubleshooting

**"Call failed" or no call connects?**
- ✅ Check phone number is verified in Twilio
- ✅ Verify Twilio account has credits
- ✅ Check phone number format: +countrycode+number

**Call connects but no questions asked?**
- ✅ Check ngrok is running
- ✅ Verify webhook URL in Twilio matches ngrok URL
- ✅ Check Flask server logs for errors
- ✅ Test webhook: `curl https://your-ngrok-url.ngrok.io/api/health`

**"Webhook error" in Twilio logs?**
- ✅ Ensure Flask server is running
- ✅ Verify ngrok URL is correct
- ✅ Check firewall/antivirus isn't blocking

## Test Webhook Manually

```bash
# Test if webhook is accessible
curl https://your-ngrok-url.ngrok.io/api/health
```

Should return: `{"status": "healthy", ...}`

## Current Configuration

- **Twilio Account SID**: Configured ✅
- **Twilio Auth Token**: Configured ✅
- **Twilio Phone Number**: +19043318746 (check .env)
- **Webhook URL**: Needs ngrok setup ⚠️

## Ready to Test!

Once ngrok is running and webhook is configured, you're ready for real calls! 🚀


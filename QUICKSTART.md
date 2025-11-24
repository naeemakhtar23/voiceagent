# 🚀 Quick Start Guide

Get your Voice Call System running in 10 minutes!

## Prerequisites Check

- ✅ Python 3.8+ installed
- ✅ SQL Server running (DESKTOP-U22UKGN\SQLEXPRESS)
- ✅ Twilio account (free trial works)
- ✅ ngrok installed

## Step-by-Step Setup

### 1. Install Dependencies (2 minutes)

```bash
cd backend
pip install -r requirements.txt
```

### 2. Setup Database (2 minutes)

1. Open SQL Server Management Studio
2. Connect to: `DESKTOP-U22UKGN\SQLEXPRESS`
3. Open file: `database/schema.sql`
4. Execute the script
5. Verify tables created: `calls`, `questions`, `call_results`

### 3. Configure Environment (2 minutes)

Create `.env` file in project root:

```env
# Twilio (get from https://console.twilio.com/)
TWILIO_ACCOUNT_SID=ACe301f2e318b9bc5b2fed0ee1a2b3af64
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Database (already configured)
DB_CONNECTION_STRING=Server=DESKTOP-U22UKGN\SQLEXPRESS;Database=ePRF;Integrated Security=True;

# Webhook (update after step 4)
WEBHOOK_BASE_URL=http://localhost:5000

# Flask
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=5000
```

### 4. Start ngrok (1 minute)

Open new terminal:
```bash
ngrok http 5000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

Update `.env`:
```env
WEBHOOK_BASE_URL=https://abc123.ngrok.io
```

**Keep ngrok running!**

### 5. Configure Twilio Webhook (2 minutes)

1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Click your Twilio phone number
3. In "Voice & Fax":
   - **A CALL COMES IN**: `https://your-ngrok-url.ngrok.io/api/voice-flow`
   - **HTTP Method**: POST
4. Save

### 6. Verify Phone Number (1 minute)

1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/verified
2. Add your mobile number
3. Verify via SMS

### 7. Start Server (30 seconds)

```bash
cd backend
python app.py
```

You should see:
```
Starting Voice Call System on port 5000
 * Running on http://0.0.0.0:5000
```

### 8. Test It! (1 minute)

1. Open browser: `http://localhost:5000`
2. Enter your verified phone number: `+1234567890`
3. Add questions:
   - "Do you have health insurance?"
   - "Are you taking medications?"
4. Click "📞 Make Call"
5. Answer on your phone!

## Verify Setup

Run the setup verification:
```bash
python setup.py
```

## Troubleshooting

**Call not connecting?**
- Verify phone number in Twilio
- Check number format: `+countrycode+number`

**Webhook not working?**
- Ensure ngrok is running
- Check URL in Twilio matches ngrok URL

**Database error?**
- Verify SQL Server is running
- Check connection string in `.env`

## Next Steps

- Read full documentation: `README.md`
- Prepare demo questions
- Test with multiple calls
- Review call history and JSON results

## Demo Checklist

- [ ] All setup steps completed
- [ ] Test call successful
- [ ] JSON results displaying correctly
- [ ] Call history working
- [ ] Sample questions prepared
- [ ] Backup plan ready (screenshots/video)

**You're ready for your demo! 🎉**


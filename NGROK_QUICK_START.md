# ngrok Quick Start Guide

## Manual Installation (2 minutes)

### Step 1: Download ngrok
1. Go to: **https://ngrok.com/download**
2. Click "Download for Windows"
3. Save the ZIP file (usually goes to Downloads folder)

### Step 2: Extract ngrok
1. Right-click the ZIP file → Extract All
2. Extract to: `C:\Users\YourUsername\ngrok\` (or any folder you prefer)
3. You should have: `C:\Users\YourUsername\ngrok\ngrok.exe`

### Step 3: Start ngrok
Open PowerShell and run:
```powershell
cd C:\Users\YourUsername\ngrok
.\ngrok.exe http 5000
```

Or if you extracted to a different location:
```powershell
# Replace with your actual path
C:\path\to\ngrok\ngrok.exe http 5000
```

### Step 4: Copy the HTTPS URL
After starting ngrok, you'll see:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:5000
```

Copy the `https://abc123.ngrok.io` part.

### Step 5: Update .env file
Edit `.env` file and update:
```env
WEBHOOK_BASE_URL=https://abc123.ngrok.io
```
(Replace with your actual ngrok URL)

### Step 6: Configure Twilio
1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Click your phone number
3. In "Voice & Fax" → "A CALL COMES IN":
   - Enter: `https://abc123.ngrok.io/api/voice-flow`
   - Method: POST
4. Save

## Quick Commands

**Start ngrok:**
```powershell
# Navigate to ngrok folder first
cd C:\Users\YourUsername\ngrok
.\ngrok.exe http 5000
```

**Or create a shortcut:**
1. Right-click `ngrok.exe` → Create shortcut
2. Right-click shortcut → Properties
3. In "Target", add: `http 5000` at the end
4. Example: `C:\Users\YourUsername\ngrok\ngrok.exe http 5000`

## Important Notes

- ✅ **Keep ngrok running** while making calls
- ✅ The URL changes each time you restart ngrok (free tier)
- ✅ For demo, this is fine - just update .env and Twilio each time
- ⚠️ If ngrok stops, Twilio won't be able to reach your webhooks

## Testing

Once ngrok is running:
1. Flask server should be running on port 5000
2. ngrok should show: `Forwarding https://xxx.ngrok.io -> http://localhost:5000`
3. Test webhook: Open browser to `https://xxx.ngrok.io/api/health`
4. Should see: `{"status": "healthy", ...}`

## Troubleshooting

**"Port 5000 already in use"**
- Make sure Flask is running: `python backend/app.py`
- Or use different port: `ngrok http 5001` (and update Flask port)

**"Connection refused"**
- Make sure Flask server is running
- Check firewall settings

**"ngrok not found"**
- Make sure you're in the correct directory
- Use full path: `C:\Users\YourUsername\ngrok\ngrok.exe http 5000`

## Alternative: Use start_ngrok.ps1 Script

After installing ngrok manually, you can use:
```powershell
.\start_ngrok.ps1
```

This script will automatically find ngrok and start it.


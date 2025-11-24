# ngrok Setup Guide

## Quick Installation

### Option 1: Automatic Installation (Recommended)

Run the installation script:
```powershell
.\install_ngrok.ps1
```

This will:
- Download ngrok automatically
- Extract it to `%USERPROFILE%\ngrok\`
- Show you how to use it

### Option 2: Manual Installation

1. **Download ngrok:**
   - Go to: https://ngrok.com/download
   - Download Windows version
   - Extract to a folder (e.g., `C:\ngrok\` or `%USERPROFILE%\ngrok\`)

2. **Add to PATH (Optional but Recommended):**
   ```powershell
   # Add to user PATH
   [Environment]::SetEnvironmentVariable('Path', $env:Path + ';C:\ngrok', 'User')
   ```
   Then restart PowerShell.

3. **Or use full path:**
   ```powershell
   C:\ngrok\ngrok.exe http 5000
   ```

## Starting ngrok

### Method 1: Use the helper script
```powershell
.\start_ngrok.ps1
```

### Method 2: Direct command
```powershell
# If in PATH:
ngrok http 5000

# Or with full path:
$env:USERPROFILE\ngrok\ngrok.exe http 5000
```

## After Starting ngrok

1. **Copy the HTTPS URL:**
   ```
   Forwarding  https://abc123.ngrok.io -> http://localhost:5000
   ```

2. **Update .env file:**
   ```env
   WEBHOOK_BASE_URL=https://abc123.ngrok.io
   ```

3. **Configure Twilio:**
   - Go to Twilio Console → Phone Numbers
   - Set webhook: `https://abc123.ngrok.io/api/voice-flow`
   - Method: POST

## Important Notes

- **Keep ngrok running** while testing/making calls
- The URL changes each time you restart ngrok (free tier)
- For fixed URL, you need ngrok paid plan ($8/month)
- For demo purposes, free tier is sufficient

## Troubleshooting

**"ngrok not recognized"**
- ngrok is not in PATH
- Use full path: `$env:USERPROFILE\ngrok\ngrok.exe http 5000`
- Or run the installation script

**"Execution policy error"**
- Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Or run PowerShell as Administrator

**"Port 5000 already in use"**
- Make sure Flask server is running on port 5000
- Or use different port: `ngrok http 5001`

## Alternative: Local Testing Without ngrok

For local testing only (not for real Twilio calls), you can:
1. Use `localhost:5000` for local webhook testing
2. Use Twilio's webhook testing tools
3. Use a local tunnel alternative (localtunnel, serveo, etc.)

But for **real calls with Twilio**, ngrok is required.


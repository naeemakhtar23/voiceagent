# How to Start ngrok (Fix "File in Use" Error)

## The Problem

The WindowsApps version of ngrok has restrictions that prevent it from running in some PowerShell contexts.

## ✅ Solution 1: Use Command Prompt (Easiest)

1. **Open Command Prompt** (not PowerShell)
   - Press `Win + R`
   - Type: `cmd`
   - Press Enter

2. **Run ngrok:**
   ```cmd
   ngrok http 5000
   ```

3. **You'll see:**
   ```
   Forwarding  https://abc123.ngrok.io -> http://localhost:5000
   ```

4. **Copy the HTTPS URL** and update your `.env` file

## ✅ Solution 2: Download Standalone ngrok

1. **Download:**
   - Go to: https://ngrok.com/download
   - Download Windows ZIP

2. **Extract:**
   - Extract to: `C:\ngrok\`
   - You'll have: `C:\ngrok\ngrok.exe`

3. **Run:**
   ```powershell
   C:\ngrok\ngrok.exe http 5000
   ```

4. **Or add to PATH:**
   ```powershell
   [Environment]::SetEnvironmentVariable('Path', $env:Path + ';C:\ngrok', 'User')
   ```
   Then restart PowerShell and use: `ngrok http 5000`

## ✅ Solution 3: Kill Stuck Processes First

If ngrok seems stuck:

```powershell
# Kill any ngrok processes
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force

# Wait 5 seconds
Start-Sleep -Seconds 5

# Try again (in Command Prompt, not PowerShell)
```

## Quick Check

After starting ngrok, verify it's working:

```powershell
# Check if ngrok is running
.\check_ngrok.ps1

# Or open in browser
# http://localhost:4040
```

## Recommended for Your Demo

**Use Solution 1 (Command Prompt):**
- Simplest and most reliable
- Works with WindowsApps version
- No downloads needed
- Just open cmd.exe and run: `ngrok http 5000`

## After ngrok Starts

1. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

2. **Update `.env` file:**
   ```env
   WEBHOOK_BASE_URL=https://abc123.ngrok.io
   ```

3. **Configure Twilio:**
   - Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
   - Click your phone number
   - Set webhook: `https://abc123.ngrok.io/api/voice-flow`
   - Method: POST

4. **You're ready to make calls!**


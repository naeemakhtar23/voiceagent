# Simple script to start ngrok
# This handles the WindowsApps version of ngrok

Write-Host "Starting ngrok on port 5000..." -ForegroundColor Cyan
Write-Host ""

# Check if ngrok is already running
$ngrokRunning = Get-Process ngrok -ErrorAction SilentlyContinue

if ($ngrokRunning) {
    Write-Host "[WARNING] ngrok is already running!" -ForegroundColor Yellow
    Write-Host "  Process ID: $($ngrokRunning.Id)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To check the URL, open: http://localhost:4040" -ForegroundColor Cyan
    Write-Host "Or run: .\check_ngrok.ps1" -ForegroundColor Cyan
    exit 0
}

# Try to start ngrok
try {
    Write-Host "Attempting to start ngrok..." -ForegroundColor Yellow
    
    # Method 1: Direct start
    $process = Start-Process -FilePath "ngrok" -ArgumentList "http","5000" -PassThru -NoNewWindow -ErrorAction Stop
    
    Write-Host "[OK] ngrok started! (PID: $($process.Id))" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting for ngrok to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    # Try to get the URL
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        if ($response.tunnels -and $response.tunnels.Count -gt 0) {
            $publicUrl = $response.tunnels[0].public_url
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Green
            Write-Host "  ngrok is running!" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "Public URL: $publicUrl" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Update your .env file:" -ForegroundColor Cyan
            Write-Host "  WEBHOOK_BASE_URL=$publicUrl" -ForegroundColor White
            Write-Host ""
            Write-Host "Configure Twilio:" -ForegroundColor Cyan
            Write-Host "  Webhook: $publicUrl/api/voice-flow" -ForegroundColor White
            Write-Host ""
            Write-Host "ngrok web interface: http://localhost:4040" -ForegroundColor Gray
            Write-Host ""
            Write-Host "Press Ctrl+C to stop ngrok" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[INFO] ngrok started but URL not available yet" -ForegroundColor Yellow
        Write-Host "  Check: http://localhost:4040" -ForegroundColor Cyan
        Write-Host "  Or run: .\check_ngrok.ps1" -ForegroundColor Cyan
    }
    
} catch {
    Write-Host "[ERROR] Failed to start ngrok: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try these alternatives:" -ForegroundColor Yellow
    Write-Host "1. Open a new PowerShell window and run: ngrok http 5000" -ForegroundColor White
    Write-Host "2. Check if ngrok needs authentication: ngrok authtoken YOUR_TOKEN" -ForegroundColor White
    Write-Host "3. Download ngrok manually from: https://ngrok.com/download" -ForegroundColor White
    exit 1
}


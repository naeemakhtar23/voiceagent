# Script to fix ngrok "file in use" error

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ngrok Troubleshooting" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if ngrok is already running
$ngrokProcesses = Get-Process ngrok -ErrorAction SilentlyContinue

if ($ngrokProcesses) {
    Write-Host "[INFO] ngrok is already running!" -ForegroundColor Green
    Write-Host ""
    foreach ($proc in $ngrokProcesses) {
        Write-Host "  Process ID: $($proc.Id)" -ForegroundColor Gray
        Write-Host "  Started: $($proc.StartTime)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # Try to get the URL
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        if ($response.tunnels -and $response.tunnels.Count -gt 0) {
            $publicUrl = $response.tunnels[0].public_url
            Write-Host "========================================" -ForegroundColor Green
            Write-Host "  ngrok is Active!" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "Public URL: $publicUrl" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Update your .env file:" -ForegroundColor Cyan
            Write-Host "  WEBHOOK_BASE_URL=$publicUrl" -ForegroundColor White
            Write-Host ""
            Write-Host "Configure Twilio webhook:" -ForegroundColor Cyan
            Write-Host "  $publicUrl/api/voice-flow" -ForegroundColor White
            Write-Host ""
            Write-Host "Web interface: http://localhost:4040" -ForegroundColor Gray
            Write-Host ""
            exit 0
        }
    } catch {
        Write-Host "[INFO] ngrok is running but API not accessible yet" -ForegroundColor Yellow
        Write-Host "  Check: http://localhost:4040" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "If you want to restart ngrok:" -ForegroundColor Yellow
    Write-Host "  1. Stop current process: Stop-Process -Name ngrok" -ForegroundColor White
    Write-Host "  2. Wait a few seconds" -ForegroundColor White
    Write-Host "  3. Start again: ngrok http 5000" -ForegroundColor White
    exit 0
}

# Check if port 5000 is in use
$port5000 = netstat -ano | Select-String ":5000.*LISTENING"
if ($port5000) {
    Write-Host "[OK] Port 5000 is in use (Flask server should be running)" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Port 5000 is not in use" -ForegroundColor Yellow
    Write-Host "  Make sure Flask server is running: python backend/app.py" -ForegroundColor White
}

Write-Host ""
Write-Host "The 'file in use' error usually means:" -ForegroundColor Yellow
Write-Host "  1. ngrok is already running (check above)" -ForegroundColor White
Write-Host "  2. WindowsApps version has restrictions" -ForegroundColor White
Write-Host ""
Write-Host "Solutions:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option 1: Use Command Prompt (cmd.exe)" -ForegroundColor Yellow
Write-Host "  - Open Command Prompt" -ForegroundColor White
Write-Host "  - Run: ngrok http 5000" -ForegroundColor White
Write-Host ""
Write-Host "Option 2: Download standalone ngrok" -ForegroundColor Yellow
Write-Host "  - Download from: https://ngrok.com/download" -ForegroundColor White
Write-Host "  - Extract to: C:\ngrok\" -ForegroundColor White
Write-Host "  - Run: C:\ngrok\ngrok.exe http 5000" -ForegroundColor White
Write-Host ""
Write-Host "Option 3: Kill any stuck processes" -ForegroundColor Yellow
Write-Host "  - Run: Get-Process ngrok | Stop-Process -Force" -ForegroundColor White
Write-Host "  - Wait 5 seconds" -ForegroundColor White
Write-Host "  - Try again: ngrok http 5000" -ForegroundColor White
Write-Host ""


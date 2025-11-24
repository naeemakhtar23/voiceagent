# Script to check ngrok status and get the public URL

Write-Host "Checking ngrok status..." -ForegroundColor Cyan
Write-Host ""

# Check if ngrok process is running
$ngrokProcess = Get-Process ngrok -ErrorAction SilentlyContinue

if ($ngrokProcess) {
    Write-Host "[OK] ngrok is running!" -ForegroundColor Green
    Write-Host "  Process ID: $($ngrokProcess.Id)" -ForegroundColor Gray
    Write-Host ""
    
    # Try to get the public URL from ngrok API
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        if ($response.tunnels -and $response.tunnels.Count -gt 0) {
            $tunnel = $response.tunnels[0]
            $publicUrl = $tunnel.public_url
            $localUrl = $tunnel.config.addr
            
            Write-Host "========================================" -ForegroundColor Green
            Write-Host "  ngrok Tunnel Active" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "Public URL:  $publicUrl" -ForegroundColor Yellow
            Write-Host "Local URL:   $localUrl" -ForegroundColor Gray
            Write-Host ""
            Write-Host "Update your .env file:" -ForegroundColor Cyan
            Write-Host "  WEBHOOK_BASE_URL=$publicUrl" -ForegroundColor White
            Write-Host ""
            Write-Host "Configure Twilio webhook:" -ForegroundColor Cyan
            Write-Host "  $publicUrl/api/voice-flow" -ForegroundColor White
            Write-Host ""
        } else {
            Write-Host "[WARNING] ngrok is running but no tunnels found" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[INFO] ngrok is running but API not accessible" -ForegroundColor Yellow
        Write-Host "  This might mean ngrok is starting up or using different port" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Check ngrok web interface: http://localhost:4040" -ForegroundColor Cyan
    }
} else {
    Write-Host "[INFO] ngrok is not running" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To start ngrok, run:" -ForegroundColor Cyan
    Write-Host "  ngrok http 5000" -ForegroundColor White
    Write-Host ""
    Write-Host "Or use the helper script:" -ForegroundColor Cyan
    Write-Host "  .\start_ngrok.ps1" -ForegroundColor White
}

Write-Host ""


# Script to kill any ngrok processes and help restart

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ngrok Process Manager" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find all ngrok processes
$ngrokProcesses = Get-Process ngrok -ErrorAction SilentlyContinue

if ($ngrokProcesses) {
    Write-Host "[INFO] Found ngrok process(es):" -ForegroundColor Yellow
    foreach ($proc in $ngrokProcesses) {
        Write-Host "  PID: $($proc.Id) | Started: $($proc.StartTime)" -ForegroundColor Gray
    }
    Write-Host ""
    
    # Check if ngrok is actually working
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop -TimeoutSec 2
        if ($response.tunnels -and $response.tunnels.Count -gt 0) {
            $publicUrl = $response.tunnels[0].public_url
            Write-Host "[SUCCESS] ngrok is working!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Public URL: $publicUrl" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "You don't need to restart - it's already running!" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Update your .env file:" -ForegroundColor Cyan
            Write-Host "  WEBHOOK_BASE_URL=$publicUrl" -ForegroundColor White
            Write-Host ""
            Write-Host "Web interface: http://localhost:4040" -ForegroundColor Gray
            exit 0
        }
    } catch {
        Write-Host "[WARNING] ngrok process exists but not responding" -ForegroundColor Yellow
    }
    
    Write-Host ""
    $response = Read-Host "Do you want to kill the existing ngrok process(es)? (y/n)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host ""
        Write-Host "Stopping ngrok processes..." -ForegroundColor Yellow
        try {
            $ngrokProcesses | Stop-Process -Force
            Write-Host "[OK] Processes stopped" -ForegroundColor Green
            Write-Host ""
            Write-Host "Waiting 5 seconds for cleanup..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
            Write-Host "[OK] Ready to start ngrok" -ForegroundColor Green
            Write-Host ""
            Write-Host "Now run in Command Prompt:" -ForegroundColor Cyan
            Write-Host "  ngrok http 5000" -ForegroundColor White
        } catch {
            Write-Host "[ERROR] Failed to stop processes: $_" -ForegroundColor Red
            Write-Host ""
            Write-Host "Try running as Administrator:" -ForegroundColor Yellow
            Write-Host "  Get-Process ngrok | Stop-Process -Force" -ForegroundColor White
        }
    } else {
        Write-Host ""
        Write-Host "Keeping existing processes. Check if ngrok is working:" -ForegroundColor Yellow
        Write-Host "  http://localhost:4040" -ForegroundColor Cyan
    }
} else {
    Write-Host "[INFO] No ngrok processes found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The 'file in use' error might be due to:" -ForegroundColor Yellow
    Write-Host "  1. WindowsApps file lock" -ForegroundColor White
    Write-Host "  2. Antivirus blocking" -ForegroundColor White
    Write-Host "  3. File permissions" -ForegroundColor White
    Write-Host ""
    Write-Host "Solutions:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Option 1: Download standalone ngrok" -ForegroundColor Yellow
    Write-Host "  - Go to: https://ngrok.com/download" -ForegroundColor White
    Write-Host "  - Extract to: C:\ngrok\" -ForegroundColor White
    Write-Host "  - Run: C:\ngrok\ngrok.exe http 5000" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 2: Run as Administrator" -ForegroundColor Yellow
    Write-Host "  - Right-click Command Prompt" -ForegroundColor White
    Write-Host "  - Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "  - Run: ngrok http 5000" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 3: Check Task Manager" -ForegroundColor Yellow
    Write-Host "  - Open Task Manager (Ctrl+Shift+Esc)" -ForegroundColor White
    Write-Host "  - Look for ngrok.exe" -ForegroundColor White
    Write-Host "  - End the process if found" -ForegroundColor White
}

Write-Host ""


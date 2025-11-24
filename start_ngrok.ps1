# Quick script to start ngrok
# This script finds ngrok and starts it

$possiblePaths = @(
    "$env:USERPROFILE\ngrok\ngrok.exe",
    "$env:LOCALAPPDATA\ngrok\ngrok.exe",
    "C:\ngrok\ngrok.exe",
    "$env:USERPROFILE\Downloads\ngrok.exe"
)

$ngrokPath = $null

# Check if ngrok is in PATH
try {
    $ngrokPath = (Get-Command ngrok -ErrorAction Stop).Source
    Write-Host "[OK] Found ngrok in PATH: $ngrokPath" -ForegroundColor Green
} catch {
    # Check common locations
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $ngrokPath = $path
            Write-Host "[OK] Found ngrok at: $ngrokPath" -ForegroundColor Green
            break
        }
    }
}

if (-not $ngrokPath) {
    Write-Host "[ERROR] ngrok not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install ngrok first:" -ForegroundColor Yellow
    Write-Host "  1. Run: .\install_ngrok.ps1" -ForegroundColor White
    Write-Host "  2. Or download from: https://ngrok.com/download" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Starting ngrok on port 5000..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start ngrok
& $ngrokPath http 5000


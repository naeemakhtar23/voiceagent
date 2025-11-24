# PowerShell script to download and setup ngrok
# This script downloads ngrok for Windows and sets it up

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ngrok Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ngrokUrl = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
$downloadPath = "$env:USERPROFILE\Downloads\ngrok.zip"
$extractPath = "$env:USERPROFILE\ngrok"
$ngrokExe = "$extractPath\ngrok.exe"

# Check if ngrok already exists
if (Test-Path $ngrokExe) {
    Write-Host "[OK] ngrok already exists at: $ngrokExe" -ForegroundColor Green
    Write-Host ""
    Write-Host "To use ngrok, run:" -ForegroundColor Yellow
    Write-Host "  $ngrokExe http 5000" -ForegroundColor White
    Write-Host ""
    Write-Host "Or add to PATH:" -ForegroundColor Yellow
    Write-Host "  [Environment]::SetEnvironmentVariable('Path', `$env:Path + ';$extractPath', 'User')" -ForegroundColor White
    exit 0
}

Write-Host "[INFO] Downloading ngrok..." -ForegroundColor Yellow
Write-Host "  URL: $ngrokUrl" -ForegroundColor Gray
Write-Host "  Destination: $downloadPath" -ForegroundColor Gray
Write-Host ""

try {
    # Download ngrok
    Invoke-WebRequest -Uri $ngrokUrl -OutFile $downloadPath -UseBasicParsing
    Write-Host "[OK] Download complete!" -ForegroundColor Green
    Write-Host ""
    
    # Create extraction directory
    if (-not (Test-Path $extractPath)) {
        New-Item -ItemType Directory -Path $extractPath -Force | Out-Null
    }
    
    Write-Host "[INFO] Extracting ngrok..." -ForegroundColor Yellow
    Expand-Archive -Path $downloadPath -DestinationPath $extractPath -Force
    Write-Host "[OK] Extraction complete!" -ForegroundColor Green
    Write-Host ""
    
    # Clean up zip file
    Remove-Item $downloadPath -Force
    
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "ngrok is installed at: $ngrokExe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To start ngrok, run:" -ForegroundColor Yellow
    Write-Host "  $ngrokExe http 5000" -ForegroundColor White
    Write-Host ""
    Write-Host "Or add to PATH (run as Administrator):" -ForegroundColor Yellow
    Write-Host "  [Environment]::SetEnvironmentVariable('Path', `$env:Path + ';$extractPath', 'User')" -ForegroundColor White
    Write-Host ""
    Write-Host "After adding to PATH, restart PowerShell and run: ngrok http 5000" -ForegroundColor Cyan
    
} catch {
    Write-Host "[ERROR] Installation failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual installation:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://ngrok.com/download" -ForegroundColor White
    Write-Host "2. Extract to a folder" -ForegroundColor White
    Write-Host "3. Run: .\ngrok.exe http 5000" -ForegroundColor White
    exit 1
}


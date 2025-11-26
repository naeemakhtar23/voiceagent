# Poppler Installation Guide

Poppler is required for PDF processing in the OCR system. This guide will help you install it on your system.

## Windows Installation

### Option 1: Using Pre-built Binaries (Recommended)

1. **Download Poppler for Windows:**
   - Visit: https://github.com/oschwartz10612/poppler-windows/releases/
   - Download the latest release (e.g., `Release-XX.XX.X-X.zip`)

2. **Extract the Archive:**
   - Extract the zip file to a location like `C:\poppler`
   - You should have a folder structure like: `C:\poppler\bin\`

3. **Add to System PATH:**
   - Open System Properties:
     - Press `Win + R`, type `sysdm.cpl`, press Enter
     - Or: Right-click "This PC" → Properties → Advanced system settings
   - Click "Environment Variables"
   - Under "System variables", find and select "Path", then click "Edit"
   - Click "New" and add: `C:\poppler\bin` (or your poppler bin path)
   - Click "OK" on all dialogs

4. **Verify Installation:**
   - Open a new Command Prompt or PowerShell window
   - Run: `pdftoppm -v`
   - You should see version information

5. **Restart Your Application:**
   - Close and restart your Flask application for PATH changes to take effect

### Option 2: Using Environment Variable (Alternative)

If you don't want to modify system PATH, you can set an environment variable:

1. Extract poppler to a location (e.g., `C:\poppler`)
2. Set the `POPPLER_PATH` environment variable to the bin folder:
   ```powershell
   $env:POPPLER_PATH = "C:\poppler\bin"
   ```
3. Or add it to your `.env` file (if your app reads it):
   ```
   POPPLER_PATH=C:\poppler\bin
   ```

## macOS Installation

Install using Homebrew:

```bash
brew install poppler
```

Verify installation:
```bash
pdftoppm -v
```

## Linux Installation

### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

### Fedora/RHEL/CentOS:
```bash
sudo dnf install poppler-utils
```

### Arch Linux:
```bash
sudo pacman -S poppler
```

### Verify Installation:
```bash
pdftoppm -v
```

## Troubleshooting

### Error: "Unable to get page count. Is poppler installed and in PATH?"

1. **Check if poppler is installed:**
   - Windows: Open Command Prompt and run `pdftoppm -v`
   - macOS/Linux: Run `pdftoppm -v` in terminal
   - If command not found, poppler is not in PATH

2. **Verify PATH:**
   - Windows: `echo %PATH%` in Command Prompt
   - macOS/Linux: `echo $PATH` in terminal
   - Check if poppler bin directory is listed

3. **Restart Application:**
   - After adding to PATH, restart your Flask application
   - PATH changes require a new terminal/application session

4. **Check Environment Variables:**
   - If using `POPPLER_PATH`, verify it's set correctly
   - Restart the application after setting the variable

## Testing PDF Processing

After installation, test PDF processing by:
1. Uploading a PDF file through the OCR interface
2. Check the application logs for any poppler-related errors
3. If successful, you should see "Processing PDF page X/Y" messages in the logs


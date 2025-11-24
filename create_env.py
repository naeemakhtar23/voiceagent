"""
Create .env file with configuration
"""
import os

env_content = """# Twilio Configuration
TWILIO_ACCOUNT_SID=ACe301f2e318b9bc5b2fed0ee1a2b3af64
TWILIO_AUTH_TOKEN=6cbd526dbb26f093a8208c03da606012
TWILIO_PHONE_NUMBER=

# Database Configuration - SQL Server
DB_CONNECTION_STRING=Server=DESKTOP-U22UKGN\\SQLEXPRESS;Database=ePRF;Integrated Security=True;

# Webhook URL (update after starting ngrok)
WEBHOOK_BASE_URL=http://localhost:5000

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=5000

# Demo Mode (set to true to simulate calls without ngrok)
DEMO_MODE=false
"""

if os.path.exists('.env'):
    print("[WARNING] .env file already exists. Skipping creation.")
    print("   If you want to recreate it, delete the existing file first.")
else:
    with open('.env', 'w') as f:
        f.write(env_content)
    print("[SUCCESS] .env file created successfully!")
    print("   Please update TWILIO_PHONE_NUMBER with your Twilio phone number")


"""
Configuration file for the Voice Call System
Handles environment variables and configuration settings
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# Database Configuration - SQL Server
DB_CONNECTION_STRING = os.getenv(
    'DB_CONNECTION_STRING',
    'Driver={SQL Server};Server=DESKTOP-U22UKGN\\SQLEXPRESS;Database=ePRF;Trusted_Connection=yes;'
)

# Webhook URL (set after Cloudflare Tunnel setup)
# Use Cloudflare Tunnel: cloudflared tunnel --url http://localhost:5000
# Copy the https://random-string.trycloudflare.com URL and set it here
WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL', '')

# Flask Configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
ELEVENLABS_AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID', '')
ELEVENLABS_WEBHOOK_SECRET = os.getenv('ELEVENLABS_WEBHOOK_SECRET', '')
# Custom endpoint override (leave empty to use default attempts)
ELEVENLABS_CALL_ENDPOINT = os.getenv('ELEVENLABS_CALL_ENDPOINT', '')

# Dialogflow Configuration
DIALOGFLOW_PROJECT_ID = os.getenv('DIALOGFLOW_PROJECT_ID', '')
DIALOGFLOW_LANGUAGE_CODE = os.getenv('DIALOGFLOW_LANGUAGE_CODE', 'en')

# Google Application Credentials (for Dialogflow)
# Set this as an environment variable or in .env file: GOOGLE_APPLICATION_CREDENTIALS
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

# Set the environment variable if provided (for Google Cloud libraries)
if GOOGLE_APPLICATION_CREDENTIALS:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS

# Application Settings
APP_NAME = "Voice Call System"
APP_VERSION = "1.0.0"


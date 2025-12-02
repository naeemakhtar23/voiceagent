# Dialogflow ES Setup Guide

This guide will help you set up Google Dialogflow ES for the Voice Bot feature.

## Prerequisites

1. Google Cloud Platform (GCP) account
2. A GCP project with billing enabled (Dialogflow ES has a free tier)

## Step 1: Create a Dialogflow Agent

1. Go to [Dialogflow Console](https://dialogflow.cloud.google.com/)
2. Click "Create Agent"
3. Fill in:
   - **Agent Name**: Voice Bot Form Assistant (or any name you prefer)
   - **Default Language**: English (en)
   - **Default Time Zone**: Your timezone
   - **Google Project**: Select or create a new GCP project
4. Click "Create"

## Step 2: Create Intents

Create the following intents in your Dialogflow agent:

### Intent 1: `yes`
- **Training Phrases**:
  - yes
  - yeah
  - yep
  - sure
  - correct
  - affirmative
  - ok
  - okay
  - yup
  - right
  - I agree
  - that's right
- **Response**: "Yes"

### Intent 2: `no`
- **Training Phrases**:
  - no
  - nope
  - nah
  - incorrect
  - negative
  - wrong
  - not
  - I disagree
  - that's wrong
- **Response**: "No"

### Intent 3: `repeat`
- **Training Phrases**:
  - repeat
  - again
  - say that again
  - what was the question
  - can you repeat
  - repeat the question
  - say it again
- **Response**: "I'll repeat the question"

### Intent 4: `skip`
- **Training Phrases**:
  - skip
  - next
  - pass
  - move on
  - continue
  - skip this
  - next question
- **Response**: "Skipping to next question"

## Step 3: Get Your Project ID

1. In Dialogflow Console, go to Settings (gear icon)
2. Note your **Project ID** (e.g., `my-voice-bot-project`)

## Step 4: Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **IAM & Admin** > **Service Accounts**
4. Click **Create Service Account**
5. Fill in:
   - **Name**: dialogflow-voice-bot
   - **Description**: Service account for Voice Bot Dialogflow integration
6. Click **Create and Continue**
7. Grant role: **Dialogflow API Client** (or **Dialogflow API User**)
8. Click **Continue** then **Done**

## Step 5: Create and Download JSON Key

1. Click on the service account you just created
2. Go to **Keys** tab
3. Click **Add Key** > **Create new key**
4. Select **JSON**
5. Click **Create** - this downloads a JSON key file
6. **Save this file securely** - you'll need it for authentication

## Step 6: Configure Environment Variables

Add the following to your `.env` file:

```env
# Dialogflow Configuration
DIALOGFLOW_PROJECT_ID=your-project-id-here
DIALOGFLOW_LANGUAGE_CODE=en

# Google Application Credentials (path to your JSON key file)
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
```

**Important**: 
- Replace `your-project-id-here` with your actual Dialogflow project ID
- Replace `path/to/your/service-account-key.json` with the actual path to your downloaded JSON key file
- On Windows, use forward slashes or escaped backslashes: `C:/path/to/key.json` or `C:\\path\\to\\key.json`

## Step 7: Install Dependencies

Make sure you have the Dialogflow library installed:

```bash
pip install google-cloud-dialogflow
```

Or install all requirements:

```bash
pip install -r backend/requirements.txt
```

## Step 8: Test the Setup

1. Start your Flask application:
   ```bash
   python backend/app.py
   ```

2. Navigate to `/voice-bot` in your browser

3. Click "Start Voice Bot Session"

4. Try answering with voice or buttons

## Fallback Mode

If Dialogflow is not configured, the system will automatically use a fallback mode with simple text matching. This allows the voice bot to work even without Dialogflow setup, though with reduced accuracy.

## Troubleshooting

### Error: "Dialogflow handler not available"
- Make sure `google-cloud-dialogflow` is installed: `pip install google-cloud-dialogflow`

### Error: "GOOGLE_APPLICATION_CREDENTIALS not set"
- Set the environment variable pointing to your service account JSON key file
- Or set it in your `.env` file as shown above

### Error: "Permission denied" or "Authentication failed"
- Verify your service account has the correct permissions (Dialogflow API Client/User)
- Check that the JSON key file path is correct
- Ensure the JSON key file is valid and not corrupted

### Error: "Project not found"
- Verify your `DIALOGFLOW_PROJECT_ID` matches your actual Dialogflow project ID
- Check that the project exists in your GCP console

## Notes

- Dialogflow ES has a free tier with generous limits for development
- The system works without Dialogflow using fallback text matching
- Voice input uses browser's Web Speech API (Chrome/Edge recommended)
- Voice output uses browser's Speech Synthesis API


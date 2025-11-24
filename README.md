# 🎙️ Voice Call System - Automated Survey with Yes/No Questions

A professional web-based voice call system that makes automated calls to mobile phones, asks yes/no questions, collects responses via speech recognition, and stores results in a SQL database with JSON format.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Demo Preparation](#demo-preparation)
- [Troubleshooting](#troubleshooting)
- [Cost Information](#cost-information)

---

## 🎯 Overview

This system enables you to:
- **Initiate voice calls** from a web dashboard to real mobile numbers
- **Ask questions sequentially** one by one during the call
- **Collect yes/no answers** using speech recognition or keypad input
- **Store responses** in SQL database with complete JSON format
- **View call history** and results in real-time
- **Generate structured JSON** responses for integration

Perfect for:
- Healthcare surveys
- Customer feedback collection
- Appointment confirmations
- Automated questionnaires
- Management demonstrations

---

## ✨ Features

### Core Functionality
- ✅ **Web Dashboard**: Modern, responsive interface for call management
- ✅ **Automated Voice Calls**: Initiate calls via Twilio API
- ✅ **Sequential Questions**: Ask questions one by one with natural flow
- ✅ **Speech Recognition**: Captures yes/no answers via voice
- ✅ **Keypad Fallback**: Accept 1=yes, 2=no as backup
- ✅ **Real-time Status**: Live call status updates
- ✅ **JSON Responses**: Structured data format for all results
- ✅ **SQL Database**: Complete data persistence
- ✅ **Call History**: Track all calls with detailed information

### Advanced Features
- 🎯 **Answer Validation**: Recognizes multiple yes/no variations
- 🎯 **Confidence Scoring**: Speech recognition confidence levels
- 🎯 **Timeout Handling**: Graceful handling of no response
- 🎯 **Error Recovery**: Robust error handling throughout
- 🎯 **Call Analytics**: Summary statistics (yes/no counts)
- 🎯 **Response Time Tracking**: Measure time to answer each question

---

## 🏗️ Architecture

### System Flow

```
┌─────────────┐
│  Web Browser │
│  (Dashboard) │
└──────┬───────┘
       │
       │ HTTP/JSON
       │
┌──────▼──────────┐
│  Flask Backend  │
│  (Python)       │
└──────┬──────────┘
       │
       ├──────────────┬──────────────┐
       │              │              │
┌──────▼──────┐  ┌───▼──────┐  ┌───▼──────┐
│   Twilio    │  │   SQL    │  │  ngrok   │
│   API       │  │ Database │  │ Webhook  │
└──────┬──────┘  └──────────┘  └──────────┘
       │
       │ Voice Call
       │
┌──────▼──────┐
│ Mobile Phone│
│  (Client)   │
└─────────────┘
```

### Call Flow Sequence

1. **User initiates call** from web dashboard
2. **Backend creates call record** in database
3. **Twilio initiates call** to mobile number
4. **Call connects** → Twilio requests TwiML from webhook
5. **System asks Question 1** → Waits for response
6. **User responds** → Speech recognition processes answer
7. **Answer stored** in database
8. **System asks Question 2** → Process repeats
9. **All questions completed** → Call ends
10. **JSON results generated** and stored

---

## 🛠️ Technology Stack

### Backend
- **Python 3.8+**: Core programming language
- **Flask 3.0**: Web framework for API and webhooks
- **Twilio SDK**: Voice call and speech recognition
- **pyodbc**: SQL Server database connectivity
- **python-dotenv**: Environment variable management

### Frontend
- **HTML5**: Structure
- **CSS3**: Modern styling with gradients
- **JavaScript (ES6+)**: Client-side logic
- **Fetch API**: HTTP requests

### Database
- **SQL Server**: Primary database (ePRF)
- **Tables**: calls, questions, call_results

### Infrastructure
- **ngrok**: Webhook tunneling for local development
- **Twilio**: Voice API and phone services

---

## 📁 Project Structure

```
ProjectSpeechAndOCR/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration management
│   ├── database.py            # Database operations
│   ├── voice_handler.py       # Twilio voice call logic
│   └── requirements.txt       # Python dependencies
│
├── frontend/
│   ├── index.html             # Web dashboard
│   ├── style.css              # Styling
│   └── app.js                 # Frontend JavaScript
│
├── database/
│   └── schema.sql             # Database schema
│
├── .env                       # Environment variables (create from .env.example)
├── .env.example               # Environment template
└── README.md                  # This file
```

---

## 🚀 Setup Instructions

### Prerequisites

1. **Python 3.8 or higher**
   ```bash
   python --version
   ```

2. **SQL Server** (already configured)
   - Server: `DESKTOP-U22UKGN\SQLEXPRESS`
   - Database: `ePRF`
   - Authentication: Windows Integrated Security

3. **Twilio Account**
   - Sign up at: https://www.twilio.com/try-twilio
   - Get Account SID, Auth Token, and Phone Number

4. **ngrok** (for webhook testing)
   - Download: https://ngrok.com/download
   - Free account required

### Step 1: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Or install individually:
```bash
pip install Flask==3.0.0 flask-cors==4.0.0 twilio==8.10.0 python-dotenv==1.0.0 pyodbc==5.0.1
```

### Step 2: Database Setup

1. Open SQL Server Management Studio (SSMS)
2. Connect to: `DESKTOP-U22UKGN\SQLEXPRESS`
3. Open and execute: `database/schema.sql`
4. Verify tables are created:
   - `calls`
   - `questions`
   - `call_results`

### Step 3: Environment Configuration

1. Create `.env` file in project root:
   ```env
   # Twilio Configuration
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+1234567890

   # Database (already configured)
   DB_CONNECTION_STRING=Server=DESKTOP-U22UKGN\SQLEXPRESS;Database=ePRF;Integrated Security=True;

   # Webhook URL (update after ngrok setup)
   WEBHOOK_BASE_URL=http://localhost:5000

   # Flask
   FLASK_ENV=development
   FLASK_DEBUG=True
   FLASK_PORT=5000
   ```

2. Get Twilio credentials:
   - Login to: https://console.twilio.com/
   - Copy Account SID and Auth Token
   - Get your Twilio phone number

### Step 4: ngrok Setup (for Webhooks)

1. Start ngrok in a separate terminal:
   ```bash
   ngrok http 5000
   ```

2. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

3. Update `.env`:
   ```env
   WEBHOOK_BASE_URL=https://abc123.ngrok.io
   ```

4. **Important**: Keep ngrok running while testing!

### Step 5: Twilio Webhook Configuration

1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Click on your Twilio phone number
3. In "Voice & Fax" section:
   - **A CALL COMES IN**: `https://your-ngrok-url.ngrok.io/api/voice-flow`
   - **HTTP Method**: POST
4. Save configuration

### Step 6: Verify Phone Number (Trial Account)

1. Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/verified
2. Add your test mobile number
3. Verify via SMS/call

### Step 7: Start the Application

```bash
# From project root
cd backend
python app.py
```

The server will start on: `http://localhost:5000`

### Step 8: Access Dashboard

Open browser: `http://localhost:5000`

---

## ⚙️ Configuration

### Database Connection

The system uses Windows Integrated Security:
```
Server=DESKTOP-U22UKGN\SQLEXPRESS;Database=ePRF;Integrated Security=True;
```

To change database, update `DB_CONNECTION_STRING` in `.env` or `backend/config.py`.

### Twilio Settings

- **Account SID**: From Twilio Console
- **Auth Token**: From Twilio Console
- **Phone Number**: Your Twilio number (format: +1234567890)

### Webhook URL

- **Local Development**: Use ngrok HTTPS URL
- **Production**: Use your domain with SSL certificate

---

## 📖 Usage Guide

### Making a Call

1. **Open Dashboard**: Navigate to `http://localhost:5000`

2. **Enter Phone Number**:
   - Format: `+1234567890` (include country code)
   - Example: `+14155551234` (US)
   - Example: `+447911123456` (UK)

3. **Add Questions**:
   - Click "➕ Add Question"
   - Enter question text
   - Add multiple questions as needed
   - Example questions:
     - "Do you have health insurance?"
     - "Are you currently taking any medications?"
     - "Have you visited a doctor in the last 6 months?"

4. **Initiate Call**:
   - Click "📞 Make Call"
   - Wait for call to connect
   - Answer on your mobile phone

5. **During Call**:
   - System will ask questions one by one
   - Answer with "yes" or "no"
   - Or press 1 for yes, 2 for no
   - System confirms each answer

6. **View Results**:
   - Results appear automatically after call
   - JSON format displayed
   - Call history updated

### Viewing Call History

- All calls listed in "Call History" section
- Click "View Results" to see JSON
- Status badges show call state:
  - 🟡 **initiated**: Call created
  - 🔵 **ringing**: Phone ringing
  - 🔵 **in-progress**: Call active
  - 🟢 **completed**: Call finished
  - 🔴 **failed**: Call failed

### JSON Response Format

```json
{
  "call_id": 1,
  "phone_number": "+1234567890",
  "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "status": "completed",
  "started_at": "2025-01-15T10:30:00",
  "ended_at": "2025-01-15T10:32:15",
  "duration_seconds": 135,
  "timestamp": "2025-01-15T10:32:16",
  "questions": [
    {
      "question_number": 1,
      "question": "Do you have health insurance?",
      "answer": "yes",
      "confidence": 0.95,
      "raw_response": "yes",
      "response_time_seconds": 3
    },
    {
      "question_number": 2,
      "question": "Are you taking medications?",
      "answer": "no",
      "confidence": 0.92,
      "raw_response": "no",
      "response_time_seconds": 2
    }
  ],
  "summary": {
    "total_questions": 2,
    "yes_count": 1,
    "no_count": 1,
    "unclear_count": 0
  }
}
```

---

## 🔌 API Endpoints

### Web Dashboard
- `GET /` - Main dashboard page

### Call Management
- `POST /api/initiate-call` - Initiate a new call
  ```json
  {
    "phone_number": "+1234567890",
    "questions": [
      {"text": "Question 1"},
      {"text": "Question 2"}
    ]
  }
  ```

- `GET /api/calls` - Get all calls
- `GET /api/call/<call_id>` - Get specific call details
- `GET /api/call-results/<call_id>` - Get call results as JSON

### Twilio Webhooks
- `POST /api/voice-flow?call_id=<id>&q_num=<num>` - Voice flow control
- `POST /api/process-answer?call_id=<id>&q_num=<num>` - Process answer
- `POST /api/call-status` - Call status updates

### Health Check
- `GET /api/health` - System health status

---

## 🗄️ Database Schema

### `calls` Table
| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| phone_number | VARCHAR(20) | Called number |
| call_sid | VARCHAR(100) | Twilio call SID |
| status | VARCHAR(50) | Call status |
| questions_json | NVARCHAR(MAX) | Questions in JSON |
| started_at | DATETIME | Call start time |
| ended_at | DATETIME | Call end time |
| duration_seconds | INT | Call duration |
| created_at | DATETIME | Record creation |

### `questions` Table
| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| call_id | INT | Foreign key to calls |
| question_text | NVARCHAR(500) | Question text |
| question_number | INT | Question order |
| response | VARCHAR(10) | yes/no/unclear |
| response_confidence | DECIMAL(5,2) | Confidence score |
| raw_response | NVARCHAR(200) | Original response |
| response_time_seconds | INT | Time to answer |
| created_at | DATETIME | Record creation |

### `call_results` Table
| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| call_id | INT | Foreign key to calls |
| json_response | NVARCHAR(MAX) | Complete JSON result |
| created_at | DATETIME | Record creation |

---

## 🎬 Demo Preparation

### Pre-Demo Checklist

- [ ] Twilio account active with verified number
- [ ] Database tables created and tested
- [ ] Backend running (`python backend/app.py`)
- [ ] ngrok tunnel active and URL configured
- [ ] Webhook URL set in Twilio console
- [ ] Test mobile number verified in Twilio
- [ ] Sample questions prepared (3-5 questions)
- [ ] Test call completed successfully

### Demo Script

1. **Introduction** (30 seconds)
   - "This is our Voice Call System for automated surveys"
   - "It makes calls, asks questions, and collects responses"

2. **Show Dashboard** (30 seconds)
   - Point out clean interface
   - Show call history (if any)

3. **Make Live Call** (2-3 minutes)
   - Enter test phone number
   - Add 3-5 sample questions
   - Click "Make Call"
   - Answer on mobile phone
   - Show real-time status updates

4. **Show Results** (1 minute)
   - Display JSON response
   - Explain structure
   - Show summary statistics

5. **Show Database** (30 seconds)
   - Open SSMS
   - Show tables with data
   - Explain data persistence

6. **Q&A** (2 minutes)
   - Answer questions
   - Discuss scalability
   - Mention integration possibilities

### Sample Questions for Demo

1. "Do you have health insurance?"
2. "Are you currently taking any medications?"
3. "Have you visited a doctor in the last 6 months?"
4. "Do you have any chronic conditions?"
5. "Would you like to receive health reminders?"

### Backup Plan

- Have a recorded demo video ready
- Screenshots of dashboard and results
- Sample JSON responses to show
- Database screenshots

---

## 🔧 Troubleshooting

### Issue: Call not connecting

**Solutions:**
- Verify phone number is verified in Twilio (trial accounts)
- Check phone number format includes country code (+)
- Verify Twilio account has credits
- Check Twilio phone number is active

### Issue: Webhook not receiving requests

**Solutions:**
- Ensure ngrok is running
- Verify ngrok URL in `.env` matches Twilio webhook
- Check firewall/antivirus isn't blocking
- Test webhook URL manually: `curl https://your-ngrok-url.ngrok.io/api/health`

### Issue: Database connection error

**Solutions:**
- Verify SQL Server is running
- Check connection string in `.env`
- Test Windows authentication
- Verify database `ePRF` exists
- Check user has permissions

### Issue: Speech recognition not working

**Solutions:**
- Speak clearly: "yes" or "no"
- Wait for beep before speaking
- Use keypad as backup (1=yes, 2=no)
- Check Twilio speech recognition settings

### Issue: Questions not being asked

**Solutions:**
- Verify questions are added before call
- Check webhook URL is accessible
- Review Flask logs for errors
- Ensure TwiML is being generated correctly

### Debug Mode

Enable detailed logging:
```python
# In backend/app.py
logging.basicConfig(level=logging.DEBUG)
```

Check logs in terminal where Flask is running.

---

## 💰 Cost Information

### Free Tier (Trial)
- **Twilio**: $15.50 credit
  - ~100 minutes of voice calls
  - Sufficient for multiple demos
- **ngrok**: Free tier
  - Random URLs (changes on restart)
  - Sufficient for development
- **Database**: Local SQL Server
  - No additional cost
- **Total**: **$0 for demo**

### Production Costs (Estimated)
- **Twilio Voice**: ~$0.013 per minute
- **Twilio Phone Number**: ~$1/month
- **ngrok Pro**: $8/month (fixed URL)
- **Hosting**: Varies (AWS, Azure, etc.)

---

## 📝 Notes

### Security Considerations
- Never commit `.env` file to version control
- Use environment variables for sensitive data
- Implement authentication for production
- Use HTTPS in production

### Production Deployment
- Use proper web server (Gunicorn, uWSGI)
- Set up SSL certificate
- Use fixed domain for webhooks
- Implement rate limiting
- Add authentication/authorization
- Set up monitoring and logging

### Extensions
- Add multi-language support
- Implement call scheduling
- Add email/SMS notifications
- Create admin dashboard
- Add analytics and reporting
- Integrate with CRM systems

---

## 📞 Support

For issues or questions:
1. Check this README
2. Review Twilio documentation: https://www.twilio.com/docs
3. Check Flask documentation: https://flask.palletsprojects.com/
4. Review application logs

---

## 📄 License

This project is created for demonstration purposes.

---

## 🎉 Success!

You now have a complete Voice Call System ready for your management demo!

**Key Highlights:**
- ✅ Professional web interface
- ✅ Real-time call monitoring
- ✅ Complete database integration
- ✅ JSON response format
- ✅ Scalable architecture
- ✅ Production-ready code

**Next Steps:**
1. Complete setup following instructions
2. Test with your phone number
3. Prepare demo questions
4. Practice demo flow
5. Present to management!

---

**Version**: 1.0.0  
**Last Updated**: January 2025  
**Database**: ePRF on DESKTOP-U22UKGN\SQLEXPRESS


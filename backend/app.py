"""
Main Flask application for Voice Call System
Handles API endpoints and webhooks
"""
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from voice_handler import VoiceHandler
from elevenlabs_handler import ElevenLabsHandler
from database import Database
from config import FLASK_PORT, FLASK_DEBUG
from demo_mode import DemoMode
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='../frontend',
            static_folder='../frontend')
CORS(app)

# Initialize handlers
db = Database()
voice_handler = VoiceHandler()
elevenlabs_handler = ElevenLabsHandler()
demo_mode = DemoMode()

# Check if demo mode is enabled
DEMO_MODE = os.getenv('DEMO_MODE', 'false').lower() == 'true'


@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')


@app.route('/style.css')
def style_css():
    """Serve CSS file"""
    return send_from_directory('../frontend', 'style.css', mimetype='text/css')


@app.route('/app.js')
def app_js():
    """Serve JavaScript file"""
    return send_from_directory('../frontend', 'app.js', mimetype='application/javascript')


@app.route('/api/initiate-call', methods=['POST'])
def initiate_call():
    """Initiate a voice call with questions"""
    try:
        data = request.json
        phone_number = data.get('phone_number')
        questions = data.get('questions', [])
        
        if not phone_number:
            return jsonify({
                'success': False,
                'error': 'Phone number is required'
            }), 400
        
        if not questions or len(questions) == 0:
            return jsonify({
                'success': False,
                'error': 'At least one question is required'
            }), 400
        
        # Validate phone number format (should start with +)
        if not phone_number.startswith('+'):
            return jsonify({
                'success': False,
                'error': 'Phone number must include country code (e.g., +1234567890)'
            }), 400
        
        # Check if demo mode is enabled
        if DEMO_MODE:
            logger.info("Demo mode enabled - simulating call")
            result = demo_mode.simulate_call(phone_number, questions)
            if result['success']:
                return jsonify({
                    'success': True,
                    'call_id': result['call_id'],
                    'call_sid': result['call_sid'],
                    'message': 'Demo call simulated successfully',
                    'demo_mode': True,
                    'results': result.get('results')
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Demo simulation failed')
                }), 500
        
        # Try to store call in database (optional - continue if fails)
        call_id = None
        try:
            call_id = db.create_call(phone_number, questions)
            logger.info(f"Call record created in database: {call_id}")
        except Exception as db_error:
            logger.warning(f"Database not available, using temporary ID: {str(db_error)}")
            import random
            call_id = random.randint(10000, 99999)  # Temporary ID if DB unavailable
            logger.info(f"Using temporary call ID: {call_id}")
        
        # Initiate Twilio call (this will work even without database)
        try:
            call_sid = voice_handler.initiate_call(phone_number, call_id, questions)
        except Exception as call_error:
            logger.error(f"Error initiating Twilio call: {str(call_error)}")
            return jsonify({
                'success': False,
                'error': f'Failed to initiate call: {str(call_error)}'
            }), 500
        
        # Try to update call with SID (optional)
        try:
            db.update_call_sid(call_id, call_sid)
        except Exception as db_error:
            logger.warning(f"Could not update call SID in database: {str(db_error)}")
            # Continue - call is still initiated successfully
        
        logger.info(f"Call initiated: ID={call_id}, SID={call_sid}, Phone={phone_number}")
        
        return jsonify({
            'success': True,
            'call_id': call_id,
            'call_sid': call_sid,
            'message': 'Call initiated successfully'
        })
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/initiate-elevenlabs-call', methods=['POST'])
def initiate_elevenlabs_call():
    """Initiate a voice call using ElevenLabs Voice Agent"""
    try:
        data = request.json
        phone_number = data.get('phone_number')
        questions = data.get('questions', [])
        
        if not phone_number:
            return jsonify({
                'success': False,
                'error': 'Phone number is required'
            }), 400
        
        if not questions or len(questions) == 0:
            return jsonify({
                'success': False,
                'error': 'At least one question is required'
            }), 400
        
        # Validate phone number format
        if not phone_number.startswith('+'):
            return jsonify({
                'success': False,
                'error': 'Phone number must include country code (e.g., +1234567890)'
            }), 400
        
        # Try to store call in database
        call_id = None
        try:
            call_id = db.create_call(phone_number, questions)
            logger.info(f"ElevenLabs call record created in database: {call_id}")
        except Exception as db_error:
            logger.warning(f"Database not available, using temporary ID: {str(db_error)}")
            import random
            call_id = random.randint(10000, 99999)
            logger.info(f"Using temporary call ID: {call_id}")
        
        # Initiate ElevenLabs call
        try:
            call_sid = elevenlabs_handler.initiate_call(phone_number, call_id, questions)
        except Exception as call_error:
            logger.error(f"Error initiating ElevenLabs call: {str(call_error)}")
            return jsonify({
                'success': False,
                'error': f'Failed to initiate call: {str(call_error)}'
            }), 500
        
        # Try to update call with SID
        try:
            db.update_call_sid(call_id, call_sid)
        except Exception as db_error:
            logger.warning(f"Could not update call SID in database: {str(db_error)}")
        
        logger.info(f"ElevenLabs call initiated: ID={call_id}, SID={call_sid}, Phone={phone_number}")
        
        return jsonify({
            'success': True,
            'call_id': call_id,
            'call_sid': call_sid,
            'message': 'ElevenLabs call initiated successfully'
        })
    except Exception as e:
        logger.error(f"Error initiating ElevenLabs call: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/elevenlabs-webhook', methods=['POST'])
def elevenlabs_webhook():
    """Webhook endpoint for ElevenLabs events"""
    try:
        # Get webhook data
        if request.is_json:
            webhook_data = request.json
        else:
            webhook_data = request.form.to_dict()
        
        # Verify webhook signature if secret is configured
        if elevenlabs_handler.webhook_secret:
            # Add signature verification logic here based on ElevenLabs docs
            # For now, we'll skip verification but log it
            logger.info("Webhook secret configured but verification not implemented yet")
        
        # Process webhook
        result = elevenlabs_handler.handle_webhook(webhook_data)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing ElevenLabs webhook: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/voice-flow', methods=['POST'])
def voice_flow():
    """
    Twilio webhook for voice flow
    Controls the question flow during the call
    """
    try:
        # Try to get call_id from query params first, then form data
        call_id = request.args.get('call_id') or request.form.get('call_id')
        current_question = int(request.args.get('q_num', request.form.get('q_num', 0)))
        
        # Log all request data for debugging
        logger.info(f"Voice flow webhook called - Args: {dict(request.args)}, Form: {dict(request.form)}")
        
        if not call_id:
            logger.error("No call_id provided in voice flow webhook")
            return '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Error: Call ID not found. Please try again.</Say><Hangup/></Response>', 200, {'Content-Type': 'text/xml'}
        
        logger.info(f"Processing voice flow: call_id={call_id}, q_num={current_question}")
        
        # Generate TwiML for current question
        twiml = voice_handler.handle_voice_flow(call_id, current_question)
        
        logger.info(f"Generated TwiML for call_id={call_id}, length={len(twiml)} characters")
        return twiml, 200, {'Content-Type': 'text/xml'}
    except Exception as e:
        logger.error(f"Error in voice flow webhook: {str(e)}", exc_info=True)
        return '<?xml version="1.0" encoding="UTF-8"?><Response><Say>An error occurred processing your call. Please try again later.</Say><Hangup/></Response>', 200, {'Content-Type': 'text/xml'}


@app.route('/api/process-answer', methods=['POST'])
def process_answer():
    """
    Twilio webhook for processing answers
    Called after caller responds to a question
    """
    try:
        call_id = request.args.get('call_id')
        question_num = int(request.args.get('q_num', 0))
        
        if not call_id:
            logger.error("No call_id provided in process answer")
            return '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Error.</Say><Hangup/></Response>', 200, {'Content-Type': 'text/xml'}
        
        # Get the speech recognition result
        speech_result = request.form.get('SpeechResult')  # What user said
        digits = request.form.get('Digits')  # Keypad input (1 or 2)
        confidence = request.form.get('Confidence')  # Speech recognition confidence
        
        logger.info(f"Answer received - Call ID: {call_id}, Q: {question_num}, Speech: {speech_result}, Digits: {digits}, Confidence: {confidence}")
        
        # Process and store answer
        twiml = voice_handler.process_answer(
            call_id=call_id,
            question_num=question_num,
            speech_result=speech_result,
            digits=digits,
            confidence=confidence
        )
        
        return twiml, 200, {'Content-Type': 'text/xml'}
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}")
        return '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Error processing answer.</Say><Hangup/></Response>', 200, {'Content-Type': 'text/xml'}


@app.route('/api/call-status', methods=['POST'])
def call_status():
    """Twilio webhook for call status updates"""
    try:
        call_sid = request.form.get('CallSid')
        call_status = request.form.get('CallStatus')
        call_duration = request.form.get('CallDuration')
        
        logger.info(f"Call status update - SID: {call_sid}, Status: {call_status}, Duration: {call_duration}")
        
        if call_sid:
            try:
                db.update_call_status(call_sid, call_status)
            except Exception as db_error:
                logger.warning(f"Database not available for status update: {str(db_error)}")
                # Continue without database update
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error updating call status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/call-results/<int:call_id>', methods=['GET'])
def get_call_results(call_id):
    """Get call results as JSON"""
    try:
        results = db.get_call_results_json(call_id)
        if results:
            return jsonify(results)
        else:
            return jsonify({
                'error': 'Call results not found. The call may still be in progress or not completed yet.'
            }), 404
    except Exception as e:
        logger.error(f"Error getting call results: {str(e)}")
        # Try to provide helpful error message
        error_msg = str(e)
        if 'IM002' in error_msg or 'connection' in error_msg.lower():
            return jsonify({
                'error': 'Database connection issue. Please check database configuration.',
                'details': 'The database may not be accessible. Results will be available once the call completes and database is connected.'
            }), 503
        else:
            return jsonify({
                'error': f'Error retrieving call results: {error_msg}'
            }), 500


@app.route('/api/calls', methods=['GET'])
def get_calls():
    """Get all calls for dashboard"""
    try:
        calls = db.get_all_calls()
        # Convert datetime objects to strings
        for call in calls:
            for key, value in call.items():
                if hasattr(value, 'isoformat'):
                    call[key] = value.isoformat()
        logger.info(f"Successfully retrieved {len(calls)} calls from database")
        return jsonify(calls)
    except Exception as e:
        logger.error(f"Error getting calls from database: {str(e)}", exc_info=True)
        # Return empty list if database is not available (demo mode)
        return jsonify([])


@app.route('/api/call/<int:call_id>', methods=['GET'])
def get_call(call_id):
    """Get specific call details"""
    try:
        call_data = db.get_call_data(call_id)
        if call_data:
            # Convert datetime objects
            for key, value in call_data.items():
                if hasattr(value, 'isoformat'):
                    call_data[key] = value.isoformat()
            return jsonify(call_data)
        else:
            return jsonify({
                'error': 'Call not found'
            }), 404
    except Exception as e:
        logger.warning(f"Database not available: {str(e)}")
        # Return a mock response for demo mode
        return jsonify({
            'id': call_id,
            'phone_number': 'N/A',
            'status': 'completed',
            'message': 'Database not available - demo mode'
        })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        db_status = db.test_connection()
        return jsonify({
            'status': 'healthy',
            'database': 'connected' if db_status else 'disconnected',
            'twilio': 'configured' if voice_handler.client else 'not configured',
            'elevenlabs': 'configured' if elevenlabs_handler.client else 'not configured'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info(f"Starting Voice Call System on port {FLASK_PORT}")
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT, host='0.0.0.0')


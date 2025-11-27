"""
Main Flask application for Voice Call System
Handles API endpoints and webhooks
"""
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from voice_handler import VoiceHandler
from elevenlabs_handler import ElevenLabsHandler
from ocr_handler import OCRHandler
from database import Database
from config import FLASK_PORT, FLASK_DEBUG
from demo_mode import DemoMode

# Try to import PaddleOCR handler (optional dependency)
try:
    from paddleocr_handler import PaddleOCRHandler
    PADDLEOCR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PaddleOCR handler not available: {str(e)}")
    PaddleOCRHandler = None
    PADDLEOCR_AVAILABLE = False
import logging
import json
import os
import re

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
ocr_handler = OCRHandler()
paddleocr_handler = None
if PADDLEOCR_AVAILABLE and PaddleOCRHandler:
    try:
        paddleocr_handler = PaddleOCRHandler()
        logger.info("PaddleOCR handler initialized successfully")
    except Exception as e:
        logger.warning(f"PaddleOCR handler initialization failed: {str(e)}. PaddleOCR features will be unavailable.")
        paddleocr_handler = None
else:
    logger.info("PaddleOCR not available - install with: pip install paddleocr paddlepaddle")
demo_mode = DemoMode()

# Check if demo mode is enabled
DEMO_MODE = os.getenv('DEMO_MODE', 'false').lower() == 'true'


@app.route('/')
def index():
    """Serve the main dashboard"""
    return render_template('index.html')


@app.route('/ocr')
def ocr_page():
    """Serve the OCR page"""
    return render_template('ocr.html')


@app.route('/style.css')
def style_css():
    """Serve CSS file"""
    return send_from_directory('../frontend', 'style.css', mimetype='text/css')


@app.route('/app.js')
def app_js():
    """Serve JavaScript file"""
    return send_from_directory('../frontend', 'app.js', mimetype='application/javascript')


@app.route('/ocr.js')
def ocr_js():
    """Serve OCR JavaScript file"""
    return send_from_directory('../frontend', 'ocr.js', mimetype='application/javascript')


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


@app.route('/api/elevenlabs-voice-flow', methods=['POST'])
def elevenlabs_voice_flow():
    """
    Twilio webhook for ElevenLabs voice flow
    Connects Twilio call to ElevenLabs WebSocket
    """
    try:
        from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
        
        call_id = request.args.get('call_id') or request.form.get('call_id')
        agent_id = request.args.get('agent_id') or request.form.get('agent_id')
        
        logger.info(f"ElevenLabs voice flow webhook called - call_id={call_id}, agent_id={agent_id}")
        
        if not call_id:
            logger.error("No call_id provided in ElevenLabs voice flow webhook")
            response = VoiceResponse()
            response.say("Error: Call ID not found. Please try again.", voice='alice')
            response.hangup()
            return str(response), 200, {'Content-Type': 'text/xml'}
        
        # Get WebSocket URL from cache
        ws_url = elevenlabs_handler.questions_cache.get(f'{call_id}_ws_url')
        if not ws_url:
            # Try to get signed URL again, but fallback to direct URL if permission is missing
            try:
                import requests
                ws_url_response = requests.get(
                    'https://api.elevenlabs.io/v1/convai/conversation/get-signed-url',
                    headers={'xi-api-key': elevenlabs_handler.api_key},
                    params={'agent_id': agent_id or elevenlabs_handler.agent_id},
                    timeout=10
                )
                if ws_url_response.status_code == 200:
                    signed_url_data = ws_url_response.json()
                    ws_url = signed_url_data.get('signed_url')
                    if ws_url:
                        elevenlabs_handler.questions_cache[f'{call_id}_ws_url'] = ws_url
                elif ws_url_response.status_code == 401:
                    # Missing permissions - use direct URL for public agents
                    logger.warning("Cannot get signed URL due to missing permissions, using direct WebSocket URL")
                    ws_url = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id or elevenlabs_handler.agent_id}'
                    elevenlabs_handler.questions_cache[f'{call_id}_ws_url'] = ws_url
            except Exception as e:
                logger.warning(f"Error getting WebSocket URL: {str(e)}, using direct URL")
                ws_url = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id or elevenlabs_handler.agent_id}'
        
        if not ws_url:
            logger.error(f"No WebSocket URL available for call_id={call_id}")
            response = VoiceResponse()
            response.say("Error: Could not connect to voice agent. Please check your API key permissions.", voice='alice')
            response.hangup()
            return str(response), 200, {'Content-Type': 'text/xml'}
        
        # Get conversation context (questions) from cache
        conversation_context = elevenlabs_handler.questions_cache.get(f'{call_id}_context', '')
        logger.info(f"Conversation context for call_id={call_id}: {conversation_context[:200]}...")
        
        # IMPORTANT: ElevenLabs native Twilio integration
        # Instead of using Media Streams (complex), we'll use ElevenLabs' native integration
        # which requires connecting the Twilio call directly to ElevenLabs phone number
        
        # However, since we're making outbound calls via Twilio, we need to bridge it differently
        # For now, let's use a simpler approach: redirect to ElevenLabs phone number
        # OR use the WebSocket connection properly
        
        # Option 1: If you have ElevenLabs phone number configured in Twilio, use it directly
        # This requires setting up the ElevenLabs phone number in Twilio console
        
        # Option 2: Use Media Streams bridge (complex, requires WebSocket server)
        # For now, let's implement a basic version that at least connects
        
        response = VoiceResponse()
        
        # Try to get ElevenLabs phone number from cache
        phone_number_id = elevenlabs_handler.questions_cache.get(f'{call_id}_phone_id')
        
        # For now, let's use a simpler approach:
        # 1. Say a greeting
        # 2. Connect to ElevenLabs via their native integration
        # But since we're using Twilio for outbound, we need the bridge
        
        # Check if we should use native ElevenLabs integration
        # If ElevenLabs phone number is configured in Twilio, we can redirect there
        # Otherwise, we need the WebSocket bridge
        
        # The issue: The agent is connecting but not receiving the questions context
        # The questions are stored in cache but never sent to ElevenLabs
        
        # Solution: Since bridging Media Streams to WebSocket is complex,
        # let's use a workaround that sends the questions via Twilio's voice features
        # This is temporary until the full WebSocket bridge is implemented
        
        if conversation_context:
            # Extract questions from the context
            import re
            # Find all questions in the context
            questions_section = conversation_context.split("Ask the following questions")
            if len(questions_section) > 1:
                questions_text = questions_section[1].split("After each answer")[0].strip()
                # Extract individual questions
                question_matches = re.findall(r'Question \d+: (.+?)(?=Question \d+:|$)', questions_text, re.DOTALL)
                
                if question_matches:
                    response.say("Hello. I will ask you a few survey questions. Please answer yes or no to each one.", voice='alice')
                    response.pause(length=1)
                    
                    # Ask each question using Twilio's voice
                    for i, question in enumerate(question_matches, 1):
                        question_text = question.strip()
                        if question_text:
                            response.say(f"Question {i}: {question_text}", voice='alice')
                            response.pause(length=0.5)
                            
                            # Collect response
                            gather = response.gather(
                                input='speech dtmf',
                                timeout=10,
                                speech_timeout='auto',
                                action=f'{elevenlabs_handler.webhook_url}/api/process-answer?call_id={call_id}&q_num={i}',
                                method='POST',
                                num_digits=1
                            )
                            gather.say("Please say yes or no, or press 1 for yes, 2 for no.", voice='alice')
                            response.append(gather)
                            
                            # If no response, continue to next question
                            response.say("Moving to the next question.", voice='alice')
                    
                    response.say("Thank you for completing the survey. Goodbye.", voice='alice')
                else:
                    response.say("I'm sorry, I couldn't find the questions. Please try again later.", voice='alice')
            else:
                response.say("Error: Questions not found. Please try again.", voice='alice')
        else:
            response.say("Error: No conversation context available. Please try again.", voice='alice')
            logger.error(f"No conversation context found for call_id={call_id}")
        
        response.hangup()
        
        logger.info(f"Returning TwiML with questions for call_id={call_id}")
        logger.warning("Using Twilio-only voice solution. ElevenLabs WebSocket bridge not fully implemented yet.")
        return str(response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Error in ElevenLabs voice flow webhook: {str(e)}", exc_info=True)
        response = VoiceResponse()
        response.say("An error occurred connecting to the voice agent. Please try again later.", voice='alice')
        response.hangup()
        return str(response), 200, {'Content-Type': 'text/xml'}


@app.route('/api/elevenlabs-stream', methods=['GET', 'POST'])
def elevenlabs_stream():
    """
    WebSocket endpoint for bridging Twilio Media Streams to ElevenLabs
    This endpoint handles the WebSocket connection from Twilio Media Streams
    and bridges it to ElevenLabs WebSocket
    """
    try:
        # This endpoint should handle WebSocket upgrade
        # For now, return a simple response indicating the endpoint exists
        # Full WebSocket implementation requires async Flask or separate WebSocket server
        
        call_id = request.args.get('call_id')
        agent_id = request.args.get('agent_id')
        ws_url = request.args.get('ws_url')
        context = request.args.get('context', '')
        
        logger.info(f"ElevenLabs stream endpoint called - call_id={call_id}, agent_id={agent_id}")
        
        # TODO: Implement full WebSocket bridge
        # For now, this is a placeholder
        # The actual implementation requires:
        # 1. WebSocket upgrade handling
        # 2. Audio format conversion between Twilio and ElevenLabs
        # 3. Bidirectional audio streaming
        
        # For immediate solution, we'll use a different approach:
        # Instead of Media Streams, we can use Twilio's <Say> and <Gather>
        # to interact with the user, then send responses to ElevenLabs
        
        return jsonify({
            'status': 'endpoint_exists',
            'message': 'WebSocket bridge endpoint (implementation in progress)',
            'call_id': call_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error in elevenlabs-stream endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/elevenlabs-webhook', methods=['POST'])
def elevenlabs_webhook():
    """Webhook endpoint for ElevenLabs events"""
    try:
        # Get webhook data
        if request.is_json:
            webhook_data = request.json
        else:
            webhook_data = request.form.to_dict()
        
        # Log raw webhook data for debugging
        logger.info(f"ElevenLabs webhook received - Method: {request.method}, Content-Type: {request.content_type}")
        logger.info(f"Raw webhook data: {json.dumps(webhook_data, indent=2, default=str)}")
        
        # Verify webhook signature if secret is configured
        if elevenlabs_handler.webhook_secret:
            # Add signature verification logic here based on ElevenLabs docs
            # For now, we'll skip verification but log it
            logger.info("Webhook secret configured but verification not implemented yet")
        
        # Process webhook
        result = elevenlabs_handler.handle_webhook(webhook_data)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing ElevenLabs webhook: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/test-log-extraction', methods=['GET'])
def test_log_extraction():
    """Test endpoint to extract questions and answers from webhook log_id=2"""
    try:
        log_id = 2
        
        # Get webhook log data
        logger.info(f"Fetching webhook log data for log_id={log_id}")
        webhook_data_str = db.get_webhook_log_data(log_id)
        
        if not webhook_data_str:
            logger.error(f"No webhook data found for log_id={log_id}")
            return jsonify({
                'status': 'error',
                'message': f'No webhook data found for log_id={log_id}'
            }), 404
        
        # Parse JSON string
        try:
            if isinstance(webhook_data_str, str):
                data = json.loads(webhook_data_str)
            else:
                data = webhook_data_str
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing webhook data JSON: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Invalid JSON in webhook data: {str(e)}'
            }), 400
        
        logger.info(f"Successfully loaded webhook data for log_id={log_id}")
        logger.info(f"Webhook data keys: {list(data.keys())}")
        
        # Extract messages using the same logic as handle_webhook
        messages_data = data.get('data', {})
        messages = []
        
        if isinstance(messages_data, dict):
            # Check if there's a nested 'data' key
            inner_data = messages_data.get('data', {})
            if isinstance(inner_data, dict):
                # Try 'messages' first
                if 'messages' in inner_data:
                    messages = inner_data.get('messages', [])
                    logger.info(f"✅ Found messages in data.data.messages: {len(messages)} messages")
                # Try 'transcript' as alternative
                elif 'transcript' in inner_data:
                    transcript_data = inner_data.get('transcript', [])
                    if isinstance(transcript_data, list):
                        messages = transcript_data
                    elif isinstance(transcript_data, str):
                        messages = [{'role': 'user', 'message': transcript_data}]
                    logger.info(f"✅ Found transcript in data.data.transcript: {len(messages)} items")
            
            # Try messages directly in data
            if not messages:
                if 'messages' in messages_data:
                    messages = messages_data.get('messages', [])
                    logger.info(f"✅ Found messages in data.messages: {len(messages)} messages")
                elif 'transcript' in messages_data:
                    transcript_data = messages_data.get('transcript', [])
                    if isinstance(transcript_data, list):
                        messages = transcript_data
                    elif isinstance(transcript_data, str):
                        messages = [{'role': 'user', 'message': transcript_data}]
                    logger.info(f"✅ Found transcript in data.transcript: {len(messages)} items")
        
        # Fallback: try root level
        if not messages:
            if 'messages' in data:
                messages = data.get('messages', [])
                logger.info(f"✅ Found messages in root: {len(messages)} messages")
            elif 'transcript' in data:
                transcript_data = data.get('transcript', [])
                if isinstance(transcript_data, list):
                    messages = transcript_data
                elif isinstance(transcript_data, str):
                    messages = [{'role': 'user', 'message': transcript_data}]
                logger.info(f"✅ Found transcript in root: {len(messages)} items")
            elif 'transcription' in data:
                transcription_data = data.get('transcription', '')
                if isinstance(transcription_data, str) and transcription_data:
                    messages = [{'role': 'user', 'message': transcription_data}]
                    logger.info(f"✅ Found transcription in root: {len(transcription_data)} chars")
        
        if not messages:
            logger.warning(f"⚠️ No messages found in webhook data for log_id={log_id}")
            return jsonify({
                'status': 'error',
                'message': 'No messages/transcript found in webhook data',
                'log_id': log_id,
                'data_keys': list(data.keys())
            }), 404
        
        # Build full transcript and extract Q&A pairs
        full_transcript = []
        questions_and_answers = []
        question_num = 0
        current_question = None
        
        for msg in messages:
            # Handle different message formats
            if isinstance(msg, dict):
                role = msg.get('role', msg.get('speaker', 'unknown'))
                message_text = msg.get('message', msg.get('text', msg.get('content', '')))
            elif isinstance(msg, str):
                role = 'user'
                message_text = msg
            else:
                continue
            
            if message_text:
                full_transcript.append(f"{role.upper()}: {message_text}")
                
                # Extract questions and answers
                # Filter out confirmation questions and greetings to get only actual survey questions
                if role == 'agent' and message_text:
                    message_lower = message_text.lower().strip()
                    # Skip confirmation questions and greetings
                    is_confirmation = any(phrase in message_lower for phrase in [
                        'is that correct', 'you said', 'did i hear', 'confirm'
                    ])
                    is_greeting = any(phrase in message_lower for phrase in [
                        'how can i help', 'calling for', 'may i proceed', 'can i help'
                    ])
                    
                    # Check if this is an actual survey question (contains question mark or "yes or no")
                    if ('?' in message_text or 'yes or no' in message_lower) and not is_confirmation and not is_greeting:
                        # Clean question text by removing "Please answer yes or no only" and similar phrases
                        cleaned_question = message_text.strip()
                        # Remove common instruction phrases
                        phrases_to_remove = [
                            'please answer yes or no only',
                            'please answer yes or no',
                            'answer yes or no only',
                            'answer yes or no',
                            'yes or no only',
                            'yes or no'
                        ]
                        for phrase in phrases_to_remove:
                            # Remove phrase at the end (case insensitive)
                            if cleaned_question.lower().endswith(phrase.lower()):
                                cleaned_question = cleaned_question[:-len(phrase)].strip()
                                # Remove trailing punctuation if any
                                if cleaned_question and cleaned_question[-1] in ['.', ',', '?']:
                                    # Keep question mark, remove others
                                    if cleaned_question[-1] != '?':
                                        cleaned_question = cleaned_question[:-1].strip()
                            # Also check if phrase appears before question mark
                            elif phrase.lower() in cleaned_question.lower():
                                # Remove phrase and any surrounding punctuation
                                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                                cleaned_question = pattern.sub('', cleaned_question).strip()
                                # Clean up multiple spaces and trailing punctuation
                                cleaned_question = re.sub(r'\s+', ' ', cleaned_question).strip()
                                if cleaned_question and cleaned_question[-1] in ['.', ',']:
                                    cleaned_question = cleaned_question[:-1].strip()
                        
                        current_question = cleaned_question
                        question_num += 1
                        logger.info(f"📝 Actual Survey Question {question_num}: {current_question}")
                elif role == 'user' and message_text and current_question:
                    # This is an answer to the current question
                    answer = elevenlabs_handler._extract_answer(message_text)
                    qa_pair = {
                        'question_number': question_num,
                        'question': current_question,
                        'answer': answer,
                        'raw_answer': message_text.strip()
                    }
                    questions_and_answers.append(qa_pair)
                    logger.info(f"✅ Answer {question_num}: {answer} (raw: {message_text.strip()})")
                    current_question = None
        
        # Log summary
        logger.info(f"📊 Summary for log_id={log_id}:")
        logger.info(f"   Total messages: {len(messages)}")
        logger.info(f"   Actual survey questions found: {len(questions_and_answers)}")
        logger.info(f"   Full transcript length: {len('\\n'.join(full_transcript))} characters")
        
        # Log each Q&A pair
        logger.info("ACTUAL SURVEY QUESTIONS AND ANSWERS:")
        for qa in questions_and_answers:
            logger.info(f"   Q{qa['question_number']}: {qa['question']}")
            logger.info(f"   A{qa['question_number']}: {qa['answer']} (raw: {qa['raw_answer']})")
        
        logger.info(f"✅ Successfully extracted {len(questions_and_answers)} actual survey Q&A pairs from log_id={log_id}")
        
        # Return result (not saving to DB as requested)
        result = {
            'status': 'success',
            'log_id': log_id,
            'total_messages': len(messages),
            'questions_and_answers': questions_and_answers,
            'full_transcript': full_transcript,
            'transcript_text': '\n'.join(full_transcript)
        }
        
        logger.info(f"✅ Successfully extracted {len(questions_and_answers)} Q&A pairs from log_id={log_id}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error extracting questions and answers from log_id=2: {str(e)}", exc_info=True)
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


@app.route('/api/ocr/poppler-status', methods=['GET'])
def poppler_status():
    """Check poppler installation status"""
    try:
        import shutil
        import os
        import platform
        
        status = {
            'poppler_path': ocr_handler.poppler_path,
            'poppler_path_env': os.environ.get('POPPLER_PATH'),
            'pdftoppm_in_path': shutil.which('pdftoppm'),
            'system': platform.system(),
        }
        
        # Check common paths
        if platform.system() == 'Windows':
            common_paths = [
                r'C:\poppler\library\bin',
                r'C:\poppler\Library\bin',
                r'C:\poppler\bin',
                r'C:\Program Files\poppler\bin',
            ]
            status['checked_paths'] = {}
            for path in common_paths:
                normalized = os.path.normpath(path)
                exists = os.path.exists(normalized)
                pdftoppm_file = os.path.join(normalized, 'pdftoppm.exe')
                has_pdftoppm = os.path.exists(pdftoppm_file)
                status['checked_paths'][path] = {
                    'exists': exists,
                    'has_pdftoppm': has_pdftoppm,
                    'normalized': normalized
                }
        
        # Check if poppler_path has pdftoppm and DLLs
        if ocr_handler.poppler_path:
            pdftoppm_check = os.path.join(ocr_handler.poppler_path, 'pdftoppm.exe')
            status['poppler_path_valid'] = os.path.exists(pdftoppm_check)
            status['pdftoppm_path'] = pdftoppm_check if os.path.exists(pdftoppm_check) else None
            
            # Check for DLLs (critical for Windows)
            if platform.system() == 'Windows' and os.path.exists(ocr_handler.poppler_path):
                try:
                    files_in_dir = os.listdir(ocr_handler.poppler_path)
                    dll_files = [f for f in files_in_dir if f.lower().endswith('.dll')]
                    exe_files = [f for f in files_in_dir if f.lower().endswith('.exe')]
                    
                    status['files_in_bin'] = {
                        'dll_count': len(dll_files),
                        'exe_count': len(exe_files),
                        'dll_files': dll_files[:10],  # First 10 DLLs
                        'exe_files': exe_files[:10],  # First 10 EXEs
                    }
                    
                    # Check for critical DLLs
                    critical_dlls = ['poppler.dll', 'poppler-cpp.dll', 'libpoppler.dll']
                    status['critical_dlls'] = {}
                    for dll in critical_dlls:
                        dll_path = os.path.join(ocr_handler.poppler_path, dll)
                        status['critical_dlls'][dll] = os.path.exists(dll_path)
                    
                    # Check if any DLLs exist
                    status['has_any_dlls'] = len(dll_files) > 0
                    if not status['has_any_dlls']:
                        status['dll_warning'] = "No DLL files found! Poppler executables require DLLs to run. You may need to re-download poppler or install Visual C++ Redistributables."
                    
                except Exception as e:
                    status['files_in_bin'] = {'error': str(e)}
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error checking poppler status: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500


# OCR Endpoints
@app.route('/api/ocr/upload', methods=['POST'])
def ocr_upload():
    """Upload and process OCR document"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not ocr_handler.allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Supported: PDF, PNG, JPG, JPEG'
            }), 400
        
        # Get file info
        file_name = file.filename
        file_ext = file_name.rsplit('.', 1)[1].lower() if '.' in file_name else ''
        file_size = len(file.read())
        file.seek(0)  # Reset file pointer
        
        # Create document record in database
        try:
            document_id = db.create_ocr_document(file_name, file_ext, file_size)
            logger.info(f"OCR document record created: ID={document_id}")
        except Exception as db_error:
            logger.error(f"Database error creating OCR document: {str(db_error)}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}'
            }), 500
        
        # Update status to processing
        try:
            db.update_ocr_document(document_id, status='processing')
        except Exception as e:
            logger.warning(f"Could not update document status: {str(e)}")
        
        # Process document in background (for now, synchronous)
        try:
            result = ocr_handler.process_uploaded_document(file, file_name)
            
            # Update document with extracted data
            db.update_ocr_document(
                document_id=document_id,
                document_text=result['document_text'],
                extracted_data=result['extracted_data'],
                parameters_list=result['parameters_list'],
                refined_text=result['refined_text'],
                status='completed'
            )
            
            logger.info(f"OCR document processed successfully: ID={document_id}")
            
            return jsonify({
                'success': True,
                'document_id': document_id,
                'message': 'Document processed successfully'
            })
        except Exception as process_error:
            logger.error(f"Error processing OCR document: {str(process_error)}")
            # Update status to error
            try:
                db.update_ocr_document(document_id, status='error')
            except:
                pass
            
            return jsonify({
                'success': False,
                'error': f'Error processing document: {str(process_error)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error in OCR upload: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ocr/paddleocr-upload', methods=['POST'])
def paddleocr_upload():
    """Upload and process OCR document using PaddleOCR"""
    try:
        logger.info("PaddleOCR upload endpoint called")
        if paddleocr_handler is None:
            logger.warning("PaddleOCR handler is None - not available")
            return jsonify({
                'success': False,
                'error': 'PaddleOCR is not available. Please install it using: pip install paddleocr paddlepaddle'
            }), 503
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not paddleocr_handler.allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type. Supported: PDF, PNG, JPG, JPEG'
            }), 400
        
        # Get file info
        file_name = file.filename
        file_ext = file_name.rsplit('.', 1)[1].lower() if '.' in file_name else ''
        file_size = len(file.read())
        file.seek(0)  # Reset file pointer
        
        # Create document record in database
        try:
            document_id = db.create_ocr_document(file_name, file_ext, file_size)
            logger.info(f"PaddleOCR document record created: ID={document_id}")
        except Exception as db_error:
            logger.error(f"Database error creating PaddleOCR document: {str(db_error)}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}'
            }), 500
        
        # Update status to processing
        try:
            db.update_ocr_document(document_id, status='processing')
        except Exception as e:
            logger.warning(f"Could not update document status: {str(e)}")
        
        # Process document with PaddleOCR
        try:
            result = paddleocr_handler.process_uploaded_document(file, file_name)
            
            # Update document with extracted data
            db.update_ocr_document(
                document_id=document_id,
                document_text=result['document_text'],
                extracted_data=result['extracted_data'],
                parameters_list=result['parameters_list'],
                refined_text=result['refined_text'],
                status='completed'
            )
            
            logger.info(f"PaddleOCR document processed successfully: ID={document_id}")
            
            return jsonify({
                'success': True,
                'document_id': document_id,
                'message': 'Document processed successfully with PaddleOCR'
            })
        except Exception as process_error:
            logger.error(f"Error processing PaddleOCR document: {str(process_error)}")
            # Update status to error
            try:
                db.update_ocr_document(document_id, status='error')
            except:
                pass
            
            return jsonify({
                'success': False,
                'error': f'Error processing document: {str(process_error)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error in PaddleOCR upload: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ocr/documents', methods=['GET'])
def get_ocr_documents():
    """Get all OCR documents"""
    try:
        documents = db.get_all_ocr_documents()
        # Convert datetime objects to strings
        for doc in documents:
            for key, value in doc.items():
                if hasattr(value, 'isoformat'):
                    doc[key] = value.isoformat()
        logger.info(f"Successfully retrieved {len(documents)} OCR documents from database")
        return jsonify(documents)
    except Exception as e:
        logger.error(f"Error getting OCR documents from database: {str(e)}", exc_info=True)
        return jsonify([])


@app.route('/api/ocr/document/<int:document_id>', methods=['GET'])
def get_ocr_document(document_id):
    """Get specific OCR document details"""
    try:
        document_data = db.get_ocr_document(document_id)
        if document_data:
            # Convert datetime objects
            for key, value in document_data.items():
                if hasattr(value, 'isoformat'):
                    document_data[key] = value.isoformat()
            return jsonify(document_data)
        else:
            return jsonify({
                'error': 'Document not found'
            }), 404
    except Exception as e:
        logger.error(f"Error getting OCR document: {str(e)}", exc_info=True)
        return jsonify({
            'error': f'Error retrieving document: {str(e)}'
        }), 500


if __name__ == '__main__':
    logger.info(f"Starting Voice Call System on port {FLASK_PORT}")
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT, host='0.0.0.0')


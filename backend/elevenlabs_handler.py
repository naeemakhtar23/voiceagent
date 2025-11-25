"""
ElevenLabs Voice Agent handler
Manages voice calls using ElevenLabs Voice Agent API
Uses Cloudflare Tunnel for webhook URLs
"""
from elevenlabs.client import ElevenLabs
from config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, ELEVENLABS_WEBHOOK_SECRET, WEBHOOK_BASE_URL, ELEVENLABS_CALL_ENDPOINT
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
from database import Database
from twilio.rest import Client as TwilioClient
import json
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElevenLabsHandler:
    def __init__(self):
        self.api_key = ELEVENLABS_API_KEY
        self.agent_id = ELEVENLABS_AGENT_ID
        self.webhook_secret = ELEVENLABS_WEBHOOK_SECRET
        self.webhook_url = WEBHOOK_BASE_URL  # This will be your Cloudflare Tunnel URL
        
        # In-memory cache for questions (used when database is unavailable)
        self.questions_cache = {}
        
        # Initialize database (optional - continue if fails)
        try:
            self.db = Database()
            self.db_available = True
        except Exception as e:
            logger.warning(f"Database not available, continuing without DB: {str(e)}")
            self.db = None
            self.db_available = False
        
        # Initialize ElevenLabs client
        if self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"ElevenLabs client initialization failed: {str(e)}")
                self.client = None
        else:
            logger.warning("ElevenLabs API key not configured")
            self.client = None
        
        # Initialize Twilio client for call initiation (ElevenLabs requires Twilio for outbound calls)
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                self.twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                self.twilio_phone = TWILIO_PHONE_NUMBER
            except Exception as e:
                logger.warning(f"Twilio client initialization failed: {str(e)}")
                self.twilio_client = None
        else:
            logger.warning("Twilio credentials not configured - required for ElevenLabs outbound calls")
            self.twilio_client = None
    
    def initiate_call(self, to_number, call_id, questions):
        """
        Initiate a voice call using ElevenLabs Voice Agent API directly
        
        This method uses ElevenLabs' phone number API to make outbound calls.
        The agent must have a phone number assigned to it.
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured.")
        
        if not self.agent_id:
            raise Exception("ElevenLabs Agent ID not configured.")
        
        try:
            # Store questions in cache
            call_id_str = str(call_id)
            self.questions_cache[call_id_str] = questions
            if call_id_str.isdigit():
                self.questions_cache[int(call_id_str)] = questions
            if call_id != call_id_str and call_id not in self.questions_cache:
                self.questions_cache[call_id] = questions
            logger.info(f"Questions cached for ElevenLabs call_id {call_id_str}: {len(questions)} questions")
            
            # Try to store questions in database
            if self.db_available and self.db:
                try:
                    for idx, question in enumerate(questions):
                        self.db.save_question(call_id, question.get('text', ''), idx)
                except Exception as db_error:
                    logger.warning(f"Database not available, using cache: {str(db_error)}")
            
            # Format questions for ElevenLabs agent
            questions_text = "\n".join([f"Question {i+1}: {q.get('text', '')}" for i, q in enumerate(questions)])
            conversation_context = f"""You are conducting a survey call. Ask the following questions one by one and wait for yes/no answers:
            
{questions_text}

After each answer, acknowledge it and move to the next question. When all questions are answered, thank the caller and end the call."""
            
            # Store context in cache
            self.questions_cache[f'{call_id_str}_context'] = conversation_context
            
            # Get the ElevenLabs phone number assigned to the agent
            phone_number_id = None
            elevenlabs_phone_number = None
            
            try:
                phone_numbers_response = requests.get(
                    'https://api.elevenlabs.io/v1/convai/phone-numbers',
                    headers={'xi-api-key': self.api_key},
                    timeout=10
                )
                
                if phone_numbers_response.status_code == 200:
                    phone_numbers = phone_numbers_response.json()
                    # Find phone number assigned to this agent
                    for pn in phone_numbers:
                        assigned_agent = pn.get('assigned_agent', {})
                        if assigned_agent.get('agent_id') == self.agent_id:
                            elevenlabs_phone_number = pn.get('phone_number')
                            phone_number_id = pn.get('phone_number_id')
                            logger.info(f"Found ElevenLabs phone number {elevenlabs_phone_number} (ID: {phone_number_id}) for agent {self.agent_id}")
                            break
                    
                    if not phone_number_id:
                        # If no phone number found for this agent, try using the first available phone number
                        if phone_numbers and len(phone_numbers) > 0:
                            phone_number_id = phone_numbers[0].get('phone_number_id')
                            elevenlabs_phone_number = phone_numbers[0].get('phone_number')
                            logger.warning(f"No phone number assigned to agent {self.agent_id}, using first available: {elevenlabs_phone_number}")
                        else:
                            raise Exception("No phone numbers found in your ElevenLabs account. Please assign a phone number to your agent in the ElevenLabs dashboard.")
                else:
                    error_msg = phone_numbers_response.text[:200] if phone_numbers_response.text else "Unknown error"
                    logger.error(f"Failed to fetch phone numbers: Status {phone_numbers_response.status_code}, Error: {error_msg}")
                    raise Exception(f"Failed to fetch phone numbers from ElevenLabs: {error_msg}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching phone numbers: {str(e)}")
                raise Exception(f"Failed to connect to ElevenLabs API: {str(e)}")
            
            if not phone_number_id:
                raise Exception("No phone number found for this agent. Please assign a phone number to your agent in the ElevenLabs dashboard.")
            
            # Store phone number ID in cache
            self.questions_cache[f'{call_id_str}_phone_id'] = phone_number_id
            
            # IMPORTANT: ElevenLabs does NOT support outbound calls via REST API
            # Based on diagnostic testing, all REST endpoints return 404/405
            # The correct approach is to use Twilio to make the outbound call,
            # then bridge it to ElevenLabs via WebSocket
            
            if not self.twilio_client:
                raise Exception(
                    "Twilio is required for outbound calls with ElevenLabs. "
                    "ElevenLabs phone numbers are for receiving calls only. "
                    "To make outbound calls, we use Twilio to initiate the call "
                    "and then connect it to ElevenLabs via WebSocket. "
                    "Please configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in your .env file."
                )
            
            # Get ElevenLabs WebSocket URL for the agent
            try:
                # Get signed WebSocket URL from ElevenLabs (required for authentication)
                ws_url_response = requests.get(
                    'https://api.elevenlabs.io/v1/convai/conversation/get-signed-url',
                    headers={'xi-api-key': self.api_key},
                    params={'agent_id': self.agent_id},
                    timeout=10
                )
                
                if ws_url_response.status_code == 200:
                    signed_url_data = ws_url_response.json()
                    websocket_url = signed_url_data.get('signed_url')
                    if not websocket_url:
                        websocket_url = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={self.agent_id}'
                    logger.info(f"Got signed WebSocket URL for agent {self.agent_id}")
                elif ws_url_response.status_code == 401:
                    error_detail = ws_url_response.json() if ws_url_response.text else {}
                    error_msg = error_detail.get('detail', {}).get('message', 'Authentication failed')
                    logger.warning(f"Could not get signed URL due to missing permissions: {error_msg}")
                    logger.info("Attempting to use direct WebSocket URL (for public agents)")
                    websocket_url = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={self.agent_id}'
                    logger.warning("Using direct WebSocket URL - this may fail if agent is private")
                else:
                    websocket_url = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={self.agent_id}'
                    logger.warning(f"Could not get signed URL (Status: {ws_url_response.status_code}), using direct URL")
            except Exception as e:
                logger.warning(f"Error getting WebSocket URL: {str(e)}, using direct URL")
                websocket_url = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={self.agent_id}'
            
            # Store context and WebSocket URL in cache for the webhook to use
            self.questions_cache[f'{call_id_str}_context'] = conversation_context
            self.questions_cache[f'{call_id_str}_ws_url'] = websocket_url
            
            # Use Twilio to initiate the outbound call
            # The webhook will connect the Twilio call to ElevenLabs WebSocket
            try:
                logger.info(f"Initiating Twilio call to {to_number}, will bridge to ElevenLabs agent {self.agent_id}")
                
                call = self.twilio_client.calls.create(
                    to=to_number,
                    from_=self.twilio_phone,
                    url=f'{self.webhook_url}/api/elevenlabs-voice-flow?call_id={call_id}&agent_id={self.agent_id}',
                    method='POST',
                    status_callback=f'{self.webhook_url}/api/call-status',
                    status_callback_method='POST'
                )
                
                logger.info(f"Twilio call initiated: SID={call.sid}, To={to_number}, From={self.twilio_phone}")
                logger.info(f"Webhook URL: {self.webhook_url}/api/elevenlabs-voice-flow")
                logger.info(f"ElevenLabs WebSocket: {websocket_url[:50]}...")
                
                return call.sid
                
            except Exception as twilio_error:
                logger.error(f"Error initiating Twilio call: {str(twilio_error)}")
                raise Exception(f"Failed to initiate call via Twilio: {str(twilio_error)}")
            
        except Exception as e:
            logger.error(f"Error initiating ElevenLabs call: {str(e)}")
            raise
    
    def handle_webhook(self, webhook_data):
        """
        Handle webhook events from ElevenLabs
        Events: call_started, call_ended, transcription, etc.
        """
        try:
            # Handle both JSON and form data
            if isinstance(webhook_data, dict):
                data = webhook_data
            else:
                data = webhook_data.to_dict() if hasattr(webhook_data, 'to_dict') else {}
            
            event_type = data.get('event_type') or data.get('eventType') or data.get('type')
            metadata = data.get('metadata', {}) or data.get('meta', {})
            call_id = metadata.get('call_id') or metadata.get('callId') or data.get('call_id') or data.get('callId')
            
            logger.info(f"ElevenLabs webhook received via Cloudflare: event={event_type}, call_id={call_id}")
            
            if event_type == 'call_started' or event_type == 'call.started':
                # Update call status in database
                if self.db_available and self.db and call_id:
                    try:
                        self.db.update_call_status(call_id, 'in-progress')
                    except Exception as db_error:
                        logger.warning(f"Could not update call status: {str(db_error)}")
            
            elif event_type == 'call_ended' or event_type == 'call.ended':
                # Mark call as completed
                if self.db_available and self.db and call_id:
                    try:
                        self.db.complete_call(call_id)
                    except Exception as db_error:
                        logger.warning(f"Could not complete call: {str(db_error)}")
                
                # Clean up cache
                if call_id and str(call_id) in self.questions_cache:
                    del self.questions_cache[str(call_id)]
            
            elif event_type == 'transcription' or event_type == 'transcription.completed':
                # Process transcription and extract answers
                transcription = data.get('transcription', {}) or data.get('data', {})
                text = transcription.get('text', '') or transcription.get('transcript', '') or data.get('text', '')
                
                # Extract yes/no answers from transcription
                answer = self._extract_answer(text)
                
                if call_id and answer and text:
                    question_num = metadata.get('question_num', 0) or metadata.get('questionNum', 0) or data.get('question_num', 0)
                    if self.db_available and self.db:
                        try:
                            self.db.save_answer(
                                call_id=call_id,
                                question_num=question_num,
                                answer=answer,
                                confidence=0.8,
                                raw_response=text
                            )
                        except Exception as db_error:
                            logger.warning(f"Could not save answer: {str(db_error)}")
            
            return {'status': 'ok'}
            
        except Exception as e:
            logger.error(f"Error handling ElevenLabs webhook: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def _extract_answer(self, text):
        """Extract yes/no answer from transcription text"""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        yes_keywords = ['yes', 'yeah', 'yep', 'correct', 'right', 'sure', 'okay', 'ok', 'yup', 'affirmative']
        no_keywords = ['no', 'nope', 'nah', 'incorrect', 'wrong', 'negative']
        
        if any(word in text_lower for word in yes_keywords):
            return 'yes'
        elif any(word in text_lower for word in no_keywords):
            return 'no'
        else:
            return 'unclear'

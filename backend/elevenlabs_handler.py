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
            
            # IMPORTANT: Use ElevenLabs' native Twilio outbound call endpoint
            # This is the correct endpoint for making outbound calls via Twilio integration
            # Endpoint: /v1/convai/twilio/outbound-call
            try:
                logger.info(f"Initiating ElevenLabs outbound call via Twilio integration")
                logger.info(f"Agent ID: {self.agent_id}, Phone Number ID: {phone_number_id}, To: {to_number}")
                
                # Prepare client data with questions for the agent
                # This data will be available to the agent during the conversation
                client_data = {
                    'call_id': call_id_str,
                    'questions': questions,
                    'questions_text': questions_text,
                    'conversation_context': conversation_context
                }
                
                # Use the correct ElevenLabs Twilio outbound endpoint
                outbound_url = 'https://api.elevenlabs.io/v1/convai/twilio/outbound-call'
                
                payload = {
                    'agent_id': self.agent_id,
                    'agent_phone_number_id': phone_number_id,  # This is the imported Twilio number ID in ElevenLabs
                    'to_number': to_number,
                    'conversation_initiation_client_data': client_data  # Pass questions to agent
                }
                
                headers = {
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json'
                }
                
                logger.info(f"Calling ElevenLabs outbound endpoint: {outbound_url}")
                logger.info(f"Payload: {json.dumps(payload, indent=2)}")
                
                response = requests.post(outbound_url, headers=headers, json=payload, timeout=15)
                
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                response_text = response.text[:1000] if response.text else "No response body"
                logger.info(f"Response body: {response_text}")
                
                if response.status_code in [200, 201, 202]:
                    try:
                        result = response.json()
                        conversation_id = result.get('conversation_id')
                        call_sid = result.get('call_sid')
                        
                        logger.info(f"✅ ElevenLabs outbound call initiated successfully!")
                        logger.info(f"Conversation ID: {conversation_id}, Call SID: {call_sid}")
                        
                        # Store conversation ID and call SID for webhook tracking
                        self.questions_cache[f'{call_id_str}_conversation_id'] = conversation_id
                        self.questions_cache[f'{call_id_str}_call_sid'] = call_sid
                        self.questions_cache[f'{call_id_str}_context'] = conversation_context
                        
                        # Return call identifier (prefer call_sid, then conversation_id, then our call_id)
                        return call_sid or conversation_id or call_id_str
                    except json.JSONDecodeError:
                        # Response might not be JSON, but status is success
                        logger.info(f"Call initiated (non-JSON response), status: {response.status_code}")
                        return call_id_str
                elif response.status_code == 401:
                    error_detail = response_text
                    raise Exception(f"Authentication failed (401): {error_detail}. Check your API key and permissions.")
                elif response.status_code == 403:
                    error_detail = response_text
                    raise Exception(f"Permission denied (403): {error_detail}. Check your API key has 'convai_write' permission.")
                elif response.status_code == 404:
                    error_detail = response_text
                    raise Exception(f"Endpoint not found (404): {error_detail}. Verify the endpoint URL is correct.")
                elif response.status_code == 422:
                    error_detail = response_text
                    raise Exception(f"Validation error (422): {error_detail}. Check that agent_id and agent_phone_number_id are correct.")
                else:
                    error_detail = response_text
                    error_msg = f"ElevenLabs API returned {response.status_code}: {error_detail}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error calling ElevenLabs outbound endpoint: {str(e)}")
                raise Exception(f"Failed to connect to ElevenLabs API: {str(e)}")
            except Exception as e:
                logger.error(f"Error initiating ElevenLabs outbound call: {str(e)}")
                raise
            
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

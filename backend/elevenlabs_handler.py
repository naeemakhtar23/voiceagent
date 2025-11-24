"""
ElevenLabs Voice Agent handler
Manages voice calls using ElevenLabs Voice Agent API
Uses Cloudflare Tunnel for webhook URLs
"""
from elevenlabs.client import ElevenLabs
from config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, ELEVENLABS_WEBHOOK_SECRET, WEBHOOK_BASE_URL
from database import Database
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
    
    def initiate_call(self, to_number, call_id, questions):
        """Initiate a voice call using ElevenLabs Voice Agent API"""
        if not self.client:
            raise Exception("ElevenLabs client not initialized. Check API key.")
        
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
            
            # Initiate call via ElevenLabs API
            # Note: The actual API method may vary - adjust based on ElevenLabs SDK version
            try:
                # Try different possible API structures
                if hasattr(self.client, 'voice_agent'):
                    # Newer API structure
                    call_response = self.client.voice_agent.create_call(
                        agent_id=self.agent_id,
                        phone_number=to_number,
                        context=conversation_context,
                        webhook_url=f'{self.webhook_url}/api/elevenlabs-webhook',
                        metadata={
                            'call_id': str(call_id),
                            'questions': json.dumps(questions)
                        }
                    )
                elif hasattr(self.client, 'calls'):
                    # Alternative API structure
                    call_response = self.client.calls.create(
                        agent_id=self.agent_id,
                        phone_number=to_number,
                        context=conversation_context,
                        webhook_url=f'{self.webhook_url}/api/elevenlabs-webhook',
                        metadata={
                            'call_id': str(call_id),
                            'questions': json.dumps(questions)
                        }
                    )
                else:
                    # Direct API call using requests if SDK doesn't have the method
                    import requests
                    headers = {
                        'xi-api-key': self.api_key,
                        'Content-Type': 'application/json'
                    }
                    payload = {
                        'agent_id': self.agent_id,
                        'phone_number': to_number,
                        'context': conversation_context,
                        'webhook_url': f'{self.webhook_url}/api/elevenlabs-webhook',
                        'metadata': {
                            'call_id': str(call_id),
                            'questions': json.dumps(questions)
                        }
                    }
                    response = requests.post(
                        'https://api.elevenlabs.io/v1/voice-agent/calls',
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    call_response = response.json()
                
                logger.info(f"ElevenLabs call initiated via Cloudflare Tunnel: Call ID={call_id}, To={to_number}, Webhook={self.webhook_url}/api/elevenlabs-webhook")
                return call_response.get('call_id') or call_response.get('id') or str(call_id)
                
            except AttributeError as e:
                logger.error(f"ElevenLabs API structure not recognized: {str(e)}")
                raise Exception(f"ElevenLabs API method not found. Please check SDK version and API documentation.")
            except Exception as api_error:
                logger.error(f"Error calling ElevenLabs API: {str(api_error)}")
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

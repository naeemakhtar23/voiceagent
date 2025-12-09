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
import re
import hmac
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of questions for the agent to ask (passed dynamically)
LIST_OF_QUESTIONS = [
    "Has an Enduring Power of Attorney been enacted for this client?",
    "Has a Do Not Resuscitate (DNR) order been discussed with the client?",
    "Has the client's family/whānau been informed about the client's CPR wishes?",
    "Does the client identify with any iwi or hapū?",
    "Has the client been offered cultural support, and did they accept or decline it?"
]


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
            
            # Update form submission tool with actual number of questions
            num_questions = len(questions)
            if num_questions > 0:
                try:
                    self.create_form_submission_tool(self.agent_id, num_questions)
                    logger.info(f"✅ Updated form submission tool with {num_questions} question properties")
                except Exception as tool_error:
                    logger.warning(f"Could not update form submission tool (continuing anyway): {str(tool_error)}")
            
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
                        # Store both forward (call_id -> conversation_id) and reverse (conversation_id -> call_id) mappings
                        self.questions_cache[f'{call_id_str}_conversation_id'] = conversation_id
                        self.questions_cache[f'{call_id_str}_call_sid'] = call_sid
                        self.questions_cache[f'{call_id_str}_context'] = conversation_context
                        
                        # Reverse mapping: conversation_id -> call_id (for webhook lookup)
                        if conversation_id:
                            self.questions_cache[f'conv_{conversation_id}_call_id'] = call_id_str
                            logger.info(f"Stored reverse mapping: conversation_id={conversation_id} -> call_id={call_id_str}")
                        
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
        Events: call_started, call_ended, transcription, post_call_transcription, etc.
        """
        # Store original webhook data for logging
        original_webhook_data = webhook_data
        log_id = None
        error_message = None
        
        try:
            # Handle both JSON and form data
            if isinstance(webhook_data, dict):
                data = webhook_data
            else:
                data = webhook_data.to_dict() if hasattr(webhook_data, 'to_dict') else {}
            
            # Log full webhook data for debugging (truncated in terminal)
            webhook_json_str = json.dumps(data, indent=2, default=str)
            logger.info(f"Webhook data received (first 1000 chars): {webhook_json_str[:1000]}...")
            
            event_type = data.get('event_type') or data.get('eventType') or data.get('type') or data.get('event')
            metadata = data.get('metadata', {}) or data.get('meta', {}) or {}
            
            # Extract identifiers early for logging
            conversation_id = None
            call_id = None
            call_sid = None
            
            # Try to extract conversation_id early for logging
            nested_data = data.get('data', {})
            if isinstance(nested_data, dict):
                conv_init_data = nested_data.get('conversation_initiation_client_data', {})
                if isinstance(conv_init_data, dict):
                    # Log the conversation_initiation_client_data to debug
                    logger.info(f"📋 conversation_initiation_client_data keys: {list(conv_init_data.keys())}")
                    if 'override_first_message' in conv_init_data:
                        first_msg = conv_init_data.get('override_first_message', '')
                        logger.info(f"✅ Found override_first_message in conversation_initiation_client_data: {first_msg[:100]}...")
                    if 'override_prompt' in conv_init_data:
                        override_prompt = conv_init_data.get('override_prompt', '')
                        logger.info(f"✅ Found override_prompt in conversation_initiation_client_data: {len(override_prompt)} chars, preview: {override_prompt[:150]}...")
                    if 'questions' in conv_init_data:
                        questions = conv_init_data.get('questions', [])
                        logger.info(f"✅ Found questions in conversation_initiation_client_data: {len(questions)} questions")
                        if questions and len(questions) > 0:
                            logger.info(f"   First question: {questions[0].get('text', 'N/A')[:100]}")
                    if 'dynamic_variables' in conv_init_data:
                        dyn_vars = conv_init_data.get('dynamic_variables', {})
                        logger.info(f"✅ Found dynamic_variables: {list(dyn_vars.keys())}")
                        if 'questions' in dyn_vars:
                            logger.info(f"   dynamic_variables.questions exists (JSON string)")
                        if 'question_list' in dyn_vars:
                            logger.info(f"   dynamic_variables.question_list exists (JSON string array)")
                        if isinstance(dyn_vars, dict):
                            conversation_id = dyn_vars.get('system__conversation_id')
            
            # Fallback to other locations
            if not conversation_id:
                conversation_id = (
                    data.get('conversation_id') or 
                    data.get('conversationId') or 
                    metadata.get('conversation_id') or 
                    metadata.get('conversationId') or
                    (data.get('conversation', {}).get('id') if isinstance(data.get('conversation'), dict) else None)
                )
            
            call_sid = (
                metadata.get('call_sid') or 
                metadata.get('callSid') or 
                data.get('call_sid') or 
                data.get('callSid') or
                data.get('sid')
            )
            
            # Save complete webhook response to database BEFORE processing
            # This ensures we capture the full data even if processing fails
            if self.db_available and self.db:
                try:
                    log_id = self.db.save_webhook_log(
                        event_type=event_type,
                        conversation_id=conversation_id,
                        call_id=None,  # Will be updated after we find it
                        call_sid=call_sid,
                        webhook_data=data,  # Save the parsed data dict
                        processed_successfully=False,  # Will update to True at end if successful
                        error_message=None
                    )
                    logger.info(f"✅ Saved webhook to logs table: log_id={log_id}, event_type={event_type}")
                except Exception as log_error:
                    logger.warning(f"Could not save webhook to logs table: {str(log_error)}")
                    # Continue processing even if logging fails
            
            # Try multiple ways to get call/conversation identifier (if not already found)
            # The webhook structure has conversation_id in nested locations
            # First check nested structure: data.data.conversation_initiation_client_data.dynamic_variables.system__conversation_id
            
            # Check nested structure first (most common for post_call_transcription)
            if not conversation_id:
                nested_data = data.get('data', {})
                if isinstance(nested_data, dict):
                    conv_init_data = nested_data.get('conversation_initiation_client_data', {})
                    if isinstance(conv_init_data, dict):
                        dyn_vars = conv_init_data.get('dynamic_variables', {})
                        if isinstance(dyn_vars, dict):
                            conversation_id = dyn_vars.get('system__conversation_id')
                            if conversation_id:
                                logger.info(f"✅ Found conversation_id in nested structure: {conversation_id}")
            
            # Fallback to other locations if not found
            if not conversation_id:
                conversation_id = (
                    data.get('conversation_id') or 
                    data.get('conversationId') or 
                    metadata.get('conversation_id') or 
                    metadata.get('conversationId') or
                    (data.get('conversation', {}).get('id') if isinstance(data.get('conversation'), dict) else None) or
                    (data.get('conversation_initiation_client_data', {}).get('dynamic_variables', {}).get('system__conversation_id') if isinstance(data.get('conversation_initiation_client_data'), dict) else None)
                )
            
            # Get call_id from metadata/data (but don't use conversation_id as fallback yet)
            call_id = (
                metadata.get('call_id') or 
                metadata.get('callId') or 
                data.get('call_id') or 
                data.get('callId')
            )
            
            # Also try to get call_sid from webhook (might be different from conversation_id)
            call_sid = (
                metadata.get('call_sid') or 
                metadata.get('callSid') or 
                data.get('call_sid') or 
                data.get('callSid') or
                data.get('sid')
            )
            
            # If we have conversation_id but not call_id, try to find it in cache
            if conversation_id and not call_id:
                # Try reverse mapping first (faster)
                reverse_key = f'conv_{conversation_id}_call_id'
                if reverse_key in self.questions_cache:
                    call_id = self.questions_cache[reverse_key]
                    logger.info(f"Found call_id {call_id} from conversation_id {conversation_id} via reverse mapping")
                else:
                    # Fallback: search cache for conversation_id to find our internal call_id
                    for key, value in self.questions_cache.items():
                        if isinstance(key, str) and key.endswith('_conversation_id') and value == conversation_id:
                            # Extract call_id from cache key (e.g., "12345_conversation_id" -> "12345")
                            call_id = key.replace('_conversation_id', '')
                            logger.info(f"Found call_id {call_id} from conversation_id {conversation_id} in cache")
                            # Store reverse mapping for future use
                            self.questions_cache[f'conv_{conversation_id}_call_id'] = call_id
                            break
            
            # If still no call_id but we have call_sid, try database lookup
            if not call_id and call_sid and self.db_available and self.db:
                try:
                    db_call_id = self.db.get_call_id_by_sid(call_sid)
                    if db_call_id:
                        call_id = db_call_id
                        logger.info(f"✅ Found call_id {call_id} from call_sid {call_sid} via database lookup")
                        # Store in cache for future use
                        self.questions_cache[f'sid_{call_sid}_call_id'] = call_id
                except Exception as db_lookup_error:
                    logger.warning(f"Could not look up call_id by call_sid: {str(db_lookup_error)}")
            
            # If still no call_id but we have conversation_id, try using it as call_sid for database lookup
            if not call_id and conversation_id and self.db_available and self.db:
                try:
                    db_call_id = self.db.get_call_id_by_sid(conversation_id)
                    if db_call_id:
                        call_id = db_call_id
                        logger.info(f"✅ Found call_id {call_id} from conversation_id {conversation_id} via database lookup (as call_sid)")
                        # Store in cache for future use
                        self.questions_cache[f'conv_{conversation_id}_call_id'] = call_id
                except Exception as db_lookup_error:
                    logger.warning(f"Could not look up call_id by conversation_id: {str(db_lookup_error)}")
            
            # Validate that call_id is numeric (database expects INT)
            # Store original value for logging purposes
            db_call_id = None
            if call_id:
                try:
                    # Try to convert to int - if it works, it's a valid database ID
                    db_call_id = int(call_id)
                    call_id = db_call_id  # Use the integer version
                except (ValueError, TypeError):
                    # call_id is not numeric (probably conversation_id string)
                    # Keep it for logging but don't use for database queries
                    logger.warning(f"call_id '{call_id}' is not numeric - will use for logging only, not database queries")
                    db_call_id = None
                    # Keep original call_id string for logging purposes
                    original_call_id_string = call_id
                    call_id = None  # Set to None so we don't try database operations
            
            logger.info(f"ElevenLabs webhook received: event={event_type}, conversation_id={conversation_id}, call_id={call_id}, db_call_id={db_call_id}")
            
            # Update webhook log with call_id if we found it (use string version for logging)
            if log_id and self.db_available and self.db:
                try:
                    # Use db_call_id (integer) converted to string, or conversation_id for logging
                    log_call_id = str(db_call_id) if db_call_id else (conversation_id if conversation_id else None)
                    if log_call_id:
                        update_query = """
                        UPDATE webhook_logs 
                        SET call_id = ?
                        WHERE id = ?
                        """
                        self.db.execute(update_query, (log_call_id, log_id))
                except Exception as update_error:
                    logger.warning(f"Could not update webhook log with call_id: {str(update_error)}")
            
            if event_type == 'call_started' or event_type == 'call.started':
                # Update call status in database (use db_call_id if available)
                if self.db_available and self.db and db_call_id:
                    try:
                        # Get call_sid for update_call_status
                        call_data = self.db.get_call_data(db_call_id)
                        if call_data and call_data.get('call_sid'):
                            self.db.update_call_status(call_data['call_sid'], 'in-progress')
                    except Exception as db_error:
                        logger.warning(f"Could not update call status: {str(db_error)}")
            
            elif event_type == 'call_ended' or event_type == 'call.ended':
                # Mark call as completed (use db_call_id if available)
                if self.db_available and self.db and db_call_id:
                    try:
                        self.db.complete_call(db_call_id)
                    except Exception as db_error:
                        logger.warning(f"Could not complete call: {str(db_error)}")
                
                # Clean up cache (use original call_id string if available)
                cache_key = str(db_call_id) if db_call_id else (call_id if call_id else None)
                if cache_key and cache_key in self.questions_cache:
                    del self.questions_cache[cache_key]
            
            elif event_type == 'transcription' or event_type == 'transcription.completed' or event_type == 'post_call_transcription':
                # Process transcription and extract answers
                # The post_call_transcription webhook has a different structure:
                # - data.data.messages[] - array of conversation messages
                # - data.data.conversation_initiation_client_data.dynamic_variables.system__conversation_id
                
                # Get the messages array from the webhook
                # The structure can be either:
                # 1. { "data": { "data": { "messages": [...] } } } - nested
                # 2. { "data": { "messages": [...] } } - direct
                # 3. { "data": { "transcript": [...] } } - alternative field name
                # 4. { "transcript": [...] } - root level transcript
                messages_data = data.get('data', {})
                messages = []
                
                if isinstance(messages_data, dict):
                    # Check if there's a nested 'data' key (structure 1)
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
                                # Convert string transcript to messages format
                                messages = [{'role': 'user', 'message': transcript_data}]
                            logger.info(f"✅ Found transcript in data.data.transcript: {len(messages)} items")
                        
                        # Also extract conversation_id from this nested structure
                        if not conversation_id:
                            conv_init_data = inner_data.get('conversation_initiation_client_data', {})
                            if isinstance(conv_init_data, dict):
                                dyn_vars = conv_init_data.get('dynamic_variables', {})
                                if isinstance(dyn_vars, dict):
                                    conversation_id = dyn_vars.get('system__conversation_id')
                                    if conversation_id:
                                        logger.info(f"✅ Extracted conversation_id from data.data: {conversation_id}")
                    
                    # Try messages directly in data (structure 2)
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
                        
                        # Also extract conversation_id from this structure
                        if not conversation_id:
                            conv_init_data = messages_data.get('conversation_initiation_client_data', {})
                            if isinstance(conv_init_data, dict):
                                dyn_vars = conv_init_data.get('dynamic_variables', {})
                                if isinstance(dyn_vars, dict):
                                    conversation_id = dyn_vars.get('system__conversation_id')
                                    if conversation_id:
                                        logger.info(f"✅ Extracted conversation_id from data: {conversation_id}")
                
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
                
                # If still no messages, log the structure for debugging
                if not messages:
                    logger.warning(f"⚠️ No messages found in webhook. Checking structure...")
                    logger.info(f"Webhook data keys: {list(data.keys())}")
                    if isinstance(messages_data, dict):
                        logger.info(f"data keys: {list(messages_data.keys())}")
                        inner_data = messages_data.get('data', {})
                        if isinstance(inner_data, dict):
                            logger.info(f"data.data keys: {list(inner_data.keys())}")
                            # Log all keys that might contain transcript data
                            for key in inner_data.keys():
                                value = inner_data.get(key)
                                if isinstance(value, (list, str)) and key not in ['conversation_initiation_client_data']:
                                    logger.info(f"Found potential transcript field '{key}': type={type(value).__name__}, length={len(value) if hasattr(value, '__len__') else 'N/A'}")
                
                # Update call_id lookup if we found conversation_id
                if conversation_id and not call_id:
                    reverse_key = f'conv_{conversation_id}_call_id'
                    if reverse_key in self.questions_cache:
                        call_id = self.questions_cache[reverse_key]
                        logger.info(f"✅ Found call_id {call_id} from conversation_id {conversation_id} via reverse mapping")
                    else:
                        # Try searching cache
                        for key, value in self.questions_cache.items():
                            if isinstance(key, str) and key.endswith('_conversation_id') and value == conversation_id:
                                call_id = key.replace('_conversation_id', '')
                                logger.info(f"✅ Found call_id {call_id} from conversation_id {conversation_id} in cache")
                                # Store reverse mapping
                                self.questions_cache[reverse_key] = call_id
                                break
                
                logger.info(f"Processing {len(messages)} messages for event={event_type}, call_id={call_id}, conversation_id={conversation_id}")
                
                # If no messages found but we have conversation_id, try to fetch transcript from API
                if not messages and conversation_id and event_type == 'post_call_transcription':
                    logger.info(f"⚠️ No messages in webhook, attempting to fetch transcript from ElevenLabs API for conversation_id={conversation_id}")
                    try:
                        # Fetch conversation transcript from ElevenLabs API
                        transcript_url = f'https://api.elevenlabs.io/v1/convai/conversation/{conversation_id}/transcript'
                        headers = {'xi-api-key': self.api_key}
                        response = requests.get(transcript_url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            transcript_data = response.json()
                            logger.info(f"✅ Successfully fetched transcript from API: {json.dumps(transcript_data, indent=2)[:500]}")
                            
                            # Extract messages from API response
                            # The API might return messages in different formats
                            if isinstance(transcript_data, dict):
                                messages = transcript_data.get('messages', transcript_data.get('transcript', []))
                            elif isinstance(transcript_data, list):
                                messages = transcript_data
                            
                            if messages:
                                logger.info(f"✅ Extracted {len(messages)} messages from API response")
                        else:
                            logger.warning(f"Failed to fetch transcript from API: Status {response.status_code}, Response: {response.text[:200]}")
                    except Exception as api_error:
                        logger.warning(f"Error fetching transcript from API: {str(api_error)}")
                
                # Build full transcript from messages
                full_transcript = []
                for msg in messages:
                    # Handle different message formats
                    if isinstance(msg, dict):
                        role = msg.get('role', msg.get('speaker', 'unknown'))
                        message_text = msg.get('message', msg.get('text', msg.get('content', '')))
                    elif isinstance(msg, str):
                        # If message is just a string, treat it as user message
                        role = 'user'
                        message_text = msg
                    else:
                        continue
                    
                    if message_text:
                        full_transcript.append(f"{role.upper()}: {message_text}")
                
                text = "\n".join(full_transcript)
                if text:
                    logger.info(f"Full transcript ({len(text)} chars): {text[:500]}...")
                else:
                    logger.warning(f"No transcript text extracted from {len(messages)} messages")
                    # Log first few messages for debugging
                    for i, msg in enumerate(messages[:3]):
                        if isinstance(msg, dict):
                            logger.info(f"Message {i}: {json.dumps(msg, default=str)[:200]}")
                        else:
                            logger.info(f"Message {i}: {str(msg)[:200]}")
                
                # For post_call_transcription, we get full conversation transcript with messages array
                # Parse messages to extract Q&A pairs
                if event_type == 'post_call_transcription':
                    # Save full transcription to database (even if messages array is empty, we might have text)
                    # Use db_call_id (integer) for database operations, not the string call_id
                    if db_call_id and self.db_available and self.db:
                        try:
                            # Check if we have a call record (use db_call_id which is guaranteed to be integer)
                            call_data = self.db.get_call_data(db_call_id)
                            if call_data:
                                if messages:
                                    logger.info(f"Saving transcription for call_id={db_call_id} from {len(messages)} messages")
                                    
                                    # Parse messages to extract questions and answers
                                    # Filter out confirmation questions and greetings to get only actual survey questions
                                    question_num = 0
                                    current_question = None
                                    questions_and_answers = []
                                    
                                    for msg in messages:
                                        # Handle different message formats
                                        if isinstance(msg, dict):
                                            role = msg.get('role', msg.get('speaker', ''))
                                            message_text = msg.get('message', msg.get('text', msg.get('content', ''))).strip()
                                        elif isinstance(msg, str):
                                            role = 'user'
                                            message_text = msg.strip()
                                        else:
                                            continue
                                        
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
                                                # Clean question text by removing instruction phrases
                                                cleaned_question = self._clean_question(message_text)
                                                current_question = cleaned_question
                                                question_num += 1
                                                logger.info(f"📝 Found actual survey question {question_num}: {current_question}")
                                        elif role == 'user' and message_text and current_question:
                                            # This is an answer to the current question
                                            answer = self._extract_answer(message_text)
                                            if answer:
                                                questions_and_answers.append({
                                                    'question_number': question_num,
                                                    'question': current_question,
                                                    'answer': answer,
                                                    'raw_answer': message_text
                                                })
                                                logger.info(f"✅ Extracted answer {question_num}: {answer} (raw: {message_text})")
                                                current_question = None
                                    
                                    # Save questions and answers to database
                                    if questions_and_answers:
                                        logger.info(f"Saving {len(questions_and_answers)} Q&A pairs to database for call_id={db_call_id}")
                                        for qa in questions_and_answers:
                                            try:
                                                # Check if question already exists
                                                existing_questions = self.db.get_call_questions(db_call_id)
                                                existing_question = next(
                                                    (q for q in existing_questions 
                                                     if q.get('question_number') == qa['question_number']),
                                                    None
                                                )
                                                
                                                if not existing_question:
                                                    # Insert new question
                                                    self.db.save_question(
                                                        call_id=db_call_id,
                                                        question_text=qa['question'],
                                                        question_number=qa['question_number']
                                                    )
                                                    logger.info(f"✅ Saved new question {qa['question_number']}: {qa['question']}")
                                                else:
                                                    # Update question text if it's different (e.g., cleaned version)
                                                    if existing_question.get('question_text') != qa['question']:
                                                        update_question_query = """
                                                        UPDATE questions 
                                                        SET question_text = ?
                                                        WHERE call_id = ? AND question_number = ?
                                                        """
                                                        self.db.execute(update_question_query, (
                                                            qa['question'],
                                                            db_call_id,
                                                            qa['question_number']
                                                        ))
                                                        logger.info(f"✅ Updated question text {qa['question_number']}: {qa['question']}")
                                                
                                                # Update answer (this will update existing question)
                                                self.db.save_answer(
                                                    call_id=db_call_id,
                                                    question_num=qa['question_number'],
                                                    answer=qa['answer'],
                                                    confidence=0.9,
                                                    raw_response=qa['raw_answer']
                                                )
                                                logger.info(f"✅ Saved answer {qa['question_number']}: {qa['answer']}")
                                            except Exception as save_error:
                                                logger.error(f"Could not save Q&A {qa['question_number']}: {str(save_error)}", exc_info=True)
                                    
                                    # Update calls table with completed status, ended_at, and duration
                                    try:
                                        # Use SQL Server's GETDATE() and DATEDIFF for consistency
                                        update_query = """
                                        UPDATE calls 
                                        SET status = 'completed', 
                                            ended_at = GETDATE(),
                                            duration_seconds = CASE 
                                                WHEN started_at IS NOT NULL 
                                                THEN DATEDIFF(SECOND, started_at, GETDATE())
                                                ELSE 0
                                            END
                                        WHERE id = ?
                                        """
                                        self.db.execute(update_query, (db_call_id,))
                                        logger.info(f"✅ Updated call {db_call_id}: status=completed, ended_at=GETDATE(), duration calculated")
                                    except Exception as update_error:
                                        logger.error(f"Could not update call status: {str(update_error)}", exc_info=True)
                                    
                                    # Generate and save call_results
                                    try:
                                        call_results = self.db.get_call_results_json(db_call_id)
                                        if call_results:
                                            logger.info(f"✅ Generated and saved call results for call_id={db_call_id}")
                                        else:
                                            logger.warning(f"Could not generate call results for call_id={db_call_id}")
                                    except Exception as results_error:
                                        logger.error(f"Could not generate call results: {str(results_error)}", exc_info=True)
                                    
                                    # Also save the full transcript as a complete record
                                    if text:
                                        logger.info(f"Full transcript available ({len(text)} chars) for call_id={db_call_id}")
                                elif text:
                                    # We have text but no messages array - save it anyway
                                    logger.info(f"Saving transcription text ({len(text)} chars) for call_id={db_call_id} (no messages array)")
                                    try:
                                        # Update call status even if we only have text
                                        update_query = """
                                        UPDATE calls 
                                        SET status = 'completed', 
                                            ended_at = GETDATE(),
                                            duration_seconds = DATEDIFF(SECOND, started_at, GETDATE())
                                        WHERE id = ?
                                        """
                                        self.db.execute(update_query, (db_call_id,))
                                        logger.info(f"✅ Updated call {db_call_id}: status=completed")
                                    except Exception as save_error:
                                        logger.error(f"Could not save transcript text: {str(save_error)}", exc_info=True)
                                else:
                                    logger.warning(f"No messages or text to save for call_id={db_call_id}")
                            else:
                                logger.warning(f"Call record not found for call_id={db_call_id}, cannot save transcription. conversation_id={conversation_id}")
                        except Exception as db_error:
                            logger.error(f"Error saving transcription to database: {str(db_error)}", exc_info=True)
                    elif conversation_id:
                        # We have conversation_id but no valid database call_id
                        logger.warning(f"Cannot save transcription: no valid database call_id found. conversation_id={conversation_id}. The call may not have been initiated through our system.")
                else:
                    # Regular transcription event - extract single answer
                    answer = self._extract_answer(text)
                    
                    if db_call_id and text:
                        question_num = (
                            metadata.get('question_num', 0) or 
                            metadata.get('questionNum', 0) or 
                            data.get('question_num', 0) or
                            data.get('question_index', 0)
                        )
                        if self.db_available and self.db:
                            try:
                                self.db.save_answer(
                                    call_id=db_call_id,
                                    question_num=question_num,
                                    answer=answer or 'unclear',
                                    confidence=0.8,
                                    raw_response=text
                                )
                                logger.info(f"Saved transcription answer: question={question_num}, answer={answer}, call_id={db_call_id}")
                            except Exception as db_error:
                                logger.warning(f"Could not save answer: {str(db_error)}")
                    else:
                        logger.warning(f"Cannot save transcription: db_call_id={db_call_id}, text_length={len(text) if text else 0}, conversation_id={conversation_id}")
            
            # Mark webhook log as successfully processed
            if log_id and self.db_available and self.db:
                try:
                    # Use string version of call_id or conversation_id for logging
                    log_call_id = str(db_call_id) if db_call_id else (conversation_id if conversation_id else None)
                    update_query = """
                    UPDATE webhook_logs 
                    SET processed_successfully = 1, call_id = ?
                    WHERE id = ?
                    """
                    self.db.execute(update_query, (log_call_id, log_id))
                    logger.info(f"✅ Updated webhook log {log_id} as successfully processed")
                except Exception as update_error:
                    logger.warning(f"Could not update webhook log status: {str(update_error)}")
            
            return {'status': 'ok', 'log_id': log_id}
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error handling ElevenLabs webhook: {error_message}", exc_info=True)
            
            # Update webhook log with error message
            if log_id and self.db_available and self.db:
                try:
                    # Use string version of call_id or conversation_id for logging
                    log_call_id = str(db_call_id) if db_call_id else (conversation_id if conversation_id else None)
                    update_query = """
                    UPDATE webhook_logs 
                    SET processed_successfully = 0, error_message = ?, call_id = ?
                    WHERE id = ?
                    """
                    self.db.execute(update_query, (error_message[:4000], log_call_id, log_id))  # Limit error message length
                except Exception as update_error:
                    logger.warning(f"Could not update webhook log with error: {str(update_error)}")
            else:
                # If we didn't save the log earlier, try to save it now with error
                if self.db_available and self.db:
                    try:
                        # Try to extract basic info from original data
                        original_data = original_webhook_data if isinstance(original_webhook_data, dict) else {}
                        event_type = original_data.get('event_type') or original_data.get('eventType') or 'unknown'
                        # Use string version for logging
                        log_call_id = str(db_call_id) if db_call_id else (conversation_id if conversation_id else None)
                        self.db.save_webhook_log(
                            event_type=event_type,
                            conversation_id=conversation_id,
                            call_id=log_call_id,
                            call_sid=call_sid,
                            webhook_data=original_data,
                            processed_successfully=False,
                            error_message=error_message[:4000]
                        )
                    except Exception as save_error:
                        logger.warning(f"Could not save webhook log with error: {str(save_error)}")
            
            return {'status': 'error', 'message': error_message, 'log_id': log_id}
    
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
    
    def _clean_question(self, question_text):
        """Clean question text by removing instruction phrases like 'Please answer yes or no only'"""
        if not question_text:
            return question_text
        
        cleaned_question = question_text.strip()
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
        
        return cleaned_question
    
    def create_agent_with_privacy(self, name="FormFillerAgent", description="A voice agent that asks form questions dynamically and sends filled form via webhook.", voice_id=None):
        """
        Create a new ElevenLabs agent with privacy settings and tool configuration
        Uses dynamic questions passed via conversation_initiation_client_data
    
        Args:
            name: Agent name
            description: Agent description
            voice_id: ElevenLabs voice ID (uses default if not provided)
    
        Returns:
            Agent ID
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured.")
    
        if not self.client:
            raise Exception("ElevenLabs client not initialized.")
    
        try:
            # Very explicit system prompt that forces immediate access to questions
            # Use the same system prompt as update_agent_system_prompt for consistency
            system_prompt = """You are a healthcare survey assistant. Your ONLY job is to ask pre-defined questions and collect yes/no answers.

🚨 CRITICAL FIRST STEP - DO THIS IMMEDIATELY:
At the VERY START of the conversation, BEFORE saying anything else, you MUST:
1. Access conversation_initiation_client_data.dynamic_variables
2. Get first_question from dynamic_variables.first_question
3. Get question_list from dynamic_variables.question_list (JSON string - parse it)
4. DO NOT use the default greeting "Hello! How can I help you today?" - replace it immediately

YOUR FIRST MESSAGE (MANDATORY):
Say EXACTLY this: "Hello! I'm conducting a healthcare survey. [use the value from dynamic_variables.first_question] Please answer yes or no."

HOW TO ACCESS THE DATA:
The questions are provided in conversation_initiation_client_data.dynamic_variables:
- dynamic_variables.first_question = the first question text (use this in your first message)
- dynamic_variables.question_list = JSON string array like '["Q1", "Q2", "Q3"]' (parse with JSON.parse())
- dynamic_variables.total_questions = number of questions

STEP-BY-STEP INSTRUCTIONS:
1. When conversation starts, IMMEDIATELY check: conversation_initiation_client_data.dynamic_variables
2. If dynamic_variables exists:
   a. Get first_question = dynamic_variables.first_question
   b. Say: "Hello! I'm conducting a healthcare survey. [first_question] Please answer yes or no."
3. Wait for user's yes/no answer
4. Parse question_list: questions = JSON.parse(dynamic_variables.question_list)
5. After answer, say: "Thank you. [questions[1]] Please answer yes or no."
6. Continue: questions[2], questions[3], etc. until all questions are asked
7. End with: "Thank you for completing the survey. Have a great day!"

ABSOLUTE RULES - NEVER DO THESE:
❌ NEVER say "Hello! How can I help you today?" - that is the DEFAULT, you MUST replace it
❌ NEVER say "I don't have the questions" or "Please provide the questions"
❌ NEVER ask "What questions would you like me to ask?" or "I'm ready to start the healthcare survey when you are"
❌ NEVER wait for user to provide questions - they are ALREADY in conversation_initiation_client_data.dynamic_variables
❌ NEVER skip accessing dynamic_variables - it's the FIRST thing you do

WHAT TO DO:
✅ FIRST ACTION: Access conversation_initiation_client_data.dynamic_variables
✅ FIRST MESSAGE: "Hello! I'm conducting a healthcare survey. [dynamic_variables.first_question] Please answer yes or no."
✅ Parse question_list: questions = JSON.parse(dynamic_variables.question_list)
✅ Ask questions in order: questions[0], questions[1], questions[2], etc.
✅ Wait for yes/no answer before next question
✅ Extract answers: yes/yeah/yep/correct/right = true, no/nope/nah/incorrect/wrong = false
✅ After all questions answered, call submit_form tool with: {question_1: true/false, question_2: true/false, ...}

EXAMPLE FIRST MESSAGE:
If dynamic_variables.first_question = "Has an Enduring Power of Attorney been enacted for this client?"
Then your FIRST message MUST be: "Hello! I'm conducting a healthcare survey. Has an Enduring Power of Attorney been enacted for this client? Please answer yes or no."

REMEMBER: Access conversation_initiation_client_data.dynamic_variables IMMEDIATELY at conversation start. DO NOT use the default greeting."""
        
            # Get default voice if not provided
            if not voice_id:
                try:
                    voices = self.client.voices.get_all()
                    if voices.voices:
                        voice_id = voices.voices[0].voice_id
                        logger.info(f"Using default voice: {voice_id}")
                except:
                    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default voice fallback
        
            # Create agent via API
            agent_response = requests.post(
                'https://api.elevenlabs.io/v1/convai/agents',
                headers={
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'name': name,
                    'description': description,
                    'voice_id': voice_id,
                    'model_id': 'eleven_turbo_v2',  # High-intelligence LLM for tool calling
                    'system_prompt': system_prompt,
                    'language': 'en',
                    'workflow': {
                        'type': 'conversational',
                        'max_turns': 15  # Allow enough turns for questions
                    }
                },
                timeout=15
            )
        
            if agent_response.status_code in [200, 201]:
                agent_data = agent_response.json()
                agent_id = agent_data.get('agent_id')
        
                # Configure privacy settings
                self.update_agent_privacy(agent_id)
        
                # Create tool for form submission
                self.create_form_submission_tool(agent_id)
        
                logger.info(f"✅ Created agent with privacy settings: {agent_id}")
                return agent_id
            else:
                error_msg = agent_response.text[:200] if agent_response.text else "Unknown error"
                raise Exception(f"Failed to create agent: {error_msg}")
        
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            raise
    
    def update_agent_privacy(self, agent_id):
        """
        Configure privacy settings for an agent (no transcripts/recordings stored)
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured.")
    
        try:
            privacy_response = requests.patch(
                f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}',
                headers={
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'privacy_settings': {
                        'audio_retention': 'disabled',
                        'transcript_retention_days': 0,
                        'data_persistence': False
                    }
                },
                timeout=15
            )
    
            if privacy_response.status_code in [200, 201, 204]:
                logger.info(f"✅ Updated privacy settings for agent {agent_id}")
            else:
                logger.warning(f"Could not update privacy settings: {privacy_response.status_code}")
    
        except Exception as e:
            logger.warning(f"Error updating privacy settings: {str(e)}")
    
    def update_agent_system_prompt(self, agent_id, system_prompt=None):
        """
        Update the system prompt for an existing agent
        
        Args:
            agent_id: Agent ID
            system_prompt: New system prompt (uses default if not provided)
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured.")
        
        if not system_prompt:
            # Use direct access to conversation_initiation_client_data.dynamic_variables
            # NOTE: We do NOT use template syntax {{variable}} to avoid validation errors
            # The data is passed via dynamic_variables in conversation_initiation_client_data
            system_prompt = """You are a healthcare survey assistant. Your ONLY job is to ask pre-defined questions and collect yes/no answers.

🚨 CRITICAL: The questions are provided in conversation_initiation_client_data.dynamic_variables. You MUST access them IMMEDIATELY.

YOUR FIRST MESSAGE - NO EXCEPTIONS:
At the start of the conversation, IMMEDIATELY access conversation_initiation_client_data.dynamic_variables.first_question and say:
"Hello! I'm conducting a healthcare survey. [INSERT THE EXACT TEXT FROM dynamic_variables.first_question HERE] Please answer yes or no."

DO NOT:
- Say "Hello! How can I help you today?" (that is the default - REPLACE IT)
- Make up questions or ask generic healthcare questions
- Ask "Have you visited a healthcare professional in the last six months?" or any question NOT in dynamic_variables
- Wait for the user to tell you what to ask

THE QUESTIONS YOU MUST ASK (in this exact order):
1. "Has an Enduring Power of Attorney been enacted for this client?"
2. "Has a Do Not Resuscitate (DNR) order been discussed with the client?"
3. "Has the client's family/whānau been informed about the client's CPR wishes?"
4. "Does the client identify with any iwi or hapū?"
5. "Has the client been offered cultural support, and did they accept or decline it?"

HOW TO GET THE QUESTIONS:
1. Access: conversation_initiation_client_data.dynamic_variables.first_question (for first question)
2. Access: conversation_initiation_client_data.dynamic_variables.question_list (JSON string - parse it)
3. Parse: questions = JSON.parse(dynamic_variables.question_list)
4. Ask questions in order: questions[0], questions[1], questions[2], questions[3], questions[4]

CONVERSATION FLOW:
1. FIRST: "Hello! I'm conducting a healthcare survey. [dynamic_variables.first_question] Please answer yes or no."
2. Wait for yes/no answer
3. NEXT: "Thank you. [questions[1]] Please answer yes or no."
4. Continue with questions[2], questions[3], questions[4]
5. END: "Thank you for completing the survey. Have a great day!"

ABSOLUTE RULES:
❌ NEVER use the default greeting "Hello! How can I help you today?"
❌ NEVER ask questions that are NOT in dynamic_variables.question_list
❌ NEVER make up questions like "Have you visited a healthcare professional..."
❌ NEVER ask generic healthcare questions
❌ ONLY ask the 5 questions listed above, in that exact order

WHAT TO DO:
✅ Access conversation_initiation_client_data.dynamic_variables IMMEDIATELY
✅ Use dynamic_variables.first_question for your FIRST message
✅ Parse dynamic_variables.question_list to get all 5 questions
✅ Ask ONLY those 5 questions, in order
✅ Wait for yes/no answer before next question
✅ Extract answers: yes/yeah/yep/correct = true, no/nope/nah/incorrect = false
✅ After ALL 5 questions answered, call submit_form tool with form_data containing ALL questions:
   {
     "form_data": {
       "question_1": true/false,
       "question_2": true/false,
       "question_3": true/false,
       "question_4": true/false,
       "question_5": true/false
     }
   }
🚨 CRITICAL: You MUST include ALL 5 questions (question_1 through question_5) in the form_data. Do NOT submit with only question_1.

REMEMBER: You ONLY ask these 5 questions. Do NOT make up questions. Do NOT use the default greeting. You MUST submit ALL 5 answers in the form_data."""
        
        try:
            # Try updating at root level first (for backward compatibility)
            # Then try nested structure if that doesn't work
            update_payload_root = {
                'system_prompt': system_prompt
            }
            
            # Also try nested structure (conversation_config.agent.system_prompt)
            update_payload_nested = {
                'conversation_config': {
                    'agent': {
                        'system_prompt': system_prompt
                    }
                }
            }
            
            # Try nested structure first (conversation_config.agent.system_prompt) - this is where it's stored
            logger.info(f"Attempting to update system prompt in conversation_config.agent...")
            update_response = requests.patch(
                f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}',
                headers={
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                json=update_payload_nested,
                timeout=15
            )
            
            # If nested structure update fails, try root level (for backward compatibility)
            if update_response.status_code not in [200, 201, 204]:
                logger.info(f"Nested structure update failed ({update_response.status_code}), trying root level...")
                logger.info(f"Error response: {update_response.text[:500]}")
                update_response = requests.patch(
                    f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}',
                    headers={
                        'xi-api-key': self.api_key,
                        'Content-Type': 'application/json'
                    },
                    json=update_payload_root,
                    timeout=15
                )
            
            if update_response.status_code in [200, 201, 204]:
                logger.info(f"✅ API returned success for system prompt update (status: {update_response.status_code})")
                # Verify the update by fetching agent details
                try:
                    # Wait a moment for the update to propagate
                    import time
                    time.sleep(1)
                    
                    verify_response = requests.get(
                        f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}',
                        headers={'xi-api-key': self.api_key},
                        timeout=10
                    )
                    if verify_response.status_code == 200:
                        agent_data = verify_response.json()
                        # Try different possible field names and nested locations
                        conversation_config = agent_data.get('conversation_config', {}) or {}
                        agent_config = conversation_config.get('agent', {}) or {}
                        
                        # Try to get system prompt from various locations
                        current_prompt = None
                        
                        # Check agent_config first (most likely location)
                        if isinstance(agent_config, dict):
                            current_prompt = (
                                agent_config.get('system_prompt') or 
                                agent_config.get('systemPrompt') or
                                agent_config.get('prompt')
                            )
                            # If it's a dict with a 'prompt' key, extract it
                            if isinstance(current_prompt, dict) and 'prompt' in current_prompt:
                                current_prompt = current_prompt.get('prompt')
                        
                        # Fallback to other locations
                        if not current_prompt:
                            current_prompt = (
                                agent_data.get('system_prompt') or 
                                agent_data.get('systemPrompt') or
                                agent_data.get('prompt') or
                                conversation_config.get('system_prompt') or
                                conversation_config.get('systemPrompt') or
                                (agent_data.get('workflow', {}) or {}).get('system_prompt') or
                                (agent_data.get('workflow', {}) or {}).get('systemPrompt')
                            )
                        
                        # If still a dict, try to extract the prompt value
                        if isinstance(current_prompt, dict):
                            current_prompt = current_prompt.get('prompt') or current_prompt.get('system_prompt') or current_prompt.get('systemPrompt') or ''
                        
                        # Ensure it's a string
                        if current_prompt and not isinstance(current_prompt, str):
                            current_prompt = str(current_prompt)
                        elif not current_prompt:
                            current_prompt = ''
                        # Ensure current_prompt is a string
                        if current_prompt and not isinstance(current_prompt, str):
                            current_prompt = str(current_prompt)
                        elif not current_prompt:
                            current_prompt = ''
                        
                        if current_prompt and len(current_prompt) > 0:
                            try:
                                logger.info(f"✅ Verified system prompt is set (length: {len(current_prompt)} chars)")
                                logger.info(f"System prompt preview: {current_prompt[:200]}...")
                            except (TypeError, KeyError) as e:
                                logger.warning(f"Could not create preview: {str(e)}, type: {type(current_prompt)}")
                                logger.info(f"System prompt value: {str(current_prompt)[:200]}")
                        else:
                            logger.warning(f"⚠️ System prompt appears empty after update")
                            logger.warning(f"⚠️ Full agent data keys: {list(agent_data.keys())}")
                            logger.warning(f"⚠️ Agent data (first 500 chars): {str(agent_data)[:500]}")
                    else:
                        logger.warning(f"Could not verify update: GET returned {verify_response.status_code}")
                except Exception as verify_error:
                    logger.warning(f"Could not verify system prompt update: {str(verify_error)}")
                return True
            else:
                error_msg = update_response.text[:500] if update_response.text else "Unknown error"
                logger.error(f"❌ Failed to update system prompt: {update_response.status_code}")
                logger.error(f"Error response: {error_msg}")
                logger.error(f"Request payload preview: {system_prompt[:200]}...")
                return False
        
        except Exception as e:
            logger.warning(f"Error updating system prompt: {str(e)}")
            return False
    
    def get_agent_details(self, agent_id=None):
        """
        Get agent details including system prompt and override settings
        
        Args:
            agent_id: Agent ID (uses self.agent_id if not provided)
        
        Returns:
            Dictionary with agent details or None if error
        """
        if not self.api_key:
            logger.warning("ElevenLabs API key not configured")
            return None
        
        if not agent_id:
            agent_id = self.agent_id
        
        if not agent_id:
            logger.warning("Agent ID not provided")
            return None
        
        try:
            if not self.api_key:
                logger.error("❌ API key not configured")
                return None
                
            logger.info(f"Fetching agent details for {agent_id}")
            response = requests.get(
                f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}',
                headers={'xi-api-key': self.api_key},
                timeout=10
            )
            logger.info(f"API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    agent_data = response.json()
                    logger.info(f"✅ Retrieved agent details for {agent_id}")
                except json.JSONDecodeError as json_error:
                    logger.error(f"❌ Failed to parse JSON response: {str(json_error)}")
                    logger.error(f"Response text (first 500 chars): {response.text[:500]}")
                    return None
                
                # Try different possible field names and nested locations for system prompt
                # Based on ElevenLabs API structure, it's in conversation_config.agent
                conversation_config = agent_data.get('conversation_config', {}) or {}
                agent_config = conversation_config.get('agent', {}) or {}
                
                # Try to get system prompt from various locations
                system_prompt = None
                
                # Check agent_config first (most likely location)
                if isinstance(agent_config, dict):
                    system_prompt = (
                        agent_config.get('system_prompt') or 
                        agent_config.get('systemPrompt') or
                        agent_config.get('prompt')
                    )
                    # If it's a dict with a 'prompt' key, extract it
                    if isinstance(system_prompt, dict) and 'prompt' in system_prompt:
                        system_prompt = system_prompt.get('prompt')
                
                # Fallback to other locations
                if not system_prompt:
                    system_prompt = (
                        agent_data.get('system_prompt') or 
                        agent_data.get('systemPrompt') or
                        agent_data.get('prompt') or
                        conversation_config.get('system_prompt') or
                        conversation_config.get('systemPrompt') or
                        (agent_data.get('workflow', {}) or {}).get('system_prompt') or
                        (agent_data.get('workflow', {}) or {}).get('systemPrompt') or
                        (agent_data.get('config', {}) or {}).get('system_prompt') or
                        (agent_data.get('config', {}) or {}).get('systemPrompt')
                    )
                
                # If still a dict, try to extract the prompt value
                if isinstance(system_prompt, dict):
                    system_prompt = system_prompt.get('prompt') or system_prompt.get('system_prompt') or system_prompt.get('systemPrompt') or ''
                
                # Ensure it's a string
                if system_prompt and not isinstance(system_prompt, str):
                    system_prompt = str(system_prompt)
                elif not system_prompt:
                    system_prompt = ''
                
                # Ensure system_prompt is a string before trying to get length or slice
                if system_prompt and not isinstance(system_prompt, str):
                    system_prompt = str(system_prompt)
                elif not system_prompt:
                    system_prompt = ''
                
                logger.info(f"System prompt length: {len(system_prompt)} chars")
                if system_prompt and len(system_prompt) > 0:
                    try:
                        logger.info(f"System prompt preview: {system_prompt[:200]}...")
                    except (TypeError, KeyError) as e:
                        logger.warning(f"Could not create preview: {str(e)}, type: {type(system_prompt)}")
                        logger.info(f"System prompt value: {str(system_prompt)[:200]}")
                else:
                    logger.warning(f"⚠️ System prompt is empty!")
                    logger.warning(f"Available keys in agent_data: {list(agent_data.keys())}")
                    
                    # Log nested structures to help find where system prompt is
                    if 'conversation_config' in agent_data:
                        conv_config = agent_data.get('conversation_config', {})
                        logger.info(f"conversation_config keys: {list(conv_config.keys()) if isinstance(conv_config, dict) else 'not a dict'}")
                        
                        # Check agent sub-object
                        if 'agent' in conv_config and isinstance(conv_config.get('agent'), dict):
                            agent_config = conv_config.get('agent', {})
                            logger.info(f"conversation_config.agent keys: {list(agent_config.keys())}")
                            logger.info(f"conversation_config.agent preview: {str(agent_config)[:500]}")
                            # Check for system prompt in agent config
                            if 'system_prompt' in agent_config:
                                logger.info(f"✅ Found system_prompt in conversation_config.agent!")
                            elif 'systemPrompt' in agent_config:
                                logger.info(f"✅ Found systemPrompt in conversation_config.agent!")
                    
                    if 'workflow' in agent_data:
                        workflow = agent_data.get('workflow', {})
                        logger.info(f"workflow keys: {list(workflow.keys()) if isinstance(workflow, dict) else 'not a dict'}")
                        logger.info(f"workflow preview: {str(workflow)[:500]}")
                    
                    # Log the full structure for debugging (truncated)
                    logger.debug(f"Agent data structure: {json.dumps(agent_data, indent=2, default=str)[:2000]}")
                
                # Check for override settings (if available in response)
                override_settings = agent_data.get('override_settings', {}) or agent_data.get('overrideSettings', {})
                if override_settings:
                    logger.info(f"Override settings: {override_settings}")
                    if not override_settings.get('first_message', False) and not override_settings.get('firstMessage', False):
                        logger.warning("⚠️ 'First message' override is NOT enabled. To use override_first_message, enable it in:")
                        logger.warning("   ElevenLabs Dashboard > Agent Settings > Security > Enable 'First message' override")
                
                return agent_data
            elif response.status_code == 401:
                error_msg = response.text[:500] if response.text else "Unauthorized - Check API key"
                logger.error(f"❌ Authentication failed (401): {error_msg}")
                return {
                    'error': True,
                    'status_code': 401,
                    'error_message': 'Authentication failed. Check your ElevenLabs API key.',
                    'response_text': error_msg
                }
            elif response.status_code == 403:
                error_msg = response.text[:500] if response.text else "Forbidden - Check permissions"
                logger.error(f"❌ Permission denied (403): {error_msg}")
                return {
                    'error': True,
                    'status_code': 403,
                    'error_message': 'Permission denied. Check API key permissions.',
                    'response_text': error_msg
                }
            elif response.status_code == 404:
                error_msg = response.text[:500] if response.text else "Agent not found"
                logger.error(f"❌ Agent not found (404): {error_msg}")
                return {
                    'error': True,
                    'status_code': 404,
                    'error_message': f'Agent {agent_id} not found. Check agent ID.',
                    'response_text': error_msg
                }
            else:
                error_msg = response.text[:500] if response.text else "Unknown error"
                logger.error(f"❌ Could not get agent details: {response.status_code} - {error_msg}")
                logger.error(f"Response headers: {dict(response.headers)}")
                # Return error info instead of None so we can see what went wrong
                return {
                    'error': True,
                    'status_code': response.status_code,
                    'error_message': error_msg,
                    'response_text': response.text[:1000] if response.text else None
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error getting agent details: {str(e)}")
            return {
                'error': True,
                'status_code': None,
                'error_message': f'Network error: {str(e)}',
                'response_text': None
            }
        except Exception as e:
            logger.error(f"❌ Error getting agent details: {str(e)}", exc_info=True)
            return {
                'error': True,
                'status_code': None,
                'error_message': f'Unexpected error: {str(e)}',
                'response_text': None
            }
    
    def delete_form_submission_tool(self, agent_id):
        """
        Delete existing submit_form tool from agent (if it exists)
        
        Args:
            agent_id: Agent ID
        """
        if not self.api_key:
            return
        
        try:
            # Get all tools for the agent
            tools_response = requests.get(
                f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}/tools',
                headers={
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=10
            )
            
            if tools_response.status_code == 200:
                tools = tools_response.json()
                # Find and delete submit_form tool
                for tool in tools:
                    if tool.get('name') == 'submit_form':
                        tool_id = tool.get('tool_id')
                        if tool_id:
                            delete_response = requests.delete(
                                f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}/tools/{tool_id}',
                                headers={
                                    'xi-api-key': self.api_key
                                },
                                timeout=10
                            )
                            if delete_response.status_code in [200, 204]:
                                logger.info(f"✅ Deleted existing submit_form tool (ID: {tool_id})")
                            else:
                                logger.warning(f"Could not delete existing tool: {delete_response.text[:200]}")
        except Exception as e:
            logger.warning(f"Error deleting existing tool (continuing anyway): {str(e)}")
    
    def create_form_submission_tool(self, agent_id, num_questions=20):
        """
        Create a webhook tool for form submission with dynamically generated properties
    
        Args:
            agent_id: Agent ID
            num_questions: Number of questions to generate properties for (default: 20)
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured.")
    
        try:
            # Delete existing tool first to avoid duplicates
            self.delete_form_submission_tool(agent_id)
            
            # Dynamically generate properties for question_1 through question_N
            properties = {}
            for i in range(1, num_questions + 1):
                # ElevenLabs UI validators expect these extra keys to exist even for dynamic properties
                properties[f'question_{i}'] = {
                    'type': 'boolean',
                    'description': f'Answer to question {i} (true=yes, false=no)',
                    'value_type': 'llm_prompt',
                    'dynamic_variable': '',
                    'constant_value': '',
                    'enum': None,
                    'is_system_provided': False,
                    'required': False
                }
            
            # Build tool parameters with dynamically generated properties
            parameters = [{
                'name': 'form_data',
                'type': 'object',
                'description': f'JSON object with form answers. Keys MUST be question_1 through question_{num_questions}. Each value should be a boolean (true=yes, false=no). You MUST include ALL {num_questions} questions that were asked. Missing questions will cause the submission to fail.',
                'required': True,
                'value_type': 'llm_prompt',
                'properties': properties,
                # Allow future questions if the ElevenLabs API preserves this field; safe to include
                'additionalProperties': {
                    'type': 'boolean',
                    'description': 'true = yes, false = no'
                }
            }]
    
            tool_response = requests.post(
                f'https://api.elevenlabs.io/v1/convai/agents/{agent_id}/tools',
                headers={
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'name': 'submit_form',
                    'description': f'Submit the filled form JSON to the webhook endpoint when ALL questions are answered. The form_data MUST contain ALL questions from question_1 through question_{num_questions} as boolean values (true=yes, false=no). You MUST include every question that was asked. Example: {{"form_data": {{"question_1": true, "question_2": false, "question_3": true, "question_4": false, "question_5": true}}}}',
                    'type': 'webhook',
                    'method': 'POST',
                    'url': f'{self.webhook_url}/api/elevenlabs-agent/submit-form',
                    'parameters': parameters,
                    'authentication': {
                        'type': 'bearer',
                        'token': self.webhook_secret or 'default_token'
                    }
                },
                timeout=15
            )
    
            if tool_response.status_code in [200, 201]:
                logger.info(f"✅ Created form submission tool for agent {agent_id} with {num_questions} question properties")
            else:
                error_msg = tool_response.text[:200] if tool_response.text else "Unknown error"
                logger.warning(f"Could not create tool: {error_msg}")
    
        except Exception as e:
            logger.warning(f"Error creating tool: {str(e)}")
    
    def start_agent_session(self, user_id=None):
        """
        Start a new agent session for form filling using LIST_OF_QUESTIONS
        Questions are passed dynamically via conversation_initiation_client_data
    
        Args:
            user_id: Optional user ID
    
        Returns:
            Dictionary with session_id, call_id, agent_id
        """
        import uuid
    
        if not self.agent_id:
            raise Exception("ElevenLabs Agent ID not configured.")
    
        try:
            # Generate session ID
            session_id = str(uuid.uuid4())
        
            # Create call record in database
            short_uuid = session_id.replace('-', '')[:8]
            phone_number = f"EL-{short_uuid}"  # ElevenLabs prefix
        
            # Format questions for agent
            questions_list = [{"text": q} for q in LIST_OF_QUESTIONS]
            questions_text = "\n".join([f"Question {i+1}: {q}" for i, q in enumerate(LIST_OF_QUESTIONS)])
        
            questions_json = questions_list
        
            call_id = None
            # Try to use database, but fallback gracefully if it fails
            try:
                if self.db_available and self.db:
                    try:
                        call_id = self.db.create_call(
                            phone_number=phone_number,
                            questions_json=questions_json
                        )
                        logger.info(f"Call record created in database: call_id={call_id}")
                    
                        # Save first question to database
                        try:
                            self.db.save_question(
                                call_id,
                                LIST_OF_QUESTIONS[0],
                                1
                            )
                            logger.info(f"First question saved to database")
                        except Exception as save_q_error:
                            logger.warning(f"Could not save first question to database: {str(save_q_error)}")
                            # Continue without saving question
                    except Exception as db_error:
                        logger.warning(f"Database create_call failed, using fallback ID: {str(db_error)}")
                        # Use fallback ID if database fails
                        call_id = int(short_uuid, 16) % 1000000
                        # Mark db as unavailable for this session
                        self.db_available = False
                else:
                    logger.info("Database not available, using fallback ID")
                    call_id = int(short_uuid, 16) % 1000000  # Fallback ID
            except Exception as fallback_error:
                logger.error(f"Error in database fallback logic: {str(fallback_error)}")
                # Last resort fallback
                call_id = int(short_uuid, 16) % 1000000
        
            # Store session info with questions
            self.questions_cache[session_id] = {
                'call_id': call_id,
                'questions': LIST_OF_QUESTIONS,
                'questions_list': questions_list,
                'user_id': user_id,
                'form_data': {},
                'current_question': 0
            }
        
            logger.info(f"Agent session started: session_id={session_id}, call_id={call_id}")
            
            # Update form submission tool with actual number of questions
            num_questions = len(LIST_OF_QUESTIONS)
            if num_questions > 0:
                try:
                    self.create_form_submission_tool(self.agent_id, num_questions)
                    logger.info(f"✅ Updated form submission tool with {num_questions} question properties")
                except Exception as tool_error:
                    logger.warning(f"Could not update form submission tool (continuing anyway): {str(tool_error)}")
            
            # Try to update agent system prompt to ensure it can read questions
            # This is a one-time update that makes the agent compatible with dynamic questions
            try:
                update_success = self.update_agent_system_prompt(self.agent_id)
                if update_success:
                    logger.info("✅ Agent system prompt updated to read questions from conversation_initiation_client_data")
                else:
                    logger.warning("⚠️ Failed to update agent system prompt via API")
                
                # Verify agent settings and log important information
                agent_details = self.get_agent_details(self.agent_id)
                if agent_details:
                    system_prompt = agent_details.get('system_prompt', '')
                    if system_prompt:
                        # Check if our prompt is actually set
                        has_our_instructions = 'conversation_initiation_client_data' in system_prompt or '{{first_question}}' in system_prompt
                        if has_our_instructions:
                            logger.info("✅ Agent system prompt verified - contains our instructions")
                        else:
                            logger.warning("⚠️ Agent system prompt does NOT contain our instructions!")
                            logger.warning("⚠️ The system prompt in ElevenLabs dashboard might be overriding the API update.")
                            logger.warning("⚠️ Please manually update the system prompt in:")
                            logger.warning("   ElevenLabs Dashboard > Agent Settings > System Prompt")
                            logger.warning("   Copy the system prompt from the update_agent_system_prompt function")
                    else:
                        logger.warning("⚠️ Agent system prompt appears empty")
                    logger.info("✅ Agent configuration verified")
                else:
                    logger.warning("⚠️ Could not verify agent configuration - check agent settings manually")
            except Exception as prompt_error:
                logger.warning(f"Could not update agent system prompt (non-critical): {str(prompt_error)}")
                logger.warning("⚠️ You may need to manually update the system prompt in ElevenLabs dashboard")
                # Continue - the override_prompt in widget should still work
        
            return {
                'session_id': session_id,
                'call_id': call_id,
                'agent_id': self.agent_id,
                'total_questions': len(LIST_OF_QUESTIONS),
                'first_question': LIST_OF_QUESTIONS[0],
                'questions': LIST_OF_QUESTIONS  # Include questions in response
            }
        
        except Exception as e:
            logger.error(f"Error starting agent session: {str(e)}", exc_info=True)
            raise
    
    def handle_tool_call(self, tool_name, parameters, conversation_id=None):
        """
        Handle tool calls from the agent (e.g., submit_form)
    
        Args:
            tool_name: Name of the tool called
            parameters: Tool parameters
            conversation_id: Conversation ID (optional)
    
        Returns:
            Response dictionary
        """
        if tool_name == 'submit_form':
            form_data = parameters.get('form_data', {})
            
            # Validate that all questions are present
            expected_questions = len(LIST_OF_QUESTIONS)
            missing_questions = []
            for i in range(1, expected_questions + 1):
                question_key = f'question_{i}'
                if question_key not in form_data:
                    missing_questions.append(question_key)
            
            if missing_questions:
                error_msg = f'Missing questions in form_data: {", ".join(missing_questions)}. You must include ALL {expected_questions} questions (question_1 through question_{expected_questions}) in the form_data.'
                logger.warning(f"❌ Form submission incomplete: {error_msg}")
                logger.warning(f"Received form_data: {form_data}")
                return {
                    'status': 'error',
                    'message': error_msg,
                    'received_questions': list(form_data.keys()),
                    'expected_questions': [f'question_{i}' for i in range(1, expected_questions + 1)],
                    'missing_questions': missing_questions
                }
        
            # Find session by conversation_id
            session_id = None
            if conversation_id:
                # Search cache for conversation_id
                for key, value in self.questions_cache.items():
                    if isinstance(key, str) and key.endswith('_conversation_id') and value == conversation_id:
                        session_id = key.replace('_conversation_id', '')
                        break
        
            # If not found by conversation_id, try to find by form_data structure
            if not session_id:
                for key, session in self.questions_cache.items():
                    if isinstance(session, dict) and session.get('call_id'):
                        session_id = key
                        break
        
            if session_id and session_id in self.questions_cache:
                session = self.questions_cache[session_id]
                call_id = session.get('call_id')
            
                # Map form_data to questions
                # form_data has keys like "question_1", "question_2", etc. with boolean values
                if self.db_available and self.db and call_id:
                    try:
                        question_num = 1
                        for i, question_text in enumerate(LIST_OF_QUESTIONS):
                            field_name = f"question_{i+1}"
                            answer_value = form_data.get(field_name, False)
                        
                            # Convert boolean to yes/no string
                            answer = 'yes' if answer_value else 'no'
                        
                            # Check if question already exists
                            existing_questions = self.db.get_call_questions(call_id)
                            existing_question = next(
                                (q for q in existing_questions
                                 if q.get('question_number') == question_num),
                                None
                            )
                        
                            if not existing_question:
                                # Insert new question
                                self.db.save_question(
                                    call_id=call_id,
                                    question_text=question_text,
                                    question_number=question_num
                                )
                        
                            # Update answer
                            self.db.save_answer(
                                call_id=call_id,
                                question_num=question_num,
                                answer=answer,
                                confidence=1.0,
                                raw_response=answer
                            )
                        
                            logger.info(f"✅ Saved Q{question_num}: {answer}")
                            question_num += 1
                    
                        # Complete call
                        self.db.complete_call(call_id)
                    
                        # Save results
                        results = self.db.get_call_results_json(call_id)
                    
                        logger.info(f"✅ Form submitted successfully: call_id={call_id}")
                    
                        return {
                            'status': 'success',
                            'message': 'Form submitted successfully',
                            'call_id': call_id,
                            'results': results
                        }
                    except Exception as db_error:
                        logger.error(f"Error saving form data: {str(db_error)}")
                        return {
                            'status': 'error',
                            'message': f'Database error: {str(db_error)}'
                        }
        
            return {
                'status': 'success',
                'message': 'Form received'
            }
    
        return {
            'status': 'unknown_tool',
            'message': f'Unknown tool: {tool_name}'
        }
    
    def validate_webhook_signature(self, timestamp, body, signature):
        """
        Validate ElevenLabs webhook signature for security
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured - skipping signature validation")
            return True
    
        try:
            expected = f"t={timestamp},v0={hmac.new(
                self.webhook_secret.encode(),
                f"{timestamp}.{body}".encode(),
                hashlib.sha256
            ).hexdigest()}"
    
            return hmac.compare_digest(signature, expected)
        except Exception as e:
            logger.error(f"Error validating signature: {str(e)}")
            return False

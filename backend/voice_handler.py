"""
Voice call handler using Twilio
Manages voice call flow and question-answer collection
"""
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, WEBHOOK_BASE_URL
from database import Database
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceHandler:
    def __init__(self):
        self.account_sid = TWILIO_ACCOUNT_SID
        self.auth_token = TWILIO_AUTH_TOKEN
        self.phone_number = TWILIO_PHONE_NUMBER
        self.webhook_url = WEBHOOK_BASE_URL
        
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
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            logger.warning("Twilio credentials not configured")
            self.client = None
    
    def initiate_call(self, to_number, call_id, questions):
        """Initiate a voice call to the specified number"""
        if not self.client:
            raise Exception("Twilio client not initialized. Check credentials.")
        
        try:
            # Store questions in cache (for use when database unavailable)
            # Store with multiple key formats to ensure retrieval works
            call_id_str = str(call_id)
            self.questions_cache[call_id_str] = questions
            # Also store with int key if it's numeric
            if call_id_str.isdigit():
                self.questions_cache[int(call_id_str)] = questions
            # Also store with original call_id if different
            if call_id != call_id_str and call_id not in self.questions_cache:
                self.questions_cache[call_id] = questions
            logger.info(f"Questions cached for call_id {call_id_str} (also as {int(call_id_str) if call_id_str.isdigit() else 'N/A'}): {len(questions)} questions: {[q.get('text', '')[:50] for q in questions]}")
            
            # Try to store questions in database (optional - continue if fails)
            if self.db_available and self.db:
                try:
                    for idx, question in enumerate(questions):
                        self.db.save_question(call_id, question.get('text', ''), idx)
                except Exception as db_error:
                    logger.warning(f"Database not available, using cache: {str(db_error)}")
            
            # Initiate the call
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=f'{self.webhook_url}/api/voice-flow?call_id={call_id}',
                method='POST',
                status_callback=f'{self.webhook_url}/api/call-status',
                status_callback_method='POST'
            )
            
            logger.info(f"Call initiated: SID={call.sid}, To={to_number}")
            return call.sid
        except Exception as e:
            logger.error(f"Error initiating call: {str(e)}")
            raise
    
    def handle_voice_flow(self, call_id, current_question=0):
        """
        Generate TwiML for voice flow
        This is called by Twilio webhook for each step of the call
        """
        try:
            # Normalize call_id to string for consistent lookup
            call_id_str = str(call_id) if call_id else None
            if not call_id_str:
                logger.error("No call_id provided to handle_voice_flow")
                response = VoiceResponse()
                response.say("Error: Call ID is missing. Please try again.", voice='alice')
                response.hangup()
                return str(response)
            
            logger.info(f"Voice flow called: call_id={call_id_str} (type: {type(call_id)}), current_question={current_question}, cache_keys={list(self.questions_cache.keys())}")
            
            # Try to get questions from cache first (faster, works without DB)
            # Check multiple variations of call_id
            questions = None
            if call_id_str in self.questions_cache:
                questions = self.questions_cache[call_id_str]
                logger.info(f"Found questions in cache with string key: {call_id_str}")
            elif call_id in self.questions_cache:
                questions = self.questions_cache[call_id]
                logger.info(f"Found questions in cache with original key: {call_id}")
            elif call_id_str.isdigit():
                try:
                    call_id_int = int(call_id_str)
                    if call_id_int in self.questions_cache:
                        questions = self.questions_cache[call_id_int]
                        logger.info(f"Found questions in cache with int key: {call_id_int}")
                except ValueError:
                    pass
            
            # If not in cache, try database
            if not questions and self.db_available and self.db:
                try:
                    # Try with int if it's a number
                    db_call_id = int(call_id_str) if call_id_str.isdigit() else call_id_str
                    call_data = self.db.get_call_data(db_call_id)
                    if call_data and call_data.get('questions_json'):
                        questions = json.loads(call_data['questions_json'])
                        # Cache for future use (use string key for consistency)
                        self.questions_cache[call_id_str] = questions
                        logger.info(f"Loaded {len(questions)} questions from database for call_id {call_id_str}")
                except Exception as db_error:
                    logger.warning(f"Database query failed: {str(db_error)}")
            
            if not questions:
                logger.error(f"No questions found for call_id={call_id_str} (original={call_id}). Cache has {len(self.questions_cache)} entries with keys: {list(self.questions_cache.keys())}")
                response = VoiceResponse()
                response.say("I'm sorry, but I could not find the questions for this call. The call will now end.", voice='alice')
                response.hangup()
                return str(response)
            
            # Validate questions list
            if not isinstance(questions, list) or len(questions) == 0:
                logger.error(f"Invalid questions format for call_id={call_id_str}: {type(questions)}, length={len(questions) if isinstance(questions, list) else 'N/A'}")
                response = VoiceResponse()
                response.say("I'm sorry, but the questions list is empty. The call will now end.", voice='alice')
                response.hangup()
                return str(response)
            
            # Validate that questions have text
            valid_questions = [q for q in questions if q and isinstance(q, dict) and q.get('text', '').strip()]
            if len(valid_questions) == 0:
                logger.error(f"No valid questions with text found for call_id={call_id_str}")
                response = VoiceResponse()
                response.say("I'm sorry, but no valid questions were found. The call will now end.", voice='alice')
                response.hangup()
                return str(response)
            
            # Use valid questions
            questions = valid_questions
            logger.info(f"Successfully retrieved {len(questions)} valid questions for call_id {call_id_str}")
            
            response = VoiceResponse()
            
            # If this is the first question, greet the caller
            if current_question == 0:
                response.say(
                    'Hello, this is an automated survey call. '
                    'I will ask you a few questions. Please answer with yes or no.',
                    voice='alice'
                )
                response.pause(length=2)  # Increased pause to allow user to process
            
            # Check if we have more questions
            if current_question < len(questions):
                question = questions[current_question]
                question_text = question.get('text', '')
                
                # Ask the question
                response.say(f'Question {current_question + 1}. {question_text}', voice='alice')
                response.pause(length=1)
                
                # Create a Gather element to collect speech and DTMF input
                gather = Gather(
                    input='speech dtmf',  # Accept both speech and keypad input
                    language='en-US',
                    speech_timeout='auto',  # Wait for natural pause in speech
                    action=f'{self.webhook_url}/api/process-answer?call_id={call_id}&q_num={current_question}',
                    method='POST',
                    timeout=15,  # Increased timeout to 15 seconds to wait for response
                    num_digits=1,  # Accept 1 digit for keypad input (1=yes, 2=no)
                    finish_on_key='#'  # Optional: finish on # key
                )
                
                # Prompt for response (inside Gather so it plays before waiting)
                gather.say('Please say yes or no, or press 1 for yes, 2 for no.', voice='alice')
                response.append(gather)
                
                # Fallback: If no response after timeout, handle it
                # This only executes if Gather times out without input
                response.say('I did not receive a response. Moving to the next question.', voice='alice')
                response.pause(length=0.5)
                # Redirect to next question
                response.redirect(f'{self.webhook_url}/api/voice-flow?call_id={call_id}&q_num={current_question + 1}')
                
            else:
                # All questions completed
                response.say(
                    'Thank you for answering all questions. Your responses have been recorded. Goodbye!',
                    voice='alice'
                )
                response.hangup()
                
                # Mark call as completed in database (optional)
                if self.db_available and self.db:
                    try:
                        self.db.complete_call(call_id)
                        self.db.get_call_results_json(call_id)
                    except Exception as db_error:
                        logger.warning(f"Could not complete call in database: {str(db_error)}")
                
                # Clean up cache after call completes
                if call_id in self.questions_cache:
                    del self.questions_cache[call_id]
            
            return str(response)
        except Exception as e:
            logger.error(f"Error in voice flow: {str(e)}")
            response = VoiceResponse()
            response.say("An error occurred. Please try again later.", voice='alice')
            response.hangup()
            return str(response)
    
    def process_answer(self, call_id, question_num, speech_result=None, digits=None, confidence=None):
        """
        Process the answer received from the caller
        This is called by Twilio webhook after each Gather
        """
        try:
            response = VoiceResponse()
            
            # Log what we received
            logger.info(f"Processing answer - call_id={call_id}, q_num={question_num}, speech={speech_result}, digits={digits}, confidence={confidence}")
            
            # Determine the answer
            answer = None
            answer_confidence = 0.0
            
            if speech_result and speech_result.strip():
                # Process speech recognition result
                speech_lower = speech_result.lower().strip()
                
                # Check for yes variations
                yes_keywords = ['yes', 'yeah', 'yep', 'correct', 'right', 'sure', 'okay', 'ok', 'yup', 'affirmative']
                if any(word in speech_lower for word in yes_keywords):
                    answer = 'yes'
                    answer_confidence = float(confidence) if confidence else 0.9
                # Check for no variations
                elif any(word in speech_lower for word in ['no', 'nope', 'nah', 'incorrect', 'wrong', 'negative']):
                    answer = 'no'
                    answer_confidence = float(confidence) if confidence else 0.9
                else:
                    # Unclear response
                    answer = 'unclear'
                    answer_confidence = 0.3
            
            elif digits and digits.strip():
                # Keypad input
                if digits == '1':
                    answer = 'yes'
                    answer_confidence = 1.0
                elif digits == '2':
                    answer = 'no'
                    answer_confidence = 1.0
                else:
                    answer = 'unclear'
                    answer_confidence = 0.3
            
            # If no answer was received, mark as timeout
            if answer is None:
                answer = 'timeout'
                answer_confidence = 0.0
                logger.warning(f"No answer received for call_id={call_id}, question={question_num}")
            
            # Store the answer in database (optional)
            if self.db_available and self.db:
                try:
                    self.db.save_answer(
                        call_id=call_id,
                        question_num=question_num,
                        answer=answer or 'timeout',
                        confidence=answer_confidence,
                        raw_response=speech_result or digits or 'timeout'
                    )
                except Exception as db_error:
                    logger.warning(f"Could not save answer to database: {str(db_error)}")
            
            # Provide feedback to caller
            if answer == 'yes':
                response.say('You said yes. Thank you.', voice='alice')
            elif answer == 'no':
                response.say('You said no. Thank you.', voice='alice')
            elif answer == 'timeout':
                response.say('I did not receive a response. Moving to the next question.', voice='alice')
            else:
                response.say('I did not understand your response. Moving to the next question.', voice='alice')
            
            response.pause(length=0.5)
            
            # Move to next question
            next_question = question_num + 1
            response.redirect(f'{self.webhook_url}/api/voice-flow?call_id={call_id}&q_num={next_question}')
            
            return str(response)
        except Exception as e:
            logger.error(f"Error processing answer: {str(e)}")
            response = VoiceResponse()
            response.say("An error occurred. Moving to the next question.", voice='alice')
            response.redirect(f'{self.webhook_url}/api/voice-flow?call_id={call_id}&q_num={question_num + 1}')
            return str(response)


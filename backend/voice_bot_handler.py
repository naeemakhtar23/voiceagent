"""
Voice Bot Handler
Manages voice bot sessions and question flow
"""
import logging
from database import Database
from dialogflow_handler import DialogflowHandler
import json

logger = logging.getLogger(__name__)

# Define the 42 questions
VOICE_BOT_QUESTIONS1 = [
    "Has an Enduring Power of Attorney been enacted for this client?",
    "Which agency made the referral and on what date?",
    "What is the ACC claim number for this client?",
    "What is the Purchase Order number?",
    "What service type and worker skill level are required?",
    "When is the first review date scheduled?",
    "Has a Do Not Resuscitate (DNR) order been discussed with the client?",
    "Is there documented DNR paperwork, and where is it stored?",
    "Has the client's family/whānau been informed about the client's CPR wishes?",
    "Does the client identify with any iwi or hapū?",
    "Has the client been offered cultural support, and did they accept or decline it?",
    "What community support base does the client have?",
    "How would the client like support workers to greet them when they arrive (e.g., in Te Reo Māori)?",
    "Which four taha (dimensions) are assessed in the Hua Oranga section?",
    "On a scale of 1–5, how does the client rate their ability to move without pain or distress (taha tinana)?",
    "What does a score of 17–20 on an individual taha scale indicate?",
    "What is the overall possible score range for all four taha combined?",
    "Areas scoring 4–8 on a taha are considered areas of __________.",
    "Name one short-term goal the client has set.",
    "Name one long-term goal the client has set.",
    "What is the purpose of the 'Goal Ladder' in the plan?",
    "How many standard Home & Community Support hours are funded per week?",
    "How many complex Home & Community Support hours are funded per week?",
    "When does the funded support officially start and end?",
    "According to policy, are support workers allowed to handle client cash or bank cards?",
    "What are the three risk rating categories used in the Potential Hazard Identification Form?",
    "Name three examples of physical hazards listed in the form.",
    "Name two examples of psychological hazards mentioned.",
    "Does the client require medication assistance, and if so, what type (e.g., fully independent, client-directed, SW responsible)?",
    "Is the client independent with mobility, or do they require aids/transfers/hoist?",
    "Does the client require any bowel management interventions (e.g., suppositories, manual evacuation)?",
    "Is the client continent with urination, and do they use any catheter or continence products?",
    "Does the client have any diagnosed mental health conditions requiring support (e.g., depression, anxiety)?",
    "Appendices & Risk Assessments",
    "What does an MST score of 2 or higher indicate in the Malnutrition Screening Tool?",
    "In the Braden Scale, what does a total score of 12 or less represent?",
    "Name three risk factors assessed in the Braden Scale.",
    "In Appendix A (Falls Risk), what score range indicates 'High risk' of falling?",
    "Name at least four intervention strategies listed to reduce falls risk.",
    "Rights, Responsibilities & Consent",
    "According to the Terms and Conditions, can a client privately employ a Phoenix support worker for the same services?",
    "How long must Phoenix Healthcare keep the client's personal information stored?"
]

VOICE_BOT_QUESTIONS = [
    "Has an Enduring Power of Attorney been enacted for this client?",
    "Has a Do Not Resuscitate (DNR) order been discussed with the client?",
    "Has the client’s family/whānau been informed about the client’s CPR wishes?",
    "Does the client identify with any iwi or hapū?",
    "Has the client been offered cultural support, and did they accept or decline it?"
]

class VoiceBotHandler:
    def __init__(self):
        self.db = Database()
        self.dialogflow = DialogflowHandler()
        self.active_sessions = {}  # session_id -> {call_id, current_question, answers, user_id}
    
    def start_session(self, user_id=None):
        """Start a new voice bot session"""
        import uuid
        import time
        session_id = str(uuid.uuid4())
        
        try:
            # Create call record in database
            # Use a shorter phone number format to fit VARCHAR(20) constraint
            # Format: VB-{short_uuid} (e.g., VB-12345678 = 11 chars, well within 20 char limit)
            short_uuid = session_id.replace('-', '')[:8]  # First 8 chars of UUID without dashes
            phone_number = f"VB-{short_uuid}"  # Format: VB-12345678 (11 chars)
            
            questions_json = [{"text": q} for q in VOICE_BOT_QUESTIONS]
            call_id = self.db.create_call(
                phone_number=phone_number,
                questions_json=questions_json
            )
            
            # Initialize session
            self.active_sessions[session_id] = {
                'call_id': call_id,
                'current_question': 0,
                'answers': {},
                'user_id': user_id
            }
            
            # Save first question to database
            self.db.save_question(
                call_id, 
                VOICE_BOT_QUESTIONS[0], 
                1
            )
            
            logger.info(f"Voice bot session started: session_id={session_id}, call_id={call_id}")
            
            return {
                'session_id': session_id,
                'call_id': call_id,
                'current_question': 0,
                'question_text': VOICE_BOT_QUESTIONS[0],
                'total_questions': len(VOICE_BOT_QUESTIONS)
            }
        except Exception as e:
            logger.error(f"Error starting voice bot session: {str(e)}")
            raise
    
    def process_answer(self, session_id, user_input, input_type='text'):
        """Process user answer and move to next question"""
        if session_id not in self.active_sessions:
            raise ValueError("Session not found")
        
        session = self.active_sessions[session_id]
        call_id = session['call_id']
        current_q = session['current_question']
        
        # Detect intent using Dialogflow
        try:
            if input_type == 'audio':
                intent_result = self.dialogflow.detect_intent_audio(
                    session_id, user_input
                )
            else:
                intent_result = self.dialogflow.detect_intent(
                    session_id, user_input
                )
        except Exception as e:
            logger.error(f"Error detecting intent: {str(e)}")
            # Fallback to simple text matching
            intent_result = self.dialogflow._fallback_intent_detection(user_input)
        
        # Map intent to answer
        intent_name = intent_result['intent'].lower()
        if 'yes' in intent_name or 'affirmative' in intent_name:
            answer = 'yes'
        elif 'no' in intent_name or 'negative' in intent_name:
            answer = 'no'
        elif 'repeat' in intent_name:
            # Repeat current question
            return {
                'action': 'repeat',
                'question_text': VOICE_BOT_QUESTIONS[current_q],
                'question_number': current_q + 1
            }
        elif 'skip' in intent_name:
            answer = 'skipped'
        else:
            # Try to extract yes/no from query text
            query_lower = intent_result['query_text'].lower()
            if any(word in query_lower for word in ['yes', 'yeah', 'yep', 'sure', 'correct', 'ok', 'okay']):
                answer = 'yes'
            elif any(word in query_lower for word in ['no', 'nope', 'nah', 'incorrect', 'not']):
                answer = 'no'
            else:
                answer = 'unclear'
        
        # Save answer to database
        try:
            self.db.save_answer(
                call_id,
                current_q + 1,
                answer,
                intent_result.get('confidence', 0.5),
                intent_result.get('query_text', user_input)
            )
        except Exception as e:
            logger.error(f"Error saving answer to database: {str(e)}")
            # Continue even if database save fails
        
        session['answers'][current_q + 1] = answer
        
        # Move to next question
        next_question = current_q + 1
        
        if next_question < len(VOICE_BOT_QUESTIONS):
            session['current_question'] = next_question
            
            # Save next question to database
            try:
                self.db.save_question(
                    call_id,
                    VOICE_BOT_QUESTIONS[next_question],
                    next_question + 1
                )
            except Exception as e:
                logger.error(f"Error saving question to database: {str(e)}")
            
            return {
                'action': 'next',
                'question_text': VOICE_BOT_QUESTIONS[next_question],
                'question_number': next_question + 1,
                'total_questions': len(VOICE_BOT_QUESTIONS),
                'previous_answer': answer
            }
        else:
            # All questions completed
            try:
                self.db.complete_call(call_id)
            except Exception as e:
                logger.error(f"Error completing call: {str(e)}")
            
            # Generate results
            try:
                results = self.db.get_call_results_json(call_id)
            except Exception as e:
                logger.error(f"Error getting call results: {str(e)}")
                results = {
                    'call_id': call_id,
                    'questions': [
                        {
                            'question_number': q_num,
                            'question': VOICE_BOT_QUESTIONS[q_num - 1],
                            'answer': session['answers'].get(q_num, 'unanswered')
                        }
                        for q_num in range(1, len(VOICE_BOT_QUESTIONS) + 1)
                    ]
                }
            
            # Clean up session
            del self.active_sessions[session_id]
            
            return {
                'action': 'complete',
                'call_id': call_id,
                'results': results
            }
    
    def get_session(self, session_id):
        """Get session information"""
        if session_id not in self.active_sessions:
            return None
        return self.active_sessions[session_id]


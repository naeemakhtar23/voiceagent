"""
Standalone script to extract questions and answers from webhook log_id=2
Reads transcript data and extracts Q&A pairs without saving to database
"""
import json
import logging
import re
from database import Database
from elevenlabs_handler import ElevenLabsHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_qa_from_log(log_id=2):
    """Extract questions and answers from webhook log data"""
    try:
        # Initialize database and handler
        db = Database()
        elevenlabs_handler = ElevenLabsHandler()
        
        # Get webhook log data
        logger.info(f"Fetching webhook log data for log_id={log_id}")
        webhook_data_str = db.get_webhook_log_data(log_id)
        
        if not webhook_data_str:
            logger.error(f"No webhook data found for log_id={log_id}")
            return None
        
        # Parse JSON string
        try:
            if isinstance(webhook_data_str, str):
                data = json.loads(webhook_data_str)
            else:
                data = webhook_data_str
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing webhook data JSON: {str(e)}")
            return None
        
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
            logger.info(f"Available keys in data: {list(data.keys())}")
            if isinstance(messages_data, dict):
                logger.info(f"Available keys in data.data: {list(messages_data.keys())}")
            return None
        
        # Build full transcript and extract Q&A pairs
        full_transcript = []
        questions_and_answers = []
        question_num = 0
        current_question = None
        
        logger.info(f"Processing {len(messages)} messages to extract Q&A pairs...")
        
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
        logger.info("=" * 80)
        logger.info(f"📊 SUMMARY FOR LOG_ID={log_id}")
        logger.info("=" * 80)
        logger.info(f"Total messages processed: {len(messages)}")
        logger.info(f"Actual survey questions and answers found: {len(questions_and_answers)}")
        logger.info(f"Full transcript length: {len('\\n'.join(full_transcript))} characters")
        logger.info("")
        
        # Log each Q&A pair
        logger.info("ACTUAL SURVEY QUESTIONS AND ANSWERS:")
        logger.info("-" * 80)
        for qa in questions_and_answers:
            logger.info(f"Q{qa['question_number']}: {qa['question']}")
            logger.info(f"A{qa['question_number']}: {qa['answer']} (raw: {qa['raw_answer']})")
            logger.info("")
        
        logger.info("=" * 80)
        logger.info(f"✅ Successfully extracted {len(questions_and_answers)} actual survey Q&A pairs from log_id={log_id}")
        logger.info("=" * 80)
        
        # Return result (not saving to DB as requested)
        result = {
            'status': 'success',
            'log_id': log_id,
            'total_messages': len(messages),
            'questions_and_answers': questions_and_answers,
            'full_transcript': full_transcript,
            'transcript_text': '\n'.join(full_transcript)
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting questions and answers from log_id={log_id}: {str(e)}", exc_info=True)
        return None


if __name__ == '__main__':
    logger.info("Starting Q&A extraction from webhook log_id=2")
    result = extract_qa_from_log(log_id=2)
    
    if result:
        logger.info("Extraction completed successfully!")
        logger.info(f"Found {len(result['questions_and_answers'])} Q&A pairs")
    else:
        logger.error("Extraction failed!")


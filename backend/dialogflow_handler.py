"""
Dialogflow ES Handler for Voice Bot
Handles Dialogflow integration for voice-based form filling
"""
import os
import logging
from config import DIALOGFLOW_PROJECT_ID, DIALOGFLOW_LANGUAGE_CODE

logger = logging.getLogger(__name__)

# Try to import Dialogflow, but handle gracefully if not installed
try:
    from google.cloud import dialogflow
    DIALOGFLOW_AVAILABLE = True
except ImportError:
    DIALOGFLOW_AVAILABLE = False
    logger.warning("google-cloud-dialogflow not installed. Install with: pip install google-cloud-dialogflow")


class DialogflowHandler:
    def __init__(self):
        self.project_id = DIALOGFLOW_PROJECT_ID
        self.language_code = DIALOGFLOW_LANGUAGE_CODE or 'en'
        self.session_client = None
        
        if not DIALOGFLOW_AVAILABLE:
            logger.warning("Dialogflow not available - install google-cloud-dialogflow")
            return
        
        if not self.project_id:
            logger.warning("DIALOGFLOW_PROJECT_ID not set in config")
            return
        
        try:
            # Initialize Dialogflow session client
            self.session_client = dialogflow.SessionsClient()
            logger.info("Dialogflow handler initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Dialogflow: {str(e)}")
            logger.warning("Dialogflow will not be available. Set GOOGLE_APPLICATION_CREDENTIALS environment variable with path to service account JSON key.")
            self.session_client = None
    
    def is_available(self):
        """Check if Dialogflow is available and configured"""
        return DIALOGFLOW_AVAILABLE and self.session_client is not None and self.project_id
    
    def detect_intent(self, session_id, text, language_code=None):
        """Detect intent from user input text"""
        if not self.is_available():
            # Fallback: simple text matching
            return self._fallback_intent_detection(text)
        
        try:
            session = self.session_client.session_path(
                self.project_id, session_id
            )
            
            text_input = dialogflow.TextInput(
                text=text, language_code=language_code or self.language_code
            )
            query_input = dialogflow.QueryInput(text=text_input)
            
            response = self.session_client.detect_intent(
                request={"session": session, "query_input": query_input}
            )
            
            return {
                'intent': response.query_result.intent.display_name,
                'confidence': response.query_result.intent_detection_confidence,
                'fulfillment_text': response.query_result.fulfillment_text,
                'query_text': response.query_result.query_text
            }
        except Exception as e:
            logger.error(f"Error detecting intent: {str(e)}")
            # Fallback to simple matching
            return self._fallback_intent_detection(text)
    
    def detect_intent_audio(self, session_id, audio_bytes, language_code=None):
        """Detect intent from audio input (non-streaming)"""
        if not self.is_available():
            logger.warning("Dialogflow not available for audio detection")
            return {'intent': 'unknown', 'confidence': 0.0, 'fulfillment_text': '', 'query_text': ''}
        
        try:
            session = self.session_client.session_path(
                self.project_id, session_id
            )
            
            audio_input = dialogflow.InputAudio(
                audio=audio_bytes
            )
            query_input = dialogflow.QueryInput(audio=audio_input)
            
            response = self.session_client.detect_intent(
                request={
                    "session": session,
                    "query_input": query_input,
                    "input_audio_config": {
                        "audio_encoding": dialogflow.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
                        "sample_rate_hertz": 16000,
                        "language_code": language_code or self.language_code
                    }
                }
            )
            
            return {
                'intent': response.query_result.intent.display_name,
                'confidence': response.query_result.intent_detection_confidence,
                'fulfillment_text': response.query_result.fulfillment_text,
                'query_text': response.query_result.query_text
            }
        except Exception as e:
            logger.error(f"Error detecting intent from audio: {str(e)}")
            return {'intent': 'unknown', 'confidence': 0.0, 'fulfillment_text': '', 'query_text': ''}
    
    def detect_intent_streaming(self, session_id, audio_chunks_generator, language_code=None):
        """
        Detect intent from streaming audio input
        This is the recommended approach for capturing the first utterance
        
        Args:
            session_id: Dialogflow session ID
            audio_chunks_generator: Generator that yields audio chunks (bytes)
            language_code: Language code (defaults to configured language)
        
        Returns:
            dict with intent, confidence, fulfillment_text, query_text
        """
        if not self.is_available():
            logger.warning("Dialogflow not available for streaming audio detection")
            return {'intent': 'unknown', 'confidence': 0.0, 'fulfillment_text': '', 'query_text': ''}
        
        try:
            from google.cloud.dialogflow import StreamingDetectIntentRequest
            from google.cloud.dialogflow import InputAudioConfig
            from google.cloud.dialogflow import QueryInput
            from google.cloud.dialogflow import StreamingDetectIntentResponse
            
            session = self.session_client.session_path(
                self.project_id, session_id
            )
            
            # Configure audio input
            audio_config = InputAudioConfig(
                audio_encoding=dialogflow.AudioEncoding.AUDIO_ENCODING_LINEAR_16,
                sample_rate_hertz=16000,
                language_code=language_code or self.language_code
            )
            
            query_input = QueryInput(audio_config=audio_config)
            
            # Create streaming request generator
            def request_generator():
                # First request: configuration
                yield StreamingDetectIntentRequest(
                    session=session,
                    query_input=query_input,
                    single_utterance=True,  # CRITICAL: This captures short words like "yes" instantly
                    output_audio_config=None
                )
                
                # Subsequent requests: audio chunks
                for audio_chunk in audio_chunks_generator:
                    yield StreamingDetectIntentRequest(
                        input_audio=audio_chunk
                    )
            
            # Use streaming detect intent
            responses = self.session_client.streaming_detect_intent(requests=request_generator())
            
            # Process responses
            final_result = None
            for response in responses:
                if response.recognition_result:
                    logger.info(f"Recognition result: {response.recognition_result}")
                
                if response.query_result:
                    final_result = {
                        'intent': response.query_result.intent.display_name if response.query_result.intent else 'unknown',
                        'confidence': response.query_result.intent_detection_confidence,
                        'fulfillment_text': response.query_result.fulfillment_text,
                        'query_text': response.query_result.query_text,
                        'is_final': response.query_result.intent_detection_confidence > 0.0
                    }
                    # If we got a confident result, return it immediately
                    if final_result['is_final'] and final_result['confidence'] > 0.5:
                        logger.info(f"Got final result: {final_result}")
                        return final_result
            
            return final_result or {'intent': 'unknown', 'confidence': 0.0, 'fulfillment_text': '', 'query_text': ''}
            
        except Exception as e:
            logger.error(f"Error detecting intent from streaming audio: {str(e)}", exc_info=True)
            return {'intent': 'unknown', 'confidence': 0.0, 'fulfillment_text': '', 'query_text': ''}
    
    def _fallback_intent_detection(self, text):
        """Fallback intent detection using simple text matching"""
        text_lower = text.lower().strip()
        
        # Yes detection
        yes_words = ['yes', 'yeah', 'yep', 'sure', 'correct', 'affirmative', 'ok', 'okay', 'yup', 'right']
        if any(word in text_lower for word in yes_words):
            return {
                'intent': 'yes',
                'confidence': 0.8,
                'fulfillment_text': 'Yes',
                'query_text': text
            }
        
        # No detection
        no_words = ['no', 'nope', 'nah', 'incorrect', 'negative', 'wrong', 'not']
        if any(word in text_lower for word in no_words):
            return {
                'intent': 'no',
                'confidence': 0.8,
                'fulfillment_text': 'No',
                'query_text': text
            }
        
        # Repeat detection
        repeat_words = ['repeat', 'again', 'say that again', 'what was the question', 'can you repeat']
        if any(word in text_lower for word in repeat_words):
            return {
                'intent': 'repeat',
                'confidence': 0.8,
                'fulfillment_text': 'Repeat',
                'query_text': text
            }
        
        # Skip detection
        skip_words = ['skip', 'next', 'pass', 'move on', 'continue']
        if any(word in text_lower for word in skip_words):
            return {
                'intent': 'skip',
                'confidence': 0.8,
                'fulfillment_text': 'Skip',
                'query_text': text
            }
        
        # Default to unclear
        return {
            'intent': 'unclear',
            'confidence': 0.3,
            'fulfillment_text': 'I did not understand that. Please say yes or no.',
            'query_text': text
        }


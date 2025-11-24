"""
Demo mode for Voice Call System
Simulates calls without requiring ngrok or real Twilio calls
Perfect for management presentations
"""
import json
import time
import random
from datetime import datetime
from database import Database

class DemoMode:
    def __init__(self):
        try:
            self.db = Database()
            self.db_available = True
        except Exception as e:
            # Database not available, but demo mode can still work
            self.db = None
            self.db_available = False
    
    def simulate_call(self, phone_number, questions):
        """Simulate a complete call flow"""
        try:
            call_id = random.randint(1000, 9999)
            call_sid = f"CA_DEMO_{call_id}_{random.randint(100000, 999999)}"
            
            # Try to use database if available
            if self.db_available and self.db:
                try:
                    call_id = self.db.create_call(phone_number, questions)
                    self.db.update_call_sid(call_id, call_sid)
                    self.db.update_call_status(call_sid, "ringing")
                    time.sleep(0.5)
                    self.db.update_call_status(call_sid, "in-progress")
                    self.db.update_call_status(call_sid, "completed")
                except Exception as db_error:
                    # Database failed, continue without it
                    self.db_available = False
            
            # Simulate answers
            answers = ["yes", "no", "yes", "no", "yes"]  # Sample answers
            question_responses = []
            
            for idx, question in enumerate(questions):
                answer = answers[idx % len(answers)]
                confidence = round(random.uniform(0.85, 0.98), 2)
                
                question_responses.append({
                    'question_number': idx + 1,
                    'question': question.get('text', ''),
                    'answer': answer,
                    'confidence': confidence,
                    'raw_response': answer,
                    'response_time_seconds': random.randint(2, 5)
                })
                
                # Try to save to database if available
                if self.db_available and self.db:
                    try:
                        self.db.save_question(call_id, question.get('text', ''), idx)
                        self.db.save_answer(
                            call_id=call_id,
                            question_num=idx,
                            answer=answer,
                            confidence=confidence,
                            raw_response=answer
                        )
                    except:
                        pass  # Continue even if DB save fails
            
            # Generate results JSON
            yes_count = sum(1 for q in question_responses if q['answer'] == 'yes')
            no_count = sum(1 for q in question_responses if q['answer'] == 'no')
            
            results = {
                'call_id': call_id,
                'phone_number': phone_number,
                'call_sid': call_sid,
                'status': 'completed',
                'started_at': datetime.now().isoformat(),
                'ended_at': datetime.now().isoformat(),
                'duration_seconds': len(questions) * 3 + 5,
                'timestamp': datetime.now().isoformat(),
                'questions': question_responses,
                'summary': {
                    'total_questions': len(questions),
                    'yes_count': yes_count,
                    'no_count': no_count,
                    'unclear_count': 0
                }
            }
            
            # Try to save results to database if available
            if self.db_available and self.db:
                try:
                    self.db.save_call_results(call_id, results)
                except:
                    pass  # Continue even if DB save fails
            
            return {
                'success': True,
                'call_id': call_id,
                'call_sid': call_sid,
                'message': 'Demo call simulated successfully',
                'results': results
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


"""
Database connection and operations for Voice Call System
Handles SQL Server database interactions
"""
import pyodbc
import json
from datetime import datetime
from config import DB_CONNECTION_STRING
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.connection_string = DB_CONNECTION_STRING
        self.conn = None
    
    def get_connection(self):
        """Get database connection"""
        try:
            # Check if connection exists and is still valid
            if self.conn is not None:
                try:
                    # Test if connection is still alive
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    return self.conn
                except (pyodbc.Error, AttributeError):
                    # Connection is stale, close it and create a new one
                    logger.warning("Database connection is stale, reconnecting...")
                    try:
                        self.conn.close()
                    except:
                        pass
                    self.conn = None
            
            # Create new connection
            if self.conn is None:
                try:
                    self.conn = pyodbc.connect(self.connection_string)
                    logger.info("Database connection established successfully")
                except pyodbc.Error as e:
                    logger.error(f"Database connection error: {str(e)}")
                    logger.error(f"Connection string: {self.connection_string[:50]}...")
                    raise
            return self.conn
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def test_connection(self):
        """Test database connection"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def execute(self, query, params=None):
        """Execute a query"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise
    
    def fetch_one(self, query, params=None):
        """Fetch one row"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            return row
        except Exception as e:
            logger.error(f"Fetch error: {str(e)}")
            raise
    
    def fetch_all(self, query, params=None):
        """Fetch all rows"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if not cursor.description:
                cursor.close()
                logger.warning("No column description available for query")
                return []
            
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            
            # Convert to list of dictionaries
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            return result
        except Exception as e:
            logger.error(f"Fetch all error: {str(e)}")
            raise
    
    # Call Management Methods
    def create_call(self, phone_number, questions_json=None):
        """Create a new call record"""
        query = """
        INSERT INTO calls (phone_number, status, questions_json, created_at)
        OUTPUT INSERTED.id
        VALUES (?, 'initiated', ?, GETDATE())
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (phone_number, json.dumps(questions_json) if questions_json else None))
            call_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            logger.info(f"Call created: ID={call_id}, Phone={phone_number}")
            return call_id
        except Exception as e:
            logger.error(f"Error creating call: {str(e)}")
            raise
    
    def update_call_sid(self, call_id, call_sid):
        """Update call with Twilio Call SID"""
        query = """
        UPDATE calls 
        SET call_sid = ?, status = 'ringing', started_at = GETDATE()
        WHERE id = ?
        """
        self.execute(query, (call_sid, call_id))
    
    def update_call_status(self, call_sid, status):
        """Update call status"""
        query = """
        UPDATE calls 
        SET status = ?
        WHERE call_sid = ?
        """
        self.execute(query, (status, call_sid))
    
    def complete_call(self, call_id):
        """Mark call as completed"""
        query = """
        UPDATE calls 
        SET status = 'completed', ended_at = GETDATE(),
            duration_seconds = DATEDIFF(SECOND, started_at, GETDATE())
        WHERE id = ?
        """
        self.execute(query, (call_id,))
    
    def get_call_data(self, call_id):
        """Get call data including questions"""
        query = """
        SELECT id, phone_number, call_sid, status, questions_json, 
               started_at, ended_at, duration_seconds, created_at
        FROM calls
        WHERE id = ?
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (call_id,))
            row = cursor.fetchone()
            
            if row:
                # Get column names BEFORE closing cursor
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    cursor.close()
                    # Convert row to dictionary
                    return dict(zip(columns, row))
                else:
                    cursor.close()
                    logger.warning(f"No column description available for call_id {call_id}")
                    return None
            cursor.close()
            return None
        except Exception as e:
            logger.error(f"Error getting call data: {str(e)}")
            raise
    
    # Question Management Methods
    def save_question(self, call_id, question_text, question_number):
        """Save question to database"""
        query = """
        INSERT INTO questions (call_id, question_text, question_number, created_at)
        VALUES (?, ?, ?, GETDATE())
        """
        self.execute(query, (call_id, question_text, question_number))
    
    def save_answer(self, call_id, question_num, answer, confidence, raw_response):
        """Save answer to a question"""
        query = """
        UPDATE questions 
        SET response = ?, response_confidence = ?, raw_response = ?,
            response_time_seconds = DATEDIFF(SECOND, created_at, GETDATE())
        WHERE call_id = ? AND question_number = ?
        """
        self.execute(query, (answer, confidence, raw_response, call_id, question_num))
    
    def get_call_questions(self, call_id):
        """Get all questions for a call"""
        query = """
        SELECT question_number, question_text, response, response_confidence,
               raw_response, response_time_seconds
        FROM questions
        WHERE call_id = ?
        ORDER BY question_number
        """
        return self.fetch_all(query, (call_id,))
    
    # Results Management
    def save_call_results(self, call_id, json_response):
        """Save final JSON results"""
        query = """
        INSERT INTO call_results (call_id, json_response, created_at)
        VALUES (?, ?, GETDATE())
        """
        self.execute(query, (call_id, json.dumps(json_response)))
    
    def get_call_results_json(self, call_id):
        """Generate and return call results as JSON"""
        try:
            # Get call info
            call_data = self.get_call_data(call_id)
            if not call_data:
                logger.warning(f"No call data found for call_id {call_id}")
                return None
            
            # Get questions and answers
            questions = self.get_call_questions(call_id)
            
            # Format as JSON with safe handling of None values
            json_response = {
                'call_id': call_id,
                'phone_number': call_data.get('phone_number', ''),
                'call_sid': call_data.get('call_sid', ''),
                'status': call_data.get('status', 'unknown'),
                'started_at': call_data['started_at'].isoformat() if call_data.get('started_at') else None,
                'ended_at': call_data['ended_at'].isoformat() if call_data.get('ended_at') else None,
                'duration_seconds': call_data.get('duration_seconds', 0),
                'timestamp': datetime.now().isoformat(),
                'questions': [
                    {
                        'question_number': q.get('question_number', 0),
                        'question': q.get('question_text', ''),
                        'answer': q.get('response', ''),
                        'confidence': float(q['response_confidence']) if q.get('response_confidence') else None,
                        'raw_response': q.get('raw_response', ''),
                        'response_time_seconds': q.get('response_time_seconds', 0)
                    }
                    for q in questions
                ],
                'summary': {
                    'total_questions': len(questions),
                    'yes_count': sum(1 for q in questions if q.get('response') == 'yes'),
                    'no_count': sum(1 for q in questions if q.get('response') == 'no'),
                    'unclear_count': sum(1 for q in questions if q.get('response') not in ['yes', 'no'])
                }
            }
            
            # Save to database
            try:
                self.save_call_results(call_id, json_response)
            except Exception as save_error:
                logger.warning(f"Could not save call results to database: {str(save_error)}")
                # Continue - results are still returned
            
            return json_response
        except Exception as e:
            logger.error(f"Error generating call results JSON: {str(e)}")
            raise
    
    def get_all_calls(self):
        """Get all calls for dashboard"""
        query = """
        SELECT id, phone_number, call_sid, status, 
               started_at, ended_at, duration_seconds, created_at
        FROM calls
        ORDER BY created_at DESC
        """
        return self.fetch_all(query)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


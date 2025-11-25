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
    
    def get_call_id_by_sid(self, call_sid):
        """Get call_id (database ID) by call_sid"""
        query = """
        SELECT id
        FROM calls
        WHERE call_sid = ?
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (call_sid,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return row[0]
            return None
        except Exception as e:
            logger.error(f"Error getting call_id by call_sid: {str(e)}")
            return None
    
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
    
    # Webhook Logs Management
    def save_webhook_log(self, event_type, conversation_id, call_id, call_sid, webhook_data, processed_successfully=True, error_message=None):
        """Save complete webhook response to logs table"""
        query = """
        INSERT INTO webhook_logs (event_type, conversation_id, call_id, call_sid, 
                                  webhook_data, processed_successfully, error_message, created_at)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())
        """
        try:
            # Convert webhook_data to JSON string if it's a dict
            if isinstance(webhook_data, dict):
                webhook_json = json.dumps(webhook_data, default=str, ensure_ascii=False)
            elif isinstance(webhook_data, str):
                webhook_json = webhook_data
            else:
                webhook_json = str(webhook_data)
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (
                event_type,
                conversation_id,
                call_id,
                call_sid,
                webhook_json,
                1 if processed_successfully else 0,
                error_message
            ))
            row = cursor.fetchone()
            log_id = row[0] if row else None
            conn.commit()
            cursor.close()
            logger.info(f"✅ Webhook log saved: event_type={event_type}, conversation_id={conversation_id}, log_id={log_id}")
            return log_id
        except Exception as e:
            logger.error(f"Error saving webhook log: {str(e)}")
            # Don't raise - we don't want webhook logging to break the webhook handler
            return None
    
    def get_webhook_logs(self, conversation_id=None, call_id=None, event_type=None, limit=100):
        """Get webhook logs with optional filters"""
        query = """
        SELECT id, event_type, conversation_id, call_id, call_sid, 
               processed_successfully, error_message, created_at
        FROM webhook_logs
        WHERE 1=1
        """
        params = []
        
        if conversation_id:
            query += " AND conversation_id = ?"
            params.append(conversation_id)
        
        if call_id:
            query += " AND call_id = ?"
            params.append(call_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"
        
        return self.fetch_all(query, tuple(params) if params else None)
    
    def get_webhook_log_data(self, log_id):
        """Get full webhook data for a specific log entry"""
        query = """
        SELECT webhook_data
        FROM webhook_logs
        WHERE id = ?
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (log_id,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return row[0]
            return None
        except Exception as e:
            logger.error(f"Error getting webhook log data: {str(e)}")
            return None
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


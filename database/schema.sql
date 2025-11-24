-- Voice Call System Database Schema
-- SQL Server Database: ePRF
-- This script creates all necessary tables for the Voice Call System

USE ePRF;
GO

-- Check if tables exist and drop them if they do
IF OBJECT_ID('call_results', 'U') IS NOT NULL
    DROP TABLE call_results;
GO

IF OBJECT_ID('questions', 'U') IS NOT NULL
    DROP TABLE questions;
GO

IF OBJECT_ID('calls', 'U') IS NOT NULL
    DROP TABLE calls;
GO

-- Calls table - stores call information
CREATE TABLE calls (
    id INT PRIMARY KEY IDENTITY(1,1),
    phone_number VARCHAR(20) NOT NULL,
    call_sid VARCHAR(100),
    status VARCHAR(50) DEFAULT 'initiated',
    questions_json NVARCHAR(MAX),
    started_at DATETIME,
    ended_at DATETIME,
    duration_seconds INT,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- Questions table - stores individual questions and their responses
CREATE TABLE questions (
    id INT PRIMARY KEY IDENTITY(1,1),
    call_id INT NOT NULL FOREIGN KEY REFERENCES calls(id) ON DELETE CASCADE,
    question_text NVARCHAR(500),
    question_number INT NOT NULL,
    response VARCHAR(10), -- 'yes', 'no', 'unclear', 'timeout'
    response_confidence DECIMAL(5,2),
    raw_response NVARCHAR(200),
    response_time_seconds INT,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- Call results table - stores final JSON responses
CREATE TABLE call_results (
    id INT PRIMARY KEY IDENTITY(1,1),
    call_id INT NOT NULL FOREIGN KEY REFERENCES calls(id) ON DELETE CASCADE,
    json_response NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- Create indexes for better performance
CREATE INDEX IX_calls_phone_number ON calls(phone_number);
CREATE INDEX IX_calls_call_sid ON calls(call_sid);
CREATE INDEX IX_calls_status ON calls(status);
CREATE INDEX IX_calls_created_at ON calls(created_at);
GO

CREATE INDEX IX_questions_call_id ON questions(call_id);
CREATE INDEX IX_questions_question_number ON questions(call_id, question_number);
GO

CREATE INDEX IX_call_results_call_id ON call_results(call_id);
GO

-- Insert sample data (optional - for testing)
-- Uncomment below if you want sample data

/*
INSERT INTO calls (phone_number, status, questions_json, created_at)
VALUES 
    ('+1234567890', 'completed', 
     '[{"text": "Do you have health insurance?"}, {"text": "Are you taking medications?"}]',
     GETDATE());
GO
*/

PRINT 'Database schema created successfully!';
PRINT 'Tables created: calls, questions, call_results';
PRINT 'Indexes created for optimal performance';
GO


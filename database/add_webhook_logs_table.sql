-- Add webhook_logs table to store complete ElevenLabs webhook responses
-- This allows us to save full webhook data that may be truncated in terminal logs

USE ePRF;
GO

-- Check if table exists and drop it if it does
IF OBJECT_ID('webhook_logs', 'U') IS NOT NULL
    DROP TABLE webhook_logs;
GO

-- Webhook logs table - stores complete webhook responses from ElevenLabs
CREATE TABLE webhook_logs (
    id INT PRIMARY KEY IDENTITY(1,1),
    event_type VARCHAR(100),
    conversation_id VARCHAR(200),
    call_id VARCHAR(200),
    call_sid VARCHAR(200),
    webhook_data NVARCHAR(MAX), -- Complete JSON response
    processed_successfully BIT DEFAULT 0,
    error_message NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- Create indexes for better performance
CREATE INDEX IX_webhook_logs_event_type ON webhook_logs(event_type);
CREATE INDEX IX_webhook_logs_conversation_id ON webhook_logs(conversation_id);
CREATE INDEX IX_webhook_logs_call_id ON webhook_logs(call_id);
CREATE INDEX IX_webhook_logs_call_sid ON webhook_logs(call_sid);
CREATE INDEX IX_webhook_logs_created_at ON webhook_logs(created_at);
GO

PRINT 'webhook_logs table created successfully!';
PRINT 'Indexes created for optimal performance';
GO


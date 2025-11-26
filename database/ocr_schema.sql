-- OCR System Database Schema
-- SQL Server Database: ePRF
-- This script creates the OCR documents table

USE ePRF;
GO

-- Check if table exists and drop it if it does
IF OBJECT_ID('ocr_documents', 'U') IS NOT NULL
    DROP TABLE ocr_documents;
GO

-- OCR documents table - stores document text and extracted data
CREATE TABLE ocr_documents (
    id INT PRIMARY KEY IDENTITY(1,1),
    document_text NVARCHAR(MAX), -- Original document text from OCR
    ExtractedData NVARCHAR(MAX), -- Extracted structured data (JSON format)
    ParametersList NVARCHAR(MAX), -- List of parameters extracted (JSON format)
    RefinedDocumentText NVARCHAR(MAX), -- Refined/cleaned document text
    file_name VARCHAR(500), -- Original file name
    file_type VARCHAR(50), -- File type (pdf, image, etc.)
    file_size BIGINT, -- File size in bytes
    status VARCHAR(50) DEFAULT 'uploaded', -- Status: uploaded, processing, completed, error
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);
GO

-- Create indexes for better performance
CREATE INDEX IX_ocr_documents_status ON ocr_documents(status);
CREATE INDEX IX_ocr_documents_created_at ON ocr_documents(created_at);
CREATE INDEX IX_ocr_documents_file_name ON ocr_documents(file_name);
GO

PRINT 'OCR documents table created successfully!';
PRINT 'Table created: ocr_documents';
PRINT 'Indexes created for optimal performance';
GO


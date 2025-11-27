"""
Text Extraction Handler - Extract text only using PyMuPDF (fitz)
No parameter extraction, just clean text in reading order
"""
import os
import logging
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


class TextExtractionHandler:
    def __init__(self):
        self.upload_folder = UPLOAD_FOLDER
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def save_uploaded_file(self, file, filename):
        """Save uploaded file to uploads folder"""
        secure_name = secure_filename(filename)
        file_path = os.path.join(self.upload_folder, secure_name)
        file.save(file_path)
        logger.info(f"File saved to: {file_path}")
        return file_path
    
    def extract_text_from_pdf_pymupdf(self, pdf_path):
        """
        Extract text from PDF using PyMuPDF (fitz) in reading order
        This provides highest-quality text extraction with layout awareness
        """
        try:
            import fitz  # PyMuPDF
            logger.info(f"Extracting text from PDF using PyMuPDF: {pdf_path}")
            
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            logger.info(f"PDF has {num_pages} pages")
            
            all_text = []
            
            for page_num in range(num_pages):
                page = doc[page_num]
                # Extract text in reading order (sort=True for proper reading order)
                text = page.get_text(sort=True)
                if text.strip():
                    all_text.append(text)
                    logger.info(f"Extracted text from page {page_num + 1}/{num_pages}")
            
            doc.close()
            
            # Join all pages with double newline
            full_text = '\n\n'.join(all_text)
            logger.info(f"✅ Successfully extracted text from {num_pages} pages")
            return full_text
            
        except ImportError:
            logger.error("PyMuPDF (fitz) is not installed. Please install it: pip install PyMuPDF")
            raise ImportError("PyMuPDF (fitz) is required for text extraction")
        except Exception as e:
            logger.error(f"Error extracting text from PDF with PyMuPDF: {str(e)}")
            raise
    
    def extract_text_from_image(self, image_path):
        """Extract text from image using PyMuPDF (for PDF pages converted to images)"""
        # For images, we still need OCR, but user wants text-only
        # You can use pytesseract or PaddleOCR here if needed
        # For now, return empty as this handler focuses on PDF text extraction
        logger.warning("Image text extraction not implemented in text-only handler")
        return ""
    
    def process_document(self, file_path, file_type):
        """Process document and extract text only (no parameters)"""
        try:
            if file_type.lower() == 'pdf':
                document_text = self.extract_text_from_pdf_pymupdf(file_path)
            elif file_type.lower() in ['png', 'jpg', 'jpeg']:
                # For images, you might want to add OCR here
                # But user specifically asked for PDF text extraction
                document_text = self.extract_text_from_image(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            return document_text
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise
    
    def process_uploaded_document(self, file, filename):
        """
        Process uploaded document: save, extract text only
        Returns dictionary with extracted text (NO parameters list)
        """
        try:
            # Get file extension
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            file_type = file_ext
            
            # Save file
            file_path = self.save_uploaded_file(file, filename)
            
            # Process document and extract text only
            logger.info(f"Processing document for text extraction: {filename}")
            document_text = self.process_document(file_path, file_type)
            
            return {
                'document_text': document_text,
                'extracted_data': None,  # No structured data extraction
                'parameters_list': None,  # NO parameters list as requested
                'refined_text': document_text,  # Use same text as refined
                'file_path': file_path,
                'file_size': os.path.getsize(file_path)
            }
        except Exception as e:
            logger.error(f"Error processing uploaded document: {str(e)}")
            raise


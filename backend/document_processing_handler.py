"""
Document Processing Handler - Extract text and tables from PDF
Uses PyMuPDF for text (sort=True) and tables (find_tables())
Falls back to pdfplumber for complex tables
"""
import os
import logging
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


class DocumentProcessingHandler:
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
    
    def extract_text_pymupdf(self, pdf_path):
        """
        Extract text from PDF using PyMuPDF in reading order
        Uses page.get_text(sort=True) for proper reading order
        """
        try:
            import fitz  # PyMuPDF
            logger.info(f"Extracting text from PDF using PyMuPDF (sort=True): {pdf_path}")
            
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            logger.info(f"PDF has {num_pages} pages")
            
            all_text = []
            
            for page_num in range(num_pages):
                page = doc[page_num]
                # Extract text in reading order (sort=True)
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
    
    def extract_tables_pymupdf(self, pdf_path):
        """
        Extract tables from PDF using PyMuPDF's native table extraction (1.23+)
        Returns list of tables as dictionaries
        """
        try:
            import fitz  # PyMuPDF
            import pandas as pd
            
            logger.info(f"Extracting tables from PDF using PyMuPDF find_tables(): {pdf_path}")
            
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            logger.info(f"PDF has {num_pages} pages")
            
            all_tables = []
            table_index = 0
            
            for page_num in range(num_pages):
                page = doc[page_num]
                
                # Use PyMuPDF's native table finder (available in 1.23+)
                try:
                    tables = page.find_tables()
                    logger.info(f"Page {page_num + 1}: Found {len(tables)} tables using PyMuPDF")
                    
                    for table_idx, table in enumerate(tables):
                        try:
                            # Extract table data
                            table_data = table.extract()
                            
                            if table_data and len(table_data) > 0:
                                # First row as headers
                                headers = table_data[0] if len(table_data) > 0 else []
                                rows = table_data[1:] if len(table_data) > 1 else []
                                
                                # Convert to DataFrame for easier handling
                                df = pd.DataFrame(rows, columns=headers)
                                
                                # Convert to dictionary format
                                table_dict = {
                                    'table_index': table_index + 1,
                                    'page': page_num + 1,
                                    'method': 'pymupdf',
                                    'headers': headers,
                                    'rows': df.values.tolist(),
                                    'row_count': len(df),
                                    'column_count': len(df.columns),
                                    'dataframe': df.to_dict('records')  # Also include as records
                                }
                                
                                all_tables.append(table_dict)
                                table_index += 1
                                logger.info(f"  Table {table_index}: {len(df)} rows x {len(df.columns)} columns")
                                
                        except Exception as table_error:
                            logger.warning(f"Error extracting table {table_idx + 1} from page {page_num + 1}: {str(table_error)}")
                            continue
                            
                except AttributeError:
                    # find_tables() not available in this PyMuPDF version
                    logger.warning(f"PyMuPDF find_tables() not available. Version might be < 1.23. Falling back to pdfplumber.")
                    doc.close()
                    return self.extract_tables_pdfplumber(pdf_path)
                except Exception as e:
                    logger.warning(f"Error using PyMuPDF find_tables() on page {page_num + 1}: {str(e)}")
                    continue
            
            doc.close()
            
            logger.info(f"✅ Successfully extracted {len(all_tables)} tables using PyMuPDF")
            return all_tables
            
        except ImportError:
            logger.error("PyMuPDF (fitz) is not installed. Please install it: pip install PyMuPDF")
            raise ImportError("PyMuPDF (fitz) is required for table extraction")
        except Exception as e:
            logger.error(f"Error extracting tables from PDF with PyMuPDF: {str(e)}")
            # Fallback to pdfplumber
            logger.info("Falling back to pdfplumber for table extraction...")
            return self.extract_tables_pdfplumber(pdf_path)
    
    def extract_tables_pdfplumber(self, pdf_path):
        """
        Extract tables from PDF using pdfplumber (fallback for complex tables)
        Returns list of tables as dictionaries
        """
        try:
            import pdfplumber
            import pandas as pd
            
            logger.info(f"Extracting tables from PDF using pdfplumber (fallback): {pdf_path}")
            
            all_tables = []
            table_index = 0
            
            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)
                logger.info(f"PDF has {num_pages} pages")
                
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    logger.info(f"Page {page_num + 1}: Found {len(tables)} tables using pdfplumber")
                    
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 0:
                            try:
                                # First row as headers
                                headers = table[0] if len(table) > 0 else []
                                rows = table[1:] if len(table) > 1 else []
                                
                                # Convert to DataFrame
                                df = pd.DataFrame(rows, columns=headers)
                                
                                # Convert to dictionary format
                                table_dict = {
                                    'table_index': table_index + 1,
                                    'page': page_num + 1,
                                    'method': 'pdfplumber',
                                    'headers': headers,
                                    'rows': df.values.tolist(),
                                    'row_count': len(df),
                                    'column_count': len(df.columns),
                                    'dataframe': df.to_dict('records')  # Also include as records
                                }
                                
                                all_tables.append(table_dict)
                                table_index += 1
                                logger.info(f"  Table {table_index}: {len(df)} rows x {len(df.columns)} columns")
                                
                            except Exception as table_error:
                                logger.warning(f"Error processing table {table_idx + 1} from page {page_num + 1}: {str(table_error)}")
                                continue
            
            logger.info(f"✅ Successfully extracted {len(all_tables)} tables using pdfplumber")
            return all_tables
            
        except ImportError:
            logger.error("pdfplumber is not installed. Please install it: pip install pdfplumber")
            raise ImportError("pdfplumber is required for table extraction fallback")
        except Exception as e:
            logger.error(f"Error extracting tables with pdfplumber: {str(e)}")
            raise
    
    def process_document(self, pdf_path):
        """
        Process PDF document: extract text and tables
        Uses PyMuPDF for text and tables, falls back to pdfplumber for complex tables
        Returns dictionary with text and tables
        """
        try:
            # Extract text using PyMuPDF (sort=True for reading order)
            document_text = self.extract_text_pymupdf(pdf_path)
            
            # Extract tables using PyMuPDF (with pdfplumber fallback)
            tables = self.extract_tables_pymupdf(pdf_path)
            
            return {
                'document_text': document_text,
                'tables': tables
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise
    
    def process_uploaded_document(self, file, filename):
        """
        Process uploaded PDF document: save, extract text and tables
        Returns dictionary with extracted data
        """
        try:
            # Save file
            file_path = self.save_uploaded_file(file, filename)
            
            # Process document
            logger.info(f"Processing document for text and table extraction: {filename}")
            result = self.process_document(file_path)
            
            # Format extracted data for database
            extracted_data = {
                'tables': result['tables'],
                'table_count': len(result['tables']),
                'extraction_method': 'pymupdf_with_pdfplumber_fallback'
            }
            
            return {
                'document_text': result['document_text'],
                'extracted_data': extracted_data,
                'parameters_list': None,  # No parameters list
                'refined_text': result['document_text'],
                'file_path': file_path,
                'file_size': os.path.getsize(file_path)
            }
        except Exception as e:
            logger.error(f"Error processing uploaded document: {str(e)}")
            raise


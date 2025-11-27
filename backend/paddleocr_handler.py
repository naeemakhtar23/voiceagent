"""
PaddleOCR Handler for document text extraction and processing
Separate implementation from Tesseract OCR
"""
import os
import json
import re
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import fitz  # PyMuPDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}


class PaddleOCRHandler:
    def __init__(self):
        self.upload_folder = UPLOAD_FOLDER
        self.ocr = None
        self._initialized = False
        # Don't initialize immediately - do it lazily when first needed
        # This allows the server to start even if PaddleOCR isn't installed
    
    def _parse_paddleocr_result(self, result):
        """
        Parse PaddleOCR result and group text by spatial proximity to form lines.
        Returns a list of text lines.
        """
        text_lines = []
        if not result:
            logger.warning("PaddleOCR result is None or empty")
            return text_lines
        
        # Log result structure for debugging
        logger.info(f"PaddleOCR result type: {type(result)}, length: {len(result) if hasattr(result, '__len__') else 'N/A'}")
        if isinstance(result, list) and len(result) > 0:
            logger.info(f"First element type: {type(result[0])}, length: {len(result[0]) if hasattr(result[0], '__len__') else 'N/A'}")
            if isinstance(result[0], list) and len(result[0]) > 0:
                logger.info(f"First detection type: {type(result[0][0])}, sample: {str(result[0][0])[:200]}")
            elif result[0] is None:
                logger.warning("First element of result is None")
        elif isinstance(result, list) and len(result) == 0:
            logger.warning("PaddleOCR result is an empty list")
        
        # Get detections - handle different result structures
        # PaddleOCR typically returns: [[[bbox, (text, confidence)], ...], ...] for multiple images
        # Or [[bbox, (text, confidence)], ...] for single image
        # Newer versions might return: [{'bbox': [...], 'text': '...', 'score': ...}, ...]
        detections = None
        
        if isinstance(result, list):
            if len(result) > 0:
                # Check if first element is a list of detections
                if isinstance(result[0], list):
                    if len(result[0]) > 0:
                        # Check if first detection is a list/tuple (standard format)
                        first_detection = result[0][0]
                        if isinstance(first_detection, (list, tuple)) and len(first_detection) >= 2:
                            detections = result[0]  # Standard format: result[0] contains detections
                            logger.info("Using standard PaddleOCR format: result[0] contains detections")
                        elif isinstance(first_detection, dict):
                            # New format: list of dictionaries
                            detections = result[0]
                            logger.info("Using dictionary format: result[0] contains dict detections")
                        else:
                            detections = result  # Alternative format
                            logger.info("Using alternative format: result itself contains detections")
                    else:
                        logger.warning("result[0] is an empty list")
                        detections = []
                elif isinstance(result[0], dict):
                    # New format: list of dictionaries directly
                    detections = result
                    logger.info("Using dictionary format: result contains dict detections directly")
                else:
                    detections = result
                    logger.info("Using result directly as detections")
            else:
                logger.warning("PaddleOCR result list is empty")
                return text_lines
        else:
            logger.warning(f"Unexpected PaddleOCR result type: {type(result)}")
            return text_lines
        
        if not detections:
            logger.warning("No detections found in PaddleOCR result")
            return text_lines
        
        logger.info(f"Found {len(detections)} detections to process")
        
        # Extract text with bounding boxes
        text_boxes = []
        detection_count = 0
        for detection in detections:
            if not detection:
                continue
            
            detection_count += 1
            # Get bounding box and text
            bbox = None
            text_info = None
            text = None
            
            # Handle different detection formats
            if isinstance(detection, dict):
                # New format: {'bbox': [...], 'text': '...', 'score': ...}
                bbox = detection.get('bbox')
                text = detection.get('text')
                if text:
                    text_info = (text, detection.get('score', 1.0))
                logger.debug(f"Detection {detection_count}: Dictionary format, text: {text[:50] if text else 'None'}")
            elif isinstance(detection, list) and len(detection) >= 2:
                bbox = detection[0]
                text_info = detection[1]
            elif isinstance(detection, tuple) and len(detection) >= 2:
                bbox = detection[0]
                text_info = detection[1]
            else:
                logger.warning(f"Detection {detection_count}: Unexpected format: {type(detection)}, value: {str(detection)[:100]}")
                continue
            
            # Extract text from text_info (if not already extracted from dict format)
            if text is None and text_info is not None:
                if isinstance(text_info, tuple) and len(text_info) >= 1:
                    text = text_info[0]
                elif isinstance(text_info, str):
                    text = text_info
                elif isinstance(text_info, list) and len(text_info) >= 1:
                    text = text_info[0]
                else:
                    logger.debug(f"Detection {detection_count}: Unexpected text_info format: {type(text_info)}, value: {str(text_info)[:100]}")
                    continue
            
            # Validate bbox structure
            if not bbox:
                logger.debug(f"Detection {detection_count}: No bbox found")
                continue
            
            # Check bbox format
            if isinstance(bbox, list) and len(bbox) >= 1:
                # bbox format: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                if isinstance(bbox[0], list) and len(bbox[0]) >= 2:
                    y_coord = bbox[0][1]
                    x_coord = bbox[0][0]
                else:
                    logger.debug(f"Detection {detection_count}: Invalid bbox format: {bbox}")
                    continue
            else:
                logger.debug(f"Detection {detection_count}: Invalid bbox type: {type(bbox)}")
                continue
            
            if text and isinstance(text, str) and text.strip():
                text_boxes.append({
                    'text': text.strip(),
                    'x': x_coord,
                    'y': y_coord,
                    'bbox': bbox
                })
                logger.debug(f"Detection {detection_count}: Extracted text: '{text[:50]}...' at ({x_coord}, {y_coord})")
            else:
                logger.debug(f"Detection {detection_count}: No valid text extracted, text: {text}, type: {type(text)}")
        
        logger.info(f"Processed {detection_count} detections, extracted {len(text_boxes)} text boxes")
        
        if not text_boxes:
            logger.warning(f"No text boxes extracted from {detection_count} detections. Trying alternative parsing...")
            # Try alternative parsing strategies
            logger.debug(f"Full result structure (first 1000 chars): {str(result)[:1000]}")
            
            # Fallback Strategy 1: Try recursive search for text in nested structures
            def extract_text_recursive(obj, texts=None):
                if texts is None:
                    texts = []
                if isinstance(obj, str) and len(obj.strip()) > 0:
                    # Found a string that might be text
                    if len(obj.strip()) > 1 or obj.strip().isalnum():
                        texts.append(obj.strip())
                elif isinstance(obj, (list, tuple)):
                    for item in obj:
                        extract_text_recursive(item, texts)
                elif isinstance(obj, dict):
                    for value in obj.values():
                        extract_text_recursive(value, texts)
                return texts
            
            try:
                fallback_texts = extract_text_recursive(result)
                if fallback_texts:
                    logger.info(f"Fallback extraction found {len(fallback_texts)} text strings")
                    # Group by approximate length (likely same line if similar)
                    text_lines = fallback_texts
                    return text_lines
            except Exception as e:
                logger.debug(f"Fallback recursive extraction failed: {str(e)}")
            
            return text_lines
        
        # Calculate adaptive Y-threshold based on text box heights
        # Use median height or a percentage of image height
        try:
            heights = []
            for tb in text_boxes:
                if isinstance(tb['bbox'], list) and len(tb['bbox']) >= 2:
                    # Calculate height from bbox
                    y_coords = [point[1] for point in tb['bbox'] if isinstance(point, list) and len(point) >= 2]
                    if y_coords:
                        height = max(y_coords) - min(y_coords)
                        heights.append(height)
            
            if heights:
                # Use 50% of median height as threshold, with min 5 and max 30 pixels
                median_height = sorted(heights)[len(heights) // 2]
                y_threshold = max(5, min(30, int(median_height * 0.5)))
            else:
                y_threshold = 15  # Default threshold
        except Exception:
            y_threshold = 15  # Fallback threshold
        
        # Group text boxes by Y-coordinate (same line if Y is within threshold)
        # Sort by Y first, then by X
        text_boxes.sort(key=lambda tb: (tb['y'], tb['x']))
        
        # Group into lines (Y-coordinate within threshold)
        lines = []
        current_line = []
        last_y = None
        
        for tb in text_boxes:
            if last_y is None or abs(tb['y'] - last_y) <= y_threshold:
                # Same line
                current_line.append(tb)
                # Update last_y to average of current line (better for slanted text)
                if current_line:
                    last_y = sum(t['y'] for t in current_line) / len(current_line)
            else:
                # New line
                if current_line:
                    # Sort current line by X coordinate
                    current_line.sort(key=lambda tb: tb['x'])
                    lines.append(current_line)
                current_line = [tb]
                last_y = tb['y']
        
        # Add last line
        if current_line:
            current_line.sort(key=lambda tb: tb['x'])
            lines.append(current_line)
        
        # Join text in each line with spaces
        for line in lines:
            line_text = ' '.join([tb['text'] for tb in line])
            if line_text.strip():
                text_lines.append(line_text.strip())
        
        # Fallback: if no lines were created, just join all text with spaces
        if not text_lines and text_boxes:
            logger.warning("Could not group text by lines, using fallback: joining all text")
            all_text = ' '.join([tb['text'] for tb in text_boxes])
            if all_text.strip():
                text_lines.append(all_text.strip())
        
        # Post-process: Merge label:value pairs that are split across lines
        # Pattern: "Label:" on one line, "Value" on next line -> "Label: Value"
        merged_lines = []
        i = 0
        while i < len(text_lines):
            current_line = text_lines[i]
            
            # Check if current line ends with colon (likely a label)
            # Also check for patterns like "Label :" or "Label:" with optional spaces
            if (current_line.rstrip().endswith(':') and i + 1 < len(text_lines)):
                next_line = text_lines[i + 1].strip()
                
                # Skip if next line is empty
                if not next_line:
                    merged_lines.append(current_line)
                    i += 1
                    continue
                
                # Check if next line is a value (not another label, not a section header)
                is_section_header = (
                    re.match(r'^[A-Z\s]{1,30}$', next_line) or  # All caps, likely header
                    re.match(r'^(Page \d+|Date Generated)', next_line, re.IGNORECASE)  # Page numbers, etc.
                )
                
                is_another_label = (
                    next_line.endswith(':') or
                    re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+:', next_line)  # "Provider Name:" pattern
                )
                
                if not is_section_header and not is_another_label:
                    # Merge them: "Label:" + "Value" -> "Label: Value"
                    merged_line = current_line.rstrip() + ' ' + next_line
                    merged_lines.append(merged_line)
                    i += 2  # Skip next line as it's been merged
                    continue
            
            merged_lines.append(current_line)
            i += 1
        
        return merged_lines
    
    def _initialize_paddleocr(self):
        """Initialize PaddleOCR (lazy initialization)"""
        if self._initialized:
            return
        
        try:
            from paddleocr import PaddleOCR
            # Initialize PaddleOCR with English language and table structure support
            # use_angle_cls=True enables text direction classification
            logger.info("Initializing PaddleOCR (this may take a moment on first use)...")
            try:
                # Try with table structure support first (if available)
                self.ocr = PaddleOCR(use_angle_cls=True, lang='en', use_table_structure=True)
                logger.info("PaddleOCR initialized with table structure support")
            except (TypeError, ValueError) as e:
                # If use_table_structure is not available in this version, use without it
                logger.info("Table structure support not available, using standard PaddleOCR")
                try:
                    self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
                except (TypeError, ValueError) as e2:
                    # Try with minimal parameters
                    logger.info("Trying minimal PaddleOCR initialization...")
                    self.ocr = PaddleOCR(lang='en')
            self._initialized = True
            logger.info("PaddleOCR initialized successfully")
        except ImportError:
            logger.error("PaddleOCR not installed. Install with: pip install paddleocr paddlepaddle")
            raise RuntimeError("PaddleOCR is not installed. Please install it using: pip install paddleocr paddlepaddle")
        except Exception as e:
            logger.error(f"Error initializing PaddleOCR: {str(e)}")
            raise
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def extract_text_from_image(self, image_path):
        """Extract text from image using PaddleOCR"""
        try:
            if not self._initialized:
                self._initialize_paddleocr()
            
            # Preprocess image with OpenCV for better OCR results
            try:
                import cv2
                import numpy as np
                img = cv2.imread(image_path)
                if img is not None:
                    # Convert to grayscale and apply threshold for better OCR
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)[1]
                    processed_img = cv2.medianBlur(thresh, 3)
                    # Save processed image temporarily
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                        cv2.imwrite(tmp_file.name, processed_img)
                        image_path = tmp_file.name
            except ImportError:
                logger.warning("OpenCV not available, skipping image preprocessing")
            except Exception as e:
                logger.warning(f"Image preprocessing failed: {str(e)}, using original image")
            
            # PaddleOCR returns list of results
            # Structure: [[[[x1, y1], [x2, y2], [x3, y3], [x4, y4]], (text, confidence)], ...]
            result = self.ocr.ocr(image_path)
            
            # Parse result and group text by spatial proximity
            text_lines = self._parse_paddleocr_result(result)
            
            extracted_text = '\n'.join(text_lines)
            logger.info(f"Extracted {len(text_lines)} text lines from image (total chars: {len(extracted_text)})")
            if len(text_lines) > 0:
                logger.debug(f"Sample extracted text (first 200 chars): {extracted_text[:200]}")
            return extracted_text
        except Exception as e:
            logger.error(f"Error extracting text from image with PaddleOCR: {str(e)}", exc_info=True)
            raise
    
    def extract_text_from_image_obj(self, image):
        """Extract text from PIL Image object using PaddleOCR"""
        try:
            if not self._initialized:
                self._initialize_paddleocr()
            
            # Ensure image is in RGB mode (PaddleOCR works best with RGB)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save image temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                image.save(tmp_file.name, 'PNG')
                tmp_path = tmp_file.name
            
            try:
                logger.debug(f"Calling PaddleOCR on temporary image: {tmp_path}")
                result = self.ocr.ocr(tmp_path)
                logger.debug(f"PaddleOCR result type: {type(result)}, length: {len(result) if result else 0}")
                
                # Parse result and group text by spatial proximity
                text_lines = self._parse_paddleocr_result(result)
                
                extracted_text = '\n'.join(text_lines)
                logger.info(f"Extracted {len(text_lines)} text lines from image object (total chars: {len(extracted_text)})")
                if not extracted_text.strip():
                    logger.warning("No text extracted from image - result structure might be different")
                    # Log more details about the result
                    if result:
                        logger.warning(f"Result is not None. Type: {type(result)}")
                        if isinstance(result, list):
                            logger.warning(f"Result is a list with {len(result)} elements")
                            if len(result) > 0:
                                logger.warning(f"First element type: {type(result[0])}, value: {str(result[0])[:500]}")
                    else:
                        logger.warning("Result is None or empty")
                elif len(text_lines) > 0:
                    logger.debug(f"Sample extracted text (first 200 chars): {extracted_text[:200]}")
                return extracted_text
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            logger.error(f"Error extracting text from image object with PaddleOCR: {str(e)}")
            raise
    
    def _extract_text_with_pdf2image(self, pdf_path):
        """Extract text from PDF using pdf2image and PaddleOCR (recommended for better table detection)"""
        all_text = []
        
        try:
            from pdf2image import convert_from_path
            
            # Convert PDF to images with high DPI for better OCR
            logger.info(f"Converting PDF to images with 300 DPI...")
            images = convert_from_path(pdf_path, dpi=300)
            num_pages = len(images)
            logger.info(f"Converted PDF to {num_pages} images")
            
            if not self._initialized:
                self._initialize_paddleocr()
            
            # Process each page
            for i, img in enumerate(images):
                page_num = i + 1
                logger.info(f"Processing PDF page {page_num}/{num_pages} with PaddleOCR")
                
                try:
                    # Convert PIL image to OpenCV format for preprocessing
                    import cv2
                    import numpy as np
                    open_cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    
                    # Preprocess image for better OCR
                    gray = cv2.cvtColor(open_cv_img, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)[1]
                    processed_img = cv2.medianBlur(thresh, 3)
                    
                    # Run PaddleOCR
                    result = self.ocr.ocr(processed_img)
                    
                    # Parse result and group text by spatial proximity
                    page_text_lines = self._parse_paddleocr_result(result)
                    
                    page_text = '\n'.join(page_text_lines)
                    if page_text and page_text.strip():
                        all_text.append(page_text)
                        logger.info(f"Page {page_num}: Extracted {len(page_text_lines)} text lines")
                    else:
                        logger.warning(f"Page {page_num}: No text extracted")
                        all_text.append("")
                        
                except ImportError:
                    # Fallback if OpenCV is not available
                    logger.warning("OpenCV not available, using PIL image directly")
                    page_text = self.extract_text_from_image_obj(img)
                    if page_text and page_text.strip():
                        all_text.append(page_text)
                    else:
                        all_text.append("")
                except Exception as ocr_error:
                    logger.error(f"PaddleOCR failed for page {page_num}: {str(ocr_error)}", exc_info=True)
                    all_text.append("")
            
            logger.info(f"✅ Successfully processed {num_pages} pages using PaddleOCR")
            return '\n\n'.join(all_text)
            
        except ImportError:
            logger.warning("pdf2image not available, falling back to PyMuPDF")
            return self._extract_text_with_pymupdf(pdf_path)
        except Exception as e:
            logger.error(f"Error in pdf2image extraction with PaddleOCR: {str(e)}")
            # Fallback to PyMuPDF
            logger.info("Falling back to PyMuPDF method...")
            return self._extract_text_with_pymupdf(pdf_path)
    
    def _extract_text_with_pymupdf(self, pdf_path):
        """Extract text from PDF using PyMuPDF and PaddleOCR (fallback method)"""
        all_text = []
        doc = None
        
        try:
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            logger.info(f"Opened PDF with {num_pages} pages using PyMuPDF for PaddleOCR")
            
            if not self._initialized:
                self._initialize_paddleocr()
            
            for page_num in range(num_pages):
                logger.info(f"Processing PDF page {page_num + 1}/{num_pages} with PaddleOCR")
                
                if doc.is_closed:
                    raise RuntimeError("PDF document was closed unexpectedly")
                
                page = doc[page_num]
                
                # Convert page to image with high resolution
                mat = fitz.Matrix(3.0, 3.0)  # 3x zoom for better quality
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                from io import BytesIO
                image = Image.open(BytesIO(img_data))
                
                # Ensure image is in RGB mode (PaddleOCR works best with RGB)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Extract text from image using PaddleOCR
                try:
                    page_text = self.extract_text_from_image_obj(image)
                    if page_text and page_text.strip():
                        all_text.append(page_text)
                        logger.info(f"Page {page_num + 1}: Extracted {len(page_text.splitlines())} lines")
                    else:
                        logger.warning(f"Page {page_num + 1}: No text extracted")
                        all_text.append("")
                except Exception as ocr_error:
                    logger.error(f"PaddleOCR failed for page {page_num + 1}: {str(ocr_error)}", exc_info=True)
                    all_text.append("")
                
                # Clean up resources
                image.close()
                pix = None
            
            logger.info(f"✅ Successfully processed {num_pages} pages using PaddleOCR")
            return '\n\n'.join(all_text)
            
        except Exception as e:
            logger.error(f"Error in PyMuPDF extraction with PaddleOCR: {str(e)}")
            raise
        finally:
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF by converting to images and using PaddleOCR"""
        logger.info("=" * 60)
        logger.info("=== STARTING PDF EXTRACTION WITH PADDLEOCR ===")
        logger.info(f"PDF path: {pdf_path}")
        logger.info("=" * 60)
        
        try:
            # Try pdf2image first (better for table detection)
            return self._extract_text_with_pdf2image(pdf_path)
        except Exception as e:
            logger.error(f"Error extracting text from PDF with PaddleOCR: {str(e)}")
            raise
    
    def process_document(self, file_path, file_type):
        """Process document and extract text using PaddleOCR"""
        try:
            if file_type.lower() == 'pdf':
                document_text = self.extract_text_from_pdf(file_path)
            elif file_type.lower() in ['png', 'jpg', 'jpeg']:
                document_text = self.extract_text_from_image(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            return document_text
        except Exception as e:
            logger.error(f"Error processing document with PaddleOCR: {str(e)}")
            raise
    
    def extract_structured_data(self, document_text):
        """
        Extract structured data from document text including tables
        Uses the same logic as Tesseract handler for consistency
        """
        try:
            extracted_data = {
                'total_words': len(document_text.split()),
                'total_characters': len(document_text),
                'total_lines': len(document_text.split('\n')),
                'extraction_date': datetime.now().isoformat(),
                'ocr_engine': 'PaddleOCR'
            }
            
            # Extract dates
            date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
            dates = re.findall(date_pattern, document_text)
            if dates:
                extracted_data['dates_found'] = dates
            
            # Extract emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, document_text)
            if emails:
                extracted_data['emails_found'] = emails
            
            # Extract phone numbers
            phone_pattern = r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}'
            phones = re.findall(phone_pattern, document_text)
            if phones:
                extracted_data['phone_numbers_found'] = phones
            
            # Use improved table detection for PaddleOCR
            try:
                tables = self._detect_and_extract_tables_paddleocr(document_text)
                if tables:
                    extracted_data['tables'] = tables
                    extracted_data['table_count'] = len(tables)
                    logger.info(f"Found {len(tables)} table(s) in document")
            except Exception as e:
                logger.warning(f"Could not extract tables: {str(e)}")
                # Fallback to standard table detection
                try:
                    from ocr_handler import OCRHandler
                    temp_handler = OCRHandler()
                    tables = temp_handler.detect_and_extract_tables(document_text)
                    if tables:
                        extracted_data['tables'] = tables
                        extracted_data['table_count'] = len(tables)
                        logger.info(f"Found {len(tables)} table(s) using fallback method")
                except Exception as e2:
                    logger.warning(f"Fallback table extraction also failed: {str(e2)}")
            
            return extracted_data
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            return {}
    
    def extract_parameters(self, document_text):
        """
        Extract parameters list from document text including table data
        Uses the same logic as Tesseract handler for consistency
        """
        try:
            parameters = []
            
            # Basic parameter extraction
            lines = document_text.split('\n')
            for line in lines:
                line = line.strip()
                if ':' in line and len(line) > 5:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        if key and value:
                            parameters.append({
                                'key': key,
                                'value': value
                            })
            
            # Extract table data as parameters
            try:
                tables = self._detect_and_extract_tables_paddleocr(document_text)
                if not tables:
                    # Fallback to standard table detection
                    from ocr_handler import OCRHandler
                    temp_handler = OCRHandler()
                    tables = temp_handler.detect_and_extract_tables(document_text)
                
                for table in tables:
                    table_title = table.get('title', 'Table')
                    headers = table.get('headers', [])
                    rows = table.get('rows', [])
                    
                    parameters.append({
                        'key': f'{table_title}_Table_Info',
                        'value': f"Found table '{table_title}' with {len(headers)} columns and {len(rows)} rows"
                    })
                    
                    for idx, row in enumerate(rows):
                        row_params = {}
                        for header in headers:
                            if header in row:
                                value = row[header]
                                row_params[header] = value
                                
                                if value and str(value).strip():
                                    parameters.append({
                                        'key': f'{table_title}_Row_{idx + 1}_{header}',
                                        'value': str(value).strip(),
                                        'type': 'table_column',
                                        'table_name': table_title,
                                        'row_number': idx + 1,
                                        'column_name': header
                                    })
                        
                        parameters.append({
                            'key': f'{table_title}_Row_{idx + 1}',
                            'value': json.dumps(row_params) if row_params else '',
                            'type': 'table_row',
                            'table_name': table_title,
                            'row_number': idx + 1,
                            'row_data': row_params
                        })
            except Exception as e:
                logger.warning(f"Could not extract table parameters: {str(e)}")
            
            return parameters
        except Exception as e:
            logger.error(f"Error extracting parameters: {str(e)}")
            return []
    
    def _detect_and_extract_tables_paddleocr(self, document_text):
        """
        Detect and extract tables from PaddleOCR text, optimized for vertical table formats
        where headers and values are on separate lines
        """
        tables = []
        try:
            lines = [line.strip() for line in document_text.split('\n')]
            
            # Look for Services table
            services_table = self._extract_services_table_vertical(lines)
            if services_table:
                tables.append(services_table)
            
            # Look for other table patterns
            other_tables = self._extract_generic_tables_vertical(lines)
            for table in other_tables:
                if table and table not in tables:
                    tables.append(table)
            
            return tables
        except Exception as e:
            logger.error(f"Error detecting tables with PaddleOCR: {str(e)}")
            return []
    
    def _extract_services_table_vertical(self, lines):
        """
        Extract Services table from vertical format where headers and values are on separate lines
        Format:
        Services:
        Service Description
        ServicelD
        Units
        ...
        YP Personal Care
        YP-HSPC
        11.75
        ...
        """
        try:
            # Find Services section
            services_idx = None
            for i, line in enumerate(lines):
                if re.match(r'(?i)^services?\s*:?\s*$', line):
                    services_idx = i
                    break
            
            if services_idx is None:
                return None
            
            # Look for header pattern - headers are typically on consecutive lines
            # Expected headers: Service Description, ServiceID, Units, Frequency, Service Start Date, Review Date, Rate
            header_keywords = [
                'service description', 'servicelid', 'serviceid', 'service id',
                'units', 'frequency', 'rate', 'start date', 'review date', 'service start date'
            ]
            
            headers = []
            header_start_idx = None
            header_end_idx = None
            
            # Find where headers start (after "Services:")
            for i in range(services_idx + 1, min(services_idx + 20, len(lines))):
                line = lines[i].strip()
                if not line:
                    continue
                    
                line_lower = line.lower()
                
                # Check if this line contains header keywords
                is_header = False
                for keyword in header_keywords:
                    if keyword in line_lower:
                        is_header = True
                        if header_start_idx is None:
                            header_start_idx = i
                        break
                
                if is_header:
                    # This is a header line
                    normalized = self._normalize_header_name(line)
                    if normalized and normalized not in headers:
                        headers.append(normalized)
                elif header_start_idx is not None:
                    # We've been collecting headers, check if this is a data line
                    # Data lines have: YP- pattern, dates, numbers, or service names
                    if (re.search(r'YP[- ]?[A-Z]', line) or 
                        re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line) or
                        re.match(r'^\d+\.?\d+$', line) or
                        (len(line) > 10 and not any(kw in line_lower for kw in header_keywords))):
                        # This is a data line, headers ended
                        header_end_idx = i
                        break
            
            # If we didn't find headers, use standard headers
            if not headers:
                headers = ['Service Description', 'ServiceID', 'Units', 'Frequency', 'Start Date', 'Review Date', 'Rate']
                # Try to find where data starts
                for i in range(services_idx + 1, min(services_idx + 20, len(lines))):
                    if re.search(r'YP[- ]?[A-Z]', lines[i]):
                        header_end_idx = i
                        break
            
            # Find data rows - look for lines with YP- pattern (service IDs) or first data value
            data_start_idx = header_end_idx if header_end_idx else None
            
            if data_start_idx is None:
                # Search for first data line
                for i in range(services_idx + 1, len(lines)):
                    line = lines[i].strip()
                    if not line:
                        continue
                    # Check if this looks like data (not a header)
                    if (re.search(r'YP[- ]?[A-Z]', line) or 
                        (re.search(r'[A-Z]{2,}-[A-Z0-9]+', line) and not any(h.lower() in line.lower() for h in headers)) or
                        (re.match(r'^\d+\.?\d+$', line) and 'Units' in [h.lower() for h in headers])):
                        data_start_idx = i
                        break
            
            if data_start_idx is None:
                logger.warning("Could not find data start index for Services table")
                return None
            
            # Extract data rows - values are in vertical format
            # Collect all potential value lines after headers
            value_lines = []
            for i in range(data_start_idx, min(data_start_idx + 50, len(lines))):
                line = lines[i]
                if not line:
                    continue
                # Stop if we hit section markers
                if re.match(r'^(NOTES|GOAL|Previous notes|Page \d+|Date Generated)', line, re.IGNORECASE):
                    break
                # Skip header-like lines
                if any(h.lower() in line.lower() for h in headers):
                    continue
                value_lines.append((i, line))
            
            # Group values into rows
            # In vertical format, values for one row appear consecutively
            rows = []
            current_row_values = []
            header_index = 0
            
            for idx, line in value_lines:
                # Try to match line to a header position
                matched = False
                
                # Check for ServiceID (YP-XXX) - usually first or second value
                if re.search(r'[A-Z]{2,}-[A-Z0-9]+', line):
                    if 'ServiceID' in headers:
                        if not current_row_values or len(current_row_values) == 0:
                            # Start new row
                            current_row_values = [''] * len(headers)
                        serviceid_idx = headers.index('ServiceID')
                        if serviceid_idx < len(current_row_values):
                            current_row_values[serviceid_idx] = re.search(r'([A-Z]{2,}-[A-Z0-9]+)', line).group(1)
                        matched = True
                
                # Check for Service Description (text, not a header, usually first)
                if not matched and len(line) > 5 and not re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line) and not re.match(r'^\d+\.?\d*$', line):
                    if 'Service Description' in headers:
                        if not current_row_values or len(current_row_values) == 0:
                            current_row_values = [''] * len(headers)
                        desc_idx = headers.index('Service Description')
                        if desc_idx < len(current_row_values) and not current_row_values[desc_idx]:
                            current_row_values[desc_idx] = line
                        matched = True
                
                # Check for Units (decimal number)
                if not matched and re.match(r'^\d+\.?\d+$', line):
                    if 'Units' in headers:
                        if not current_row_values or len(current_row_values) == 0:
                            current_row_values = [''] * len(headers)
                        units_idx = headers.index('Units')
                        if units_idx < len(current_row_values) and not current_row_values[units_idx]:
                            current_row_values[units_idx] = line
                        matched = True
                
                # Check for Frequency
                if not matched and re.match(r'^(Weekly|Daily|Monthly|Bi-weekly|Biweekly)$', line, re.IGNORECASE):
                    if 'Frequency' in headers:
                        if not current_row_values or len(current_row_values) == 0:
                            current_row_values = [''] * len(headers)
                        freq_idx = headers.index('Frequency')
                        if freq_idx < len(current_row_values) and not current_row_values[freq_idx]:
                            current_row_values[freq_idx] = line
                        matched = True
                
                # Check for dates
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
                if date_match:
                    date_str = date_match.group(1)
                    if not current_row_values or len(current_row_values) == 0:
                        current_row_values = [''] * len(headers)
                    # Assign to first available date field
                    if 'Start Date' in headers and not current_row_values[headers.index('Start Date')]:
                        current_row_values[headers.index('Start Date')] = date_str
                    elif 'Review Date' in headers and not current_row_values[headers.index('Review Date')]:
                        current_row_values[headers.index('Review Date')] = date_str
                    matched = True
                
                # If we didn't match and have values, save the row and start new one
                if not matched and current_row_values and any(v for v in current_row_values if v):
                    # Create row dict
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if i < len(current_row_values):
                            row_dict[header] = current_row_values[i] if current_row_values[i] else ''
                        else:
                            row_dict[header] = ''
                    if any(v for v in row_dict.values() if v):
                        rows.append(row_dict)
                    current_row_values = []
            
            # Save last row
            if current_row_values and any(v for v in current_row_values if v):
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(current_row_values):
                        row_dict[header] = current_row_values[i] if current_row_values[i] else ''
                    else:
                        row_dict[header] = ''
                if any(v for v in row_dict.values() if v):
                    rows.append(row_dict)
            
            if rows:
                return {
                    'title': 'Services',
                    'headers': headers,
                    'rows': rows
                }
            
            return None
        except Exception as e:
            logger.error(f"Error extracting Services table (vertical): {str(e)}")
            return None
    
    def _normalize_header_name(self, header):
        """Normalize header names to standard format"""
        header_lower = header.lower().strip()
        
        # Map variations to standard names
        mappings = {
            'service description': 'Service Description',
            'servicelid': 'ServiceID',
            'serviceid': 'ServiceID',
            'service id': 'ServiceID',
            'units': 'Units',
            'frequency': 'Frequency',
            'rate': 'Rate',
            'start date': 'Start Date',
            'service start date': 'Start Date',
            'review date': 'Review Date'
        }
        
        for key, value in mappings.items():
            if key in header_lower:
                return value
        
        # Return capitalized version if no match
        return header.strip()
    
    def _extract_generic_tables_vertical(self, lines):
        """Extract other tables in vertical format"""
        tables = []
        # This can be extended for other table types
        return tables
    
    def refine_document_text(self, document_text):
        """
        Refine and clean document text while preserving table structure
        Specifically handles PaddleOCR output where label:value pairs are split across lines
        """
        try:
            if not document_text:
                return ""
            
            lines = document_text.split('\n')
            refined_lines = []
            i = 0
            
            # First pass: Merge label:value pairs split across lines
            while i < len(lines):
                current_line = lines[i].strip()
                
                if not current_line:
                    refined_lines.append('')
                    i += 1
                    continue
                
                # Check if current line ends with colon (likely a label)
                if current_line.endswith(':') and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    
                    # Check if next line is a value (not another label, not empty, not a section header)
                    if (next_line and 
                        not next_line.endswith(':') and 
                        not re.match(r'^[A-Z\s]{1,25}$', next_line) and  # Not all caps short text (likely header)
                        len(next_line) > 0):
                        # Merge: "Label:" + "Value" -> "Label: Value"
                        merged = current_line + ' ' + next_line
                        refined_lines.append(merged)
                        i += 2  # Skip next line
                        continue
                
                refined_lines.append(current_line)
                i += 1
            
            # Second pass: Use standard refinement for other cleanup
            try:
                from ocr_handler import OCRHandler
                temp_handler = OCRHandler()
                # Get the refined text from standard handler
                standard_refined = temp_handler.refine_document_text('\n'.join(refined_lines))
                return standard_refined
            except Exception as e:
                logger.warning(f"Could not use standard refinement: {str(e)}")
                # Fallback: return merged lines
                return '\n'.join(refined_lines)
        except Exception as e:
            logger.error(f"Error refining document text: {str(e)}")
            return document_text
    
    def save_uploaded_file(self, file, filename):
        """Save uploaded file to upload folder"""
        try:
            filename = secure_filename(filename)
            file_path = os.path.join(self.upload_folder, filename)
            file.save(file_path)
            logger.info(f"File saved: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    def process_uploaded_document(self, file, filename):
        """
        Process uploaded document: save, extract text, extract data, refine text
        Returns dictionary with all extracted information
        """
        try:
            # Get file extension
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            file_type = file_ext
            
            # Save file
            file_path = self.save_uploaded_file(file, filename)
            
            # Process document and extract text
            logger.info(f"Processing document with PaddleOCR: {filename}")
            document_text = self.process_document(file_path, file_type)
            
            # Extract structured data
            logger.info("Extracting structured data...")
            extracted_data = self.extract_structured_data(document_text)
            
            # Extract parameters
            logger.info("Extracting parameters...")
            parameters_list = self.extract_parameters(document_text)
            
            # Refine document text
            logger.info("Refining document text...")
            refined_text = self.refine_document_text(document_text)
            
            return {
                'document_text': document_text,
                'extracted_data': extracted_data,
                'parameters_list': parameters_list,
                'refined_text': refined_text,
                'file_path': file_path,
                'file_size': os.path.getsize(file_path)
            }
        except Exception as e:
            logger.error(f"Error processing uploaded document with PaddleOCR: {str(e)}")
            raise


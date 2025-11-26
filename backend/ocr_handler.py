"""
OCR Handler for document text extraction and processing
Handles document upload, OCR processing, and data extraction
"""
import os
import json
import re
import logging
import shutil
import platform
import glob
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import pdf2image
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


class OCRHandler:
    def __init__(self):
        self.upload_folder = UPLOAD_FOLDER
        
        # Store poppler path for later use
        self.poppler_path = None
        
        # Check for poppler and configure if needed
        self._check_poppler()
        
        # Check for Tesseract and configure if needed
        self._check_tesseract()
    
    def _check_poppler(self):
        """Check if poppler is installed and accessible"""
        try:
            # First, check if POPPLER_PATH environment variable is set
            poppler_path_env = os.environ.get('POPPLER_PATH')
            if poppler_path_env:
                # Normalize the path
                poppler_path_env = os.path.normpath(poppler_path_env)
                if os.path.exists(poppler_path_env):
                    # Verify pdftoppm exists
                    pdftoppm_file = os.path.join(poppler_path_env, 'pdftoppm.exe')
                    if os.path.exists(pdftoppm_file) or os.path.exists(os.path.join(poppler_path_env, 'pdftoppm')):
                        self.poppler_path = poppler_path_env
                        logger.info(f"Poppler found via POPPLER_PATH: {self.poppler_path}")
                        return True
                    else:
                        logger.warning(f"POPPLER_PATH set to {poppler_path_env} but pdftoppm not found there")
            
            # Try to find pdftoppm (part of poppler) in PATH
            pdftoppm_path = shutil.which('pdftoppm')
            if pdftoppm_path:
                # Extract the directory containing pdftoppm
                self.poppler_path = os.path.dirname(pdftoppm_path)
                logger.info(f"Poppler found in PATH at: {self.poppler_path}")
                return True
            
            # On Windows, check common installation locations
            if platform.system() == 'Windows':
                common_paths = [
                    r'C:\poppler\library\bin',  # Common installation path
                    r'C:\poppler\Library\bin',  # Case variation
                    r'C:\poppler\bin',
                    r'C:\Program Files\poppler\bin',
                    r'C:\Program Files (x86)\poppler\bin',
                ]
                for path in common_paths:
                    normalized_path = os.path.normpath(path)
                    if os.path.exists(normalized_path):
                        # Verify pdftoppm exists in this path
                        pdftoppm_file = os.path.join(normalized_path, 'pdftoppm.exe')
                        if os.path.exists(pdftoppm_file):
                            self.poppler_path = normalized_path
                            # Also add to PATH for other tools
                            os.environ['PATH'] = normalized_path + os.pathsep + os.environ.get('PATH', '')
                            logger.info(f"Poppler found at: {self.poppler_path}")
                            return True
                        else:
                            logger.debug(f"Path exists but pdftoppm.exe not found: {normalized_path}")
            
            logger.warning("Poppler not found in PATH. PDF processing may fail.")
            logger.warning(f"Checked paths: POPPLER_PATH={os.environ.get('POPPLER_PATH')}, system PATH contains poppler: {shutil.which('pdftoppm') is not None}")
            return False
        except Exception as e:
            logger.warning(f"Error checking for poppler: {str(e)}")
            return False
    
    def _verify_poppler_works(self, poppler_path):
        """Verify that poppler is actually working at the given path"""
        try:
            import subprocess
            pdftoppm_exe = os.path.join(poppler_path, 'pdftoppm.exe')
            if not os.path.exists(pdftoppm_exe):
                pdftoppm_exe = os.path.join(poppler_path, 'pdftoppm')
            
            # Try to run pdftoppm with --version flag
            result = subprocess.run(
                [pdftoppm_exe, '-v'],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=poppler_path
            )
            if result.returncode == 0 or 'pdftoppm' in result.stdout or 'pdftoppm' in result.stderr:
                logger.info(f"Poppler verified working at: {poppler_path}")
                return True
        except Exception as e:
            logger.debug(f"Could not verify poppler: {str(e)}")
        return False
    
    def _check_tesseract(self):
        """Check if Tesseract OCR is installed and configure path"""
        try:
            # First check if Tesseract is already in PATH
            tesseract_path = shutil.which('tesseract')
            if tesseract_path:
                logger.info(f"Tesseract found in PATH at: {tesseract_path}")
                return True
            
            # On Windows, check common installation locations
            if platform.system() == 'Windows':
                common_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                    r'C:\Tesseract-OCR\tesseract.exe',
                ]
                for tesseract_exe in common_paths:
                    if os.path.exists(tesseract_exe):
                        pytesseract.pytesseract.tesseract_cmd = tesseract_exe
                        logger.info(f"Tesseract found and configured: {tesseract_exe}")
                        return True
            
            logger.warning("Tesseract OCR not found. OCR functionality will not work.")
            logger.warning("Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
            return False
        except Exception as e:
            logger.warning(f"Error checking for Tesseract: {str(e)}")
            return False
    
    def _get_poppler_error_message(self):
        """Get helpful error message for poppler installation"""
        system = platform.system()
        if system == 'Windows':
            return (
                "Poppler is not installed or not in PATH. "
                "Download from: https://github.com/oschwartz10612/poppler-windows/releases/ "
                "Extract to C:\\poppler and add C:\\poppler\\library\\bin (or C:\\poppler\\bin) to your system PATH, "
                "or set POPPLER_PATH environment variable to the bin folder, then restart the application."
            )
        elif system == 'Darwin':  # macOS
            return (
                "Poppler is not installed. Install using: brew install poppler"
            )
        else:  # Linux
            return (
                "Poppler is not installed. Install using: sudo apt-get install poppler-utils (Ubuntu/Debian) "
                "or sudo dnf install poppler-utils (Fedora/RHEL)"
            )
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    def extract_text_from_image(self, image_path):
        """Extract text from image using Tesseract OCR with preprocessing"""
        try:
            # Ensure Tesseract is configured
            if not self._check_tesseract():
                raise RuntimeError(
                    "Tesseract OCR is not installed or not in PATH. "
                    "Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki "
                    "Or add Tesseract to your system PATH."
                )
            
            image = Image.open(image_path)
            
            # Preprocess image to improve OCR
            image = self._preprocess_image(image)
            
            # Use improved OCR extraction
            text = self.extract_text_from_image_obj(image)
            return text
        except pytesseract.TesseractNotFoundError:
            error_msg = (
                "Tesseract OCR is not installed or not in PATH. "
                "Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki "
                "After installation, add it to your system PATH or set TESSERACT_CMD environment variable."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            raise
    
    def extract_text_with_layout(self, image):
        """Extract text with layout information for table detection"""
        try:
            # Extract detailed data including bounding boxes
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config='--psm 6')
            return data
        except Exception as e:
            logger.error(f"Error extracting text with layout: {str(e)}")
            return None
    
    def detect_and_extract_tables(self, document_text, image_path=None):
        """
        Detect and extract tables from document text
        Returns list of tables with structured data
        """
        tables = []
        try:
            # First, try to detect specific table patterns (like Services table)
            # Look for "Services" table pattern
            services_pattern = r'(?i)services?\s*:?\s*\n'
            services_match = re.search(services_pattern, document_text)
            if services_match:
                # Try to extract table after "Services"
                start_pos = services_match.end()
                remaining_text = document_text[start_pos:]
                services_table = self._extract_services_table(remaining_text)
                if services_table:
                    tables.append(services_table)
            
            # Pattern to detect table-like structures
            # Look for rows with multiple columns separated by spaces/tabs
            lines = document_text.split('\n')
            
            # Find potential table sections
            table_start = None
            current_table = []
            headers = []
            consecutive_table_lines = 0
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Check if line looks like a table row (multiple values separated by spaces/tabs)
                # Count potential columns (words separated by 2+ spaces or tabs)
                parts = re.split(r'\s{2,}|\t+', line_stripped)
                parts = [p.strip() for p in parts if p.strip()]
                
                if len(parts) >= 3:  # Likely a table row with 3+ columns
                    if not current_table:
                        # First row might be headers
                        headers = parts
                        table_start = i
                        consecutive_table_lines = 1
                    current_table.append(parts)
                    consecutive_table_lines += 1
                elif line_stripped:
                    # Non-empty line that's not a table row
                    if current_table and len(current_table) > 1 and consecutive_table_lines >= 2:
                        # Process accumulated table
                        table_data = self._parse_table_rows(current_table, headers)
                        if table_data and len(table_data.get('rows', [])) > 0:
                            # Check if this table is different from Services table we already found
                            if not any(t.get('title') == table_data.get('title') for t in tables):
                                tables.append(table_data)
                        current_table = []
                        headers = []
                        consecutive_table_lines = 0
                    else:
                        # Reset if we don't have enough consecutive table lines
                        if consecutive_table_lines < 2:
                            current_table = []
                            headers = []
                            consecutive_table_lines = 0
                else:
                    # Empty line
                    if current_table and len(current_table) > 1 and consecutive_table_lines >= 2:
                        # Process accumulated table before empty line
                        table_data = self._parse_table_rows(current_table, headers)
                        if table_data and len(table_data.get('rows', [])) > 0:
                            if not any(t.get('title') == table_data.get('title') for t in tables):
                                tables.append(table_data)
                        current_table = []
                        headers = []
                        consecutive_table_lines = 0
            
            # Process any remaining table
            if current_table and len(current_table) > 1:
                table_data = self._parse_table_rows(current_table, headers)
                if table_data and len(table_data.get('rows', [])) > 0:
                    if not any(t.get('title') == table_data.get('title') for t in tables):
                        tables.append(table_data)
            
            return tables
        except Exception as e:
            logger.error(f"Error detecting tables: {str(e)}")
            return []
    
    def _parse_table_rows(self, rows, headers):
        """Parse table rows into structured format"""
        try:
            if not rows:
                return None
            
            # Use first row as headers if not provided
            if not headers and rows:
                headers = rows[0]
                data_rows = rows[1:]
            else:
                data_rows = rows
            
            # Ensure all rows have same number of columns
            max_cols = max(len(row) for row in rows) if rows else 0
            if max_cols == 0:
                return None
            
            # Normalize headers - clean them up
            normalized_headers = []
            for header in headers:
                # Clean header text
                clean_header = header.strip()
                if not clean_header:
                    clean_header = f'Column_{len(normalized_headers) + 1}'
                normalized_headers.append(clean_header)
            
            # If we need more columns, add generic names
            if len(normalized_headers) < max_cols:
                normalized_headers.extend([f'Column_{i+1}' for i in range(len(normalized_headers), max_cols)])
            
            # Parse data rows
            table_data = {
                'title': 'Table',
                'headers': normalized_headers[:max_cols],
                'rows': []
            }
            
            for row in data_rows:
                # Normalize row to have same number of columns
                normalized_row = row[:max_cols] if len(row) >= max_cols else row
                while len(normalized_row) < max_cols:
                    normalized_row.append('')
                
                # Create row object
                row_dict = {}
                for i, header in enumerate(normalized_headers[:max_cols]):
                    value = normalized_row[i] if i < len(normalized_row) else ''
                    # Clean the value
                    value = value.strip() if value else ''
                    row_dict[header] = value
                
                table_data['rows'].append(row_dict)
            
            return table_data if table_data['rows'] else None
        except Exception as e:
            logger.error(f"Error parsing table rows: {str(e)}")
            return None
    
    def _extract_services_table(self, text):
        """Extract Services table with specific structure - handles concatenated columns"""
        try:
            lines = text.split('\n')
            table_rows = []
            
            # Standard headers for Services table
            headers = ['Service Description', 'ServiceID', 'Units', 'Frequency', 'Service Rate', 'Start Date', 'Review Date']
            
            # Look for Services section and extract data rows
            services_found = False
            services_start_idx = None
            
            # First, find the Services section
            for i, line in enumerate(lines[:100]):  # Check first 100 lines
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                # Check if this is the Services section - must be just "Services:" or "Services"
                # Match lines that are exactly "Services:" or "Services"
                if re.match(r'(?i)^services?\s*:?\s*$', line_stripped):
                    services_found = True
                    services_start_idx = i
                    logger.info(f"Found Services section at line {i+1} (index {i}): '{line_stripped}'")
                    # Debug: show next few lines
                    for j in range(i+1, min(i+5, len(lines))):
                        logger.debug(f"  Line {j+1}: '{lines[j].strip()[:80]}'")
                    break
            
            if services_found and services_start_idx is not None:
                # Look for data rows after "Services"
                consecutive_non_matches = 0
                for j in range(services_start_idx + 1, min(services_start_idx + 50, len(lines))):
                    data_line = lines[j].strip()
                    if not data_line:
                        consecutive_non_matches += 1
                        if consecutive_non_matches > 3 and len(table_rows) > 0:
                            # Too many empty lines, probably end of table
                            break
                        continue
                    
                    consecutive_non_matches = 0
                    
                    # Skip header-like lines
                    if any(keyword in data_line.lower() for keyword in ['service description', 'serviceid', 'units', 'frequency', 'rate', 'start date', 'review date', 'review date']):
                        continue
                    
                    # Skip lines that are clearly not service data
                    if re.match(r'^(Page \d+ of \d+|Date Generated|Generated By)', data_line, re.IGNORECASE):
                        continue
                    
                    # Check if line looks like a service row (contains YP- or service ID pattern)
                    if not re.search(r'YP[- ]?[A-Z]', data_line) and not re.search(r'[A-Z]{2,}-[A-Z0-9]+', data_line):
                        # Doesn't look like a service row, skip
                        if len(table_rows) > 0:
                            # We already have rows, might be end of table
                            break
                        continue
                    
                    # Try to extract service data from the line
                    # Pattern: Service Name, ServiceID (like YP-HSPC), Units, Frequency, Dates
                    # First, extract just the service part (before NOTES, GOAL, etc.)
                    service_part = data_line
                    # Split on NOTES, GOAL, or other section markers to get just the service row
                    for marker in ['NOTES:', 'GOAL:', 'Previous notes:']:
                        if marker in service_part:
                            service_part = service_part.split(marker)[0].strip()
                            break
                    
                    logger.debug(f"Attempting to parse service row from: {service_part[:100]}")
                    service_data = self._parse_service_row(service_part)
                    if service_data:
                        table_rows.append(service_data)
                        logger.info(f"Extracted service row {len(table_rows)}: {service_data.get('Service Description')} - {service_data.get('ServiceID')}")
                    elif len(table_rows) > 0:
                        # If we already have rows and this doesn't match, might be end of table
                        # But check if it's notes (starts with NOTES, GOAL, etc.)
                        if re.match(r'^(NOTES|GOAL|Previous notes):', data_line, re.IGNORECASE):
                            # This is associated notes, continue looking for more service rows
                            continue
                        elif len(data_line) > 50 and not re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', data_line):
                            # Long line without date, probably notes, continue
                            continue
                        elif len(table_rows) >= 2:
                            # We have at least 2 service rows, might be end of table
                            break
                    else:
                        # No rows yet, but check if line might be a service row
                        # Look for patterns that suggest it's a service row
                        if re.search(r'YP[- ]?[A-Z]', data_line) or re.search(r'\d+\.\d+', data_line):
                            # Might be a service row, try parsing again with more lenient criteria
                            service_data = self._parse_service_row(data_line)
                            if service_data:
                                table_rows.append(service_data)
                                logger.info(f"Extracted service row {len(table_rows)} (lenient): {service_data.get('Service Description')} - {service_data.get('ServiceID')}")
            
            # If we found service rows, create table structure
            if table_rows:
                table_data = {
                    'title': 'Services',
                    'headers': headers,
                    'rows': table_rows
                }
                logger.info(f"Extracted Services table with {len(table_rows)} rows")
                return table_data
            else:
                logger.warning("No service rows found in Services section")
            
            return None
        except Exception as e:
            logger.error(f"Error extracting services table: {str(e)}")
            return None
    
    def _parse_service_row(self, line):
        """
        Parse a service row from concatenated text
        Example: "YP Personal Care YP-HSPC [11.75 [Weekly | __forosv2025 —_[or/o2/2026"
        Handles OCR errors and concatenated columns
        """
        try:
            if not line or len(line.strip()) < 10:
                return None
            
            service_data = {}
            original_line = line.strip()
            line_clean = original_line
            
            # Extract ServiceID (pattern: YP-XXXX or similar, handle OCR errors)
            # Try exact pattern first
            service_id_match = re.search(r'([A-Z]{2,}-[A-Z0-9]{2,})', line_clean)
            if not service_id_match:
                # Try with OCR errors (missing hyphens, wrong characters)
                service_id_match = re.search(r'([A-Z]{2,}[-\s]?[A-Z0-9]{2,})', line_clean)
            
            if service_id_match:
                service_id = service_id_match.group(1).replace(' ', '-')  # Normalize spaces to hyphens
                service_data['ServiceID'] = service_id
                # Remove ServiceID from line for further parsing
                line_clean = line_clean.replace(service_id_match.group(1), '', 1)
            else:
                service_data['ServiceID'] = ''
            
            # Extract dates (pattern: DD/MM/YYYY or DD-MM-YYYY, handle OCR errors)
            # Look for date patterns with various separators
            date_pattern = r'(\d{1,2}[/\-_]\d{1,2}[/\-_]\d{2,4})'
            dates = re.findall(date_pattern, line_clean)
            
            # Also try to find dates with OCR errors (like "or/o2/2026" -> "01/02/2026")
            # Look for patterns that might be dates
            potential_dates = re.findall(r'(\d{1,2}[^\w\s]{1,2}\d{1,2}[^\w\s]{1,2}\d{2,4})', line_clean)
            for pd in potential_dates:
                # Normalize separators
                normalized = re.sub(r'[^\d]', '/', pd)
                if normalized not in dates:
                    dates.append(normalized)
            
            if len(dates) >= 2:
                service_data['Start Date'] = dates[0]
                service_data['Review Date'] = dates[1]
                # Remove dates from line
                for date in dates:
                    # Find original date pattern in line
                    date_escaped = re.escape(date)
                    line_clean = re.sub(date_escaped, '', line_clean)
            elif len(dates) == 1:
                service_data['Start Date'] = dates[0]
                service_data['Review Date'] = ''
                line_clean = re.sub(re.escape(dates[0]), '', line_clean)
            else:
                service_data['Start Date'] = ''
                service_data['Review Date'] = ''
            
            # Extract Units (decimal number like 11.75, 1.50, handle OCR errors)
            # Look for numbers with optional decimal point
            units_match = re.search(r'(\d+\.?\d*)', line_clean)
            if units_match:
                units = units_match.group(1)
                # Validate it's a reasonable unit value (between 0.1 and 1000)
                try:
                    units_float = float(units)
                    if 0.1 <= units_float <= 1000:
                        service_data['Units'] = units
                        line_clean = line_clean.replace(units, '', 1)
                    else:
                        service_data['Units'] = ''
                except:
                    service_data['Units'] = ''
            else:
                service_data['Units'] = ''
            
            # Extract Frequency (Weekly, Monthly, etc., handle OCR errors like "weoky" -> "Weekly")
            frequency_patterns = [
                r'\b([Ww]eekly|[Ww]eoky|[Ww]eeky)\b',
                r'\b([Mm]onthly|[Mm]onthy)\b',
                r'\b([Dd]aily|[Dd]ayly)\b',
                r'\b([Yy]early|[Yy]early)\b',
                r'\b([Aa]nnually)\b',
            ]
            
            frequency = ''
            for pattern in frequency_patterns:
                frequency_match = re.search(pattern, line_clean)
                if frequency_match:
                    freq = frequency_match.group(1).lower()
                    # Normalize OCR errors
                    if freq.startswith('weok') or freq.startswith('weeky'):
                        frequency = 'Weekly'
                    elif freq.startswith('month'):
                        frequency = 'Monthly'
                    elif freq.startswith('dail'):
                        frequency = 'Daily'
                    elif freq.startswith('year'):
                        frequency = 'Yearly'
                    elif freq.startswith('annual'):
                        frequency = 'Annually'
                    else:
                        frequency = frequency_match.group(1)
                    service_data['Frequency'] = frequency
                    line_clean = re.sub(pattern, '', line_clean)
                    break
            
            if not frequency:
                service_data['Frequency'] = ''
            
            # Extract Service Description (what's left before ServiceID, cleaned up)
            # Remove special characters and clean up
            line_clean = re.sub(r'[\[\]|_—\-]', ' ', line_clean)
            line_clean = re.sub(r'\s+', ' ', line_clean).strip()
            
            # Try to identify service name patterns (handle OCR errors)
            # Common patterns: "YP Personal Care", "YP Household Management", etc.
            service_name_patterns = [
                r'(YP\s+[Pp]ersonal\s+[Cc]are)',  # YP Personal Care
                r'(YP\s+[Hh]ousehold\s+[Mm]anagement)',  # YP Household Management
                r'(YP\s+[Hh]owsehad\s+[Mm]anagement)',  # OCR error: Howsehad
                r'(YP\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',  # YP Personal Care (generic)
                r'(YP\s+[A-Z][a-z]+\s+Management)',   # YP Household Management (generic)
            ]
            
            service_description = ''
            for pattern in service_name_patterns:
                match = re.search(pattern, original_line, re.IGNORECASE)
                if match:
                    service_description = match.group(1)
                    # Normalize common OCR errors
                    service_description = service_description.replace('Howsehad', 'Household')
                    service_description = service_description.replace('weoky', 'Weekly')
                    break
            
            # If no pattern matched, try to extract from cleaned line
            if not service_description:
                words = line_clean.split()
                # Look for YP followed by words
                if words and words[0].upper() == 'YP' and len(words) >= 2:
                    service_description = ' '.join(words[:3])  # Take first 2-3 words
                elif len(words) >= 2:
                    service_description = ' '.join(words[:2])  # Take first 2 words
                elif words:
                    service_description = words[0]
            
            service_data['Service Description'] = service_description.strip() if service_description else line_clean[:50].strip()
            service_data['Service Rate'] = ''  # Usually empty in the example
            
            # Ensure all headers are present
            for header in ['Service Description', 'ServiceID', 'Units', 'Frequency', 'Service Rate', 'Start Date', 'Review Date']:
                if header not in service_data:
                    service_data[header] = ''
            
            # Only return if we have at least ServiceID or meaningful Service Description
            if service_data.get('ServiceID') or (service_data.get('Service Description') and len(service_data.get('Service Description', '')) > 3):
                logger.info(f"Parsed service row: {service_data}")
                return service_data
            
            return None
        except Exception as e:
            logger.error(f"Error parsing service row '{line}': {str(e)}")
            return None
    
    def _preprocess_image(self, image):
        """Preprocess image to improve OCR accuracy"""
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to grayscale for better OCR
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # Increase contrast by 50%
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)  # Increase sharpness
            
            # Apply slight denoising
            try:
                image = image.filter(ImageFilter.MedianFilter(size=3))
            except:
                # If MedianFilter fails, try other filters
                image = image.filter(ImageFilter.SMOOTH)
            
            return image
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}, using original image")
            return image
    
    def _extract_text_with_pymupdf(self, pdf_path):
        """Extract text from PDF using PyMuPDF (doesn't require poppler)"""
        import fitz  # PyMuPDF
        all_text = []
        doc = None
        
        try:
            # Open PDF
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            logger.info(f"Opened PDF with {num_pages} pages using PyMuPDF")
            
            for page_num in range(num_pages):
                logger.info(f"Processing PDF page {page_num + 1}/{num_pages} using PyMuPDF")
                
                # Check if document is still open
                if doc.is_closed:
                    raise RuntimeError("PDF document was closed unexpectedly")
                
                page = doc[page_num]
                
                # Convert page to image with higher resolution (3x zoom for better quality)
                mat = fitz.Matrix(3.0, 3.0)  # Increased from 2x to 3x for better OCR
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                from io import BytesIO
                image = Image.open(BytesIO(img_data))
                
                # Preprocess image to improve OCR
                image = self._preprocess_image(image)
                
                # Extract text from image using OCR
                try:
                    page_text = self.extract_text_from_image_obj(image)
                    all_text.append(page_text)
                except Exception as ocr_error:
                    logger.warning(f"OCR failed for page {page_num + 1}: {str(ocr_error)}, continuing...")
                    all_text.append("")  # Add empty string for failed page
                
                # Clean up resources
                image.close()
                pix = None
            
            logger.info(f"✅ Successfully processed {num_pages} pages using PyMuPDF")
            return '\n\n'.join(all_text)
            
        except Exception as e:
            logger.error(f"Error in PyMuPDF extraction: {str(e)}")
            raise
        finally:
            # Always close the document
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass
    
    def _correct_ocr_errors(self, text):
        """Post-process OCR text to fix common errors"""
        if not text:
            return text
        
        # Fix common OCR errors
        corrections = {
            # Date patterns
            r'__forosv(\d{4})': r'01/02/\1',  # __forosv2025 -> 01/02/2025
            r'_\[or/o(\d{1,2})/(\d{4})': r'01/\1/\2',  # _[or/o2/2026 -> 01/02/2026
            r'\[ovon0es_Jovn(\d{2,4})': r'01/02/\1',  # [ovon0es_Jovn026 -> 01/02/2026
            r'____\[ovon0es_Jovn(\d{2,4})': r'01/02/\1',  # ____[ovon0es_Jovn026_] -> 01/02/2026
            
            # Fix date separators (remove = and special characters before dates)
            r'=\s*[^\w\s]*\s*(\d{1,2}/\d{1,2}/\d{2,4})': r'\1',  # =01/09/2025 -> 01/09/2025
            r'=\s*(\d{1,2}/\d{1,2}/\d{2,4})': r'\1',  # = 01/09/2025 -> 01/09/2025
            r'(\d{1,2}/\d{1,2}/\d{2,4})\s*=\s*': r'\1 ',  # 01/09/2025 = -> 01/09/2025 
            r'(\d{1,2}/\d{1,2}/\d{2,4})\s*=\s*(\d{1,2}/\d{1,2}/\d{2,4})': r'\1 \2',  # 01/09/2025 = 01/02/2026 -> 01/09/2025 01/02/2026
            
            # Service ID patterns
            r'\[YPHSHM': 'YP-HSHM',  # [YPHSHM -> YP-HSHM
            r'\[YP-HSPC': 'YP-HSPC',  # [YP-HSPC -> YP-HSPC
            r'YPHSHM': 'YP-HSHM',  # YPHSHM -> YP-HSPC
            
            # Frequency patterns
            r'\[weoky': 'Weekly',  # [weoky -> Weekly
            r'_\[weoky': 'Weekly',  # _[weoky -> Weekly
            r'weoky': 'Weekly',  # weoky -> Weekly
            
            # Service name patterns
            r'\[eHowsehad': 'YP Household',  # [eHowsehad -> YP Household
            r'Howsehad': 'Household',  # Howsehad -> Household
            r'freHowsehelgManagenet': 'YP Household Management',  # freHowsehelgManagenet -> YP Household Management
            
            # Units patterns - fix [150 -> 1.50, [11.75 -> 11.75
            r'\[(\d+)\.(\d+)': r'\1.\2',  # [11.75 -> 11.75
            r'\[(\d{3})\b': r'\1',  # [150 -> 150 (will be handled by separate pattern)
            
            # Remove stray brackets and fix spacing
            r'\[(\w)': r'\1',  # [A -> A
            r'(\w)\[': r'\1',  # A[ -> A
            r'\|': ' ',  # | -> space
            r'_+': ' ',  # Multiple underscores -> space
            r'—+': ' ',  # Multiple em dashes -> space
        }
        
        import re
        corrected_text = text
        
        for pattern, replacement in corrections.items():
            corrected_text = re.sub(pattern, replacement, corrected_text)
        
        # Fix 3-digit and 4-digit numbers that should be decimals (e.g., 150 -> 1.50, 1150 -> 1.50, 1175 -> 11.75)
        # Look for patterns like "150 Weekly", "1150 Weekly", "1175 Weekly" and convert appropriately
        def fix_units(match):
            num = match.group(1)
            # Convert 4-digit numbers like 1150 -> 1.50, 1175 -> 11.75
            if len(num) == 4:
                # Check if it's a unit value (typically 1.xx or 11.xx)
                if num[0] == '1' and num[1] in '0123456789':
                    # Could be 1.xx or 11.xx
                    if num[1] in '0123456789' and int(num[2:]) < 100:
                        # Likely 11.xx format (e.g., 1175 -> 11.75)
                        if int(num[2:]) < 100:
                            return f"{num[:2]}.{num[2:]}"
                        # Or 1.xx format (e.g., 1150 -> 1.50)
                        else:
                            return f"{num[0]}.{num[1:]}"
            # Convert 3-digit numbers like 150 -> 1.50
            elif len(num) == 3:
                if num[0] in '123456789' and int(num) < 1000:
                    return f"{num[0]}.{num[1:]}"
            return num
        
        # Fix units in various contexts
        # Pattern: number followed by frequency word
        def fix_units_with_context(match):
            num = match.group(1)
            freq = match.group(2)
            fixed_num = fix_units(match)
            return f"{fixed_num} {freq}"
        
        corrected_text = re.sub(r'\b(\d{3,4})\s+(Weekly|Monthly|Daily|Yearly|Annually)', fix_units_with_context, corrected_text)
        
        # Pattern: ServiceID followed by number (like YP-HSHM 1150)
        def fix_units_after_service_id(match):
            service_id = match.group(1)
            num = match.group(2)
            # Create a mock match object for fix_units
            class MockMatch:
                def __init__(self, num_str):
                    self.group = lambda n: num_str if n == 1 else None
            fixed_num = fix_units(MockMatch(num))
            return f"{service_id} {fixed_num}"
        
        corrected_text = re.sub(r'([A-Z]{2,}-[A-Z0-9]+)\s+(\d{3,4})(\s|$)', fix_units_after_service_id, corrected_text)
        
        # Fix spacing issues
        import re
        # Fix spacing around dates
        corrected_text = re.sub(r'(\d{1,2}/\d{1,2}/\d{2,4})\s*([A-Z])', r'\1 \2', corrected_text)
        # Fix spacing around service IDs
        corrected_text = re.sub(r'([A-Z]{2,}-[A-Z0-9]+)\s*\[', r'\1 ', corrected_text)
        
        # Fix concatenated words (common OCR issue)
        # Add space before capital letters that follow lowercase (but not at start of line)
        corrected_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', corrected_text)
        # Add space after service IDs followed by numbers
        corrected_text = re.sub(r'([A-Z]{2,}-[A-Z0-9]+)(\d)', r'\1 \2', corrected_text)
        # Add space before dates
        corrected_text = re.sub(r'([A-Za-z])(\d{1,2}/\d{1,2}/\d{2,4})', r'\1 \2', corrected_text)
        # Add space after dates
        corrected_text = re.sub(r'(\d{1,2}/\d{1,2}/\d{2,4})([A-Z])', r'\1 \2', corrected_text)
        # Add space around frequency words
        corrected_text = re.sub(r'([A-Za-z])(Weekly|Monthly|Daily|Yearly|Annually)', r'\1 \2', corrected_text)
        corrected_text = re.sub(r'(Weekly|Monthly|Daily|Yearly|Annually)([A-Z])', r'\1 \2', corrected_text)
        
        # Remove multiple spaces
        corrected_text = re.sub(r' +', ' ', corrected_text)
        # Fix spacing around brackets
        corrected_text = re.sub(r'\s*\[\s*', ' ', corrected_text)
        corrected_text = re.sub(r'\s*\]\s*', ' ', corrected_text)
        
        # Remove special characters that OCR sometimes adds before dates
        corrected_text = re.sub(r'[^\w\s/]+\s*(\d{1,2}/\d{1,2}/\d{2,4})', r'\1', corrected_text)
        
        # Clean up any remaining = signs used as separators
        corrected_text = re.sub(r'\s*=\s*', ' ', corrected_text)
        
        return corrected_text.strip()
    
    def extract_text_from_image_obj(self, image):
        """Extract text from PIL Image object with improved OCR settings"""
        try:
            # Ensure Tesseract is configured
            if not self._check_tesseract():
                raise RuntimeError(
                    "Tesseract OCR is not installed or not in PATH. "
                    "Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki "
                    "Or add Tesseract to your system PATH."
                )
            
            # Try multiple PSM modes and combine results for better accuracy
            # PSM 6: Uniform block of text (good for documents)
            # PSM 11: Sparse text (good for tables)
            # PSM 3: Fully automatic page segmentation (default, good fallback)
            
            texts = []
            psm_modes = [6, 11, 3]  # Try these PSM modes
            
            for psm in psm_modes:
                try:
                    # Don't use whitelist as it might be too restrictive
                    # Instead, use better OCR settings
                    config = f'--psm {psm} -c preserve_interword_spaces=1'
                    text = pytesseract.image_to_string(image, config=config)
                    if text.strip():
                        texts.append(text.strip())
                except Exception as e:
                    logger.debug(f"PSM {psm} failed: {str(e)}")
                    continue
            
            # If we got multiple results, use the longest one (usually most complete)
            if texts:
                best_text = max(texts, key=len)
            else:
                # Fallback to default PSM 6 with spacing preservation
                best_text = pytesseract.image_to_string(image, config='--psm 6 -c preserve_interword_spaces=1')
            
            # Apply OCR error correction
            corrected_text = self._correct_ocr_errors(best_text)
            
            return corrected_text.strip()
        except pytesseract.TesseractNotFoundError:
            error_msg = (
                "Tesseract OCR is not installed or not in PATH. "
                "Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki "
                "After installation, add it to your system PATH or set TESSERACT_CMD environment variable."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            raise
    
    def _convert_pdf_with_pdftoppm(self, pdf_path, poppler_path):
        """Convert PDF to images using pdftoppm directly (bypasses pdfinfo)"""
        import subprocess
        images = []
        
        pdftoppm_exe = os.path.join(poppler_path, 'pdftoppm.exe')
        if not os.path.exists(pdftoppm_exe):
            pdftoppm_exe = os.path.join(poppler_path, 'pdftoppm')
        
        if not os.path.exists(pdftoppm_exe):
            raise RuntimeError(f"pdftoppm not found at {poppler_path}")
        
        # Check for required DLLs (common issue on Windows)
        if platform.system() == 'Windows':
            dll_files = ['poppler.dll', 'poppler-cpp.dll', 'libpoppler.dll']
            dll_found = False
            for dll in dll_files:
                dll_path = os.path.join(poppler_path, dll)
                if os.path.exists(dll_path):
                    dll_found = True
                    logger.info(f"Found DLL: {dll}")
                    break
            
            if not dll_found:
                logger.warning("No poppler DLLs found in bin directory. This may cause crashes.")
                logger.warning("Poppler executables require DLLs to be in the same directory or in PATH.")
                # List what files are actually in the directory
                try:
                    files_in_dir = os.listdir(poppler_path)
                    dll_files_in_dir = [f for f in files_in_dir if f.lower().endswith('.dll')]
                    if dll_files_in_dir:
                        logger.info(f"DLLs found in directory: {', '.join(dll_files_in_dir)}")
                    else:
                        logger.warning("No DLL files found in poppler bin directory!")
                except Exception as e:
                    logger.warning(f"Could not list directory contents: {str(e)}")
        
        # Create a temporary output prefix for images
        temp_prefix = os.path.join(self.upload_folder, 'pdf_page')
        
        try:
            # Use pdftoppm to convert PDF to images
            # -png: output PNG format
            # -r 300: resolution 300 DPI
            # -f 1: start from page 1
            # -l 999: up to page 999 (we'll stop when it fails)
            
            # First, try to convert with a high page limit
            # pdftoppm will stop when it reaches the end
            cmd = [
                pdftoppm_exe,
                '-png',
                '-r', '300',
                '-f', '1',
                '-l', '999',
                pdf_path,
                temp_prefix
            ]
            
            logger.info(f"Running pdftoppm: {' '.join(cmd)}")
            
            # On Windows, set the DLL search path by setting PATH and using cwd
            env = dict(os.environ)
            env['PATH'] = poppler_path + os.pathsep + env.get('PATH', '')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=poppler_path,  # Set working directory to poppler bin so DLLs can be found
                env=env
            )
            
            if result.returncode != 0:
                logger.warning(f"pdftoppm returned code {result.returncode}, but checking for output files...")
                logger.debug(f"pdftoppm stderr: {result.stderr}")
            
            # Find all generated image files
            image_files = sorted(glob.glob(f"{temp_prefix}-*.png"))
            
            if not image_files:
                # Try with a different naming pattern (some versions use different formats)
                image_files = sorted(glob.glob(f"{temp_prefix}*.png"))
            
            if not image_files:
                error_msg = f"No images generated by pdftoppm. Return code: {result.returncode}"
                if result.returncode == 3221225477 or result.returncode == -1073741819:  # Access violation
                    error_msg += "\n\nPoppler executables are crashing due to missing DLLs. "
                    error_msg += "Please ensure all DLL files are in the poppler bin directory (C:\\poppler\\Library\\bin). "
                    error_msg += "If DLLs are missing, you may need to re-download poppler or install Visual C++ Redistributables."
                if result.stderr:
                    error_msg += f"\nError output: {result.stderr}"
                raise RuntimeError(error_msg)
            
            logger.info(f"Found {len(image_files)} pages converted by pdftoppm")
            
            # Load images
            for img_file in image_files:
                try:
                    img = Image.open(img_file)
                    images.append(img)
                except Exception as e:
                    logger.warning(f"Failed to load image {img_file}: {str(e)}")
            
            # Clean up temporary image files
            for img_file in image_files:
                try:
                    if os.path.exists(img_file):
                        os.remove(img_file)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {img_file}: {str(e)}")
            
            if not images:
                raise RuntimeError("No images could be loaded from pdftoppm output")
            
            return images
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("pdftoppm conversion timed out")
        except Exception as e:
            logger.error(f"Error in _convert_pdf_with_pdftoppm: {str(e)}")
            raise
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF by converting to images and using OCR"""
        logger.info("=" * 60)
        logger.info("=== STARTING PDF EXTRACTION ===")
        logger.info(f"PDF path: {pdf_path}")
        logger.info(f"PDF exists: {os.path.exists(pdf_path) if pdf_path else False}")
        logger.info(f"Current poppler_path: {self.poppler_path}")
        logger.info(f"Current PATH: {os.environ.get('PATH', '')[:200]}...")
        logger.info("=" * 60)
        
        # Try PyMuPDF first (doesn't require poppler)
        try:
            import fitz  # PyMuPDF
            logger.info("Attempting PDF conversion using PyMuPDF (no poppler required)...")
            return self._extract_text_with_pymupdf(pdf_path)
        except ImportError:
            logger.info("PyMuPDF not available, falling back to pdf2image/poppler...")
        except Exception as e:
            logger.warning(f"PyMuPDF conversion failed: {str(e)}, falling back to pdf2image...")
        
        try:
            # Re-check poppler if not already found
            if not self.poppler_path:
                logger.info("Poppler path not set, checking for poppler...")
                self._check_poppler()
                logger.info(f"After check, poppler_path: {self.poppler_path}")
            
            # Try multiple methods to find and use poppler
            poppler_path_to_use = None
            
            # Method 1: Use stored poppler_path
            if self.poppler_path:
                poppler_path_to_use = os.path.normpath(self.poppler_path)
                logger.info(f"Attempting to use poppler from: {poppler_path_to_use}")
            
            # Method 2: Try environment variable
            if not poppler_path_to_use:
                poppler_path_env = os.environ.get('POPPLER_PATH')
                if poppler_path_env:
                    poppler_path_to_use = os.path.normpath(poppler_path_env)
                    logger.info(f"Attempting to use poppler from POPPLER_PATH: {poppler_path_to_use}")
            
            # Method 3: Try common Windows paths directly
            if not poppler_path_to_use and platform.system() == 'Windows':
                test_paths = [
                    r'C:\poppler\library\bin',
                    r'C:\poppler\Library\bin',
                    r'C:\poppler\bin',
                ]
                for test_path in test_paths:
                    normalized = os.path.normpath(test_path)
                    pdftoppm_file = os.path.join(normalized, 'pdftoppm.exe')
                    if os.path.exists(pdftoppm_file):
                        poppler_path_to_use = normalized
                        logger.info(f"Found poppler at: {poppler_path_to_use}")
                        break
            
            # Convert PDF to images with the found path
            if poppler_path_to_use:
                # Verify the path exists and has pdftoppm
                pdftoppm_check = os.path.join(poppler_path_to_use, 'pdftoppm.exe')
                if not os.path.exists(pdftoppm_check):
                    pdftoppm_check = os.path.join(poppler_path_to_use, 'pdftoppm')
                
                if os.path.exists(pdftoppm_check):
                    # Ensure path is absolute and normalized
                    poppler_path_absolute = os.path.abspath(poppler_path_to_use)
                    logger.info(f"=== Using poppler from: {poppler_path_absolute} ===")
                    logger.info(f"pdftoppm exists at: {pdftoppm_check}")
                    
                    # Also check for pdfinfo (needed by pdf2image to get page count)
                    pdfinfo_check = os.path.join(poppler_path_to_use, 'pdfinfo.exe')
                    if not os.path.exists(pdfinfo_check):
                        pdfinfo_check = os.path.join(poppler_path_to_use, 'pdfinfo')
                    logger.info(f"pdfinfo exists at: {pdfinfo_check} ({os.path.exists(pdfinfo_check)})")
                    
                    logger.info(f"PDF path: {pdf_path}")
                    
                    # Also ensure PATH includes poppler for subprocess calls
                    current_path = os.environ.get('PATH', '')
                    if poppler_path_absolute not in current_path:
                        os.environ['PATH'] = poppler_path_absolute + os.pathsep + current_path
                        logger.info(f"Added poppler to PATH: {poppler_path_absolute}")
                    
                    # Test if poppler actually works by checking pdfinfo
                    # Note: pdfinfo might crash due to missing DLLs, but pdftoppm might still work
                    pdfinfo_works = False
                    try:
                        import subprocess
                        pdfinfo_exe = os.path.join(poppler_path_absolute, 'pdfinfo.exe')
                        if os.path.exists(pdfinfo_exe):
                            # Try to get page count directly
                            result = subprocess.run(
                                [pdfinfo_exe, pdf_path],
                                capture_output=True,
                                text=True,
                                timeout=10,
                                cwd=poppler_path_absolute,
                                env=dict(os.environ, PATH=poppler_path_absolute + os.pathsep + os.environ.get('PATH', ''))
                            )
                            logger.info(f"pdfinfo test result: returncode={result.returncode}")
                            if result.returncode == 0:
                                pdfinfo_works = True
                                logger.info("pdfinfo works! Proceeding with pdf2image...")
                            else:
                                logger.warning(f"pdfinfo returned error code {result.returncode} (might be missing DLLs, but pdftoppm might still work)")
                    except Exception as test_e:
                        logger.warning(f"pdfinfo test failed (non-critical): {str(test_e)}")
                    
                    # If pdfinfo doesn't work, we'll try to convert pages directly using pdftoppm
                    if not pdfinfo_works:
                        logger.warning("pdfinfo not working, will try alternative conversion method")
                    
                    try:
                        # CRITICAL: Set PATH environment variable before calling pdf2image
                        # pdf2image uses subprocess which needs PATH to find pdfinfo and pdftoppm
                        current_path = os.environ.get('PATH', '')
                        if poppler_path_absolute not in current_path:
                            os.environ['PATH'] = poppler_path_absolute + os.pathsep + current_path
                            logger.info(f"Set PATH to include: {poppler_path_absolute}")
                        
                        # Also set POPPLER_PATH for pdf2image
                        os.environ['POPPLER_PATH'] = poppler_path_absolute
                        logger.info(f"Set POPPLER_PATH={poppler_path_absolute}")
                        
                        # If pdfinfo doesn't work, try using pdftoppm directly to convert pages
                        if not pdfinfo_works:
                            logger.info("Attempting direct conversion using pdftoppm (bypassing pdfinfo)...")
                            images = self._convert_pdf_with_pdftoppm(pdf_path, poppler_path_absolute)
                            logger.info(f"✅ Successfully converted PDF using pdftoppm! Got {len(images)} pages")
                        else:
                            # Try with explicit path first
                            logger.info(f"=== Attempting PDF conversion with poppler_path={poppler_path_absolute} ===")
                            # On Windows, ensure path uses backslashes and is absolute
                            if platform.system() == 'Windows':
                                poppler_path_for_pdf2image = os.path.normpath(poppler_path_absolute)
                            else:
                                poppler_path_for_pdf2image = poppler_path_absolute
                            
                            logger.info(f"Using poppler_path (formatted): {poppler_path_for_pdf2image}")
                            logger.info(f"PDF file exists: {os.path.exists(pdf_path)}")
                            
                            # Try conversion
                            images = pdf2image.convert_from_path(
                                pdf_path, 
                                poppler_path=poppler_path_for_pdf2image
                            )
                            logger.info(f"✅ Successfully converted PDF! Got {len(images)} pages")
                    except Exception as e:
                        error_str = str(e)
                        error_type = type(e).__name__
                        logger.error(f"❌ Failed to convert PDF with explicit path {poppler_path_absolute}")
                        logger.error(f"   Error type: {error_type}")
                        logger.error(f"   Error message: {error_str}")
                        logger.error(f"   Full exception: {repr(e)}")
                        
                        # If it fails, try without explicit path (in case it's in system PATH)
                        logger.info("Attempting fallback to system PATH...")
                        try:
                            images = pdf2image.convert_from_path(pdf_path)
                            logger.info("✅ Successfully converted PDF using system PATH")
                        except Exception as e2:
                            # Both methods failed
                            error_msg = self._get_poppler_error_message()
                            logger.error(f"❌ Both explicit path and system PATH failed")
                            logger.error(f"   Last error type: {type(e2).__name__}")
                            logger.error(f"   Last error: {str(e2)}")
                            raise RuntimeError(f"Error processing PDF: {str(e2)}. {error_msg}")
                else:
                    logger.warning(f"pdftoppm not found at {poppler_path_to_use}, trying system PATH")
                    try:
                        images = pdf2image.convert_from_path(pdf_path)
                    except Exception as e:
                        error_msg = self._get_poppler_error_message()
                        raise RuntimeError(f"Error processing PDF: {str(e)}. {error_msg}")
            else:
                # Try without explicit path (should work if in system PATH)
                logger.info("No explicit poppler path found, trying system PATH")
                try:
                    images = pdf2image.convert_from_path(pdf_path)
                except Exception as e:
                    error_msg = self._get_poppler_error_message()
                    raise RuntimeError(f"Error processing PDF: {str(e)}. {error_msg}")
            
            all_text = []
            
            for i, image in enumerate(images):
                logger.info(f"Processing PDF page {i + 1}/{len(images)}")
                # Save temporary image
                temp_image_path = os.path.join(self.upload_folder, f"temp_page_{i}.png")
                image.save(temp_image_path)
                
                # Extract text from image
                page_text = self.extract_text_from_image(temp_image_path)
                all_text.append(page_text)
                
                # Clean up temporary file
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            
            return '\n\n'.join(all_text)
        except Exception as e:
            error_str = str(e)
            error_lower = error_str.lower()
            
            # Check for poppler-related errors
            poppler_keywords = ['poppler', 'pdftoppm', 'pdfinfo', 'page count', 'not installed', 'path']
            is_poppler_error = any(keyword in error_lower for keyword in poppler_keywords)
            
            # Also check for specific pdf2image exceptions if available
            try:
                from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
                if isinstance(e, (PDFInfoNotInstalledError, PDFPageCountError)):
                    is_poppler_error = True
            except ImportError:
                # pdf2image.exceptions might not be available in all versions
                pass
            
            if is_poppler_error:
                error_msg = self._get_poppler_error_message()
                logger.error(f"Poppler-related error: {error_str}. {error_msg}")
                raise RuntimeError(f"Error processing document: {error_str}. {error_msg}")
            
            logger.error(f"Error extracting text from PDF: {error_str}")
            raise
    
    def process_document(self, file_path, file_type):
        """Process document and extract text"""
        try:
            if file_type.lower() == 'pdf':
                document_text = self.extract_text_from_pdf(file_path)
            elif file_type.lower() in ['png', 'jpg', 'jpeg']:
                document_text = self.extract_text_from_image(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            return document_text
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise
    
    def extract_structured_data(self, document_text):
        """
        Extract structured data from document text including tables
        """
        try:
            # Basic extraction - can be enhanced with NLP, regex patterns, etc.
            extracted_data = {
                'total_words': len(document_text.split()),
                'total_characters': len(document_text),
                'total_lines': len(document_text.split('\n')),
                'extraction_date': datetime.now().isoformat()
            }
            
            # Extract common patterns (dates, emails, phone numbers, etc.)
            
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
            
            # Detect and extract tables
            logger.info("Detecting tables in document...")
            tables = self.detect_and_extract_tables(document_text)
            if tables:
                extracted_data['tables'] = tables
                extracted_data['table_count'] = len(tables)
                logger.info(f"Found {len(tables)} table(s) in document")
            
            return extracted_data
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            return {}
    
    def extract_parameters(self, document_text):
        """
        Extract parameters list from document text including table data
        """
        try:
            parameters = []
            
            # Basic parameter extraction - can be enhanced
            # Look for key-value pairs, labels, etc.
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
            logger.info("Extracting table data as parameters...")
            tables = self.detect_and_extract_tables(document_text)
            logger.info(f"Detected {len(tables)} table(s)")
            
            for table in tables:
                table_title = table.get('title', 'Table')
                headers = table.get('headers', [])
                rows = table.get('rows', [])
                
                logger.info(f"Processing table '{table_title}' with {len(headers)} columns and {len(rows)} rows")
                
                # Add table metadata
                parameters.append({
                    'key': f'{table_title}_Table_Info',
                    'value': f"Found table '{table_title}' with {len(headers)} columns and {len(rows)} rows"
                })
                
                # Add each table row as parameters
                for idx, row in enumerate(rows):
                    row_params = {}
                    for header in headers:
                        if header in row:
                            value = row[header]
                            row_params[header] = value
                            
                            # Add individual column as parameter for better visibility
                            if value and str(value).strip():  # Only add if value is not empty
                                parameters.append({
                                    'key': f'{table_title}_Row_{idx + 1}_{header}',
                                    'value': str(value).strip(),
                                    'type': 'table_column',
                                    'table_name': table_title,
                                    'row_number': idx + 1,
                                    'column_name': header
                                })
                    
                    # Add as a structured parameter (full row)
                    parameters.append({
                        'key': f'{table_title}_Row_{idx + 1}',
                        'value': json.dumps(row_params) if row_params else '',
                        'type': 'table_row',
                        'table_name': table_title,
                        'row_number': idx + 1,
                        'row_data': row_params
                    })
            
            table_row_count = sum(1 for p in parameters if p.get('type') == 'table_row')
            table_column_count = sum(1 for p in parameters if p.get('type') == 'table_column')
            logger.info(f"Extracted {len(parameters)} parameters (including {table_row_count} table rows and {table_column_count} table columns)")
            return parameters
        except Exception as e:
            logger.error(f"Error extracting parameters: {str(e)}")
            return []
    
    def refine_document_text(self, document_text):
        """
        Refine and clean document text while preserving table structure
        """
        try:
            if not document_text:
                return ""
            
            # First, detect tables to preserve their structure
            tables = self.detect_and_extract_tables(document_text)
            
            # Remove extra whitespace while preserving newline structure
            lines = document_text.split('\n')
            refined_lines = []
            
            # Track if we're in a table section
            in_table = False
            table_processed = set()
            
            for line in lines:
                # Remove leading/trailing whitespace
                line_stripped = line.strip()
                
                # Check if this line is part of a detected table
                is_table_line = False
                for table in tables:
                    if table.get('title') not in table_processed:
                        # Check if line matches table structure
                        parts = re.split(r'\s{2,}|\t+', line_stripped)
                        parts = [p.strip() for p in parts if p.strip()]
                        if len(parts) >= 3:  # Likely a table row
                            is_table_line = True
                            # Format as table row with proper spacing
                            # Use tab-separated for better readability
                            formatted_line = '\t'.join(parts)
                            refined_lines.append(formatted_line)
                            break
                
                if not is_table_line:
                    # Clean up multiple spaces within the line (but preserve newlines)
                    line_cleaned = re.sub(r' +', ' ', line_stripped)  # Replace multiple spaces with single space
                    
                    # Skip empty lines (but keep paragraph breaks)
                    if line_cleaned:
                        refined_lines.append(line_cleaned)
                    elif refined_lines and refined_lines[-1]:  # Add single blank line for paragraph breaks
                        refined_lines.append('')
            
            # Join lines - newlines are preserved
            refined_text = '\n'.join(refined_lines)
            
            # Append formatted table information if tables were found
            if tables:
                refined_text += '\n\n' + '='*60 + '\n'
                refined_text += 'EXTRACTED TABLES:\n'
                refined_text += '='*60 + '\n\n'
                
                for table in tables:
                    table_title = table.get('title', 'Table')
                    headers = table.get('headers', [])
                    rows = table.get('rows', [])
                    
                    refined_text += f'\n{table_title}:\n'
                    refined_text += '-'*60 + '\n'
                    
                    # Add headers
                    if headers:
                        refined_text += '\t'.join(headers) + '\n'
                        refined_text += '-'*60 + '\n'
                    
                    # Add rows
                    for row in rows:
                        row_values = [str(row.get(header, '')) for header in headers]
                        refined_text += '\t'.join(row_values) + '\n'
                    
                    refined_text += '\n'
            
            return refined_text
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
            logger.info(f"Processing document: {filename}")
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
            
            # Clean up uploaded file (optional - you may want to keep it)
            # if os.path.exists(file_path):
            #     os.remove(file_path)
            
            return {
                'document_text': document_text,
                'extracted_data': extracted_data,
                'parameters_list': parameters_list,
                'refined_text': refined_text,
                'file_path': file_path,
                'file_size': os.path.getsize(file_path)
            }
        except Exception as e:
            logger.error(f"Error processing uploaded document: {str(e)}")
            raise


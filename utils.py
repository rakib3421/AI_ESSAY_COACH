"""
Utilities module for the Essay Revision Application
Contains utility functions for file handling, validation, and document processing
"""
import os
import re
import logging
from flask import session, redirect, url_for, flash
from functools import wraps
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_LINE_SPACING, WD_UNDERLINE
import datetime
from io import BytesIO
from config import Config

logger = logging.getLogger(__name__)

def allowed_file(filename):
    """
    Check if file extension is allowed with comprehensive validation
    
    Args:
        filename (str): Name of the file to check
    
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    if not filename:
        return False, "No filename provided"
    
    if '.' not in filename:
        return False, "File must have an extension"
    
    file_extension = filename.rsplit('.', 1)[1].lower()
    
    if file_extension not in Config.ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(Config.ALLOWED_EXTENSIONS)
        return False, f"File type '{file_extension}' not allowed. Allowed types: {allowed_list}"
    
    # Check for suspicious filenames
    suspicious_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    for pattern in suspicious_patterns:
        if pattern in filename:
            return False, "Filename contains invalid characters"
    
    return True, "File type is valid"

def validate_file_upload(file):
    """
    Comprehensive file upload validation
    
    Args:
        file: Flask file upload object
    
    Returns:
        tuple: (bool, str) - (is_valid, error_message)
    """
    if not file:
        return False, "No file provided"
    
    if not file.filename:
        return False, "No file selected"
    
    # Check filename
    is_valid_name, name_error = allowed_file(file.filename)
    if not is_valid_name:
        return False, name_error
    
    # Check file size
    try:
        if not is_file_size_valid(file):
            max_size_mb = Config.MAX_CONTENT_LENGTH / (1024 * 1024)
            return False, f"File size exceeds maximum limit of {max_size_mb:.1f} MB"
    except Exception as e:
        logger.error(f"Error checking file size: {e}")
        return False, "Unable to validate file size"
    
    # Check if file is empty
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset pointer
    
    if file_size == 0:
        return False, "File is empty"
    
    if file_size < 10:  # Less than 10 bytes is likely invalid
        return False, "File appears to be invalid or corrupted"
    
    return True, "File validation passed"

def safe_get_string(data, key, default=''):
    """Safely extract and strip string values from request data, handling None values"""
    value = data.get(key, default)
    if value is None:
        return default
    return str(value).strip()

def is_file_size_valid(file):
    """
    Check if file size is within limits with error handling
    
    Args:
        file: Flask file upload object
    
    Returns:
        bool: True if file size is valid, False otherwise
    """
    try:
        current_position = file.tell()  # Save current position
        file.seek(0, 2)  # Seek to end of file
        file_size = file.tell()
        file.seek(current_position)  # Reset to original position
        return file_size <= Config.MAX_CONTENT_LENGTH
    except Exception as e:
        logger.error(f"Error checking file size: {e}")
        return False

def extract_text_from_file(file_path):
    """
    Extract text from uploaded file with comprehensive error handling
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        tuple: (str or None, str) - (extracted_text, error_message)
    """
    if not file_path:
        return None, "No file path provided"
    
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        # Check file size before processing
        file_size = os.path.getsize(file_path)
        if file_size > Config.MAX_CONTENT_LENGTH:
            max_size_mb = Config.MAX_CONTENT_LENGTH / (1024 * 1024)
            return None, f"File size ({file_size / (1024 * 1024):.1f} MB) exceeds maximum limit of {max_size_mb:.1f} MB"
        
        if file_size == 0:
            return None, "File is empty"
        
        file_extension = file_path.lower().split('.')[-1]
        
        if file_extension == 'txt':
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                    if not text.strip():
                        return None, "Text file is empty or contains only whitespace"
                    return text, "Success"
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as file:
                        text = file.read()
                        if not text.strip():
                            return None, "Text file is empty or contains only whitespace"
                        return text, "Success"
                except Exception as e:
                    return None, f"Failed to read text file with alternative encoding: {e}"
        
        elif file_extension == 'docx':
            try:
                from docx import Document
                doc = Document(file_path)
                text_parts = []
                
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_parts.append(paragraph.text)
                
                if not text_parts:
                    return None, "Word document appears to be empty or contains no readable text"
                
                text = '\n'.join(text_parts)
                return text, "Success"
                
            except Exception as e:
                return None, f"Failed to extract text from Word document: {e}"
        
        else:
            return None, f"Unsupported file type: {file_extension}"
    
    except PermissionError:
        return None, "Permission denied: Unable to access the file"
    except OSError as e:
        return None, f"Operating system error: {e}"
    except Exception as e:
        logger.error(f"Unexpected error extracting text from file {file_path}: {e}")
        return None, f"Unexpected error processing file: {e}"

def get_current_user():
    """Get current user information from session"""
    if 'user_id' not in session:
        return None
    return {
        'id': session['user_id'],
        'username': session['username'],
        'role': session['role']
    }

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] != role:
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_text(text):
    """Remove or replace invalid XML characters for Word document compatibility."""
    if not isinstance(text, str):
        text = str(text)
    
    if not text:
        return ""
    
    # Remove null bytes first
    text = text.replace('\x00', '')
    
    # Replace problematic Unicode characters
    replacements = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2026': '...',  # Horizontal ellipsis
        '\u00a0': ' ',  # Non-breaking space
        '\u200b': '',   # Zero width space
        '\u200e': '',   # Left-to-right mark
        '\u200f': '',   # Right-to-left mark
        '\ufeff': '',   # Zero width no-break space
        '—': '-',       # Em dash
        '–': '-',       # En dash
        '"': '"',       # Left double quote
        '"': '"',       # Right double quote
        ''': "'",       # Left single quote
        ''': "'",       # Right single quote
        '…': '...',     # Horizontal ellipsis
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Keep only XML-compatible characters
    result = []
    for char in text:
        cp = ord(char)
        # XML 1.0 valid characters: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
        if (cp == 0x09 or cp == 0x0A or cp == 0x0D or 
            (0x20 <= cp <= 0xD7FF) or 
            (0xE000 <= cp <= 0xFFFD) or 
            (0x10000 <= cp <= 0x10FFFF)):
            result.append(char)
        elif cp < 0x20:  # Control characters
            if cp == 0x09 or cp == 0x0A or cp == 0x0D:  # Tab, LF, CR are allowed
                result.append(char)
            # Skip other control characters
        else:
            # For other problematic characters, try to find ASCII equivalent
            if char.isspace():
                result.append(' ')
            elif char.isalnum():
                try:
                    ascii_char = char.encode('ascii', 'ignore').decode('ascii')
                    if ascii_char:
                        result.append(ascii_char)
                except:
                    pass
    
    return ''.join(result)

def extract_suggestions_from_feedback(feedback):
    """Extract suggestions from feedback containing tags <delete>, <add>, <replace>"""
    suggestions = []
    delete_pattern = re.compile(r'<delete>(.*?)</delete>')
    add_pattern = re.compile(r'<add>(.*?)</add>')
    replace_pattern = re.compile(r'<replace>(.*?)\|(.*?)</replace>')

    for match in delete_pattern.findall(feedback):
        suggestions.append({'type': 'delete', 'text': match})
    for match in add_pattern.findall(feedback):
        suggestions.append({'type': 'add', 'text': match})
    for match in replace_pattern.findall(feedback):
        suggestions.append({'type': 'replace', 'text': f'{match[0]} -> {match[1]}'})
    
    return suggestions

def create_word_document_with_suggestions(essay_text, analysis_data, accepted_suggestions):
    """Create Word document with highlighted suggestions"""
    doc = Document()
    
    # Add document properties with sanitized text
    doc.core_properties.author = sanitize_text("AI Essay Coach")
    doc.core_properties.title = sanitize_text("Essay Analysis Report")
    doc.core_properties.created = datetime.datetime.now()
    
    # Set document-wide double spacing
    from docx.shared import Pt
    from docx.enum.text import WD_LINE_SPACING
    
    # Configure document styles for double spacing
    styles = doc.styles
    style = styles['Normal']
    style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)
    
    # Add header with logo and title
    section = doc.sections[0]
    header = section.header
    header_para = header.paragraphs[0]
    header_para.text = sanitize_text("AI Essay Coach - Analysis Report")
    header_para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    
    # Add score table first
    doc.add_heading(sanitize_text('Rubric Scores & Analysis'), level=1)
    score_table = doc.add_table(rows=1, cols=4)
    score_table.style = 'Table Grid'
    score_header_cells = score_table.rows[0].cells
    score_header_cells[0].text = sanitize_text('Category')
    score_header_cells[1].text = sanitize_text('Score')
    score_header_cells[2].text = sanitize_text('Weight')
    score_header_cells[3].text = sanitize_text('Explanation')

    # Define rubric weights
    rubric_weights = {
        'ideas': {'weight': 30, 'label': 'Ideas & Content'},
        'organization': {'weight': 25, 'label': 'Organization & Structure'},
        'style': {'weight': 20, 'label': 'Voice & Style'},
        'grammar': {'weight': 25, 'label': 'Grammar & Conventions'}
    }

    total_score = 0
    for category, score in analysis_data['scores'].items():
        row_cells = score_table.add_row().cells
        weight_info = rubric_weights.get(category, {'weight': 25, 'label': category.title()})
        row_cells[0].text = sanitize_text(weight_info['label'])
        row_cells[1].text = sanitize_text(f"{score}/{weight_info['weight']}")
        row_cells[2].text = sanitize_text(f"{weight_info['weight']}%")
        reason = analysis_data.get('score_reasons', {}).get(category, 'No reason provided.')
        row_cells[3].text = sanitize_text(str(reason))
        total_score += score

    # Add total score row
    total_row = score_table.add_row().cells
    total_row[0].text = sanitize_text('TOTAL SCORE')
    total_row[1].text = sanitize_text(f"{total_score}/100")
    total_row[2].text = sanitize_text('100%')
    total_row[3].text = sanitize_text('Overall performance based on rubric criteria')
    
    # Make total row bold
    for cell in total_row:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True

    # Add examples section with proper formatting
    doc.add_heading(sanitize_text('Supporting Evidence for Rubric Scores'), level=1)
    for dimension in ['ideas', 'organization', 'style', 'grammar']:
        examples = analysis_data.get('examples', {}).get(dimension, [])
        if examples:
            doc.add_heading(sanitize_text(rubric_weights.get(dimension, {'label': dimension.title()})['label']), level=2)
            for i, example_text in enumerate(examples[:2], 1):  # Limit to 2 examples
                sanitized_text = sanitize_text(str(example_text))
                p = doc.add_paragraph()
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
                p.add_run(f'{i}. ').bold = True
                p.add_run(sanitized_text)

    # Add essay with inline suggestions and comments
    doc.add_heading(sanitize_text('Essay with AI Coaching Suggestions'), level=1)
    
    # Add instructions paragraph
    instructions = doc.add_paragraph()
    instructions.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    instructions_run = instructions.add_run(
        "Instructions: Text marked with blue strikethrough should be deleted. "
        "Text marked with red underline should be added. "
        "Explanations for each suggestion are provided in parentheses."
    )
    instructions_run.italic = True
    instructions_run.font.size = Pt(10)
    
    # Add spacing
    doc.add_paragraph()
    
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE

    # Ensure tagged_essay is sanitized
    tagged_essay = sanitize_text(str(analysis_data.get('tagged_essay', essay_text)))

    # Regex patterns for tags
    delete_pattern = re.compile(r'<delete>(.*?)</delete>')
    add_pattern = re.compile(r'<add>(.*?)</add>')
    replace_pattern = re.compile(r'<replace>(.*?)\|(.*?)</replace>')

    # Get suggestions from analysis data
    suggestions = analysis_data.get('suggestions', [])

    # Helper to add colored run with sanitized text and proper formatting
    def add_colored_run(paragraph, text, color, strike=False, underline=False):
        sanitized_text = sanitize_text(str(text))
        run = paragraph.add_run(sanitized_text)
        run.font.color.rgb = RGBColor(*color)
        run.font.strike = strike
        if underline:
            from docx.enum.text import WD_UNDERLINE
            run.font.underline = WD_UNDERLINE.SINGLE
        return run

    pos = 0
    length = len(tagged_essay)

    while pos < length:
        next_delete = delete_pattern.search(tagged_essay, pos)
        next_add = add_pattern.search(tagged_essay, pos)
        next_replace = replace_pattern.search(tagged_essay, pos)

        candidates = [m for m in [next_delete, next_add, next_replace] if m and m.start() >= pos]

        if not candidates:
            remaining_text = sanitize_text(tagged_essay[pos:])
            if remaining_text:
                paragraph.add_run(remaining_text)
            pos = length
            continue

        next_tag = min(candidates, key=lambda m: m.start())

        if next_tag.start() > pos:
            before_text = sanitize_text(tagged_essay[pos:next_tag.start()])
            if before_text:
                paragraph.add_run(before_text)

        if next_tag == next_delete:
            text = sanitize_text(str(next_tag.group(1) or ''))
            if text:
                # Deletions: blue color with strikethrough
                run = add_colored_run(paragraph, text, (0, 0, 255), strike=True)
                # Find reason for this suggestion
                reason = ''
                for s in suggestions:
                    if s.get('type', '').lower() == 'delete' and sanitize_text(str(s.get('text', ''))) == text:
                        reason = sanitize_text(str(s.get('reason', '')))
                        break
                # Add reason as inline comment (in parentheses) - smaller font, italic
                if reason:
                    reason_run = paragraph.add_run(f' ({reason})')
                    reason_run.italic = True
                    reason_run.font.size = Pt(9)
                    reason_run.font.color.rgb = RGBColor(100, 100, 100)  # Gray color
            pos = next_tag.end()
        elif next_tag == next_add:
            text = sanitize_text(str(next_tag.group(1) or ''))
            if text:
                # Additions: red color with underline
                run = add_colored_run(paragraph, text, (255, 0, 0), underline=True)
                reason = ''
                for s in suggestions:
                    if s.get('type', '').lower() == 'add' and sanitize_text(str(s.get('text', ''))) == text:
                        reason = sanitize_text(str(s.get('reason', '')))
                        break
                if reason:
                    reason_run = paragraph.add_run(f' ({reason})')
                    reason_run.italic = True
                    reason_run.font.size = Pt(9)
                    reason_run.font.color.rgb = RGBColor(100, 100, 100)  # Gray color
            pos = next_tag.end()
        elif next_tag == next_replace:
            old_word = sanitize_text(str(next_tag.group(1) or ''))
            new_word = sanitize_text(str(next_tag.group(2) or ''))
            if old_word:
                run_old = add_colored_run(paragraph, old_word, (0, 0, 255), strike=True)
                reason = ''
                for s in suggestions:
                    if (s.get('type', '').lower() == 'replace' and 
                        sanitize_text(str(s.get('text', ''))) == f"{old_word} -> {new_word}"):
                        reason = sanitize_text(str(s.get('reason', '')))
                        break
                if reason:
                    reason_run = paragraph.add_run(f' ({reason})')
                    reason_run.italic = True
                    reason_run.font.size = Pt(9)
                    reason_run.font.color.rgb = RGBColor(100, 100, 100)  # Gray color
            paragraph.add_run(' → ')  # Better arrow symbol
            if new_word:
                run_new = add_colored_run(paragraph, new_word, (255, 0, 0), underline=True)
            pos = next_tag.end()

    return doc

def calculate_scores_with_rubric(text_analysis, rubric_config=None):
    """Calculate scores using modular rubric engine"""
    if not rubric_config:
        # Use default weights
        rubric_config = {
            'ideas_weight': 30,
            'organization_weight': 25,
            'style_weight': 20,
            'grammar_weight': 25
        }
    
    # Extract base scores from AI analysis (0-100 scale)
    base_scores = text_analysis.get('scores', {})
    
    # Convert to weighted scores
    weighted_scores = {}
    total_score = 0
    
    for dimension in ['ideas', 'organization', 'style', 'grammar']:
        base_score = base_scores.get(dimension, 75)  # Default to 75 if missing
        weight_key = f"{dimension}_weight"
        weight = rubric_config.get(weight_key, 25)
        
        # Calculate weighted score (base_score * weight / 100)
        weighted_score = (base_score * weight) / 100
        weighted_scores[dimension] = weighted_score
        total_score += weighted_score
    
    weighted_scores['total'] = total_score
    return weighted_scores

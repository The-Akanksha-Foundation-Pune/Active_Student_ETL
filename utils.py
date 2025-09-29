import re
from datetime import datetime
import logging

def clean_student_name(value):
    return re.sub(r'\s+', " ", value).strip().title()

def convert_grade_name(value):
    grade_mapping = {
        "Jr.KG": "JR.KG",
        "Sr.KG": "SR.KG",
        "I": "1", "II": "2", "III": "3", "IV": "4", "V": "5", "VI": "6", "VII": "7", "VIII": "8","IX": "9", "X": "10"
    }
    # Handle 'GRADE X' format
    match = re.match(r"GRADE (\w+)", value, re.IGNORECASE) # Added re.IGNORECASE
    if match:
        roman = match.group(1).upper() # Convert to upper for mapping
        return f"GRADE {grade_mapping.get(roman, roman)}"
    # Handle direct mappings
    return grade_mapping.get(value.strip().upper(), value.strip()) # Trim and upper for direct mapping

def format_date_column(original_date):
    try:
        return datetime.strptime(original_date, '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        logging.warning(f"Invalid date format: {original_date}")
        return original_date

def clean_gender(value):
    if value:
        value = value.strip().upper()
        return "M" if value == "MALE" else "F" if value == "FEMALE" else None
    return None

def extract_division(value):
    if value:
        match = re.search(r'[A-Za-z]+', value)
        return match.group(0).upper() if match else value.strip().upper() # Ensure consistent casing
    return None

def generate_unique_key(record, academic_year):
    # Ensure all components are strings to avoid errors
    school_name = str(record.get('school_name', '')).strip()
    student_id = str(record.get('student_id', '')).strip()
    grade_name = str(record.get('grade_name', '')).strip() # Use original grade for key generation if needed, or converted. Sticking to original for key integrity.
    
    # Apply cleaning/conversion functions that are part of the key logic
    converted_grade = convert_grade_name(grade_name)

    return f"{school_name}_{student_id}_{academic_year}_{converted_grade}"


def trim_string(value):
    """Trims whitespace from a string value."""
    if isinstance(value, str):
        return value.strip()
    return value

def validate_student_record(record):
    """
    Validates a single student record.
    Returns (True, record) if valid, (False, error_message) otherwise.
    """
    required_fields = ['school_name', 'status', 'grade_name', 'student_name', 'student_id', 'gender', 'division_name']
    
    for field in required_fields:
        if field not in record or not trim_string(record[field]): # Check for existence and non-empty after trimming
            return False, f"Missing or empty required field: '{field}'"
            
    # Basic data type checks and specific value validations
    if not isinstance(record.get('student_id'), (str, int)):
        return False, "Invalid 'student_id' type, must be string or int."
    
    # Further validation could be added here, e.g., regex for student_id format,
    # or checking if grade_name is within an expected set after conversion.
    
    return True, record
import mysql.connector
import logging
from datetime import datetime
from utils import convert_grade_name, format_date_column, clean_gender, extract_division, clean_student_name, trim_string


def connect_to_mysql(db_config):
    try:
        logging.info("Attempting to connect to MySQL database...")
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            logging.info("Successfully connected to MySQL database.")
            return conn
        else:
            logging.error("MySQL connection established but not connected.")
            return None
    except mysql.connector.Error as err:
        logging.error(f"Failed to connect to MySQL: {err}", exc_info=True) # exc_info=True to log traceback
        return None

def fetch_existing_keys(cursor, academic_year):
    try:
        logging.info(f"Fetching existing unique keys for academic year: {academic_year} from active_student_data.")
        cursor.execute("SELECT unique_key FROM active_student_data WHERE academic_year = %s", (academic_year,))
        keys = set(row[0] for row in cursor.fetchall())
        logging.info(f"Found {len(keys)} existing unique keys for {academic_year}.")
        return keys
    except mysql.connector.Error as err:
        logging.error(f"Error fetching unique keys for {academic_year}: {err}", exc_info=True)
        return set()

def get_current_record_details(cursor, unique_key):
    """Fetches the current details of a record from active_student_data."""
    try:
        logging.debug(f"Fetching current details for unique_key: {unique_key}")
        cursor.execute(
            """
            SELECT status, grade_name, student_name, gender, division_name
            FROM active_student_data
            WHERE unique_key = %s
            """,
            (unique_key,)
        )
        result = cursor.fetchone()
        if result:
            return {
                'status': result[0],
                'grade_name': result[1],
                'student_name': result[2],
                'gender': result[3],
                'division_name': result[4]
            }
        return None
    except mysql.connector.Error as err:
        logging.error(f"Error fetching current record details for {unique_key}: {err}", exc_info=True)
        return None

def log_history(cursor, unique_key, change_type, field_changed=None, old_value=None, new_value=None):
    """
    Logs a change event to the student_data_history table.
    """
    sql_insert_history = """
    INSERT INTO student_data_history (unique_key, change_type, field_changed, old_value, new_value, change_timestamp)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(sql_insert_history, (unique_key, change_type, field_changed, old_value, new_value, timestamp))
        logging.debug(f"History logged: Key={unique_key}, Type={change_type}, Field={field_changed}, Old='{old_value}', New='{new_value}'")
    except mysql.connector.Error as err:
        logging.error(f"Error logging history for Unique Key {unique_key}, Change Type {change_type}: {err}", exc_info=True)


def update_existing_record(cursor, record, unique_key):
    # Fetch current record details to compare for history logging
    current_record_details = get_current_record_details(cursor, unique_key)
    
    if not current_record_details:
        logging.warning(f"Could not find existing record for update with unique_key: {unique_key}. Skipping update.")
        return

    sql_update = """
    UPDATE active_student_data
    SET status = %s, grade_name = %s, student_name = %s, gender = %s, division_name = %s, timestamp = %s
    WHERE unique_key = %s
    """
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Apply cleaning functions to the record values before comparison/update
        new_status = trim_string(record.get('status'))
        new_grade_name = convert_grade_name(record.get('grade_name'))
        new_student_name = clean_student_name(record.get('student_name'))
        new_gender = record.get('gender')  # Gender already cleaned in main.py
        new_division_name = extract_division(record.get('division_name'))

        # Compare and log changes
        fields_to_check = {
            'status': new_status,
            'grade_name': new_grade_name,
            'student_name': new_student_name,
            'gender': new_gender,
            'division_name': new_division_name
        }

        has_changed = False
        for field, new_val in fields_to_check.items():
            old_val = current_record_details.get(field)
            if str(old_val) != str(new_val): # Convert to string for consistent comparison, especially with None/empty strings
                log_history(cursor, unique_key, 'UPDATE', field, old_val, new_val)
                has_changed = True

        if has_changed:
            cursor.execute(sql_update, (
                new_status,
                new_grade_name,
                new_student_name,
                new_gender,
                new_division_name,
                timestamp,
                unique_key
            ))
            logging.info(f"Updated record for Unique Key: {unique_key}. Changes detected.")
        else:
            logging.info(f"No significant changes detected for Unique Key: {unique_key}. Skipping update.")

    except mysql.connector.Error as err:
        logging.error(f"Error updating record for Unique Key {unique_key}: {err}", exc_info=True)

def insert_new_record(cursor, record, unique_key, academic_year):
    sql_insert = """
    INSERT INTO active_student_data (school_name, status, grade_name, student_name, student_id, gender, division_name, academic_year, unique_key, timestamp)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Apply cleaning/conversion functions before insertion
        cleaned_school_name = trim_string(record.get('school_name'))
        cleaned_status = trim_string(record.get('status'))
        converted_grade = convert_grade_name(record.get('grade_name'))
        cleaned_student_name = clean_student_name(record.get('student_name'))
        cleaned_student_id = trim_string(record.get('student_id')) # Ensure student_id is trimmed
        cleaned_gender = record.get('gender')  # Gender already cleaned in main.py
        extracted_division = extract_division(record.get('division_name'))

        cursor.execute(sql_insert, (
            cleaned_school_name,
            cleaned_status,
            converted_grade,
            cleaned_student_name,
            cleaned_student_id,
            cleaned_gender,
            extracted_division,
            academic_year,
            unique_key,
            timestamp
        ))
        logging.info(f"Inserted new record for Unique Key: {unique_key}. School: {cleaned_school_name}, Student: {cleaned_student_name}.")
        log_history(cursor, unique_key, 'INSERT', 'New Record', None, "Initial Insertion") # Log initial insertion
    except mysql.connector.Error as err:
        # Check if the error is due to a duplicate unique_key (e.g., race condition)
        if err.errno == 1062: # MySQL error code for Duplicate entry for key 'PRIMARY' or unique constraint
            logging.warning(f"Attempted to insert duplicate unique key {unique_key}. Likely a race condition or already exists. Skipping insertion.")
        else:
            logging.error(f"Error inserting record for Unique Key {unique_key}: {err}", exc_info=True)

def fetch_duplicate_records(cursor):
    try:
        logging.info("Checking for duplicate records in active_student_data based on unique_key.")
        cursor.execute(
            """
            SELECT unique_key, COUNT(*) AS count_duplicates
            FROM active_student_data
            GROUP BY unique_key
            HAVING COUNT(*) > 1
            """
        )
        duplicates = cursor.fetchall()
        if duplicates:
            logging.error("Duplicate unique_key records found! This indicates a potential issue with database constraints or previous data. Please investigate.")
            for duplicate in duplicates:
                logging.error(f"Duplicate Key: {duplicate[0]}, Count: {duplicate[1]}")
        else:
            logging.info("No duplicate unique_key records found. Database integrity maintained.")
    except mysql.connector.Error as err:
        logging.error(f"Error fetching duplicate records: {err}", exc_info=True)
        
def mark_records_as_inactive(cursor, existing_keys, api_keys):
    """
    Updates the status to 'Inactive' for records that are present in the database
    but not in the API response.
    """
    inactive_keys = existing_keys - api_keys
    
    if not inactive_keys:
        logging.info("No records to mark as Inactive.")
        return

    sql_update_status = """
    UPDATE active_student_data
    SET status = 'Inactive', timestamp = %s
    WHERE unique_key = %s AND status != 'Inactive'
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    logging.info(f"Attempting to mark {len(inactive_keys)} records as 'Inactive'.")

    for unique_key in inactive_keys:
        try:
            # Fetch current status to log history only if status actually changes
            cursor.execute("SELECT status FROM active_student_data WHERE unique_key = %s", (unique_key,))
            current_status = cursor.fetchone()
            if current_status and current_status[0] != 'Inactive':
                cursor.execute(sql_update_status, (timestamp, unique_key))
                if cursor.rowcount > 0: # Check if any row was actually updated
                    logging.info(f"Marked Unique Key {unique_key} as 'Inactive'.")
                    log_history(cursor, unique_key, 'INACTIVATE', 'status', current_status[0], 'Inactive')
                else:
                     logging.debug(f"Unique Key {unique_key} was already 'Inactive' or not found. No update needed.")
            else:
                logging.debug(f"Unique Key {unique_key} is already 'Inactive' or not found in DB. No action required.")

        except mysql.connector.Error as err:
            logging.error(f"Error marking Unique Key {unique_key} as Inactive: {err}", exc_info=True)
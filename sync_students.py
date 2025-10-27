"""
Unified Student Data Sync Script
Checks if database is empty, then either initializes or updates records
"""

import sys
import mysql.connector
import json
import logging
import requests
import re
import urllib3
from datetime import datetime
import configparser

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== LOGGING SETUP ==========
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('student_sync.log')
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ========== CONFIG LOAD ==========
config = configparser.ConfigParser()
config.read('config.ini')

api_url = config['api']['url']
api_key = config['api']['key']

db_config = {
    'user': config['mysql']['user'],
    'password': config['mysql']['password'],
    'host': config['mysql']['host'],
    'port': int(config['mysql']['port']),
    'database': config['mysql']['database']
}

# ========== DATA CLEANING FUNCTIONS ==========
def clean_student_name(value):
    return re.sub(r'\s+', ' ', value).strip().title() if value else None

def convert_grade_name(value):
    if not value:
        return None
    value = value.strip()
    if value == "Jr.KG":
        return "JR.KG"
    elif value == "Sr.KG":
        return "SR.KG"
    roman_to_number = {
        "I": "1", "II": "2", "III": "3", "IV": "4", "V": "5",
        "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10"
    }
    match = re.match(r"GRADE (\w+)", value.upper())
    if match:
        roman = match.group(1)
        return f"GRADE {roman_to_number.get(roman.upper(), roman)}"
    return value.upper()

def clean_gender(value):
    if not value:
        return None
    value = value.strip().upper()
    return "M" if value == "MALE" else "F" if value == "FEMALE" else value

def extract_division(value):
    if not value:
        return None
    match = re.search(r'[A-Za-z]+', value)
    return match.group(0).upper() if match else value.upper()

def generate_unique_key(record):
    school = re.sub(r'\s+', ' ', record['school_name']).strip().upper()
    student_id = str(record['student_id']).strip().upper()
    academic_year = record['academic_year'].strip()
    # Note: grade_name is NOT included in unique key to allow grade updates
    # A student can only have ONE record per academic year (updated when grade changes)
    return f"{school}_{student_id}_{academic_year}"

# ========== DATABASE FUNCTIONS ==========
def connect_to_mysql():
    try:
        logger.info("Connecting to MySQL...")
        conn = mysql.connector.connect(**db_config)
        logger.info("Connected to MySQL.")
        return conn
    except mysql.connector.Error as err:
        logger.error(f"MySQL connection failed: {err}")
        return None

def create_tables_if_not_exist(cursor):
    """Create tables if they don't exist"""
    sql_commands = [
        """CREATE TABLE IF NOT EXISTS active_student_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            school_name VARCHAR(255) NOT NULL,
            status VARCHAR(50),
            grade_name VARCHAR(50),
            student_name VARCHAR(500) NOT NULL,
            student_id VARCHAR(50) NOT NULL,
            gender CHAR(50),
            division_name VARCHAR(10) NOT NULL,
            academic_year VARCHAR(10) NOT NULL,
            unique_key VARCHAR(255) NOT NULL UNIQUE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )""",
        
        """CREATE TABLE IF NOT EXISTS student_data_history (
            history_id INT AUTO_INCREMENT PRIMARY KEY,
            unique_key VARCHAR(255) NOT NULL,
            change_type ENUM('INSERT', 'UPDATE', 'INACTIVATE') NOT NULL,
            field_changed VARCHAR(255),
            old_value TEXT,
            new_value TEXT,
            change_timestamp DATETIME NOT NULL,
            INDEX (unique_key),
            INDEX (change_timestamp)
        )"""
    ]
    
    try:
        for i, sql in enumerate(sql_commands, 1):
            cursor.execute(sql)
            logger.info(f"Table {i} created/verified successfully.")
    except mysql.connector.Error as err:
        logger.error(f"Error creating tables: {err}")
        raise

def is_database_empty(cursor):
    """Check if the database has any records"""
    try:
        cursor.execute("SELECT COUNT(*) FROM active_student_data")
        count = cursor.fetchone()[0]
        return count == 0
    except mysql.connector.Error as err:
        logger.error(f"Error checking database: {err}")
        return True  # Assume empty if error

def check_record_exists(cursor, unique_key):
    """Check if a record with the unique_key already exists"""
    try:
        cursor.execute("SELECT COUNT(*) FROM active_student_data WHERE unique_key = %s", (unique_key,))
        count = cursor.fetchone()[0]
        return count > 0
    except mysql.connector.Error as err:
        logger.error(f"Error checking record existence: {err}")
        return False

# ========== API FETCH ==========
def fetch_data_from_api():
    try:
        logger.info("Fetching data from API...")
        params = {'api-key': api_key, 'school_name': 'ALL'}
        full_url = requests.Request('GET', api_url, params=params).prepare().url
        logger.info(f"Request URL: {full_url}")
        
        response = requests.get(api_url, params=params, verify=False, timeout=30)
        if response.status_code == 200:
            logger.info("Data fetched successfully.")
            return response.json()
        else:
            logger.error(f"Failed to retrieve data. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return None

# ========== INSERT/UPDATE FUNCTIONS ==========
def insert_or_update_record(cursor, record, academic_year, timestamp):
    """Insert new record or update existing one. Returns 'insert' or 'update'"""
    grade_clean = convert_grade_name(record.get('grade_name'))
    # Generate unique key WITHOUT grade_name (allows grade updates)
    unique_key = generate_unique_key({
        'school_name': record.get('school_name'),
        'student_id': record.get('student_id'),
        'academic_year': academic_year
    })
    
    exists = check_record_exists(cursor, unique_key)
    
    if exists:
        # Update existing record
        sql = """
            UPDATE active_student_data
            SET status = %s, grade_name = %s, student_name = %s,
                gender = %s, division_name = %s, timestamp = %s
            WHERE unique_key = %s
        """
        cursor.execute(sql, (
            record.get('status'),
            grade_clean,
            clean_student_name(record.get('student_name')),
            clean_gender(record.get('gender')),
            extract_division(record.get('division_name')),
            timestamp,
            unique_key
        ))
        logger.info(f"[UPDATE] {unique_key}")
        return 'update'
    else:
        # Insert new record
        sql = """
            INSERT INTO active_student_data (
                school_name, status, grade_name, student_name, student_id, gender,
                division_name, academic_year, unique_key, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            cursor.execute(sql, (
                re.sub(r'\s+', ' ', record.get('school_name', '')).strip().upper(),
                record.get('status'),
                grade_clean,
                clean_student_name(record.get('student_name')),
                record.get('student_id'),
                clean_gender(record.get('gender')),
                extract_division(record.get('division_name')),
                academic_year,
                unique_key,
                timestamp
            ))
            logger.info(f"[INSERT] {unique_key}")
            return 'insert'
        except mysql.connector.Error as e:
            # If duplicate key error, it means the record already exists
            if e.errno == 1062:
                logger.warning(f"[DUPLICATE] {unique_key} - skipping")
                return 'duplicate'
            else:
                raise

# ========== MAIN FUNCTION ==========
def main():
    logger.info("=" * 80)
    logger.info("STUDENT DATA SYNC - Starting Process")
    logger.info("=" * 80)
    
    # Fetch data from API
    json_response = fetch_data_from_api()
    if not json_response:
        logger.error("No data fetched. Exiting.")
        sys.exit(1)
    
    students_data = json_response.get('data', [])
    if not students_data:
        logger.error("API returned empty student data.")
        sys.exit(1)
    
    logger.info(f"API returned {len(students_data)} records")
    
    # Connect to database
    conn = connect_to_mysql()
    if not conn:
        sys.exit(1)
    
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    logger.info("Creating/verifying tables...")
    create_tables_if_not_exist(cursor)
    
    # Determine academic year
    now = datetime.now()
    academic_year = f"{now.year}-{now.year + 1}" if now.month >= 5 else f"{now.year - 1}-{now.year}"
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # Check if database is empty
    db_empty = is_database_empty(cursor)
    
    if db_empty:
        logger.info("Database is empty. Performing full data import...")
        mode = "INITIAL"
    else:
        logger.info("Database has existing data. Performing incremental update...")
        mode = "UPDATE"
    
    # Process records
    insert_count = 0
    update_count = 0
    
    for record in students_data:
        try:
            result = insert_or_update_record(cursor, record, academic_year, timestamp)
            
            # Count based on return value
            if result == 'insert':
                insert_count += 1
            elif result == 'update':
                update_count += 1
            elif result == 'duplicate':
                update_count += 1  # Count duplicates as updates
                
        except Exception as e:
            logger.error(f"Error processing record: {e}")
            continue
    
    # Get database count for verification BEFORE closing connection
    cursor.execute("SELECT COUNT(*) FROM active_student_data")
    db_total = cursor.fetchone()[0]
    
    # Commit transaction
    conn.commit()
    cursor.close()
    conn.close()
    
    logger.info("=" * 80)
    logger.info(f"SYNC COMPLETE - Mode: {mode}")
    logger.info(f"Records inserted: {insert_count}")
    logger.info(f"Records updated: {update_count}")
    logger.info(f"Total records in database: {db_total}")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    print(f"\n✅ Sync completed successfully!")
    print(f"   Mode: {mode}")
    print(f"   Inserted: {insert_count} records")
    print(f"   Updated: {update_count} records")
    print(f"   Total in DB: {db_total} records")

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    main()


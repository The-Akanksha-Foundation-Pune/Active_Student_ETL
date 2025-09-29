import sys
import mysql.connector
import json
import logging
import requests
import re
from datetime import datetime
import configparser

# ---------- Logging setup ----------
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler('active_students_update.log')
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ---------- Config load ----------
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

# ---------- API fetch ----------
def fetch_data_from_api():
    try:
        logger.info("Fetching data from API...")
        params = {'api-key': api_key, 'school_name': 'ALL'}
        full_url = requests.Request('GET', api_url, params=params).prepare().url
        logger.info(f"Request URL: {full_url}")
        print(f"[DEBUG] Requesting URL: {full_url}")

        response = requests.get(api_url, params=params)
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

# ---------- Cleaning functions ----------
def clean_student_name(value):
    return re.sub(r'\s+', " ", value).strip().title() if value else None

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

def format_date_column(original_date):
    try:
        return datetime.strptime(original_date, '%d/%m/%Y').strftime('%Y-%m-%d')
    except Exception:
        logger.warning(f"Invalid date format: {original_date}")
        return None

def clean_gender(value):
    if not value:
        return None
    value = value.strip().upper()
    return "M" if value == "MALE" else "F" if value == "FEMALE" else value

def extract_division(value):
    match = re.search(r'[A-Za-z]+', value)
    return match.group(0).upper() if match else value

# ---------- Unique key generator ----------
def generate_unique_key(record):
    school = re.sub(r'\s+', ' ', record['school_name']).strip().upper()
    student_id = str(record['student_id']).strip().upper()
    academic_year = record['academic_year'].strip()
    grade_name = convert_grade_name(record['grade_name']).strip().upper()
    return f"{school}_{student_id}_{academic_year}_{grade_name}"

# ---------- MySQL connection ----------
def connect_to_mysql():
    try:
        logger.info("Connecting to MySQL...")
        conn = mysql.connector.connect(**db_config)
        logger.info("Connected to MySQL.")
        return conn
    except mysql.connector.Error as err:
        logger.error(f"MySQL connection failed: {err}")
        return None

# ---------- Insert or update logic ----------
def insert_or_update(cursor, record, academic_year, timestamp):
    grade_clean = convert_grade_name(record.get('grade_name'))
    unique_key = generate_unique_key({
        'school_name': record.get('school_name'),
        'student_id': record.get('student_id'),
        'academic_year': academic_year,
        'grade_name': grade_clean
    })
    created_date_raw = record.get('created_date')
    created_date = format_date_column(created_date_raw) if created_date_raw else None

    # Check if record exists
    cursor.execute("SELECT COUNT(*) FROM active_student_data WHERE unique_key = %s", (unique_key,))
    exists = cursor.fetchone()[0]

    if exists:
        # Perform update
        update_sql = """
            UPDATE active_student_data
            SET created_date = %s, status = %s, grade_name = %s, student_name = %s,
                gender = %s, division_name = %s, academic_year = %s, timestamp = %s
            WHERE unique_key = %s
        """
        cursor.execute(update_sql, (
            created_date,
            record.get('status'),
            grade_clean,
            clean_student_name(record.get('student_name')),
            clean_gender(record.get('gender')),
            extract_division(record.get('division_name')),
            academic_year,
            timestamp,
            unique_key
        ))
        logger.info(f"[UPDATE] {unique_key}")
    else:
        # Perform insert
        insert_sql = """
            INSERT INTO active_student_data (
                created_date, school_name, status, grade_name, student_name, student_id, gender,
                division_name, academic_year, unique_key, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_sql, (
            created_date,
            record.get('school_name').upper(),
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

# ---------- Main function ----------
def main():
    logger.info("==== Starting Active Student Update ====")
    print("Starting update process...")

    json_response = fetch_data_from_api()
    if not json_response:
        logger.error("No data fetched. Exiting.")
        sys.exit()

    students_data = json_response.get('data', [])
    if not students_data:
        logger.error("API returned empty student data.")
        sys.exit()

    conn = connect_to_mysql()
    if not conn:
        sys.exit()

    cursor = conn.cursor()
    now = datetime.now()
    academic_year = f"{now.year}-{now.year + 1}" if now.month >= 5 else f"{now.year - 1}-{now.year}"
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    logger.info(f"Processing {len(students_data)} records...")

    for record in students_data:
        insert_or_update(cursor, record, academic_year, timestamp)

    conn.commit()
    cursor.close()
    conn.close()

    logger.info("==== Update Process Complete ====")
    print("✅ Process completed.")

# ---------- Entry ----------
if __name__ == "__main__":
    main()

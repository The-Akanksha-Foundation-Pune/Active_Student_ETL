# main.py
import logging
from api import fetch_data_from_api
from database import (
    connect_to_mysql, fetch_existing_keys, update_existing_record,
    insert_new_record, fetch_duplicate_records, mark_records_as_inactive
)
from utils import generate_unique_key, validate_student_record, trim_string, convert_grade_name, clean_student_name, clean_gender, extract_division
from logging_config import setup_logging # Assuming you have this module for logging setup
from datetime import datetime
import configparser
import sys

# Setup logging first
setup_logging()

# Read configuration
config = configparser.ConfigParser()
try:
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
    logging.info("Configuration loaded successfully from config.ini.")
except KeyError as e:
    logging.critical(f"Missing configuration key in config.ini: {e}. Please check your config file.")
    sys.exit(1)
except Exception as e:
    logging.critical(f"Error loading configuration from config.ini: {e}", exc_info=True)
    sys.exit(1)


def main():
    logging.info("=== Starting Daily Student Data Update Process ===")
    start_time = datetime.now()

    logging.info(f"Fetching data from API: {api_url}")
    json_response = fetch_data_from_api(api_url, api_key)
    if not json_response:
        logging.error("No data fetched from API. Exiting process.")
        sys.exit(1)

    students_data = json_response.get('data', [])
    if not students_data:
        logging.warning("No student data found in the API response 'data' field. The API might have returned an empty dataset.")
        sys.exit(0) # Exit gracefully if no student data, as it might be a valid empty response

    logging.info(f"Successfully fetched {len(students_data)} records from API.")

    conn = connect_to_mysql(db_config)
    if not conn:
        logging.critical("MySQL connection failed. Exiting process.")
        sys.exit(1)

    cursor = conn.cursor()
    logging.info("Database connection and cursor established.")

    # Determine the current academic year
    current_year = datetime.now().year
    current_month = datetime.now().month
    academic_year = f"{current_year}-{current_year + 1}" if current_month >= 5 else f"{current_year - 1}-{current_year}"
    logging.info(f"Determined current academic year: {academic_year}")

    logging.info(f"Fetching existing unique keys from database for academic year {academic_year}.")
    existing_keys = fetch_existing_keys(cursor, academic_year)
    logging.info(f"Retrieved {len(existing_keys)} existing keys from the database.")

    processed_api_keys = set()
    new_records_count = 0
    updated_records_count = 0
    skipped_invalid_records_count = 0

    logging.info("Starting processing of API records for validation, insertion, and update.")
    for i, record in enumerate(students_data):
        log_prefix = f"Record {i+1}/{len(students_data)}:"
        logging.debug(f"{log_prefix} Raw record: {record}")

        # --- Data Validation and Trimming ---
        is_valid, validation_result = validate_student_record(record)
        if not is_valid:
            logging.warning(f"{log_prefix} Skipping invalid record due to validation error: {validation_result}. Record: {record}")
            skipped_invalid_records_count += 1
            continue # Skip to the next record
        
        # Trim all string values in the record defensively, even if not explicitly cleaned later
        # Create a copy to modify
        processed_record = {k: trim_string(v) for k, v in record.items()}

        # Apply specific cleaning/conversion functions for unique key generation and database storage
        # Note: These are applied again in database.py's insert/update functions
        # This is mainly for consistency and to ensure the unique key is correctly generated.
        processed_record['grade_name'] = convert_grade_name(processed_record.get('grade_name'))
        processed_record['student_name'] = clean_student_name(processed_record.get('student_name'))
        processed_record['gender'] = clean_gender(processed_record.get('gender'))
        processed_record['division_name'] = extract_division(processed_record.get('division_name'))

        unique_key = generate_unique_key(processed_record, academic_year)
        processed_api_keys.add(unique_key)
        logging.debug(f"{log_prefix} Generated Unique Key: {unique_key}")

        if unique_key not in existing_keys:
            logging.info(f"{log_prefix} Unique Key {unique_key} is NEW. Attempting to insert.")
            insert_new_record(cursor, processed_record, unique_key, academic_year)
            new_records_count += 1
        else:
            logging.debug(f"{log_prefix} Unique Key {unique_key} ALREADY EXISTS. Attempting to update.")
            update_existing_record(cursor, processed_record, unique_key)
            updated_records_count += 1
            # Remove from existing_keys set to track what's left for inactivation
            existing_keys.discard(unique_key)

    logging.info("Finished processing all API records.")
    logging.info(f"Summary: New records inserted: {new_records_count}, Records updated (or checked for update): {updated_records_count}, Invalid records skipped: {skipped_invalid_records_count}.")

    logging.info("Starting process to mark inactive records.")
    # existing_keys now only contains keys that were in DB but NOT in the current API response
    mark_records_as_inactive(cursor, existing_keys, processed_api_keys)
    logging.info("Finished marking inactive records.")
    
    logging.info("Checking for any duplicate unique_key entries in the database.")
    fetch_duplicate_records(cursor)
    logging.info("Duplicate check complete.")

    try:
        conn.commit()
        logging.info("All database transactions committed successfully.")
    except mysql.connector.Error as err:
        logging.error(f"Error committing transactions: {err}", exc_info=True)
        conn.rollback()
        logging.error("Database rollback performed due to commit error.")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        logging.info("Database connection closed.")

    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"=== Daily update process completed successfully in {duration}. ===")

if __name__ == "__main__":
    main()
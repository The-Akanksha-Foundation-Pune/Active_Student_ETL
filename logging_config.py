import logging
from datetime import datetime
import os

def setup_logging():
    # Generate log filename
    current_date = datetime.now()
    month_name = current_date.strftime('%B')
    week_number = current_date.strftime('%U')
    academic_year = f"{current_date.year}-{current_date.year + 1}" if current_date.month >= 5 else f"{current_date.year - 1}-{current_date.year}"
    log_filename = f"{month_name}_week{week_number}_{academic_year}.log"

    # Log file directory - use local logs directory
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Full path to the log file
    log_file_path = os.path.join(log_dir, log_filename)

    # Configure logging
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Add console logging as well
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Add the console handler to the root logger
    logging.getLogger().addHandler(console_handler)

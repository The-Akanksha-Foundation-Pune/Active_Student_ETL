#!/usr/bin/env python3
"""
Database Setup Script
Creates the required tables for the Active Student Data ETL system.
"""

import mysql.connector
import configparser
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_database():
    """Create the required database tables."""
    
    # Read configuration
    config = configparser.ConfigParser()
    try:
        config.read('config.ini')
        db_config = {
            'user': config['mysql']['user'],
            'password': config['mysql']['password'],
            'host': config['mysql']['host'],
            'port': int(config['mysql']['port']),
            'database': config['mysql']['database']
        }
        logging.info("Configuration loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        sys.exit(1)

    # Connect to MySQL
    try:
        logging.info("Connecting to MySQL database...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        logging.info("Successfully connected to MySQL database.")
    except mysql.connector.Error as err:
        logging.error(f"Failed to connect to MySQL: {err}")
        sys.exit(1)

    # SQL commands to create tables
    sql_commands = [
        # Create main table
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
            unique_key VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )""",
        
        # Create history table
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

    # Execute SQL commands
    try:
        for i, sql in enumerate(sql_commands, 1):
            logging.info(f"Executing SQL command {i}/{len(sql_commands)}...")
            cursor.execute(sql)
            logging.info(f"SQL command {i} executed successfully.")
        
        # Add unique constraint to unique_key (this might fail if duplicates exist)
        try:
            logging.info("Adding unique constraint to unique_key...")
            cursor.execute("ALTER TABLE active_student_data ADD CONSTRAINT UQ_unique_key UNIQUE (unique_key)")
            logging.info("Unique constraint added successfully.")
        except mysql.connector.Error as err:
            if err.errno == 1062:  # Duplicate entry error
                logging.warning("Unique constraint already exists or there are duplicate entries.")
            else:
                logging.warning(f"Could not add unique constraint: {err}")
        
        # Commit all changes
        conn.commit()
        logging.info("All database changes committed successfully.")
        
    except mysql.connector.Error as err:
        logging.error(f"Error executing SQL commands: {err}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        logging.info("Database connection closed.")

    logging.info("✅ Database setup completed successfully!")
    logging.info("You can now run the main ETL script: python main.py")

if __name__ == "__main__":
    setup_database()

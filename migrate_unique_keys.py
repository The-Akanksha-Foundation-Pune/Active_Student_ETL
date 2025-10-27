"""
Migration Script: Update unique_key format to support grade changes
Removes grade_name from unique_key to allow updating grades
"""

import mysql.connector
import configparser
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()
config.read('config.ini')

db_config = {
    'user': config['mysql']['user'],
    'password': config['mysql']['password'],
    'host': config['mysql']['host'],
    'port': int(config['mysql']['port']),
    'database': config['mysql']['database']
}

def migrate():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # Step 1: Add new column for new unique key format
        logging.info("Adding new unique_key2 column...")
        cursor.execute("ALTER TABLE active_student_data ADD COLUMN unique_key2 VARCHAR(255)")
        logging.info("✓ Column added")
        
        # Step 2: Update all records with new unique key (without grade)
        logging.info("Updating unique_key2 with new format...")
        cursor.execute("""
            UPDATE active_student_data 
            SET unique_key2 = CONCAT(school_name, '_', student_id, '_', academic_year)
            WHERE unique_key2 IS NULL
        """)
        logging.info(f"✓ Updated {cursor.rowcount} records")
        
        # Step 3: Handle duplicates (keep only most recent by timestamp)
        logging.info("Checking for duplicate keys...")
        cursor.execute("""
            SELECT unique_key2, COUNT(*) as cnt 
            FROM active_student_data 
            GROUP BY unique_key2 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        logging.info(f"Found {len(duplicates)} duplicate keys")
        
        for key, count in duplicates:
            logging.info(f"Removing {count-1} old record(s) for key: {key}")
            cursor.execute("""
                DELETE FROM active_student_data 
                WHERE unique_key2 = %s 
                AND id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM active_student_data 
                        WHERE unique_key2 = %s 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    ) AS temp
                )
            """, (key, key))
            logging.info(f"✓ Removed {cursor.rowcount} duplicate record(s)")
        
        # Step 4: Drop old unique_key column and rename new one
        logging.info("Dropping old unique_key constraint...")
        cursor.execute("ALTER TABLE active_student_data DROP INDEX unique_key")
        cursor.execute("ALTER TABLE active_student_data DROP COLUMN unique_key")
        logging.info("✓ Old column removed")
        
        logging.info("Renaming unique_key2 to unique_key...")
        cursor.execute("ALTER TABLE active_student_data CHANGE COLUMN unique_key2 unique_key VARCHAR(255)")
        logging.info("✓ Renamed")
        
        logging.info("Adding back unique constraint...")
        cursor.execute("ALTER TABLE active_student_data ADD CONSTRAINT UQ_unique_key UNIQUE (unique_key)")
        logging.info("✓ Unique constraint added")
        
        conn.commit()
        logging.info("✅ Migration completed successfully!")
        
    except mysql.connector.Error as err:
        logging.error(f"❌ Migration failed: {err}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("=" * 80)
    print("UNIQUE KEY MIGRATION - Removing grade_name from unique_key")
    print("=" * 80)
    print()
    print("This will:")
    print("1. Update unique_key format: school_student_academic_year (no grade)")
    print("2. Remove duplicate records (keeps most recent)")
    print("3. Allow grade changes to update existing records")
    print()
    response = input("Continue? (yes/no): ")
    if response.lower() == 'yes':
        migrate()
    else:
        print("Migration cancelled.")


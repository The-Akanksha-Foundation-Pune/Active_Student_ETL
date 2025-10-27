# Student Data Sync System

## Overview
This is a unified ETL system for syncing student data from an API to a MySQL database. The system automatically detects if the database is empty and performs appropriate operations.

## Quick Start

### 1. Setup
```bash
# Run the database setup (creates tables)
python3 setup_database.py
```

### 2. Sync Data
```bash
# Run the unified sync script
python3 sync_students.py
```

## How It Works

### The Unified Script: `sync_students.py`

This single script handles both initial import and updates:

1. **Checks if database is empty**
   - If empty → performs full data import
   - If not empty → performs incremental updates

2. **Fetches data from API**
   - Fetches all student records from the API
   - Handles SSL certificate issues automatically

3. **Processes each record**
   - **New records**: Inserts into database
   - **Existing records**: Updates with latest data
   - Generates unique keys based on: School + Student ID + Academic Year + Grade

4. **Updates timestamps**
   - Automatically updates timestamps for all processed records

## Files Overview

### Core Files
- **`sync_students.py`** - Main sync script (unified, runs both initial and updates)
- **`config.ini`** - Configuration file (API credentials, database settings)
- **`setup_database.py`** - Database setup script
- **`requirements.txt`** - Python dependencies

### Helper Files (for reference)
- **`main.py`** - Original sync script with history tracking
- **`api.py`** - API utility functions
- **`database.py`** - Database utility functions
- **`utils.py`** - Data cleaning and utility functions
- **`logging_config.py`** - Logging configuration

## Configuration

Edit `config.ini` with your settings:

```ini
[api]
url = https://your-api-endpoint.com/getActiveStudents.htm
key = your-api-key

[mysql]
user = your_db_user
password = your_db_password
host = localhost
port = 3306
database = your_database_name
```

## Features

- ✅ Automatic database detection (empty vs. has data)
- ✅ SSL verification bypass (for development servers)
- ✅ Data normalization (grade conversion, name cleaning, etc.)
- ✅ Unique key generation (prevents duplicates)
- ✅ Comprehensive logging
- ✅ Error handling

## Usage Examples

### Run sync
```bash
python3 sync_students.py
```

### Check logs
```bash
cat student_sync.log
```

### Setup new database
```bash
python3 setup_database.py
```

## Output

The script provides real-time feedback:

```
✅ Sync completed successfully!
   Mode: UPDATE
   Inserted: 14721 records
   Updated: 0 records
```

## Database Schema

### active_student_data
- `id` - Primary key
- `school_name` - School name
- `status` - Student status
- `grade_name` - Grade (normalized)
- `student_name` - Student name
- `student_id` - Student ID
- `gender` - Gender (M/F)
- `division_name` - Division
- `academic_year` - Academic year
- `unique_key` - Unique identifier
- `timestamp` - Last update time

### student_data_history
- `history_id` - Primary key
- `unique_key` - Record key
- `change_type` - Type of change
- `field_changed` - Field name
- `old_value` - Previous value
- `new_value` - New value
- `change_timestamp` - When changed

## Notes

- The script handles SSL certificate issues automatically
- All data is normalized (school names uppercase, grades converted, etc.)
- Unique keys prevent duplicate records
- The script can be run multiple times safely (idempotent)


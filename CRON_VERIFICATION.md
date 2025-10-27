# How to Verify Cron Job Execution on Production Server

## Quick Verification Methods

### 1. Check the Sync Log File

```bash
# View recent sync activity
tail -50 student_sync.log

# Check last successful sync
grep "SYNC COMPLETE" student_sync.log | tail -1

# Check for errors
grep "ERROR" student_sync.log | tail -10
```

### 2. Use the Verification Script

```bash
# Run verification script
./verify_sync.sh

# Or
bash verify_sync.sh
```

This will show:
- When the last sync ran
- How many records were inserted/updated
- Total records in database
- Any recent errors

### 3. Check Database Records

```sql
-- Check total records
SELECT COUNT(*) FROM active_student_data;

-- Check last updated timestamp
SELECT MAX(timestamp) as last_sync FROM active_student_data;

-- Check records updated today
SELECT COUNT(*) 
FROM active_student_data 
WHERE DATE(timestamp) = CURDATE();
```

### 4. Check Cron Logs (System Level)

```bash
# View cron execution logs
# On Ubuntu/Debian:
grep CRON /var/log/syslog | grep "sync_students"

# On macOS:
log show --predicate 'subsystem == "com.apple.cron"' --last 1d

# On CentOS/RHEL:
grep sync_students /var/log/cron
```

### 5. Monitor Cron Activity

Add this to your crontab to capture output:

```bash
# Edit crontab
crontab -e

# Add this line (captures output to a file)
0 2 1 * * cd /Users/admin/Downloads/ETL/Active && python3 sync_students.py >> cron_output.log 2>&1
```

Then check:
```bash
cat cron_output.log
```

## Database Verification Queries

```sql
-- Check sync frequency
SELECT 
    DATE(timestamp) as sync_date,
    COUNT(*) as records
FROM active_student_data 
GROUP BY DATE(timestamp)
ORDER BY sync_date DESC
LIMIT 7;

-- Check for recent updates
SELECT 
    COUNT(*) as total_records,
    MAX(timestamp) as last_update
FROM active_student_data;
```

## Email Notifications (Optional)

To receive email alerts when cron runs:

```bash
# Add to crontab with email
MAILTO=your-email@example.com
0 2 1 * * cd /Users/admin/Downloads/ETL/Active && python3 sync_students.py
```

## Expected Output from Script

When cron runs successfully, you'll see in the log:

```
2025-10-27 13:46:00 - INFO - ================================================================================
2025-10-27 13:46:00 - INFO - SYNC COMPLETE - Mode: UPDATE
2025-10-27 13:46:00 - INFO - Records inserted: 0
2025-10-27 13:46:00 - INFO - Records updated: 14721
2025-10-27 13:46:00 - INFO - Total records in database: 14721
2025-10-27 13:46:00 - INFO - Timestamp: 2025-10-27 13:46:00
2025-10-27 13:46:00 - INFO - ================================================================================
```

## Troubleshooting

### If logs show errors:
```bash
# Check full error details
grep "ERROR" student_sync.log | tail -20

# Check if database is accessible
mysql -u your_user -p your_database -e "SELECT 1;"

# Check if API is accessible
curl "https://akanksha.edustems.com/getActiveStudents.htm?api-key=YOUR_KEY&school_name=ALL"
```

### If cron isn't running:
```bash
# Check if cron service is running
# On macOS:
sudo launchctl list | grep cron

# On Linux:
sudo systemctl status cron

# Check your crontab
crontab -l
```

## Recommended Monitoring Setup

1. **Daily Check Script** (run this yourself to verify):
```bash
#!/bin/bash
# check_sync.sh - Run this daily to verify sync

LOG_FILE="/path/to/Active/student_sync.log"
DAYS_OLD=$(find "$LOG_FILE" -mtime +2)

if [ -n "$DAYS_OLD" ]; then
    echo "⚠️  WARNING: Last sync was more than 2 days ago!"
else
    echo "✅ Sync is running regularly"
fi
```

2. **Add to your regular checks**:
   - Check logs weekly
   - Verify record counts
   - Monitor for errors

3. **Automated Monitoring** (optional):
```bash
# Email alert if sync fails
*/30 * * * * cd /path/to/Active && python3 sync_students.py || echo "Sync failed!" | mail -s "Student Sync Error" your-email@example.com
```


# Setting Up Cron Job for Student Sync

## Quick Setup

### 1. Test the Script First

```bash
cd /Users/admin/Downloads/ETL/Active
python3 sync_students.py
```

### 2. Add to Cron

```bash
# Open crontab editor
crontab -e

# Add this line (runs monthly on 1st at 2 AM)
0 2 1 * * cd /Users/admin/Downloads/ETL/Active && /usr/bin/python3 sync_students.py

# Or run daily at 3 AM
0 3 * * * cd /Users/admin/Downloads/ETL/Active && /usr/bin/python3 sync_students.py
```

### 3. Verify It's Added

```bash
# Check your crontab
crontab -l

# You should see your cron job listed
```

## Verify Cron is Running

### Method 1: Check Logs
```bash
cd /Users/admin/Downloads/ETL/Active

# View last sync
tail -20 student_sync.log

# Check if ran today
grep "$(date +'%Y-%m-%d')" student_sync.log | grep "SYNC COMPLETE"
```

### Method 2: Use Verification Script
```bash
cd /Users/admin/Downloads/ETL/Active
./verify_sync.sh
```

### Method 3: Check Database
```sql
-- Check last updated records
SELECT MAX(timestamp) as last_sync FROM active_student_data;
```

## Cron Schedule Examples

```
0 2 1 * *     # Monthly on 1st at 2 AM
0 3 * * *     # Daily at 3 AM
0 2 * * 1     # Every Monday at 2 AM
0 0 * * *     # Daily at midnight
0 */6 * * *   # Every 6 hours
```

## Troubleshooting

### If cron doesn't run:

1. **Check cron service status:**
```bash
# macOS
sudo launchctl list | grep cron

# Linux
sudo systemctl status cron
```

2. **Check cron logs:**
```bash
# macOS
log show --predicate 'subsystem == "com.apple.cron"' --last 1d | grep sync_students

# Linux
grep sync_students /var/log/cron
```

3. **Check script permissions:**
```bash
ls -la sync_students.py
chmod +x sync_students.py
```

4. **Test manually:**
```bash
cd /Users/admin/Downloads/ETL/Active
python3 sync_students.py
```

## Monitoring

### Daily Check Command
```bash
cd /Users/admin/Downloads/ETL/Active && ./verify_sync.sh
```

### Email Notifications (Optional)
Add to crontab to get email alerts:
```bash
MAILTO=your-email@example.com
0 2 1 * * cd /Users/admin/Downloads/ETL/Active && python3 sync_students.py
```

### Automated Monitoring
Create a monitoring script that runs daily:
```bash
# Add to crontab
0 9 * * * cd /Users/admin/Downloads/ETL/Active && ./verify_sync.sh
```

## What You'll See When It Runs

**In the log file (`student_sync.log`):**
```
2025-10-27 02:00:00 - INFO - STUDENT DATA SYNC - Starting Process
2025-10-27 02:00:05 - INFO - API returned 14721 records
2025-10-27 02:01:30 - INFO - SYNC COMPLETE - Mode: UPDATE
2025-10-27 02:01:30 - INFO - Records inserted: 5
2025-10-27 02:01:30 - INFO - Records updated: 14716
2025-10-27 02:01:30 - INFO - Total records in database: 14721
```

## Notes

- ✅ Script creates tables automatically
- ✅ Handles grade changes by updating records
- ✅ Safe to run multiple times
- ✅ Logs all activity to `student_sync.log`
- ✅ Updates only changed fields


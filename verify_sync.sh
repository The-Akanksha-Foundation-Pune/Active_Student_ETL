#!/bin/bash
# Quick verification script to check if cron ran successfully

echo "=================================================="
echo "Student Sync Verification"
echo "=================================================="
echo ""

# Check if log file exists and is recent
LOG_FILE="student_sync.log"

if [ -f "$LOG_FILE" ]; then
    echo "✅ Log file exists: $LOG_FILE"
    
    # Get last modification time
    LAST_RUN=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$LOG_FILE" 2>/dev/null || stat -c "%y" "$LOG_FILE" 2>/dev/null | cut -d'.' -f1)
    echo "📅 Last modified: $LAST_RUN"
    
    # Get last successful sync from log
    LAST_SYNC=$(grep "SYNC COMPLETE" "$LOG_FILE" | tail -1)
    if [ ! -z "$LAST_SYNC" ]; then
        echo ""
        echo "Last successful sync:"
        echo "$LAST_SYNC"
        echo ""
        
        # Get sync details
        INSERTED=$(grep "Records inserted:" "$LOG_FILE" | tail -1 | sed -n 's/.*Records inserted: \([0-9]*\).*/\1/p')
        UPDATED=$(grep "Records updated:" "$LOG_FILE" | tail -1 | sed -n 's/.*Records updated: \([0-9]*\).*/\1/p')
        TOTAL=$(grep "Total records in database:" "$LOG_FILE" | tail -1 | sed -n 's/.*Total records in database: \([0-9]*\).*/\1/p')
        
        echo "📊 Last Run Stats:"
        echo "   Inserted: $INSERTED records"
        echo "   Updated: $UPDATED records"
        echo "   Total in DB: $TOTAL records"
    else
        echo "⚠️  No successful sync found in logs"
    fi
    
    # Check for errors
    ERROR_COUNT=$(grep -i "ERROR" "$LOG_FILE" | tail -5)
    if [ ! -z "$ERROR_COUNT" ]; then
        echo ""
        echo "⚠️  Recent errors found:"
        echo "$ERROR_COUNT"
    fi
else
    echo "❌ Log file not found: $LOG_FILE"
fi

echo ""
echo "=================================================="
echo "To view full log: tail -f student_sync.log"
echo "=================================================="


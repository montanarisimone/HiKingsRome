# Copyright © 2025 Simone Montanari. All Rights Reserved.
# This file is part of HiKingsRome and may not be used or distributed without written permission.

#!/usr/bin/env python3
"""
Backup script for HikyTheBot SQLite database
This script creates a daily backup of the SQLite database and deletes old backups
"""

import os
import sys
import time
import shutil
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backup.log')
    ]
)
logger = logging.getLogger('backup')

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Backup the HikyTheBot SQLite database')
    parser.add_argument('--db-path', default='hiky_bot.db', help='Path to the SQLite database')
    parser.add_argument('--backup-dir', default='./backups', help='Directory to store backups')
    parser.add_argument('--days', type=int, default=7, help='Keep backups for this many days')
    parser.add_argument('--no-cleanup', action='store_true', help='Skip deletion of old backups')
    return parser.parse_args()

def create_backup(db_path, backup_dir):
    """Create a backup of the database with timestamp"""
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"hiky_bot_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Create backup using shutil.copy2 to preserve metadata
        shutil.copy2(db_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return None

def cleanup_old_backups(backup_dir, days_to_keep):
    """Delete backups older than the specified number of days"""
    if not os.path.exists(backup_dir):
        logger.warning(f"Backup directory does not exist: {backup_dir}")
        return
        
    # Calculate cutoff date
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # Count old files for logging
    removed_count = 0
    
    # Iterate through files in backup directory
    for filename in os.listdir(backup_dir):
        if not filename.startswith("hiky_bot_") or not filename.endswith(".db"):
            continue  # Skip files that don't match our pattern
            
        file_path = os.path.join(backup_dir, filename)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # Remove file if older than cutoff date
        if file_mtime < cutoff_date:
            try:
                os.remove(file_path)
                removed_count += 1
                logger.debug(f"Removed old backup: {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove {file_path}: {e}")
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} old backup(s)")
    else:
        logger.info("No old backups to remove")

def main():
    """Main function"""
    args = parse_args()
    
    # Resolve paths
    db_path = os.path.abspath(os.path.expanduser(args.db_path))
    backup_dir = os.path.abspath(os.path.expanduser(args.backup_dir))
    
    # Check if database file exists
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return 1
    
    # Create backup
    backup_path = create_backup(db_path, backup_dir)
    if not backup_path:
        return 1
    
    # Clean up old backups if not disabled
    if not args.no_cleanup:
        cleanup_old_backups(backup_dir, args.days)
    
    logger.info("Backup completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())

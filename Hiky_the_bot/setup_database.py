# Copyright © 2025 Simone Montanari. All Rights Reserved.
# This file is part of HiKingsRome and may not be used or distributed without written permission.

#!/usr/bin/env python3
import sqlite3
import os
import sys
from datetime import datetime

# Database file path
DB_PATH = 'hiky_bot.db'

def setup_database():
    """Create and initialize the database with required tables"""
    
    # Check if database already exists
    if os.path.exists(DB_PATH):
        choice = input(f"Database {DB_PATH} already exists. Overwrite? (y/n): ")
        if choice.lower() != 'y':
            print("Setup cancelled.")
            sys.exit(0)
    
    # Create or connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        name TEXT NOT NULL DEFAULT 'Not set',
        surname TEXT NOT NULL DEFAULT 'Not set',
        email TEXT NOT NULL DEFAULT 'Not set',
        phone TEXT NOT NULL DEFAULT 'Not set',
        birth_date TEXT NOT NULL DEFAULT 'Not set',
        is_guide BOOLEAN NOT NULL DEFAULT 0,
        registration_timestamp TIMESTAMP,
        last_updated TIMESTAMP,
        basic_consent BOOLEAN NOT NULL DEFAULT 0,
        car_sharing_consent BOOLEAN NOT NULL DEFAULT 0,
        photo_consent BOOLEAN NOT NULL DEFAULT 0,
        marketing_consent BOOLEAN NOT NULL DEFAULT 0,
        consent_version TEXT
    )
    ''')
    
    # Create hikes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hikes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hike_name TEXT NOT NULL,
        hike_date DATE NOT NULL,
        max_participants INTEGER NOT NULL,
        guides INTEGER DEFAULT 1,
        latitude REAL,
        longitude REAL,
        difficulty TEXT,
        variable_costs REAL DEFAULT 0,
        fixed_cost_coverage REAL DEFAULT 0.5,
        max_cost_per_participant REAL DEFAULT 0,
        actual_attendance INTEGER DEFAULT 0,
        fee_locked BOOLEAN DEFAULT 0,
        final_participant_fee REAL DEFAULT 0,
        final_guide_fee REAL DEFAULT 0,
        description TEXT,
        created_by INTEGER,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (created_by) REFERENCES users(telegram_id)
    )
    ''')
    
    # Create registrations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        hike_id INTEGER NOT NULL,
        registration_timestamp TIMESTAMP NOT NULL,
        name_surname TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        birth_date TEXT NOT NULL,
        medical_conditions TEXT,
        has_equipment BOOLEAN NOT NULL,
        car_sharing BOOLEAN NOT NULL,
        location TEXT NOT NULL,
        notes TEXT,
        reminder_preference TEXT,
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
        FOREIGN KEY (hike_id) REFERENCES hikes(id),
        UNIQUE(telegram_id, hike_id)
    )
    ''')

    # Create a table to track attendance confirmations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration_id INTEGER NOT NULL,
        telegram_id INTEGER NOT NULL,
        hike_id INTEGER NOT NULL,
        attended BOOLEAN DEFAULT 0,
        confirmation_timestamp TIMESTAMP,
        FOREIGN KEY (registration_id) REFERENCES registrations(id),
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
        FOREIGN KEY (hike_id) REFERENCES hikes(id)
    )
    ''')
    
    # Create admins table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        telegram_id INTEGER PRIMARY KEY,
        role TEXT NOT NULL,
        added_by INTEGER,
        added_on TIMESTAMP NOT NULL,
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
        FOREIGN KEY (added_by) REFERENCES users(telegram_id)
    )
    ''')
    
    # Create group members table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS group_members (
        telegram_id INTEGER PRIMARY KEY,
        joined_date TIMESTAMP NOT NULL,
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
    )
    ''')

    # Create maintenance table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        maintenance_date DATE NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        reason TEXT,
        created_by INTEGER,
        created_on TIMESTAMP,
        sent_notification INTEGER DEFAULT 0,
        FOREIGN KEY (created_by) REFERENCES users(telegram_id)
    )
    ''')

    # Create fixed_costs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fixed_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        frequency TEXT NOT NULL,
        description TEXT,
        created_by INTEGER,
        created_on TIMESTAMP,
        last_updated TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(telegram_id)
    )
    ''')
    
    # Insert default costs if they don't exist
    default_costs = [
        ('Domain', 15.0, 'yearly', 'Domain name registration'),
        ('AI Claude', 0.0, 'monthly', 'AI assistant subscription'),
        ('Google Cloud', 8.0, 'monthly', 'Server hosting costs'),
        ('Website', 0.0, 'yearly', 'Website hosting and maintenance')
    ]
    
    for cost in default_costs:
        cursor.execute('''
        INSERT OR IGNORE INTO fixed_costs (name, amount, frequency, description, created_on, last_updated)
        SELECT ?, ?, ?, ?, datetime('now'), datetime('now')
        WHERE NOT EXISTS (SELECT 1 FROM fixed_costs WHERE name = ?)
        ''', (cost[0], cost[1], cost[2], cost[3], cost[0]))
    
    # Commit changes and close connection
    conn.commit()
    
    # Ask to add an admin user
    add_admin = input("Would you like to add an admin user? (y/n): ")
    if add_admin.lower() == 'y':
        telegram_id = input("Enter the Telegram ID of the admin: ")
        try:
            telegram_id = int(telegram_id)
            
            # Add user record first if it doesn't exist
            cursor.execute('''
            INSERT OR IGNORE INTO users (telegram_id, registration_timestamp, last_updated, basic_consent, is_guide)
            VALUES (?, ?, ?, 1, 1)
            ''', (telegram_id, datetime.now(), datetime.now()))
            
            # Add admin record
            cursor.execute('''
            INSERT INTO admins (telegram_id, role, added_on)
            VALUES (?, 'admin', ?)
            ''', (telegram_id, datetime.now()))
            
            conn.commit()
            print(f"Admin user with Telegram ID {telegram_id} added successfully.")
        except ValueError:
            print("Invalid Telegram ID. Please enter a number.")
    
    conn.close()
    print(f"Database setup complete. Database file: {DB_PATH}")

if __name__ == "__main__":
    setup_database()

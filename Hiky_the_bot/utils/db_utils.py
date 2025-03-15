#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime, date, timedelta
import pytz

# Database file path
DB_PATH = 'hiky_bot.db'

# Rome timezone for consistent timestamps
rome_tz = pytz.timezone('Europe/Rome')

class DBUtils:
    """Utility class for database operations"""
    
    @staticmethod
    def get_connection():
        """Get a connection to the SQLite database"""
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"Database file {DB_PATH} not found. Run setup_database.py first.")
        
        conn = sqlite3.connect(DB_PATH)
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        # Configure to return rows as dictionaries
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def check_user_exists(telegram_id):
        """Check if a user exists in the database"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    
    @staticmethod
    def add_or_update_user(telegram_id, username=None):
        """Add a new user or update existing user info"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        if DBUtils.check_user_exists(telegram_id):
            # Update existing user
            cursor.execute("""
            UPDATE users 
            SET username = ?, last_updated = ?
            WHERE telegram_id = ?
            """, (username, now, telegram_id))
        else:
            # Add new user
            cursor.execute("""
            INSERT INTO users (telegram_id, username, registration_timestamp, last_updated)
            VALUES (?, ?, ?, ?)
            """, (telegram_id, username, now, now))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def get_privacy_settings(telegram_id):
        """Get privacy settings for a user"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            basic_consent, 
            car_sharing_consent, 
            photo_consent, 
            marketing_consent,
            consent_version
        FROM users 
        WHERE telegram_id = ?
        """, (telegram_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)  # Convert to regular dictionary
        return None
    
    @staticmethod
    def update_privacy_settings(telegram_id, settings):
        """Update privacy settings for a user"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
        UPDATE users 
        SET 
            basic_consent = ?,
            car_sharing_consent = ?,
            photo_consent = ?,
            marketing_consent = ?,
            consent_version = ?,
            last_updated = ?
        WHERE telegram_id = ?
        """, (
            settings.get('basic_consent', False), 
            settings.get('car_sharing_consent', False),
            settings.get('photo_consent', False),
            settings.get('marketing_consent', False),
            settings.get('consent_version', '1.0'),
            now,
            telegram_id
        ))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def check_is_admin(telegram_id):
        """Check if a user is an admin"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT role FROM admins 
        WHERE telegram_id = ?
        """, (telegram_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    @staticmethod
    def get_available_hikes(telegram_id=None, include_inactive=False, include_registered=False):
        """Get available upcoming hikes"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        today = date.today()
        max_date = today + timedelta(days=60)  # Within 60 days
        
        # Calculate min_date based on context
        if include_inactive:
            # For admin view, show hikes starting from today
            min_date = today
        else:
            # For regular users, keep 2 day buffer
            min_date = today + timedelta(days=2)
        
        # Base query to get hikes within date range
        query = """
        SELECT 
            h.id, 
            h.hike_name, 
            h.hike_date, 
            h.max_participants,
            h.latitude,
            h.longitude,
            h.difficulty,
            h.description,
            h.is_active,
            (SELECT COUNT(*) FROM registrations r WHERE r.hike_id = h.id) as current_participants
        FROM hikes h
        WHERE 
            h.hike_date BETWEEN ? AND ?
        """
        
        # Add active filter unless specifically requested to include inactive
        if not include_inactive:
            query += " AND h.is_active = 1"
        
        # If telegram_id is provided and we don't want to include registered hikes, exclude hikes the user is already registered for
        params = [min_date, max_date]
        if telegram_id and not include_registered:
            query += """
            AND h.id NOT IN (
                SELECT hike_id FROM registrations 
                WHERE telegram_id = ?
            )
            """
            params.append(telegram_id)
        
        query += " ORDER BY h.hike_date ASC"
        
        cursor.execute(query, params)
        hikes = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return hikes
    
    @staticmethod
    def get_user_hikes(telegram_id):
        """Get upcoming hikes for a specific user"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        today = date.today()
        
        cursor.execute("""
        SELECT 
            r.id as registration_id,
            h.id as hike_id,
            h.hike_name,
            h.hike_date,
            r.car_sharing,
            h.latitude,
            h.longitude
        FROM registrations r
        JOIN hikes h ON r.hike_id = h.id
        WHERE 
            r.telegram_id = ? AND
            h.hike_date >= ? AND
            h.is_active = 1
        ORDER BY h.hike_date ASC
        """, (telegram_id, today))
        
        hikes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return hikes
    
    @staticmethod
    def add_registration(telegram_id, hike_id, registration_data):
        """Add a new hike registration"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # First check if spots are available
        cursor.execute("""
        SELECT 
            h.max_participants,
            (SELECT COUNT(*) FROM registrations r WHERE r.hike_id = h.id) as current_participants
        FROM hikes h
        WHERE h.id = ?
        """, (hike_id,))
        
        hike_info = cursor.fetchone()
        if not hike_info:
            conn.close()
            return {"success": False, "error": "Hike not found"}
        
        if hike_info['current_participants'] >= hike_info['max_participants']:
            conn.close()
            return {"success": False, "error": "No spots available"}
        
        # Check if user is already registered
        cursor.execute("""
        SELECT id FROM registrations
        WHERE telegram_id = ? AND hike_id = ?
        """, (telegram_id, hike_id))
        
        if cursor.fetchone():
            conn.close()
            return {"success": False, "error": "Already registered for this hike"}
        
        # Add registration
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute("""
            INSERT INTO registrations (
                telegram_id,
                hike_id,
                registration_timestamp,
                name_surname,
                email,
                phone,
                birth_date,
                medical_conditions,
                has_equipment,
                car_sharing,
                location,
                notes,
                reminder_preference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                telegram_id,
                hike_id,
                now,
                registration_data.get('name_surname', ''),
                registration_data.get('email', ''),
                registration_data.get('phone', ''),
                registration_data.get('birth_date', ''),
                registration_data.get('medical_conditions', ''),
                1 if registration_data.get('has_equipment') else 0,
                1 if registration_data.get('car_sharing') else 0,
                registration_data.get('location', ''),
                registration_data.get('notes', ''),
                registration_data.get('reminder_preference', 'No reminders')
            ))
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def cancel_registration(telegram_id, registration_id):
        """Cancel a hike registration"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Verify the registration belongs to the user
        cursor.execute("""
        SELECT id FROM registrations
        WHERE id = ? AND telegram_id = ?
        """, (registration_id, telegram_id))
        
        if not cursor.fetchone():
            conn.close()
            return {"success": False, "error": "Registration not found"}
        
        # Delete the registration
        cursor.execute("""
        DELETE FROM registrations
        WHERE id = ?
        """, (registration_id,))
        
        conn.commit()
        conn.close()
        return {"success": True}
    
    @staticmethod
    def add_hike(hike_data, created_by):
        """Add a new hike (admin only)"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            INSERT INTO hikes (
                hike_name,
                hike_date,
                max_participants,
                latitude,
                longitude,
                difficulty,
                description,
                created_by,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                hike_data.get('hike_name', ''),
                hike_data.get('hike_date', ''),
                hike_data.get('max_participants', 0),
                hike_data.get('latitude'),
                hike_data.get('longitude'),
                hike_data.get('difficulty', ''),
                hike_data.get('description', ''),
                created_by
            ))
            
            hike_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return {"success": True, "hike_id": hike_id}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_hike(hike_id, hike_data, updated_by):
        """Update an existing hike (admin only)"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if updater is admin
        if not DBUtils.check_is_admin(updated_by):
            conn.close()
            return {"success": False, "error": "Admin privileges required"}
        
        try:
            cursor.execute("""
            UPDATE hikes
            SET 
                hike_name = ?,
                hike_date = ?,
                max_participants = ?,
                latitude = ?,
                longitude = ?,
                difficulty = ?,
                description = ?
            WHERE id = ?
            """, (
                hike_data.get('hike_name'),
                hike_data.get('hike_date'),
                hike_data.get('max_participants'),
                hike_data.get('latitude'),
                hike_data.get('longitude'),
                hike_data.get('difficulty'),
                hike_data.get('description'),
                hike_id
            ))
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def add_group_member(telegram_id):
        """Add a user to group members"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # Add user if not exists
            cursor.execute("""
            INSERT OR IGNORE INTO users (telegram_id, registration_timestamp, last_updated)
            VALUES (?, ?, ?)
            """, (telegram_id, now, now))
            
            # Add to group members
            cursor.execute("""
            INSERT OR IGNORE INTO group_members (telegram_id, joined_date)
            VALUES (?, ?)
            """, (telegram_id, now))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error:
            conn.close()
            return False
    
    @staticmethod
    def remove_group_member(telegram_id):
        """Remove a user from group members"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            DELETE FROM group_members
            WHERE telegram_id = ?
            """, (telegram_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error:
            conn.close()
            return False
    
    @staticmethod
    def check_in_group(telegram_id):
        """Check if a user is in the group"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT telegram_id FROM group_members
        WHERE telegram_id = ?
        """, (telegram_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
        
    @staticmethod
    def get_users_for_reminder(days_before):
        """Get users who need reminders"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        today = date.today()
        reminder_date = today + timedelta(days=days_before)
        
        cursor.execute("""
        SELECT 
            r.telegram_id,
            r.reminder_preference,
            h.id as hike_id,
            h.hike_name,
            h.hike_date,
            h.latitude,
            h.longitude
        FROM registrations r
        JOIN hikes h ON r.hike_id = h.id
        WHERE 
            h.hike_date = ? AND
            (
                r.reminder_preference LIKE ? OR
                r.reminder_preference LIKE ?
            )
        """, (
            reminder_date,
            f"%{days_before} days%",
            "%both%"
        ))
        
        reminders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return reminders
    
    @staticmethod
    def add_admin(admin_id, added_by, role='admin'):
        """Add a new admin user"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        if not DBUtils.check_user_exists(admin_id):
            conn.close()
            return {"success": False, "error": "User does not exist"}
        
        # Check if already admin
        if DBUtils.check_is_admin(admin_id):
            conn.close()
            return {"success": False, "error": "User is already an admin"}
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute("""
            INSERT INTO admins (telegram_id, role, added_by, added_on)
            VALUES (?, ?, ?, ?)
            """, (admin_id, role, added_by, now))
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_hike_participants(hike_id):
        """Get all participants for a specific hike"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            r.id as registration_id,
            r.telegram_id,
            r.name_surname,
            r.email,
            r.phone,
            r.birth_date,
            r.medical_conditions,
            r.has_equipment,
            r.car_sharing,
            r.location,
            r.notes,
            r.reminder_preference,
            r.registration_timestamp
        FROM registrations r
        WHERE r.hike_id = ?
        ORDER BY r.registration_timestamp ASC
        """, (hike_id,))
        
        participants = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return participants

    @staticmethod
    def cancel_hike(hike_id, admin_id):
        """Cancel a hike by setting is_active to 0 (admin only)"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            conn.close()
            return {"success": False, "error": "Admin privileges required"}
        
        try:
            # Get registered users for notifications
            cursor.execute("""
            SELECT 
                r.telegram_id,
                h.hike_name,
                h.hike_date
            FROM registrations r
            JOIN hikes h ON r.hike_id = h.id
            WHERE h.id = ?
            """, (hike_id,))
            
            registrations = [dict(row) for row in cursor.fetchall()]
            
            # Update hike status
            cursor.execute("""
            UPDATE hikes
            SET is_active = 0
            WHERE id = ?
            """, (hike_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True, 
                "registrations": registrations
            }
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}

    @staticmethod
    def reactivate_hike(hike_id, admin_id):
        """Reactivate a cancelled hike by setting is_active to 1 (admin only)"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            conn.close()
            return {"success": False, "error": "Admin privileges required"}
        
        try:
            # Check if hike exists and is currently inactive
            cursor.execute("""
            SELECT id, hike_name, hike_date, is_active 
            FROM hikes 
            WHERE id = ?
            """, (hike_id,))
            
            hike = cursor.fetchone()
            if not hike:
                conn.close()
                return {"success": False, "error": "Hike not found"}
                
            if hike['is_active'] == 1:
                conn.close()
                return {"success": False, "error": "Hike is already active"}
                
            # Get hike details for return
            hike_info = {
                'hike_name': hike['hike_name'],
                'hike_date': hike['hike_date']
            }
            
            # Update hike status
            cursor.execute("""
            UPDATE hikes
            SET is_active = 1
            WHERE id = ?
            """, (hike_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True, 
                "hike_info": hike_info
            }
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}

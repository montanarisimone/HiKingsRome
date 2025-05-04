# Copyright © 2025 Simone Montanari. All Rights Reserved.
# This file is part of HiKingsRome and may not be used or distributed without written permission.

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
            INSERT INTO users (
                telegram_id, 
                username, 
                name,
                surname,
                email,
                phone,
                birth_date,
                registration_timestamp, 
                last_updated
            )
            VALUES (?, ?, 'Not set', 'Not set', 'Not set', 'Not set', 'Not set', ?, ?)
            """, (telegram_id, username, now, now))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def get_user_profile(telegram_id):
        """Get user profile information"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            telegram_id,
            username,
            name,
            surname,
            email,
            phone,
            birth_date,
            is_guide
        FROM users 
        WHERE telegram_id = ?
        """, (telegram_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)  # Convert to regular dictionary
        return None
    
    @staticmethod
    def update_user_profile(telegram_id, profile_data):
        """Update user profile information"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # Check if required fields are provided when updating
            if profile_data.get('name') is not None and not profile_data.get('name'):
                conn.close()
                return {"success": False, "error": "Name cannot be empty"}
                
            if profile_data.get('surname') is not None and not profile_data.get('surname'):
                conn.close()
                return {"success": False, "error": "Surname cannot be empty"}
                
            if profile_data.get('email') is not None and not profile_data.get('email'):
                conn.close()
                return {"success": False, "error": "Email cannot be empty"}
                
            if profile_data.get('phone') is not None and not profile_data.get('phone'):
                conn.close()
                return {"success": False, "error": "Phone cannot be empty"}
                
            if profile_data.get('birth_date') is not None and not profile_data.get('birth_date'):
                conn.close()
                return {"success": False, "error": "Birth date cannot be empty"}
            
            # Get current profile data first
            cursor.execute("""
            SELECT name, surname, email, phone, birth_date 
            FROM users 
            WHERE telegram_id = ?
            """, (telegram_id,))

            current_data = cursor.fetchone()

            # If there's no current data, we need to make sure all required fields are provided
            if not current_data:
                required_fields = ['name', 'surname', 'email', 'phone', 'birth_date']
                for field in required_fields:
                    if field not in profile_data or not profile_data[field]:
                        # Skip incomplete profile updates
                        if len(profile_data) < len(required_fields):
                            # This is a partial update, which is ok during profile setup
                            break
                        conn.close()
                        return {"success": False, "error": f"Required field '{field}' is missing"}
            
            # Update only the provided fields
            update_fields = []
            params = []
            
            # Only update fields that are provided
            if 'name' in profile_data:
                update_fields.append("name = ?")
                params.append(profile_data['name'])
                
            if 'surname' in profile_data:
                update_fields.append("surname = ?")
                params.append(profile_data['surname'])
                
            if 'email' in profile_data:
                update_fields.append("email = ?")
                params.append(profile_data['email'])
                
            if 'phone' in profile_data:
                update_fields.append("phone = ?")
                params.append(profile_data['phone'])
                
            if 'birth_date' in profile_data:
                update_fields.append("birth_date = ?")
                params.append(profile_data['birth_date'])
                
            if not update_fields:
                # Nothing to update
                conn.close()
                return {"success": True}
                
            # Add last_updated and telegram_id parameters
            update_fields.append("last_updated = ?")
            params.append(now)
            params.append(telegram_id)
            
            # Create the SQL query
            query = f"""
            UPDATE users 
            SET {', '.join(update_fields)}
            WHERE telegram_id = ?
            """
            
            cursor.execute(query, params)
        
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_guide_status(telegram_id, is_guide):
        """Update user's guide status (admin only)"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute("""
            UPDATE users 
            SET 
                is_guide = ?,
                last_updated = ?
            WHERE telegram_id = ?
            """, (
                1 if is_guide else 0,
                now,
                telegram_id
            ))
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
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
    def get_fixed_costs():
        """Get all fixed costs"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            id,
            name,
            amount,
            frequency,
            description,
            created_by,
            created_on,
            last_updated
        FROM fixed_costs
        ORDER BY name ASC
        """)
        
        costs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return costs
    
    @staticmethod
    def add_fixed_cost(admin_id, cost_data):
        """Add a new fixed cost"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute("""
            INSERT INTO fixed_costs (
                name,
                amount,
                frequency,
                description,
                created_by,
                created_on,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cost_data.get('name', ''),
                cost_data.get('amount', 0.0),
                cost_data.get('frequency', 'monthly'),
                cost_data.get('description', ''),
                admin_id,
                now,
                now
            ))
            
            cost_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return {"success": True, "cost_id": cost_id}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_fixed_cost(cost_id, admin_id, cost_data):
        """Update an existing fixed cost"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            conn.close()
            return {"success": False, "error": "Admin privileges required"}
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # First you get the current cost data
            cursor.execute("SELECT * FROM fixed_costs WHERE id = ?", (cost_id,))
            current_cost = cursor.fetchone()
            
            if not current_cost:
                conn.close()
                return {"success": False, "error": "Cost not found"}

            # Prepare fields to be updated
            fields_to_update = []
            params = []

            # Update only fields that have been specified
            if 'name' in cost_data and cost_data['name'] is not None:
                fields_to_update.append("name = ?")
                params.append(cost_data['name'])
                
            if 'amount' in cost_data and cost_data['amount'] is not None:
                fields_to_update.append("amount = ?")
                params.append(cost_data['amount'])
                
            if 'frequency' in cost_data and cost_data['frequency'] is not None:
                fields_to_update.append("frequency = ?")
                params.append(cost_data['frequency'])
                
            if 'description' in cost_data and cost_data['description'] is not None:
                fields_to_update.append("description = ?")
                params.append(cost_data['description'])

            # Always add timestamp update
            fields_to_update.append("last_updated = ?")
            params.append(now)

            # Add the cost ID to the end of the parameters
            params.append(cost_id)

            # If there are no fields to update, exit
            if not fields_to_update:
                conn.close()
                return {"success": True, "message": "No fields to update"}

            # Construct query
            query = f"""
            UPDATE fixed_costs
            SET {', '.join(fields_to_update)}
            WHERE id = ?
            """
            
            logger.info(f"Update Query: {query}")
            logger.info(f"Parameters: {params}")

            cursor.execute(query, params)
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            logger.error(f"Error SQL in update_fixed_cost: {e}")
            conn.close()
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"General error in update_fixed_cost: {e}")
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def delete_fixed_cost(cost_id, admin_id):
        """Delete a fixed cost"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            conn.close()
            return {"success": False, "error": "Admin privileges required"}
        
        try:
            cursor.execute("""
            DELETE FROM fixed_costs
            WHERE id = ?
            """, (cost_id,))
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_cost_summary():
        """Get a summary of costs by frequency"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            frequency,
            SUM(amount) as total_amount
        FROM fixed_costs
        GROUP BY frequency
        ORDER BY 
            CASE 
                WHEN frequency = 'monthly' THEN 1
                WHEN frequency = 'quarterly' THEN 2
                WHEN frequency = 'yearly' THEN 3
                ELSE 4
            END
        """)
        
        summary = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return summary
    
    @staticmethod
    def sync_guide_status_with_admin():
        """Sync guide status with admin status for all users"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Set is_guide=1 for all admins
        cursor.execute("""
        UPDATE users
        SET is_guide = 1
        WHERE telegram_id IN (SELECT telegram_id FROM admins)
        """)
        
        # Set is_guide=0 for non-admins
        cursor.execute("""
        UPDATE users
        SET is_guide = 0
        WHERE telegram_id NOT IN (SELECT telegram_id FROM admins)
        """)
        
        conn.commit()
        conn.close()
        return True
    
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
            h.guides,
            h.latitude,
            h.longitude,
            h.difficulty,
            h.description,
            h.is_active,
            (SELECT COUNT(*) FROM registrations r 
             JOIN users u ON r.telegram_id = u.telegram_id
             WHERE r.hike_id = h.id AND u.is_guide = 0) as current_participants
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

        # Check if user is admin/guide
        is_admin = DBUtils.check_is_admin(telegram_id)
        is_guide = False

        if is_admin:
            # Check if user's profile has guide status
            cursor.execute("SELECT is_guide FROM users WHERE telegram_id = ?", (telegram_id,))
            user_info = cursor.fetchone()
            if user_info and user_info['is_guide'] == 1:
                is_guide = True

        # First check if spots are available - skip this check for guides
        if not is_guide:
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

        else:
            # For guides, just check if the hike exists
            cursor.execute("SELECT id FROM hikes WHERE id = ?", (hike_id,))
            if not cursor.fetchone():
                conn.close()
                return {"success": False, "error": "Hike not found"}
        
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
                guides,
                latitude,
                longitude,
                difficulty,
                description,
                created_by,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                hike_data.get('hike_name', ''),
                hike_data.get('hike_date', ''),
                hike_data.get('max_participants', 0),
                hike_data.get('guides', 0),
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
    def get_all_admins():
        """Get a list of all admin users"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT telegram_id, role
        FROM admins
        """)
        
        admins = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return admins
    
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
                r.reminder_preference = ? OR
                r.reminder_preference = '5 and 2 days'
            )
        """, (
            reminder_date,
            f"%{days_before} days%"
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
            
            # Also update guide status
            cursor.execute("""
            UPDATE users
            SET is_guide = 1
            WHERE telegram_id = ?
            """, (admin_id,))
            
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
            r.registration_timestamp,
            u.is_guide
        FROM registrations r
        JOIN users u ON r.telegram_id = u.telegram_id
        WHERE r.hike_id = ?
        ORDER BY u.is_guide DESC, r.registration_timestamp ASC
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
    def add_maintenance(admin_id, maintenance_date, start_time, end_time, reason=None):
        """Add a new maintenance schedule"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            cursor.execute("""
            INSERT INTO maintenance (
                maintenance_date,
                start_time,
                end_time,
                reason,
                created_by,
                created_on,
                sent_notification
            ) VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (
                maintenance_date,
                start_time,
                end_time,
                reason,
                admin_id,
                now
            ))
            
            maintenance_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return {"success": True, "maintenance_id": maintenance_id}

        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_maintenance(maintenance_id, admin_id, maintenance_date=None, start_time=None, end_time=None, reason=None):
        """Update existing maintenance schedule"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            conn.close()
            return {"success": False, "error": "Admin privileges required"}
        
        # Build update query
        update_fields = []
        params = []

        if maintenance_date:
            update_fields.append("maintenance_date = ?")
            params.append(maintenance_date)
            
        if start_time:
            update_fields.append("start_time = ?")
            params.append(start_time)
            
        if end_time:
            update_fields.append("end_time = ?")
            params.append(end_time)
            
        if reason is not None:  # Allow empty reason
            update_fields.append("reason = ?")
            params.append(reason)
        
        # Reset notification flag if date or time changed
        if maintenance_date or start_time or end_time:
            update_fields.append("sent_notification = 0")
        
        if not update_fields:
            conn.close()
            return {"success": True}  # Nothing to update
        
        params.append(maintenance_id)
        
        try:
            cursor.execute(f"""
            UPDATE maintenance
            SET {', '.join(update_fields)}
            WHERE id = ?
            """, params)
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def delete_maintenance(maintenance_id, admin_id):
        """Delete maintenance schedule"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            conn.close()
            return {"success": False, "error": "Admin privileges required"}
        
        try:
            cursor.execute("""
            DELETE FROM maintenance
            WHERE id = ?
            """, (maintenance_id,))
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_maintenance_schedules(include_past=False):
        """Get all maintenance schedules, optionally including past schedules"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')  # Convert date to string in ISO format
    
        now = datetime.now().time()
        now_str = now.strftime('%H:%M:%S')  # Convert time to string
        
        query = """
        SELECT 
            id,
            maintenance_date,
            start_time,
            end_time,
            reason,
            created_by,
            created_on,
            sent_notification
        FROM maintenance
        """
        
        if not include_past:
            query += """
            WHERE (maintenance_date > ?) OR
                  (maintenance_date = ? AND end_time > ?)
            """
            cursor.execute(query, (today_str, today_str, now_str))
        else:
            cursor.execute(query)
        
        schedules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return schedules
    
    @staticmethod
    def get_pending_maintenance_notifications():
        """Get maintenance schedules that need notifications sent"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        today = date.today()
        now = datetime.now()
        
        # Find maintenance scheduled in the next 2 hours that haven't had notifications sent
        two_hours_later = (now + timedelta(hours=2))
        notification_date = two_hours_later.date()
        notification_time = two_hours_later.time()
        
        cursor.execute("""
        SELECT 
            id,
            maintenance_date,
            start_time,
            end_time,
            reason
        FROM maintenance
        WHERE 
            sent_notification = 0 AND
            ((maintenance_date = ? AND start_time <= ?) OR
             (maintenance_date = ? AND ? > ?))
        """, (
            notification_date, notification_time,  # Same day, starting within 2 hours
            today, notification_date, today        # Different day, but within 2 hours
        ))
        
        schedules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return schedules
    
    @staticmethod
    def mark_maintenance_notification_sent(maintenance_id):
        """Mark that a notification has been sent for this maintenance"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE maintenance
        SET sent_notification = 1
        WHERE id = ?
        """, (maintenance_id,))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def get_all_users():
        """Get all user IDs for sending notifications"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT telegram_id FROM users")
        users = [row['telegram_id'] for row in cursor.fetchall()]
        
        conn.close()
        return users

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

# Copyright © 2025 Simone Montanari. All Rights Reserved.
# This file is part of HiKingsRome and may not be used or distributed without written permission.

#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime, date, timedelta
import pytz
import logging
import math

# Database file path
DB_PATH = 'hiky_bot.db'

# Rome timezone for consistent timestamps
rome_tz = pytz.timezone('Europe/Rome')

# Set logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
    def calculate_dynamic_fees(hike_id, admin_id):
        """
        Calculate the final fees based on actual attendance
        
        Args:
            hike_id: ID of the hike to calculate fees for
            admin_id: ID of the admin making the change
            
        Returns:
            dict: Success flag and fee calculation results
        """
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            return {"success": False, "error": "Admin privileges required"}
        
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get hike details
            cursor.execute("""
            SELECT 
                h.id, 
                h.hike_name, 
                h.max_participants,
                h.guides,
                h.variable_costs,
                h.fixed_cost_coverage,
                h.max_cost_per_participant,
                h.actual_attendance,
                h.fee_locked,
                (SELECT COUNT(*) FROM registrations r 
                 JOIN users u ON r.telegram_id = u.telegram_id
                 WHERE r.hike_id = h.id AND u.is_guide = 0) as registered_participants,
                (SELECT COUNT(*) FROM registrations r 
                 JOIN users u ON r.telegram_id = u.telegram_id
                 WHERE r.hike_id = h.id AND u.is_guide = 1) as registered_guides
            FROM hikes h
            WHERE h.id = ?
            """, (hike_id,))
            
            hike = cursor.fetchone()
            if not hike:
                conn.close()
                return {"success": False, "error": "Hike not found"}
            
            # Convert to dict
            hike_data = dict(hike)
            
            # If fee is already locked, return current values
            if hike_data.get('fee_locked'):
                cursor.execute("""
                SELECT final_participant_fee, final_guide_fee
                FROM hikes
                WHERE id = ?
                """, (hike_id,))
                
                fees = cursor.fetchone()
                if fees:
                    conn.close()
                    return {
                        "success": True, 
                        "participant_fee": fees['final_participant_fee'],
                        "guide_fee": fees['final_guide_fee'],
                        "is_locked": True
                    }
            
            # Get actual attendance if available, otherwise use registered participants
            actual_attendance = hike_data.get('actual_attendance', 0)
            if actual_attendance <= 0:
                # Count attendance confirmations
                cursor.execute("""
                SELECT COUNT(*) as count
                FROM attendance
                WHERE hike_id = ? AND attended = 1
                """, (hike_id,))
                
                attendance_count = cursor.fetchone()
                if attendance_count and attendance_count['count'] > 0:
                    actual_attendance = attendance_count['count']
                else:
                    # Fall back to registered participants
                    actual_attendance = hike_data.get('registered_participants', 0)
            
            # Get registered guides
            registered_guides = hike_data.get('registered_guides', 0)
            if registered_guides <= 0:
                registered_guides = hike_data.get('guides', 1)  # Default to planned guides
                
            # Calculate the monthly fixed costs
            monthly_fixed_costs = DBUtils.get_monthly_fixed_costs()
            
            # Calculate fees based on actual attendance
            variable_costs = hike_data.get('variable_costs', 0)
            fixed_cost_coverage = hike_data.get('fixed_cost_coverage', 0.5)
            max_cost_per_participant = hike_data.get('max_cost_per_participant', 0)
            
            # Guide fee calculation
            guide_fee = 0
            if actual_attendance + registered_guides > 0:
                guide_fee = variable_costs / (actual_attendance + registered_guides)
                guide_fee = math.ceil(guide_fee)  # Round up guide fee
                
            # Participant fee calculation
            participant_fee = guide_fee  # Start with the guide fee portion
            if actual_attendance > 0:
                fixed_cost_portion = (fixed_cost_coverage * monthly_fixed_costs) / actual_attendance
                participant_fee += fixed_cost_portion
                participant_fee = math.ceil(participant_fee)  # Round up participant fee
                
            # Apply maximum cost cap if set
            if max_cost_per_participant > 0 and participant_fee > max_cost_per_participant:
                participant_fee = max_cost_per_participant
                
            conn.close()
            
            return {
                "success": True,
                "participant_fee": participant_fee,
                "guide_fee": guide_fee,
                "actual_attendance": actual_attendance,
                "registered_guides": registered_guides,
                "is_locked": False
            }
                
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def lock_fees(hike_id, admin_id, participant_fee, guide_fee):
        """
        Lock the fees for a hike at specific values
        
        Args:
            hike_id: ID of the hike
            admin_id: ID of the admin making the change
            participant_fee: Final fee for participants
            guide_fee: Final fee for guides
            
        Returns:
            dict: Success flag and result message
        """
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            return {"success": False, "error": "Admin privileges required"}
        
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        try:
            # Update the hike with final fees
            cursor.execute("""
            UPDATE hikes
            SET 
                fee_locked = 1,
                final_participant_fee = ?,
                final_guide_fee = ?
            WHERE id = ?
            """, (
                participant_fee,
                guide_fee,
                hike_id
            ))
            
            conn.commit()
            conn.close()
            return {"success": True}
                
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def unlock_fees(hike_id, admin_id):
        """
        Unlock the fees for a hike
        
        Args:
            hike_id: ID of the hike
            admin_id: ID of the admin making the change
            
        Returns:
            dict: Success flag and result message
        """
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            return {"success": False, "error": "Admin privileges required"}
        
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        try:
            # Update the hike to unlock fees
            cursor.execute("""
            UPDATE hikes
            SET 
                fee_locked = 0,
                final_participant_fee = 0,
                final_guide_fee = 0
            WHERE id = ?
            """, (hike_id,))
            
            conn.commit()
            conn.close()
            return {"success": True}
                
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_actual_attendance(hike_id, admin_id, attendance_count):
        """
        Update the actual attendance for a hike
        
        Args:
            hike_id: ID of the hike
            admin_id: ID of the admin making the change
            attendance_count: Number of participants who attended
            
        Returns:
            dict: Success flag and result message
        """
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            return {"success": False, "error": "Admin privileges required"}
        
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        try:
            # Validate attendance count
            if attendance_count < 0:
                conn.close()
                return {"success": False, "error": "Attendance count cannot be negative"}
            
            # Update the hike with actual attendance
            cursor.execute("""
            UPDATE hikes
            SET actual_attendance = ?
            WHERE id = ?
            """, (
                attendance_count,
                hike_id
            ))
            
            conn.commit()
            conn.close()
            return {"success": True}
                
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def record_attendance(hike_id, telegram_id, attended):
        """
        Record attendance for a participant
        
        Args:
            hike_id: ID of the hike
            telegram_id: ID of the participant
            attended: Boolean indicating if they attended
            
        Returns:
            dict: Success flag and result message
        """
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get registration ID
            cursor.execute("""
            SELECT id FROM registrations
            WHERE telegram_id = ? AND hike_id = ?
            """, (telegram_id, hike_id))
            
            registration = cursor.fetchone()
            if not registration:
                conn.close()
                return {"success": False, "error": "Registration not found"}
            
            registration_id = registration['id']
            now = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if attendance record exists
            cursor.execute("""
            SELECT id FROM attendance
            WHERE registration_id = ?
            """, (registration_id,))
            
            attendance_record = cursor.fetchone()
            
            if attendance_record:
                # Update existing record
                cursor.execute("""
                UPDATE attendance
                SET 
                    attended = ?,
                    confirmation_timestamp = ?
                WHERE registration_id = ?
                """, (
                    1 if attended else 0,
                    now,
                    registration_id
                ))
            else:
                # Create new record
                cursor.execute("""
                INSERT INTO attendance (
                    registration_id,
                    telegram_id,
                    hike_id,
                    attended,
                    confirmation_timestamp
                ) VALUES (?, ?, ?, ?, ?)
                """, (
                    registration_id,
                    telegram_id,
                    hike_id,
                    1 if attended else 0,
                    now
                ))
            
            conn.commit()
            conn.close()
            return {"success": True}
                
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    
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
            h.variable_costs,
            h.fixed_cost_coverage,
            h.max_cost_per_participant,
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
                variable_costs,
                fixed_cost_coverage,
                max_cost_per_participant,
                created_by,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                hike_data.get('hike_name', ''),
                hike_data.get('hike_date', ''),
                hike_data.get('max_participants', 0),
                hike_data.get('guides', 0),
                hike_data.get('latitude'),
                hike_data.get('longitude'),
                hike_data.get('difficulty', ''),
                hike_data.get('description', ''),
                hike_data.get('variable_costs', 0),
                hike_data.get('fixed_cost_coverage', 0.5),  # Default 50%
                hike_data.get('max_cost_per_participant', 0),  # Default no maximum
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
                description = ?,
                variable_costs = ?,
                fixed_cost_coverage = ?,
                max_cost_per_participant = ?
            WHERE id = ?
            """, (
                hike_data.get('hike_name'),
                hike_data.get('hike_date'),
                hike_data.get('max_participants'),
                hike_data.get('latitude'),
                hike_data.get('longitude'),
                hike_data.get('difficulty'),
                hike_data.get('description'),
                hike_data.get('variable_costs', 0),
                hike_data.get('fixed_cost_coverage', 0.5),
                hike_data.get('max_cost_per_participant', 0),
                hike_id
            ))
            
            conn.commit()
            conn.close()
            return {"success": True}
            
        except sqlite3.Error as e:
            conn.close()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_monthly_fixed_costs():
        """Get the total monthly fixed costs"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Get monthly costs
        cursor.execute("""
        SELECT SUM(amount) as total
        FROM fixed_costs
        WHERE frequency = 'monthly'
        """)
        monthly = cursor.fetchone()
        monthly_amount = monthly['total'] if monthly and monthly['total'] is not None else 0
        
        # Get quarterly costs (divided by 3 to get monthly equivalent)
        cursor.execute("""
        SELECT SUM(amount) as total
        FROM fixed_costs
        WHERE frequency = 'quarterly'
        """)
        quarterly = cursor.fetchone()
        quarterly_amount = (quarterly['total'] / 3) if quarterly and quarterly['total'] is not None else 0
        
        # Get yearly costs (divided by 12 to get monthly equivalent)
        cursor.execute("""
        SELECT SUM(amount) as total
        FROM fixed_costs
        WHERE frequency = 'yearly'
        """)
        yearly = cursor.fetchone()
        yearly_amount = (yearly['total'] / 12) if yearly and yearly['total'] is not None else 0
        
        conn.close()
        
        # Return total monthly cost
        return monthly_amount + quarterly_amount + yearly_amount
    
    @staticmethod
    def calculate_fee_ranges(hike_data, fixed_costs_monthly=None, participant_count=None):
        """
        Calculate fee ranges for guides and participants based on fixed and variable costs.
        
        Args:
            hike_data (dict): Hike details including variable_costs, guides, max_participants, fixed_cost_coverage
            fixed_costs_monthly (float, optional): Monthly fixed costs amount
            participant_count (int, optional): Current participants count, if None use min 1 and max from hike data
            
        Returns:
            dict: Dictionary containing min/max fees for guides and participants
        """
        # Extract data
        variable_costs = float(hike_data.get('variable_costs', 0))
        guide_count = int(hike_data.get('guides', 1))
        max_participants = int(hike_data.get('max_participants', 0))
        fixed_cost_coverage = float(hike_data.get('fixed_cost_coverage', 0.5))  # Default 50%
        max_cost_per_participant = float(hike_data.get('max_cost_per_participant', 0))
        
        # Get monthly fixed costs if not provided
        if fixed_costs_monthly is None:
            fixed_costs_monthly = DBUtils.get_monthly_fixed_costs()
        
        # Determine participant counts for min/max scenarios
        min_participant_scenario = 1  # Minimum case: only 1 participant
        max_participant_scenario = max_participants  # Maximum case: full attendance
        
        if participant_count is not None:
            current_participants = min(participant_count, max_participants)
            min_participant_scenario = current_participants
            max_participant_scenario = current_participants
        
        # Calculate guide fees
        guide_fee_min = variable_costs / (min_participant_scenario + guide_count) if (min_participant_scenario + guide_count) > 0 else 0
        guide_fee_max = variable_costs / (max_participant_scenario + guide_count) if (max_participant_scenario + guide_count) > 0 else 0

        # Round up guide fees
        guide_fee_min = math.ceil(guide_fee_min)
        guide_fee_max = math.ceil(guide_fee_max)
        
        # Calculate participant fees
        fixed_cost_portion_min = (fixed_cost_coverage * fixed_costs_monthly / min_participant_scenario) if min_participant_scenario > 0 else 0
        fixed_cost_portion_max = (fixed_cost_coverage * fixed_costs_monthly / max_participant_scenario) if max_participant_scenario > 0 else 0
        
        participant_fee_min = fixed_cost_portion_min + guide_fee_min
        participant_fee_max = fixed_cost_portion_max + guide_fee_max

        # Round up participant fees
        participant_fee_min = math.ceil(participant_fee_min)
        participant_fee_max = math.ceil(participant_fee_max)
        
        # Apply maximum cost cap if set
        if max_cost_per_participant > 0:
            participant_fee_min = min(participant_fee_min, max_cost_per_participant)
            participant_fee_max = min(participant_fee_max, max_cost_per_participant)
        
        return {
            'guide_fee_min': guide_fee_min,
            'guide_fee_max': guide_fee_max,
            'participant_fee_min': participant_fee_min,
            'participant_fee_max': participant_fee_max,
            'fixed_costs_monthly': fixed_costs_monthly,
            'variable_costs': variable_costs,
            'fixed_cost_coverage': fixed_cost_coverage,
            'max_cost_per_participant': max_cost_per_participant
        }
    
    @staticmethod
    def update_hike_cost_settings(hike_id, admin_id, fixed_cost_coverage, max_cost_per_participant):
        """Update hike cost settings (admin only)"""
        conn = DBUtils.get_connection()
        cursor = conn.cursor()
        
        # Check if admin
        if not DBUtils.check_is_admin(admin_id):
            conn.close()
            return {"success": False, "error": "Admin privileges required"}
        
        try:
            # Validate inputs
            fixed_cost_coverage = float(fixed_cost_coverage)
            if fixed_cost_coverage < 0 or fixed_cost_coverage > 1:
                conn.close()
                return {"success": False, "error": "Fixed cost coverage must be between 0 and 1 (0% to 100%)"}
            
            max_cost_per_participant = float(max_cost_per_participant)
            if max_cost_per_participant < 0:
                conn.close()
                return {"success": False, "error": "Maximum cost per participant cannot be negative"}
            
            # Update hike settings
            cursor.execute("""
            UPDATE hikes
            SET 
                fixed_cost_coverage = ?,
                max_cost_per_participant = ?
            WHERE id = ?
            """, (
                fixed_cost_coverage,
                max_cost_per_participant,
                hike_id
            ))
            
            conn.commit()
            conn.close()
            return {"success": True}
                
        except (ValueError, sqlite3.Error) as e:
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

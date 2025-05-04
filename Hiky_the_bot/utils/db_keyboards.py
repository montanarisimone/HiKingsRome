# Copyright © 2025 Simone Montanari. All Rights Reserved.
# This file is part of HiKingsRome and may not be used or distributed without written permission.

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

class KeyboardBuilder:
    @staticmethod
    def create_menu_keyboard():
        """Create the main menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("Personal Profile 👤", callback_data='personal_profile')],
            [InlineKeyboardButton("Manage Hikes 🏔️", callback_data='manage_hikes')],
            [InlineKeyboardButton("Useful links 🔗", callback_data='links')],
            [InlineKeyboardButton("Make Donation 💖", callback_data='donation')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_profile_keyboard():
        """Create the profile management keyboard"""
        keyboard = [
            [InlineKeyboardButton("View profile info 📋", callback_data='view_profile')],
            [InlineKeyboardButton("Edit profile 📝", callback_data='edit_profile')],
            [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_edit_profile_keyboard():
        """Create keyboard for editing profile fields"""
        keyboard = [
            [InlineKeyboardButton("Name 📝", callback_data='edit_name')],
            [InlineKeyboardButton("Surname 📝", callback_data='edit_surname')],
            [InlineKeyboardButton("Email 📧", callback_data='edit_email')],
            [InlineKeyboardButton("Phone 📱", callback_data='edit_phone')],
            [InlineKeyboardButton("Birth Date 📅", callback_data='edit_birth_date')],
            [InlineKeyboardButton("🔙 Back to profile", callback_data='back_to_profile')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_manage_hikes_keyboard():
        """Create the hikes management submenu keyboard"""
        keyboard = [
            [InlineKeyboardButton("Sign up for hike 🏃", callback_data='signup')],
            [InlineKeyboardButton("My Hikes 🎒", callback_data='myhikes')],
            [InlineKeyboardButton("Hike Calendar 📅", callback_data='calendar')],
            [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_admin_keyboard():
        """Create the admin menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("Create new hike 🏔️", callback_data='admin_create_hike')],
            [InlineKeyboardButton("Manage existing hikes 📝", callback_data='admin_manage_hikes')],
            [InlineKeyboardButton("Schedule maintenance 🔧", callback_data='admin_maintenance')],
            [InlineKeyboardButton("Cost Control 💰", callback_data='admin_costs')],
            [InlineKeyboardButton("Query Database 🔍", callback_data='query_db')],
            [InlineKeyboardButton("Add admin 👑", callback_data='admin_add_admin')],
            [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_yes_no_keyboard(yes_callback, no_callback):
        """Create a generic Yes/No keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data=yes_callback),
                InlineKeyboardButton("No ❌", callback_data=no_callback)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_back_to_menu_keyboard():
        """Create a keyboard with just the back to menu button"""
        keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_links_keyboard():
        """Create the useful links keyboard"""
        keyboard = [
            [InlineKeyboardButton("🌐 Website", url="https://www.hikingsrome.com/")],
            [InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/hikingsrome/")],
            [InlineKeyboardButton("💬 Telegram Group", url="https://t.me/+dku6thBDTGM0MWZk")],
            [InlineKeyboardButton("🗺 Komoot", url="https://www.komoot.com/it-it/user/3261856743261")],
            [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_donation_keyboard():
        """Create the donation options keyboard"""
        keyboard = [
            [InlineKeyboardButton("✨ Telegram Stars", callback_data='donation_stars')],
            [InlineKeyboardButton("💲 PayPal", url="https://paypal.me/hikingsrome?country.x=IT&locale.x=it_IT")],
            [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_location_keyboard():
        """Create the location choice keyboard"""
        keyboard = [
            [InlineKeyboardButton("Rome Resident 🏛", callback_data='rome_resident')],
            [InlineKeyboardButton("Outside Rome 🌍", callback_data='outside_rome')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_reminder_keyboard():
        """Create the reminder preference keyboard"""
        keyboard = [
            [InlineKeyboardButton("5 days before", callback_data='reminder_5')],
            [InlineKeyboardButton("2 days before", callback_data='reminder_2')],
            [InlineKeyboardButton("Both", callback_data='reminder_both')],
            [InlineKeyboardButton("No reminders", callback_data='reminder_none')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_privacy_settings_keyboard(current_choices):
        """Create the privacy settings keyboard with current choices"""
        keyboard = [
            [InlineKeyboardButton(
                f"Share contacts for car sharing: {'✅' if current_choices.get('car_sharing_consent') else '❌'}",
                callback_data='privacy_carsharing'
            )],
            [InlineKeyboardButton(
                f"Photo sharing: {'✅' if current_choices.get('photo_consent') else '❌'}",
                callback_data='privacy_photos'
            )],
            [InlineKeyboardButton(
                f"Marketing communications: {'✅' if current_choices.get('marketing_consent') else '❌'}",
                callback_data='privacy_marketing'
            )],
            [InlineKeyboardButton("💾 Save preferences", callback_data='privacy_save')],
            [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_equipment_keyboard():
        """Create the equipment choice keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data='yes_eq'),
                InlineKeyboardButton("No ❌", callback_data='no_eq')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_car_share_keyboard():
        """Create the car sharing choice keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data='yes_car'),
                InlineKeyboardButton("No ❌", callback_data='no_car')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_hike_navigation_keyboard(current_index, total_hikes):
        """Create navigation keyboard for viewing user's hikes"""
        keyboard = []
        
        # Previous/Next buttons
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data='prev_hike'))
        if current_index < total_hikes - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data='next_hike'))
        if nav_buttons:
            keyboard.append(nav_buttons)

        # Cancel registration button
        keyboard.append([
            InlineKeyboardButton("❌ Cancel registration", callback_data=f'cancel_hike_{current_index}')
        ])

        # Back to menu button
        keyboard.append([InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')])
        
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_final_notes_keyboard():
        """Create keyboard for final registration confirmation"""
        keyboard = [
            [
                InlineKeyboardButton("Accept ✅", callback_data='accept'),
                InlineKeyboardButton("Reject ❌", callback_data='reject')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_municipi_keyboard(municipi):
        """Create keyboard for selecting a municipio"""
        keyboard = []
        for municipio in municipi:
            keyboard.append([
                InlineKeyboardButton(f"Municipio {municipio}", callback_data=f'mun_{municipio}')
            ])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_quartiere_keyboard(quartieri, show_back=True):
        """Create keyboard for selecting a quartiere"""
        keyboard = []
        for quartiere in quartieri:
            keyboard.append([InlineKeyboardButton(quartiere, callback_data=f'q_{quartiere}')])
        
        keyboard.append([InlineKeyboardButton("Other area in this municipio", callback_data='other_area')])
        if show_back:
            keyboard.append([InlineKeyboardButton("🔙 Back to municipi", callback_data='back_municipi')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_hikes_selection_keyboard(hikes, selected_indices=None):
        """Create keyboard for selecting hikes to register for"""
        if selected_indices is None:
            selected_indices = []
            
        keyboard = []
        
        for idx, hike in enumerate(hikes):
            available_spots = hike['max_participants'] - hike['current_participants']
            hike_date = datetime.strptime(hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
            
            # Determine availability indicator
            if available_spots > 1:
                spot_indicator = "🟢"
            elif available_spots == 1:
                spot_indicator = "🔴"
            else:
                spot_indicator = "⚫"
            
            # First row: date with availability indicator
            keyboard.append([
                InlineKeyboardButton(
                    f"🗓 {hike_date} - {spot_indicator} {available_spots}/{hike['max_participants']}",
                    callback_data=f'info_hike{idx}_date'
                )
            ])
            
            # Second row: hike name and selection button (if spots available)
            if available_spots > 0:
                is_selected = idx in selected_indices
                select_emoji = "☑️" if is_selected else "⬜"
                keyboard.append([
                    InlineKeyboardButton(
                        f"{select_emoji} {hike['hike_name']}",
                        callback_data=f'select_hike{idx}'
                    )
                ])
            else:
                # If no spots, show just the name without selection possibility
                keyboard.append([
                    InlineKeyboardButton(
                        f"⚫ {hike['hike_name']}",
                        callback_data='ignore'
                    )
                ])
            
            # Separator between hikes
            if idx < len(hikes) - 1:
                keyboard.append([InlineKeyboardButton("┄┄┄┄┄┄┄", callback_data='ignore')])
        
        # Confirmation button at the end
        keyboard.append([InlineKeyboardButton("✅ Confirm selection", callback_data='confirm_hikes')])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_admin_hikes_keyboard(hikes):
        """Create keyboard for admin to manage hikes"""
        keyboard = []
        
        # First add active hikes
        active_hikes = [h for h in hikes if h.get('is_active') == 1]
        for hike in active_hikes:
            hike_date = datetime.strptime(hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
            spots_left = hike['max_participants'] - hike['current_participants']
            
            keyboard.append([
                InlineKeyboardButton(
                    f"🟢 {hike_date} - {hike['hike_name']} ({spots_left} spots left)",
                    callback_data=f"admin_hike_{hike['id']}"
                )
            ])
        
        # Then add inactive/cancelled hikes
        inactive_hikes = [h for h in hikes if h.get('is_active') == 0]
        for hike in inactive_hikes:
            hike_date = datetime.strptime(hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
            
            keyboard.append([
                InlineKeyboardButton(
                    f"🔴 {hike_date} - {hike['hike_name']} (cancelled)",
                    callback_data=f"admin_hike_{hike['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_admin_hike_options_keyboard(hike_id, is_active):
        """Create keyboard for admin options for a specific hike"""
        keyboard = [
            [InlineKeyboardButton("👥 View participants", callback_data=f'admin_participants_{hike_id}')],
            [InlineKeyboardButton("💰 Edit cost settings", callback_data=f'admin_edit_costs_{hike_id}')]
        ]
        
        # Show edit and cancel options only for active hikes
        if is_active:
            keyboard.append([InlineKeyboardButton("❌ Cancel hike", callback_data=f'admin_cancel_{hike_id}')])
        else:
            # For cancelled hikes, maybe add a reactivate option
            keyboard.append([InlineKeyboardButton("🔄 Reactivate hike", callback_data=f'admin_reactivate_{hike_id}')])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to hikes", callback_data='admin_manage_hikes')])
        
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_difficulty_keyboard():
        """Create keyboard for selecting hike difficulty"""
        difficulties = ["Easy", "Moderate", "Challenging", "Hard"]
        keyboard = []
        
        for difficulty in difficulties:
            keyboard.append([
                InlineKeyboardButton(difficulty, callback_data=f'difficulty_{difficulty.lower()}')
            ])
        
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_maintenance_keyboard(schedules=None):
        """Create keyboard for maintenance management"""
        keyboard = []
        
        # Add existing maintenance schedules if any
        if schedules:
            for schedule in schedules:
                m_date = schedule['maintenance_date']
                if isinstance(m_date, str):
                    m_date = datetime.strptime(m_date, '%Y-%m-%d').strftime('%d/%m/%Y')
                
                start = schedule['start_time']
                if isinstance(start, str):
                    start = start.split('.')[0]  # Remove microseconds if present
                    
                end = schedule['end_time']
                if isinstance(end, str):
                    end = end.split('.')[0]  # Remove microseconds if present
                    
                keyboard.append([
                    InlineKeyboardButton(
                        f"📅 {m_date}: {start}-{end}",
                        callback_data=f"edit_maintenance_{schedule['id']}"
                    )
                ])
        
        # Add buttons for adding new maintenance or returning
        keyboard.append([InlineKeyboardButton("➕ Schedule new maintenance", callback_data='add_maintenance')])
        keyboard.append([InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_maintenance_actions_keyboard(maintenance_id):
        """Create keyboard for specific maintenance actions"""
        keyboard = [
            [InlineKeyboardButton("📝 Edit date", callback_data=f'maintenance_edit_date_{maintenance_id}')],
            [InlineKeyboardButton("⏰ Edit time", callback_data=f'maintenance_edit_time_{maintenance_id}')],
            [InlineKeyboardButton("🗒 Edit reason", callback_data=f'maintenance_edit_reason_{maintenance_id}')],
            [InlineKeyboardButton("❌ Delete", callback_data=f'maintenance_delete_{maintenance_id}')],
            [InlineKeyboardButton("🔙 Back to maintenance list", callback_data='admin_maintenance')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_cost_control_keyboard(costs=None):
        """Create keyboard for cost control management"""
        keyboard = []
        
        # Add existing costs if any
        if costs:
            for cost in costs:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{cost['name']} - {cost['amount']}€ ({cost['frequency']})",
                        callback_data=f"edit_cost_{cost['id']}"
                    )
                ])
        
        # Add buttons for adding new cost or returning
        keyboard.append([InlineKeyboardButton("➕ Add new fixed cost", callback_data='add_cost')])
        keyboard.append([InlineKeyboardButton("📊 View cost summary", callback_data='cost_summary')])
        keyboard.append([InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_cost_actions_keyboard(cost_id):
        """Create keyboard for specific cost actions"""
        keyboard = [
            [InlineKeyboardButton("📝 Edit name", callback_data=f'cost_edit_name_{cost_id}')],
            [InlineKeyboardButton("💰 Edit amount", callback_data=f'cost_edit_amount_{cost_id}')],
            [InlineKeyboardButton("🔄 Edit frequency", callback_data=f'cost_edit_frequency_{cost_id}')],
            [InlineKeyboardButton("🗒 Edit description", callback_data=f'cost_edit_description_{cost_id}')],
            [InlineKeyboardButton("❌ Delete", callback_data=f'cost_delete_{cost_id}')],
            [InlineKeyboardButton("🔙 Back to cost list", callback_data='admin_costs')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_frequency_keyboard(cost_id):
        """Create keyboard for selecting cost frequency"""
        frequencies = ["Monthly", "Quarterly", "Yearly"]
        keyboard = []
        
        for frequency in frequencies:
            keyboard.append([
                InlineKeyboardButton(
                    frequency, 
                    callback_data=f'frequency_{frequency.lower()}_{cost_id}'
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data=f'edit_cost_{cost_id}')])
        
        return InlineKeyboardMarkup(keyboard)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

class KeyboardBuilder:
    @staticmethod
    def create_menu_keyboard():
        """Create the main menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("Sign up for hike 🏃", callback_data='signup')],
            [InlineKeyboardButton("My Hikes 🎒", callback_data='myhikes')],
            [InlineKeyboardButton("Useful links 🔗", callback_data='links')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_admin_keyboard():
        """Create the admin menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("Create new hike 🏔️", callback_data='admin_create_hike')],
            [InlineKeyboardButton("Manage existing hikes 📝", callback_data='admin_manage_hikes')],
            [InlineKeyboardButton("View participants 👥", callback_data='admin_view_participants')],
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
        
        for hike in hikes:
            hike_date = datetime.strptime(hike['hike_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
            spots_left = hike['max_participants'] - hike['current_participants']
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{hike_date} - {hike['hike_name']} ({spots_left} spots left)",
                    callback_data=f"admin_hike_{hike['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to admin menu", callback_data='back_to_admin')])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_admin_hike_options_keyboard(hike_id):
        """Create keyboard for admin options for a specific hike"""
        keyboard = [
            [InlineKeyboardButton("✏️ Edit details", callback_data=f'admin_edit_{hike_id}')],
            [InlineKeyboardButton("👥 View participants", callback_data=f'admin_participants_{hike_id}')],
            [InlineKeyboardButton("❌ Cancel hike", callback_data=f'admin_cancel_{hike_id}')],
            [InlineKeyboardButton("🔙 Back to hikes", callback_data='admin_manage_hikes')]
        ]
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

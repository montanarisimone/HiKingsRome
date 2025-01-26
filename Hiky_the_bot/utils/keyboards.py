from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class KeyboardBuilder:
    @staticmethod
    def create_menu_keyboard():
        """Crea la keyboard del menu principale"""
        keyboard = [
            [InlineKeyboardButton("Sign up for hike 🏃", callback_data='signup')],
            [InlineKeyboardButton("My Hikes 🎒", callback_data='myhikes')],
            [InlineKeyboardButton("Useful links 🔗", callback_data='links')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_yes_no_keyboard(yes_callback, no_callback):
        """Crea una keyboard generica Yes/No"""
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data=yes_callback),
                InlineKeyboardButton("No ❌", callback_data=no_callback)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_back_to_menu_keyboard():
        """Crea una keyboard con solo il bottone back to menu"""
        keyboard = [[InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_links_keyboard():
        """Crea la keyboard per i link utili"""
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
        """Crea la keyboard per la scelta della location"""
        keyboard = [
            [InlineKeyboardButton("Rome Resident 🏛", callback_data='rome_resident')],
            [InlineKeyboardButton("Outside Rome 🌍", callback_data='outside_rome')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_reminder_keyboard():
        """Crea la keyboard per i reminder"""
        keyboard = [
            [InlineKeyboardButton("7 days before", callback_data='reminder_7')],
            [InlineKeyboardButton("3 days before", callback_data='reminder_3')],
            [InlineKeyboardButton("Both", callback_data='reminder_both')],
            [InlineKeyboardButton("No reminders", callback_data='reminder_none')]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_privacy_initial_keyboard(has_record=False):
        """Crea la keyboard iniziale per la privacy"""
        if has_record:
            keyboard = [
                [InlineKeyboardButton("✏️ Modify settings", callback_data='privacy_modify')],
                [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("📜 View full policy", url="https://www.hikingsrome.com/privacy")],
                [InlineKeyboardButton("✅ Set privacy preferences", callback_data='privacy_start')]
            ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_equipment_keyboard():
        """Crea la keyboard per la scelta dell'equipment"""
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data='yes_eq'),
                InlineKeyboardButton("No ❌", callback_data='no_eq')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_car_share_keyboard():
        """Crea la keyboard per la scelta del car sharing"""
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data='yes_car'),
                InlineKeyboardButton("No ❌", callback_data='no_car')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_hike_navigation_keyboard(current_index, total_hikes):
        """Crea la keyboard per la navigazione degli hike"""
        keyboard = []
        
        # Bottoni precedente/successivo
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data='prev_hike'))
        if current_index < total_hikes - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data='next_hike'))
        if nav_buttons:
            keyboard.append(nav_buttons)

        # Bottone per la cancellazione
        keyboard.append([InlineKeyboardButton("❌ Cancel registration", 
                                            callback_data=f'cancel_hike_{current_index}')])

        # Bottone per tornare al menu
        keyboard.append([InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')])
        
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_final_notes_keyboard():
        """Crea la keyboard per le note finali"""
        keyboard = [
            [
                InlineKeyboardButton("Accept ✅", callback_data='accept'),
                InlineKeyboardButton("Reject ❌", callback_data='reject')
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_municipi_keyboard(municipi):
        """Crea la keyboard per la selezione del municipio"""
        keyboard = []
        for municipio in municipi:
            keyboard.append([InlineKeyboardButton(
                f"Municipio {municipio}", 
                callback_data=f'mun_{municipio}'
            )])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def create_quartiere_keyboard(quartieri, show_back=True):
         """Crea la keyboard per la selezione del quartiere"""
         keyboard = []
         for quartiere in quartieri:
             keyboard.append([InlineKeyboardButton(quartiere, callback_data=f'q_{quartiere}')])
          
         keyboard.append([InlineKeyboardButton("Other area in this municipio", callback_data='other_area')])
         if show_back:
             keyboard.append([InlineKeyboardButton("🔙 Back to municipi", callback_data='back_municipi')])
         
         return InlineKeyboardMarkup(keyboard)

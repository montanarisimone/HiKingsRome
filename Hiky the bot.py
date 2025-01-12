!pip install python-telegram-bot==13.7
!pip install gspread oauth2client
!pip install pytz

## PARTE 1 - IMPORT E SETUP INIZIALE
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, timedelta
from calendar import monthcalendar, month_name
import pytz

# Stati della conversazione
(CHOOSING, NAME, EMAIL, PHONE, BIRTH_DATE, MEDICAL, HIKE_CHOICE, EQUIPMENT, 
 CAR_SHARE, MUNICIPIO, ELSEWHERE, NOTES, IMPORTANT_NOTES) = range(13)

# Definisci il fuso orario di Roma
rome_tz = pytz.timezone('Europe/Rome')

# Funzioni utilità
def setup_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)
    
    # Open both sheets
    sheet_responses = client.open_by_key('[INSERT GOOGLE SHEET ID]').worksheet('Registrazioni')
    sheet_hikes = client.open_by_key('[INSERT GOOGLE SHEET ID]').worksheet('ProssimeUscite')
    return sheet_responses, sheet_hikes

def get_available_hikes(sheet_hikes, sheet_responses, user_id=None):
    """Gets available hikes from ProssimeUscite sheet and counts current participants"""
    # Leggi tutti gli hike
    hikes_data = sheet_hikes.get_all_records()
    
    # Leggi tutte le registrazioni per contare i partecipanti
    registrations = sheet_responses.get_all_records(expected_headers=[
        'Timestamp_risposte',
        'Telegram_ID',
        'Name and surname',
        'Email',
        'Phone number',
        'Birth date',
        'Medical conditions',
        'Choose the hike',
        'Do you have all the necessary equipment?',
        'Do you have a car you can share?',
        'What municipio do you live in?',
        'Something important we need to know?'
    ])
    
    # Conta i partecipanti per ogni hike
    participants_count = {}
    user_bookings = set()

    for registration in registrations:
        hikes = registration.get('Choose the hike', '').split('; ')
        # Se è una registrazione dell'utente corrente, salva gli hike prenotati
        if user_id and str(registration['Telegram_ID']) == str(user_id):
            user_bookings.update(hikes)

        for hike in hikes:
            if hike:  # Ignora stringhe vuote
                participants_count[hike] = participants_count.get(hike, 0) + 1
    
    # Today's date and 2 months limit
    today = datetime.now(rome_tz).date()
    min_date = today + timedelta(days=2)
    max_date = today + timedelta(days=60)
    
    available_hikes = []
    
    for hike in hikes_data:
        # Convert date string to date object
        hike_date = datetime.strptime(hike['data'], '%d/%m/%Y').date()
        
        # Check if hike is within valid date range
        if min_date <= hike_date <= max_date:
            hike_identifier = f"{hike_date.strftime('%d/%m/%Y')} - {hike['hike']}"

            # Aggiungi l'hike solo se non è già stato prenotato dall'utente
            if not user_id or hike_identifier not in user_bookings:
                available_hikes.append({
                    'date': hike_date,
                    'name': hike['hike'],
                    'max_participants': int(hike['max_partecipanti']),
                    'current_participants': participants_count.get(hike_identifier, 0)
                })
    
    # Sort by date
    return sorted(available_hikes, key=lambda x: x['date'])

def create_hikes_keyboard(hikes, context):
    """Creates keyboard with available hikes"""
    keyboard = []
    
    for idx, hike in enumerate(hikes):
        available_spots = hike['max_participants'] - hike['current_participants']
        date_str = hike['date'].strftime('%d/%m/%Y')
        
        # Prima riga: solo la data
        keyboard.append([InlineKeyboardButton(
            f"🗓 {date_str}",
            callback_data=f'info_hike{idx}_date'
        )])
        
        # Seconda riga: nome dell'hike
        keyboard.append([InlineKeyboardButton(
            f"🏃 {hike['name']}",
            callback_data=f'info_hike{idx}_name'
        )])
        
        # Terza riga: posti disponibili
        if available_spots > 1:
            spots_text = f"🟢 {available_spots}/{hike['max_participants']} spots available"
        elif available_spots == 1:
            spots_text = f"🔴 Last spot available!"
        else:
            spots_text = "⚫ Fully booked"
        
        keyboard.append([InlineKeyboardButton(
            spots_text,
            callback_data=f'info_hike{idx}_spots'
        )])
        
        # Quarta riga: bottone di selezione (solo se ci sono posti disponibili)
        if available_spots > 0:
            select_text = "✓ Select" if idx not in context.user_data.get('selected_hikes', []) else "✓ Selected!"
            keyboard.append([InlineKeyboardButton(select_text, callback_data=f'select_hike{idx}')])
        
        # Separatore tra gli hike
        if idx < len(hikes) - 1:
            keyboard.append([InlineKeyboardButton("─────────", callback_data='ignore')])
    
    # Bottone di conferma alla fine
    keyboard.append([InlineKeyboardButton("✅ Confirm selection", callback_data='confirm_hikes')])
    return InlineKeyboardMarkup(keyboard)

def create_year_selector():
    current_year = date.today().year
    keyboard = []
    decades = list(range(1980, current_year, 10))
    for i in range(0, len(decades), 2):
        row = []
        for year in decades[i:i+2]:
            row.append(InlineKeyboardButton(
                f"{year}s", 
                callback_data=f'decade_{year}'
            ))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def create_year_buttons(decade):
    keyboard = []
    years = list(range(decade, decade + 10))
    for i in range(0, len(years), 3):
        row = []
        for year in years[i:i+3]:
            row.append(InlineKeyboardButton(
                str(year), 
                callback_data=f'year_{year}'
            ))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def create_month_buttons(year):
    keyboard = []
    for i in range(1, 13, 3):
        row = []
        for month in range(i, min(i + 3, 13)):
            row.append(InlineKeyboardButton(
                month_name[month], 
                callback_data=f'month_{year}_{month}'
            ))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def create_calendar(year, month):
    keyboard = []
    
    keyboard.append([
        InlineKeyboardButton("<<", callback_data=f'year_{year-1}_{month}'),
        InlineKeyboardButton(f"{year}", callback_data=f'ignore'),
        InlineKeyboardButton(">>", callback_data=f'year_{year+1}_{month}')
    ])
    
    keyboard.append([
        InlineKeyboardButton("<<", callback_data=f'month_{year}_{month-1}'),
        InlineKeyboardButton(f"{month_name[month]}", callback_data=f'ignore'),
        InlineKeyboardButton(">>", callback_data=f'month_{year}_{month+1}')
    ])
    
    keyboard.append([
        InlineKeyboardButton(day, callback_data='ignore') 
        for day in ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
    ])
    
    for week in monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data='ignore'))
            else:
                row.append(InlineKeyboardButton(
                    str(day), 
                    callback_data=f'date_{year}_{month}_{day}'
                ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

## PARTE 2 - Funzioni menu principale
def start(update, context):
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("Sign up for hike 🏃", callback_data='signup')],
        [InlineKeyboardButton("My Hikes 🎒", callback_data='myhikes')],
        [InlineKeyboardButton("Useful links 🔗", callback_data='links')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "Hi, I'm Hiky and I'll help you interact with @hikingsrome.\n"
        "How can I assist you?",
        reply_markup=reply_markup
    )
    return CHOOSING

def check_future_hikes_availability(query, context, user_id):
    """
    Controlla la disponibilità di hike futuri per l'utente.
    Restituisce:
    - None se non ci sono hike futuri o se l'utente è già registrato a tutti
    - La lista degli hike disponibili altrimenti
    """
    # Get available hikes with user_id per filtrare gli hike già prenotati
    available_hikes = get_available_hikes(
        context.bot_data['sheet_hikes'],
        context.bot_data['sheet_responses'],
        user_id
    )
    
    if not available_hikes:
        query.edit_message_text(
            "There are no available hikes at the moment.\n"
            "Use /start to go back to the home menu."
        )
        return None
    
    return available_hikes

def handle_menu_choice(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'signup':
        # Controlla disponibilità hike prima di iniziare il questionario
        available_hikes = check_future_hikes_availability(query, context, query.from_user.id)
        if not available_hikes:
            return CHOOSING
        
        # Salva gli hike disponibili per usarli più tardi
        context.user_data['available_hikes'] = available_hikes
        query.edit_message_text("👋 Name and surname?")
        return NAME

    elif query.data == 'myhikes':
        return show_my_hikes(query, context)
    elif query.data == 'links':
        keyboard = [
            [InlineKeyboardButton("🌐 Website", url="https://www.hikingsrome.com/")],
            [InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/hikingsrome/")],
            [InlineKeyboardButton("💬 Telegram Group", url="https://t.me/+dku6thBDTGM0MWZk")],
            [InlineKeyboardButton("🗺 Komoot", url="https://www.komoot.com/it-it/user/3261856743261")],
            [InlineKeyboardButton("💲 PayPal", url="https://paypal.me/hikingsrome?country.x=IT&locale.x=it_IT")],
            [InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "Here are some useful links:",
            reply_markup=reply_markup
        )
        return CHOOSING
    elif query.data == 'back_to_menu':
        keyboard = [
            [InlineKeyboardButton("Sign up for hike 🏃", callback_data='signup')],
            [InlineKeyboardButton("My Hikes 🎒", callback_data='myhikes')],
            [InlineKeyboardButton("Useful links 🔗", callback_data='links')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "Hi, I'm Hiky and I'll help you interact with @hikingsrome.\n"
            "How can I assist you?",
            reply_markup=reply_markup
        )
        return CHOOSING


## PARTE 3 - Funzioni gestione hike prenotati
def get_user_hikes(sheet_responses, user_id):
    """Get all future hikes for a specific user"""
    registrations = sheet_responses.get_all_records()
    user_hikes = []
    today = datetime.now(rome_tz).date()
    
    for reg in registrations:
        if str(reg['Telegram_ID']) == str(user_id):
            hikes = reg['Choose the hike'].split('; ')
            car_shared = reg['Do you have a car you can share?']
            for hike in hikes:
                if hike:  # ignora stringhe vuote
                    date_str, name = hike.split(' - ', 1)
                    hike_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    # Aggiungi solo gli hike futuri
                    if hike_date >= today:
                        user_hikes.append({
                            'date': hike_date,
                            'name': name,
                            'car_shared': car_shared
                        })
    
    # Ordina per data
    return sorted(user_hikes, key=lambda x: x['date'])

def show_my_hikes(update, context):
    """Handle both direct commands and callback queries"""
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id  # Per callback query
        message = update.message
    else:
        user_id = update.message.from_user.id  # Per comando diretto
        message = update.message

    hikes = get_user_hikes(context.bot_data['sheet_responses'], user_id)
    
    if not hikes:
        message.reply_text(
            "You are not registered for any hikes yet.\n"
            "Use /start to go back to the home menu."
        )
        return ConversationHandler.END
    
    context.user_data['my_hikes'] = hikes
    context.user_data['current_hike_index'] = 0
    
    return show_hike_details(update, context)

def handle_hike_navigation(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'next_hike':
        context.user_data['current_hike_index'] += 1
    elif query.data == 'prev_hike':
        context.user_data['current_hike_index'] -= 1
    
    return show_hike_details(query, context)

def show_hike_details(update, context):
    hikes = context.user_data['my_hikes']
    current_index = context.user_data['current_hike_index']
    hike = hikes[current_index]
    
    # Prepara i bottoni di navigazione
    keyboard = []
    
    # Bottoni precedente/successivo
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data='prev_hike'))
    if current_index < len(hikes) - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data='next_hike'))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Bottone per tornare al menu
    keyboard.append([InlineKeyboardButton("🔙 Back to menu", callback_data='back_to_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Prepara il messaggio
    message_text = (
        f"🗓 *Date:* {hike['date'].strftime('%d/%m/%Y')}\n"
        f"🏃 *Hike:* {hike['name']}\n"
        f"🚗 *Car sharing:* {hike['car_shared']}\n\n"
        f"Hike {current_index + 1} of {len(hikes)}"
    )
    
    if isinstance(update, CallbackQuery):
        update.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return CHOOSING

## PARTE 4 - Gestione delle domande del questionario
def handle_invalid_message(update, context):
    keyboard = [
        [
            InlineKeyboardButton("Yes ✅", callback_data='restart_yes'),
            InlineKeyboardButton("No ❌", callback_data='restart_no')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "❓ Do you want to start a new form?",
        reply_markup=reply_markup
    )

def handle_restart_choice(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'restart_yes':
        context.user_data.clear()
        query.message.reply_text("👋 Name and surname?")
        return NAME
    else:
        query.edit_message_text(
            "ℹ️ If you need help, send a message in the telegram group or send an email to hikingsrome@gmail.com"
        )
        return ConversationHandler.END

def save_name(update, context):
    context.user_data['name'] = update.message.text
    update.message.reply_text("📧 Email?")
    return EMAIL

def save_email(update, context):
    context.user_data['email'] = update.message.text
    update.message.reply_text("📱 Phone number?")
    return PHONE

def save_phone(update, context):
    context.user_data['phone'] = update.message.text
    update.message.reply_text(
        "📅 Select the decade of your birth year:",
        reply_markup=create_year_selector()
    )
    return BIRTH_DATE

def handle_calendar(update, context):
    query = update.callback_query
    query.answer()
    
    data = query.data.split('_')
    action = data[0]
    
    if action == 'decade':
        decade = int(data[1])
        query.edit_message_text(
            "📅 Select your birth year:",
            reply_markup=create_year_buttons(decade)
        )
        return BIRTH_DATE
        
    elif action == 'year':
        year = int(data[1])
        context.user_data['birth_year'] = year
        query.edit_message_text(
            "📅 Select birth month:",
            reply_markup=create_month_buttons(year)
        )
        return BIRTH_DATE
        
    elif action == 'month':
        year = int(data[1])
        month = int(data[2])
        query.edit_message_text(
            "📅 Select birth day:",
            reply_markup=create_calendar(year, month)
        )
        return BIRTH_DATE
        
    elif action == 'date':
        year = int(data[1])
        month = int(data[2])
        day = int(data[3])
        
        selected_date = f"{day:02d}/{month:02d}/{year}"
        context.user_data['birth_date'] = selected_date
        
        query.edit_message_text(f"📅 Selected birth date: {selected_date}")
        
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🏥 Medical conditions\n"
                 "_Do you have any medical conditions that might create difficulties for you "
                 "(Knee pain, cardiopathy, allergies etc.)?_",
            parse_mode='Markdown'
        )
        return MEDICAL

## PARTE 5 - Gestione delle risposte e selezione hike
def save_medical(update, context):
    context.user_data['medical'] = update.message.text
    context.user_data['selected_hikes'] = []

    # Gli hike disponibili sono già stati salvati in context.user_data['available_hikes']
    available_hikes = context.user_data['available_hikes']
    reply_markup = create_hikes_keyboard(available_hikes, context)
    
    update.message.reply_text(
        "🎯 Choose the hike(s) you want to participate in.\n"
        "Click to select/deselect a hike.\n"
        "Click '✅ Confirm selection' when done.",
        reply_markup=reply_markup
    )
    return HIKE_CHOICE

def handle_hike(update, context):
    query = update.callback_query
    query.answer()
    
    # Ignora i click sulle righe informative e sul separatore
    if query.data.startswith('info_hike') or query.data == 'ignore':
        return HIKE_CHOICE
    
    if query.data.startswith('select_hike'):
        hike_idx = int(query.data.replace('select_hike', ''))
        selected_hikes = context.user_data.get('selected_hikes', [])
        available_hikes = context.user_data['available_hikes']
        
        if hike_idx in selected_hikes:
            selected_hikes.remove(hike_idx)
            query.answer("Hike deselected")
        else:
            selected_hikes.append(hike_idx)
            query.answer("Hike selected")
            
        context.user_data['selected_hikes'] = selected_hikes
        
        # Aggiorna la keyboard con le nuove selezioni
        reply_markup = create_hikes_keyboard(available_hikes, context)
        query.edit_message_reply_markup(reply_markup=reply_markup)
        return HIKE_CHOICE
        
    elif query.data == 'confirm_hikes':
        selected_hikes = context.user_data.get('selected_hikes', [])
        if not selected_hikes:
            query.answer("❗ Please select at least one hike!", show_alert=True)
            return HIKE_CHOICE
        
        # Store selected hikes details
        available_hikes = context.user_data['available_hikes']
        context.user_data['selected_hikes_details'] = [
            available_hikes[idx] for idx in selected_hikes
        ]
        
        # Next question
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data='yes_eq'),
                InlineKeyboardButton("No ❌", callback_data='no_eq')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🎒 Do you have all the necessary equipment?\n"
                 "_You can find the required equipment on the hike webpage.\n"
                 "Remember, you could be excluded on the day of the event if you do not "
                 "meet the required equipment standards._",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return EQUIPMENT

## PARTE 6 - Gestione delle domande finali e salvataggio
def handle_equipment(update, context):
    query = update.callback_query
    query.answer()
    
    context.user_data['equipment'] = 'Yes' if query.data == 'yes_eq' else 'No'
    
    keyboard = [
        [
            InlineKeyboardButton("Yes ✅", callback_data='yes_car'),
            InlineKeyboardButton("No ❌", callback_data='no_car')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="🚗 Do you have a car you can share?\n"
             "_Don't worry, we will share tolls and fuel. Let us know seats number "
             "in the notes section at the bottom of the form._",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return CAR_SHARE

def handle_car_share(update, context):
    query = update.callback_query
    query.answer()
    
    context.user_data['car_share'] = 'Yes' if query.data == 'yes_car' else 'No'
    
    keyboard = []
    for i in range(1, 16):
        keyboard.append([InlineKeyboardButton(f"Municipio {i}", callback_data=f'mun_{i}')])
    keyboard.append([InlineKeyboardButton("Elsewhere 🌍", callback_data='elsewhere')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📍 What *municipio* do you live in?\n"
             "_We need this information to better organise transport sharing_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return MUNICIPIO

def handle_municipio(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'elsewhere':
        query.edit_message_text("🌍 Where?")
        return ELSEWHERE
    
    context.user_data['municipio'] = query.data
    return ask_notes(update, context, query.message.chat_id)

def handle_elsewhere(update, context):
    context.user_data['municipio'] = f"Elsewhere - {update.message.text}"
    return ask_notes(update, context, update.message.chat_id)

def ask_notes(update, context, chat_id):
    context.bot.send_message(
        chat_id=chat_id,
        text="📝 Something important we need to know?\n"
             "_Whatever you want to tell us. If you share the car, remember the number of available seats._",
        parse_mode='Markdown'
    )
    return NOTES

## PARTE 7 - Funzioni finali e main()
def save_notes(update, context):
    context.user_data['notes'] = update.message.text
    
    keyboard = [
        [
            InlineKeyboardButton("Accept ✅", callback_data='accept'),
            InlineKeyboardButton("Reject ❌", callback_data='reject')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "⚠️ *IMPORTANT NOTES*\n"
        "Please note that you may be excluded from the event if all available spots are taken.\n"
        "Additionally, you could be excluded on the day of the event if you do not meet the required equipment standards.\n"
        "It's essential to ensure you have all necessary gear to participate in the hike safely.\n"
        "For any information, please contact us at hikingsrome@gmail.com",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return IMPORTANT_NOTES

def handle_final_choice(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'accept':
        # Get fresh count of participants before saving
        available_hikes = get_available_hikes(
            context.bot_data['sheet_hikes'],
            context.bot_data['sheet_responses']
        )
        
        # Check if selected hikes are still available
        selected_hikes = context.user_data.get('selected_hikes_details', [])
        for selected_hike in selected_hikes:
            for available_hike in available_hikes:
                if (selected_hike['date'] == available_hike['date'] and 
                    selected_hike['name'] == available_hike['name']):
                    if available_hike['current_participants'] >= available_hike['max_participants']:
                        query.edit_message_text(
                            f"❌ Sorry, the hike {selected_hike['name']} is now full.\n"
                            "Please start again and choose another hike.\n"
                            "Use /start to fill out the form again"
                        )
                        return ConversationHandler.END

        # Save to Google Sheets
        sheet_responses = context.bot_data['sheet_responses']
        data = context.user_data
        timestamp = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
        telegram_id = str(query.from_user.id)  # Aggiungo l'ID Telegram
        
        # Format selected hikes for saving
        hikes_text = '; '.join([
            f"{hike['date'].strftime('%d/%m/%Y')} - {hike['name']}"
            for hike in selected_hikes
        ])
        
        # Save to sheet
        sheet_responses.append_row([
            timestamp,  # Timestamp_risposte
            telegram_id,
            data.get('name', ''),  # Name and surname
            data.get('email', ''),  # Email
            data.get('phone', ''),  # Phone number
            data.get('birth_date', ''),  # Birth date
            data.get('medical', ''),  # Medical conditions
            hikes_text,  # Choose the hike
            data.get('equipment', ''),  # Do you have all the necessary equipment?
            data.get('car_share', ''),  # Do you have a car you can share?
            data.get('municipio', ''),  # What municipio do you live in?
            data.get('notes', '')  # Something important we need to know?
        ])
        
        query.edit_message_text(
            "✅ Thanks for signing up for the next hike.\n"
            "You can use /start to go back to the home menu."
        )
    else:
        query.edit_message_text(
            "❌ We are sorry but accepting these rules is necessary to participate in the walks.\n"
            "Thank you for your time.\n"
            "You can use /start to go back to the home menu."
        )
    
    return ConversationHandler.END

def cancel(update, context):
    context.user_data.clear()
    update.message.reply_text(
        '❌ Registration cancelled.\n'
        'You can use /start to go back to the home menu.'
    )
    return ConversationHandler.END

def main():
    TOKEN = '[INSERT_YOUR_TOKEN]'
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Setup sheets
    sheet_responses, sheet_hikes = setup_google_sheets()
    dp.bot_data['sheet_responses'] = sheet_responses
    dp.bot_data['sheet_hikes'] = sheet_hikes
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(Filters.text & ~Filters.command, handle_invalid_message),
            CallbackQueryHandler(handle_restart_choice, pattern='^restart_')
        ],
        states={
            CHOOSING: [
                CommandHandler('start', start),
                CallbackQueryHandler(handle_menu_choice, pattern='^(signup|myhikes|links|back_to_menu)$'),
                CallbackQueryHandler(handle_hike_navigation, pattern='^(prev_hike|next_hike)$')
            ],
            NAME: [
                CommandHandler('start', start),
                MessageHandler(Filters.text & ~Filters.command, save_name)
            ],
            EMAIL: [
                CommandHandler('start', start),
                MessageHandler(Filters.text & ~Filters.command, save_email)
            ],
            PHONE: [
                CommandHandler('start', start),
                MessageHandler(Filters.text & ~Filters.command, save_phone)
            ],
            BIRTH_DATE: [
                CommandHandler('start', start),
                CallbackQueryHandler(handle_calendar)
            ],
            MEDICAL: [
                CommandHandler('start', start),
                MessageHandler(Filters.text & ~Filters.command, save_medical)
            ],
            HIKE_CHOICE: [
                CommandHandler('start', start),
                CallbackQueryHandler(handle_hike)
            ],
            EQUIPMENT: [
                CommandHandler('start', start),
                CallbackQueryHandler(handle_equipment)
            ],
            CAR_SHARE: [
                CommandHandler('start', start),
                CallbackQueryHandler(handle_car_share)
            ],
            MUNICIPIO: [
                CommandHandler('start', start),
                CallbackQueryHandler(handle_municipio)
            ],
            ELSEWHERE: [
                CommandHandler('start', start),
                MessageHandler(Filters.text & ~Filters.command, handle_elsewhere)
            ],
            NOTES: [
                CommandHandler('start', start),
                MessageHandler(Filters.text & ~Filters.command, save_notes)
            ],
            IMPORTANT_NOTES: [
                CommandHandler('start', start),
                CallbackQueryHandler(handle_final_choice)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    dp.add_handler(conv_handler)
    
    updater.start_polling()
    
    try:
        print("🚀 Bot started! Press CTRL+C to stop.")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Bot stopped!")
        updater.stop()

if __name__ == '__main__':
    main()

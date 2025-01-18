## PARTE 1 - IMPORT E SETUP INIZIALE
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, timedelta
from datetime import time as datetime_time  # Rinominato per evitare conflitti
import time  # Modulo time per sleep()
from calendar import monthcalendar, month_name
import pytz
import requests
import os
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_requests=5, time_window=60):  # 5 richieste per minuto
        self.requests = defaultdict(list)
        self.max_requests = max_requests
        self.time_window = time_window

    def is_allowed(self, user_id):
        now = datetime.now()
        # Rimuovi richieste vecchie
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < timedelta(seconds=self.time_window)
        ]
        # Controlla se l'utente può fare una nuova richiesta
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(now)
            return True
        return False


def check_user_membership(update, context):
    """Verifica se l'utente è membro del gruppo privato"""
    PRIVATE_GROUP_ID = os.environ.get('TELEGRAM_GROUP_ID') # ID come stringa
    if not PRIVATE_GROUP_ID:
        raise ValueError("No telegram group ID provided")
        
    user_id = update.effective_user.id
    try:
        member = context.bot.get_chat_member(PRIVATE_GROUP_ID, user_id)
        #print(f"Membership info: {member}")
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking membership: {e}")
        #print(f"User ID: {user_id}, Group ID: {PRIVATE_GROUP_ID}")
        return False

# Stati della conversazione
(CHOOSING, NAME, EMAIL, PHONE, BIRTH_DATE, MEDICAL, HIKE_CHOICE, EQUIPMENT,
 CAR_SHARE, LOCATION_CHOICE, QUARTIERE_CHOICE, FINAL_LOCATION, CUSTOM_QUARTIERE,
 ELSEWHERE, NOTES, IMPORTANT_NOTES, REMINDER_CHOICE) = range(17)

# Definisci il fuso orario di Roma
rome_tz = pytz.timezone('Europe/Rome')

## FUNZIONI UTILITY
def setup_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)

    # Get sheet ID from environment variable
    SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
    if not SHEET_ID:
        raise ValueError("No Google Sheet ID provided")

    # Open both sheets
    sheet_responses = client.open_by_key(SHEET_ID).worksheet('Registrazioni')
    sheet_hikes = client.open_by_key(SHEET_ID).worksheet('ProssimeUscite')
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
        'Location',
        'Something important we need to know?',
        'reminder_preference'
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
    min_date = today + timedelta(days=2) # the hike must be at least 2 days after today's date
    max_date = today + timedelta(days=60) # the hike cannot be more than 60 days after today's date

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
        
        # Determina l'indicatore di disponibilità
        if available_spots > 1:
            spot_indicator = "🟢"
        elif available_spots == 1:
            spot_indicator = "🔴"
        else:
            spot_indicator = "⚫"
            
        # Prima riga: data con indicatore di disponibilità
        keyboard.append([InlineKeyboardButton(
            f"{spot_indicator} {date_str} ({available_spots}/{hike['max_participants']})",
            callback_data=f'info_hike{idx}_date'
        )])

        # Seconda riga: nome dell'hike e bottone di selezione (se ci sono posti disponibili)
        if available_spots > 0:
            is_selected = idx in context.user_data.get('selected_hikes', [])
            select_emoji = "☑️" if is_selected else "⬜"
            keyboard.append([InlineKeyboardButton(
                f"{select_emoji} {hike['name']}",
                callback_data=f'select_hike{idx}'
            )])
        else:
            # Se non ci sono posti, mostra solo il nome senza possibilità di selezione
            keyboard.append([InlineKeyboardButton(
                f"⚫ {hike['name']}",
                callback_data='ignore'
            )])

        # Separatore tra gli hike
        if idx < len(hikes) - 1:
            keyboard.append([InlineKeyboardButton("┄┄┄┄┄┄┄", callback_data='ignore')])

    # Bottone di conferma alla fine
    keyboard.append([InlineKeyboardButton("✅ Confirm selection", callback_data='confirm_hikes')])
    return InlineKeyboardMarkup(keyboard)
    

def create_year_selector():
    current_year = date.today().year
    current_month = date.today().month
    current_day = date.today().day
    
    keyboard = []
    decades = list(range(1980, (current_year - 18) + 1, 10))
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
    current_year = date.today().year
    end_year = min(decade + 10, current_year - 18 + 1)
    years = list(range(decade, end_year))
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
    current_date = date.today()
    limit_date = date(current_date.year - 18, current_date.month, current_date.day)
    
    if year == limit_date.year:
        max_month = limit_date.month
    else:
        max_month = 12

    for i in range(1, max_month + 1, 3):
        row = []
        for month in range(i, min(i + 3, max_month + 1)):
            row.append(InlineKeyboardButton(
                month_name[month],
                callback_data=f'month_{year}_{month}'
            ))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def create_calendar(year, month):
    keyboard = []
    current_date = date.today()
    limit_date = date(current_date.year - 18, current_date.month, current_date.day)

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
                selected_date = date(year, month, day)
                if selected_date <= limit_date:
                    row.append(InlineKeyboardButton(
                        str(day),
                        callback_data=f'date_{year}_{month}_{day}'
                    ))
                else:
                    row.append(InlineKeyboardButton(" ", callback_data='ignore'))
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

def get_weather_forecast(lat, lon, date_str, api_key):
    """
    Ottiene le previsioni meteo per una data specifica
    Usa coordinate invece del nome della località per maggiore precisione
    """
    try:
        # Converti la data stringa in oggetto datetime
        target_date = datetime.strptime(date_str, '%d/%m/%Y').date()
        today = datetime.now().date()
        days_diff = (target_date - today).days

        if days_diff <= 5:  # Usiamo forecast giornaliero per previsioni fino a 5 giorni
            url = f"https://api.openweathermap.org/data/2.5/forecast/daily"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': api_key,
                'units': 'metric',
                'cnt': days_diff + 1
            }
            response = requests.get(url, params=params)
            data = response.json()
            forecast = data['list'][-1]  # Prendiamo l'ultimo giorno (quello target)

            return {
                'temp_min': round(forecast['temp']['min']),
                'temp_max': round(forecast['temp']['max']),
                'description': forecast['weather'][0]['description'],
                'probability_rain': round(forecast.get('pop', 0) * 100),  # Probabilità di pioggia in percentuale
                'accuracy': 'high'
            }

        else:  # Per previsioni oltre 5 giorni usiamo il forecast climatico
            url = "https://api.openweathermap.org/data/2.5/climate/forecast/daily"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': api_key,
                'units': 'metric'
            }
            response = requests.get(url, params=params)
            data = response.json()

            return {
                'temp_min': round(data['temperature']['min']),
                'temp_max': round(data['temperature']['max']),
                'probability_rain': round(data.get('probability_of_precipitation', 0) * 100),
                'accuracy': 'low'  # Indichiamo che è una previsione a lungo termine
            }

    except Exception as e:
        print(f"Error getting weather forecast: {e}")
        return None

def format_weather_message(weather, days_until_hike):
    """
    Formatta il messaggio meteo in base all'accuratezza della previsione
    """
    if not weather:
        return "⚠️ _Weather forecast not available_"

    if weather['accuracy'] == 'high':
        return (
            f"🌡 *Weather Forecast*:\n"
            f"Temperature: {weather['temp_min']}°C - {weather['temp_max']}°C\n"
            f"Conditions: {weather['description']}\n"
            f"Chance of rain: {weather['probability_rain']}%"
        )
    else:
        return (
            f"🌡 *Weather Trend* (preliminary forecast):\n"
            f"Expected temperature: {weather['temp_min']}°C - {weather['temp_max']}°C\n"
            f"Chance of rain: {weather['probability_rain']}%\n"
            f"_A more accurate forecast will be provided 3 days before the hike_"
        )

def check_and_send_reminders(context):
    """
    Funzione da eseguire periodicamente per controllare e inviare i reminder
    Args:
        context: JobContext passato da job_queue
    """
    sheet_responses = context.bot.dispatcher.bot_data['sheet_responses']
    sheet_hikes = context.bot.dispatcher.bot_data['sheet_hikes']
    registrations = sheet_responses.get_all_records()
    hikes_data = sheet_hikes.get_all_records()
    today = datetime.now(rome_tz).date()

    # Mappa degli hike con le loro coordinate
    hikes_coords = {
        hike['hike']: {'lat': hike['latitude'], 'lon': hike['longitude']}
        for hike in hikes_data
    }

    for reg in registrations:
        hikes = reg['Choose the hike'].split('; ')
        reminder_pref = reg['Reminder preference']
        telegram_id = reg['Telegram_ID']

        for hike in hikes:
            if hike:
                date_str, name = hike.split(' - ', 1)
                hike_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                days_until_hike = (hike_date - today).days

                # Controlla se è il momento di inviare un reminder
                if ((days_until_hike == 7 and ('7' in reminder_pref or 'both' in reminder_pref)) or
                    (days_until_hike == 3 and ('3' in reminder_pref or 'both' in reminder_pref))):

                    # Ottieni previsioni meteo
                    coords = hikes_coords.get(name)
                    weather = None
                    if coords:
                        weather = get_weather_forecast(
                            coords['lat'],
                            coords['lon'],
                            date_str,
                            os.getenv('OPENWEATHER_API_KEY')
                        )

                    weather_msg = format_weather_message(weather, days_until_hike)

                    message = (
                        f"⏰ *Reminder*: You have an upcoming hike!\n\n"
                        f"🗓 *Date:* {date_str}\n"
                        f"🏃 *Hike:* {name}\n\n"
                        f"{weather_msg}\n\n"
                        f"_Remember to check the required equipment and be prepared!_"
                    )

                    try:
                        context.bot.send_message(
                            chat_id=telegram_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        print(f"Error sending reminder to {telegram_id}: {e}")

def error_handler(update, context):
    """Gestisce gli errori in modo globale"""
    try:
        raise context.error
    except telegram.error.NetworkError:
        message = "⚠️ Network error occurred. Please try again."
    except telegram.error.Unauthorized:
        # l'utente ha bloccato il bot
        return
    except telegram.error.TimedOut:
        message = "⚠️ Request timed out. Please try again."
    except telegram.error.TelegramError:
        message = "⚠️ Telegram error occurred. Please try again later."
    except Exception as e:
        message = "⚠️ An unexpected error occurred. Please try again later."
        print(f"Unexpected error: {e}")

    # Invia messaggio all'utente se possibile
    if update and update.effective_chat:
        try:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message
            )
        except:
            pass

## PARTE 2 - Funzioni menu principale
def menu(update, context):
    # Check rate limiting
    if not context.bot_data['rate_limiter'].is_allowed(update.effective_user.id):
        update.message.reply_text(
            "⚠️ You're making too many requests. Please wait a minute and try again."
        )
        return ConversationHandler.END

    # check appartenenza al gruppo
    if not check_user_membership(update, context):
        update.message.reply_text(
            "⚠️ You need to be a member of Hikings Rome group to use this bot.\n"
            "Request access to the group and try again!"
        )
        return ConversationHandler.END

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
            "Use /menu to go back to the home menu."
        )
        return None

    return available_hikes

def restart(update, context):
    """Comando per resettare il bot"""
    print("Restart command received")  # Debug print
    user_id = update.effective_user.id
    current_state = context.chat_data.get('last_state')
    
    # Se l'utente stava compilando il form, chiedi conferma
    if current_state in [NAME, EMAIL, PHONE, BIRTH_DATE, MEDICAL, HIKE_CHOICE, EQUIPMENT, 
                        CAR_SHARE, LOCATION_CHOICE, QUARTIERE_CHOICE, FINAL_LOCATION, 
                        CUSTOM_QUARTIERE, NOTES, REMINDER_CHOICE]:
        keyboard = [
            [
                InlineKeyboardButton("Yes ✅", callback_data='yes_restart'),
                InlineKeyboardButton("No ❌", callback_data='no_restart')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "⚠️ You are in the middle of registration.\n"
            "Are you sure you want to restart? All progress will be lost.",
            reply_markup=reply_markup
        )
        return current_state  # Ritorniamo lo stato corrente invece di CHOOSING
    
    # Se non c'è niente da confermare, procedi con il restart
    return direct_restart(update, context)

def direct_restart(update, context):
    """Esegue il restart direttamente"""
    print("Executing direct restart")  # Debug print
    context.user_data.clear()
    context.chat_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("Sign up for hike 🏃", callback_data='signup')],
        [InlineKeyboardButton("My Hikes 🎒", callback_data='myhikes')],
        [InlineKeyboardButton("Useful links 🔗", callback_data='links')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if isinstance(update, CallbackQuery):
            # Prima prova a eliminare il messaggio precedente
            try:
                update.message.delete()
            except:
                pass
            # Invia un nuovo messaggio invece di modificare quello esistente
            update.message.reply_text(
                "Hi, I'm Hiky and I'll help you interact with @hikingsrome.\n"
                "How can I assist you?",
                reply_markup=reply_markup
            )
        else:
            update.message.reply_text(
                "Hi, I'm Hiky and I'll help you interact with @hikingsrome.\n"
                "How can I assist you?",
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"Error in direct_restart: {e}")
        # Se fallisce, invia un nuovo messaggio
        try:
            if isinstance(update, CallbackQuery):
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Hi, I'm Hiky and I'll help you interact with @hikingsrome.\n"
                         "How can I assist you?",
                    reply_markup=reply_markup
                )
            else:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text="Hi, I'm Hiky and I'll help you interact with @hikingsrome.\n"
                         "How can I assist you?",
                    reply_markup=reply_markup
                )
        except:
            pass
            
    return CHOOSING

def handle_restart_confirmation(update, context):
    """Gestisce la conferma del restart"""
    print("Handling restart confirmation")  # Debug print
    query = update.callback_query
    query.answer()
    
    if query.data == 'yes_restart':
        try:
            query.message.delete()  # Elimina il messaggio di conferma
        except:
            pass
        return direct_restart(query, context)
    else:
        current_state = context.chat_data.get('last_state', CHOOSING)
        try:
            query.edit_message_text("✅ Restart cancelled. You can continue from where you left off.")
            # Invia la domanda appropriata in base allo stato
            if current_state == NAME:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="👋 Name and surname?"
                )
            elif current_state == EMAIL:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📧 Email?"
                )
            elif current_state == PHONE:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📱 Phone number?"
                )
            elif current_state == BIRTH_DATE:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📅 Select the decade of your birth year:",
                    reply_markup=create_year_selector()
                )
            elif current_state == MEDICAL:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="🏥 Medical conditions\n"
                         "_Do you have any medical conditions that might create difficulties for you "
                         "(Knee pain, cardiopathy, allergies etc.)?_",
                    parse_mode='Markdown'
                )
            elif current_state == HIKE_CHOICE:
                # Ricostruisci la keyboard degli hike disponibili
                available_hikes = context.user_data.get('available_hikes', [])
                reply_markup = create_hikes_keyboard(available_hikes, context)
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="🎯 Choose the hike(s) you want to participate in.\n"
                         "Click to select/deselect a hike.\n"
                         "Click '✅ Confirm selection' when done.",
                    reply_markup=reply_markup
                )
            elif current_state == EQUIPMENT:
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
            elif current_state == CAR_SHARE:
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
            elif current_state == LOCATION_CHOICE:
                keyboard = [
                    [InlineKeyboardButton("Rome Resident 🏛", callback_data='rome_resident')],
                    [InlineKeyboardButton("Outside Rome 🌍", callback_data='outside_rome')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📍 Where do you live?\n"
                         "_This information helps us organize transport and meeting points_",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif current_state == NOTES:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="📝 Something important we need to know?\n"
                         "_Whatever you want to tell us. If you share the car, remember the number of available seats._",
                    parse_mode='Markdown'
                )
        except Exception as e:
            print(f"Error in handle_restart_confirmation: {e}")
            # Se fallisce, invia un messaggio generico
            try:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Please continue with your previous answer."
                )
            except:
                pass
        
        return current_state


def handle_menu_choice(update, context):
    query = update.callback_query
    query.answer()

    if not check_user_membership(update, context):
        query.edit_message_text(
            "⚠️ You need to be a member of Hikings Rome group to use this bot.\n"
            "Request access to the group and try again!"
        )
        return ConversationHandler.END

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
            "Use /menu to go back to the home menu."
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

    # Bottone per la cancellazione
    keyboard.append([InlineKeyboardButton("❌ Cancel registration", callback_data=f'cancel_hike_{current_index}')])

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

def handle_cancel_request(update, context):
    """Gestisce la richiesta iniziale di cancellazione"""
    query = update.callback_query
    query.answer()

    # Ottieni l'indice dell'hike da cancellare
    hike_index = int(query.data.split('_')[2])
    hike = context.user_data['my_hikes'][hike_index]
    context.user_data['hike_to_cancel'] = hike  # Salva l'hike da cancellare

    keyboard = [
        [
            InlineKeyboardButton("Yes ✅", callback_data='confirm_cancel'),
            InlineKeyboardButton("No ❌", callback_data='abort_cancel')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        f"Are you sure you want to cancel your registration for:\n\n"
        f"🗓 {hike['date'].strftime('%d/%m/%Y')}\n"
        f"🏃 {hike['name']}?",
        reply_markup=reply_markup
    )
    return CHOOSING

def handle_cancel_confirmation(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'abort_cancel':
        return show_hike_details(query, context)

    hike_to_cancel = context.user_data['hike_to_cancel']
    sheet_responses = context.bot_data['sheet_responses']
    user_id = query.from_user.id

    # Trova TUTTE le righe dell'utente
    registrations = sheet_responses.get_all_records()
    user_rows = []
    for idx, reg in enumerate(registrations, start=2):  # start=2 perché la prima riga sono le intestazioni
        if str(reg['Telegram_ID']) == str(user_id):
            user_rows.append({
                'row': idx,
                'hikes': reg['Choose the hike'].split('; '),
                'current_reg': reg
            })

    if not user_rows:
        query.edit_message_text(
            "❌ Something went wrong.\n"
            "Use /menu to go back to the home menu."
        )
        return ConversationHandler.END

    # Formato dell'hike da cancellare
    hike_to_remove = f"{hike_to_cancel['date'].strftime('%d/%m/%Y')} - {hike_to_cancel['name']}"
    
    success = False
    for row_data in user_rows:
        if hike_to_remove in row_data['hikes']:
            # Rimuovi l'hike dalla lista
            new_hikes = [h for h in row_data['hikes'] if h and h != hike_to_remove]
            
            if new_hikes:
                # Se ci sono ancora altri hike, aggiorna la riga
                sheet_responses.update_cell(row_data['row'], 8, '; '.join(new_hikes))
            else:
                # Se non ci sono più hike, elimina l'intera riga
                sheet_responses.delete_rows(row_data['row'])
            
            success = True
            break

    if success:
        query.edit_message_text(
            "✅ Registration successfully cancelled.\n"
            "Use /menu to go back to the home menu."
        )
    else:
        query.edit_message_text(
            "❌ Could not find the registration to cancel.\n"
            "Use /menu to go back to the home menu."
        )

    return ConversationHandler.END

## PARTE 4 - Gestione delle domande del questionario
def handle_invalid_message(update, context):
    if not check_user_membership(update, context):
        update.message.reply_text(
            "⚠️ You need to be a member of Hikings Rome group to use this bot.\n"
            "Request access to the group and try again!"
        )
        return ConversationHandler.END

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
    context.chat_data['last_state'] = NAME
    context.user_data['name'] = update.message.text
    update.message.reply_text("📧 Email?")
    return EMAIL

def save_email(update, context):
    context.chat_data['last_state'] = EMAIL
    context.user_data['email'] = update.message.text
    update.message.reply_text("📱 Phone number?")
    return PHONE

def save_phone(update, context):
    context.chat_data['last_state'] = PHONE
    context.user_data['phone'] = update.message.text
    update.message.reply_text(
        "📅 Select the decade of your birth year:",
        reply_markup=create_year_selector()
    )
    return BIRTH_DATE

def handle_calendar(update, context):
    context.chat_data['last_state'] = BIRTH_DATE
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
    context.chat_data['last_state'] = MEDICAL
    context.user_data['medical'] = update.message.text
    context.user_data['selected_hikes'] = []

    # Gli hike disponibili sono già stati salvati in context.user_data['available_hikes']
    available_hikes = context.user_data['available_hikes']
    reply_markup = create_hikes_keyboard(available_hikes, context)

    update.message.reply_text(
        "🎯 Choose the hike(s) you want to participate in:\n\n"
        "🟢 Many spots available\n"
        "🔴 Last spot available\n"
        "⚫ Fully booked\n\n"
        "_Click on the hike name to select/deselect._\n"
        "_Click '✅ Confirm selection' when done._",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return HIKE_CHOICE

def handle_hike(update, context):
    context.chat_data['last_state'] = HIKE_CHOICE
    query = update.callback_query
    query.answer()

    # Ignora i click sulle righe informative e sul separatore
    if query.data == 'ignore':
        return HIKE_CHOICE

    if query.data.startswith('info_hike'):
        # Per click sulla data, mostra un messaggio informativo
        hike_idx = int(query.data.split('_')[1].replace('hike', ''))
        hike = context.user_data['available_hikes'][hike_idx]
        available_spots = hike['max_participants'] - hike['current_participants']
        
        if available_spots > 0:
            query.answer(
                f"Click on the hike name below to select/deselect",
                show_alert=False
            )
        else:
            query.answer(
                "This hike is fully booked",
                show_alert=True
            )
        return HIKE_CHOICE

    if query.data.startswith('select_hike'):
        hike_idx = int(query.data.replace('select_hike', ''))
        selected_hikes = context.user_data.get('selected_hikes', [])
        available_hikes = context.user_data['available_hikes']

        # Verifica che ci siano ancora posti disponibili
        hike = available_hikes[hike_idx]
        available_spots = hike['max_participants'] - hike['current_participants']
        
        if available_spots <= 0:
            query.answer("This hike is fully booked", show_alert=True)
            return HIKE_CHOICE

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
    context.chat_data['last_state'] = EQUIPMENT
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
    context.chat_data['last_state'] = CAR_SHARE
    query = update.callback_query
    query.answer()

    context.user_data['car_share'] = 'Yes' if query.data == 'yes_car' else 'No'

    # Inizia il processo di selezione della location
    keyboard = [
        [InlineKeyboardButton("Rome Resident 🏛", callback_data='rome_resident')],
        [InlineKeyboardButton("Outside Rome 🌍", callback_data='outside_rome')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="📍 Where do you live?\n"
             "_This information helps us organize transport and meeting points_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return LOCATION_CHOICE

def handle_location_choice(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'outside_rome':
        query.edit_message_text(
            "🌍 Please specify your location (e.g., Frascati, Tivoli, etc.):"
        )
        return CUSTOM_QUARTIERE
    
    # Definizione dei municipi con i loro quartieri
    municipi_data = {
        'I': ['Centro Storico', 'Trastevere', 'Testaccio', 'Esquilino', 'Prati'],
        'II': ['Parioli', 'Flaminio', 'Salario', 'Trieste'],
        'III': ['Monte Sacro', 'Val Melaina', 'Fidene', 'Bufalotta'],
        'IV': ['San Basilio', 'Tiburtino', 'Pietralata'],
        'V': ['Prenestino', 'Centocelle', 'Tor Pignattara'],
        'VI': ['Torre Angela', 'Tor Bella Monaca', 'Lunghezza'],
        'VII': ['Appio-Latino', 'Tuscolano', 'Cinecittà'],
        'VIII': ['Ostiense', 'Garbatella', 'San Paolo'],
        'IX': ['EUR', 'Torrino', 'Laurentino'],
        'X': ['Ostia', 'Acilia', 'Infernetto'],
        'XI': ['Portuense', 'Magliana', 'Trullo'],
        'XII': ['Monte Verde', 'Gianicolense', 'Pisana'],
        'XIII': ['Aurelio', 'Boccea', 'Casalotti'],
        'XIV': ['Monte Mario', 'Primavalle', 'Ottavia'],
        'XV': ['La Storta', 'Cesano', 'Prima Porta']
    }
    
    context.user_data['municipi_data'] = municipi_data
    
    # Crea keyboard per i municipi
    keyboard = []
    for municipio in municipi_data.keys():
        keyboard.append([InlineKeyboardButton(
            f"Municipio {municipio}", 
            callback_data=f'mun_{municipio}'
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        "🏛 Select your municipio:",
        reply_markup=reply_markup
    )
    return QUARTIERE_CHOICE

def handle_quartiere_choice(update, context):
    query = update.callback_query
    query.answer()
    
    municipio = query.data.replace('mun_', '')
    context.user_data['selected_municipio'] = municipio
    municipi_data = context.user_data['municipi_data']
    
    quartieri = municipi_data[municipio]
    keyboard = []
    
    # Crea bottoni per ogni quartiere
    for quartiere in quartieri:
        keyboard.append([InlineKeyboardButton(quartiere, callback_data=f'q_{quartiere}')])
    
    # Aggiungi opzioni aggiuntive
    keyboard.append([InlineKeyboardButton("Other area in this municipio", callback_data='other_area')])
    keyboard.append([InlineKeyboardButton("🔙 Back to municipi", callback_data='back_municipi')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"🏘 Select your area in Municipio {municipio}:",
        reply_markup=reply_markup
    )
    return FINAL_LOCATION

def handle_final_location(update, context):
    query = update.callback_query
    query.answer()
    
    if query.data == 'back_municipi':
        return handle_location_choice(update, context)
    
    if query.data == 'other_area':
        query.edit_message_text("📍 Please specify your area in this municipio:")
        return CUSTOM_QUARTIERE
    
    quartiere = query.data.replace('q_', '')
    municipio = context.user_data['selected_municipio']
    location = f"Municipio {municipio} - {quartiere}"
    context.user_data['location'] = location
    
    return handle_reminder_preferences(update, context)

def handle_custom_location(update, context):
    context.chat_data['last_state'] = CUSTOM_QUARTIERE
    
    if 'selected_municipio' in context.user_data:
        # Custom area in a municipio
        municipio = context.user_data['selected_municipio']
        location = f"Municipio {municipio} - {update.message.text}"
    else:
        # Location outside Rome
        location = f"Outside Rome - {update.message.text}"
    
    context.user_data['location'] = location
    
    # Crea e invia il pannello dei reminder direttamente
    keyboard = [
        [InlineKeyboardButton("7 days before", callback_data='reminder_7')],
        [InlineKeyboardButton("3 days before", callback_data='reminder_3')],
        [InlineKeyboardButton("Both", callback_data='reminder_both')],
        [InlineKeyboardButton("No reminders", callback_data='reminder_none')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "⏰ Would you like to receive reminders before the hike?\n"
        "_Choose your preferred reminder option:_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return REMINDER_CHOICE
    

def handle_reminder_preferences(update, context):
    query = update.callback_query
    query.answer()

    keyboard = [
        [InlineKeyboardButton("7 days before", callback_data='reminder_7')],
        [InlineKeyboardButton("3 days before", callback_data='reminder_3')],
        [InlineKeyboardButton("Both", callback_data='reminder_both')],
        [InlineKeyboardButton("No reminders", callback_data='reminder_none')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="⏰ Would you like to receive reminders before the hike?\n"
             "_Choose your preferred reminder option:_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return REMINDER_CHOICE

def save_reminder_preference(update, context):
    context.chat_data['last_state'] = REMINDER_CHOICE
    query = update.callback_query
    query.answer()

    reminder_choice = query.data.replace('reminder_', '')
    reminder_mapping = {
        '7': '7 days',
        '3': '3 days',
        'both': '7 and 3 days',
        'none': 'No reminders'
    }
    context.user_data['reminder_preference'] = reminder_mapping[reminder_choice]

    return ask_notes(update, context, query.message.chat_id)

def handle_elsewhere(update, context):
    context.chat_data['last_state'] = ELSEWHERE
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
    context.chat_data['last_state'] = NOTES
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
                            "Use /menu to fill out the form again"
                        )
                        return ConversationHandler.END

        # Save to Google Sheets
        try:
            sheet_responses = context.bot_data['sheet_responses']
            data = context.user_data
            timestamp = datetime.now(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
            telegram_id = str(query.from_user.id)

            # Format selected hikes for saving
            hikes_text = '; '.join([
                f"{hike['date'].strftime('%d/%m/%Y')} - {hike['name']}"
                for hike in selected_hikes
            ])

            # Retry logic for sheet writing
            for attempt in range(3):
                try:
                    sheet_responses.append_row([
                        timestamp,
                        telegram_id,
                        data.get('name', ''),
                        data.get('email', ''),
                        data.get('phone', ''),
                        data.get('birth_date', ''),
                        data.get('medical', ''),
                        hikes_text,
                        data.get('equipment', ''),
                        data.get('car_share', ''),
                        data.get('location', ''),
                        data.get('notes', ''),
                        data.get('reminder_preference', 'No reminders')
                    ])
                    break
                except gspread.exceptions.APIError as e:
                    if attempt == 2:  # ultimo tentativo
                        raise e
                    time.sleep(1)  # attendi prima di riprovare

            query.edit_message_text(
                "✅ Thanks for signing up for the next hike.\n"
                "You can use /menu to go back to the home menu."
            )

        except Exception as e:
            print(f"Error saving registration: {e}")
            query.edit_message_text(
                "⚠️ There was an error saving your registration. Please try again later or contact support."
            )
            return ConversationHandler.END

    else:
        query.edit_message_text(
            "❌ We are sorry but accepting these rules is necessary to participate in the walks.\n"
            "Thank you for your time.\n"
            "You can use /menu to go back to the home menu."
        )

    return ConversationHandler.END

def cancel(update, context):
    context.user_data.clear()
    update.message.reply_text(
        '❌ Registration cancelled.\n'
        'You can use /menu to go back to the home menu.'
    )
    return ConversationHandler.END

import atexit

def cleanup():
    """Funzione di cleanup che viene chiamata all'uscita"""
    try:
        updater.stop()
    except:
        pass

atexit.register(cleanup)

def main():
    
    # Get port number from environment variable
    port = int(os.environ.get('PORT', 10000))
    
    # token bot telegram
    TOKEN = os.environ.get('TELEGRAM_TOKEN')
    # api meteo
    os.environ['OPENWEATHER_API_KEY'] = os.environ.get('OPENWEATHER_API_KEY')

    if not TOKEN:
        raise ValueError("No telegram token provided")

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Setup sheets
    sheet_responses, sheet_hikes = setup_google_sheets()
    dp.bot_data['sheet_responses'] = sheet_responses
    dp.bot_data['sheet_hikes'] = sheet_hikes

    # Setup rate limiter
    rate_limiter = RateLimiter(max_requests=5, time_window=60)  # 5 richieste al minuto
    dp.bot_data['rate_limiter'] = rate_limiter

    # Setup error handler
    dp.add_error_handler(error_handler)

    dp.add_handler(CommandHandler('restart', restart))

    # Aggiungi job scheduler per i reminder
    job_queue = updater.job_queue
    job_queue.run_daily(
        callback=check_and_send_reminders,
        time=datetime_time(hour=9, minute=0, tzinfo=rome_tz)  # Invia reminder alle 9:00 ora di Roma
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('menu', menu),
            MessageHandler(Filters.text & ~Filters.command, handle_invalid_message),
            CallbackQueryHandler(handle_restart_choice, pattern='^restart_')
        ],
        states={
            CHOOSING: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_menu_choice, pattern='^(signup|myhikes|links|back_to_menu)$'),
                CallbackQueryHandler(handle_hike_navigation, pattern='^(prev_hike|next_hike)$'),
                CallbackQueryHandler(handle_cancel_request, pattern='^cancel_hike_\d+$'),
                CallbackQueryHandler(handle_cancel_confirmation, pattern='^(confirm_cancel|abort_cancel)$'),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$')
            ],
            REMINDER_CHOICE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(save_reminder_preference, pattern='^reminder_')
            ],
            NAME: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_name)
            ],
            EMAIL: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_email)
            ],
            PHONE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_phone)
            ],
            BIRTH_DATE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_calendar)
            ],
            MEDICAL: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_medical)
            ],
            HIKE_CHOICE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_hike)
            ],
            EQUIPMENT: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_equipment)
            ],
            CAR_SHARE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_car_share)
            ],
            LOCATION_CHOICE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_location_choice)
            ],
            QUARTIERE_CHOICE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_quartiere_choice)
            ],
            FINAL_LOCATION: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_final_location)
            ],
            CUSTOM_QUARTIERE: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, handle_custom_location)
            ],
            NOTES: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                MessageHandler(Filters.text & ~Filters.command, save_notes)
            ],
            IMPORTANT_NOTES: [
                CommandHandler('menu', menu),
                CommandHandler('restart', restart),
                CallbackQueryHandler(handle_restart_confirmation, pattern='^(yes_restart|no_restart)$'),
                CallbackQueryHandler(handle_final_choice)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('restart', restart)
        ]
    )

    dp.add_handler(conv_handler)

    # Avvia il bot
    # Start the webhook
    updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )
    #updater.start_polling(drop_pending_updates=True)  # Aggiungi drop_pending_updates=True
    #print("🚀 Bot started! Press CTRL+C to stop.")

    # Blocca l'esecuzione fino a quando il bot non viene fermato
    updater.idle()

    #print("🛑 Bot stopped!")

if __name__ == '__main__':
    main()

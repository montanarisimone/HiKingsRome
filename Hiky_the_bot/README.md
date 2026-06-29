# Hiky the Bot 🤖
*HiKingsRome's Telegram assistant*

Hiky handles everything the community needs to organise hikes — sign-ups, reminders, the calendar, weather forecasts, and a full admin dashboard. It runs as a Docker container on a home NAS and talks to a local SQLite database.

## Features

### 🏔️ Hike calendar
Monthly view of all upcoming hikes with difficulty indicators, real-time spot availability, meeting point, distance, elevation, and fee per person. Fees show as estimated or locked depending on how many people have registered.

### 📋 Registration
Multi-step sign-up form that pre-fills from your saved profile. Covers medical conditions, equipment confirmation, car sharing preferences, location (Rome municipality/neighbourhood hierarchy), reminder preferences, and additional notes. Prevents duplicate registrations and checks spot availability in real time. You can register for multiple hikes in one go.

### 👤 User profile
Store your name, surname, email, phone, and birth date once — the registration form uses them automatically every time. Every field is editable. Age verification (18+) via a calendar-based date picker. Privacy consent management with required and optional consents (car sharing, photos, marketing), including version tracking.

### ⏰ Reminders
Opt-in automated messages 5 days and/or 2 days before a hike. Each reminder includes the meeting point, essential equipment info, and a weather forecast (temperature, conditions, precipitation probability) with an accuracy indicator based on how far out the forecast is.

### 🗂️ My hikes
View all your registrations with full hike details, and cancel with confirmation. Separate views for past and upcoming hikes are in progress.

### 💖 Donations
PayPal support built in.

### 👑 Admin dashboard
Role-based access — the admin menu is only visible to users with admin privileges.

- **Hike management** — create hikes (name, date, difficulty, location, participant limit, guide quota), edit, cancel, or reactivate them at any time
- **Participant lists** — full contact details, registration status, and fee tracking per hike; guides are automatically assigned when an admin registers
- **Fee management** — real-time fee calculation based on current registrations, with a clear distinction between locked and estimated fees; guide-specific fee display
- **Database query tool** — run pre-defined queries or write custom SQL directly from Telegram; parameterised queries prevent injection; results are formatted for readability
- **Maintenance scheduling** — set downtime windows with start/end time and reason; all users get notified automatically; editable and cancellable
- **User management** — promote regular users to admin

### 🔧 Under the hood
- Telegram group membership check before granting any access
- Rate limiting to keep things stable under peak load
- Automatic database backups
- Comprehensive error handling with user-friendly messages throughout

## Tech stack

- **Python 3.11**
- **python-telegram-bot 13.7**
- **SQLite** — single-file database, persisted via Docker volume
- **OpenWeatherMap API** — weather forecasts in reminders
- **Docker + docker-compose** — deployed on a home NAS

## Project structure

```
Hiky_the_bot/
├── HikyTheBot.py           # Entry point; all conversation handlers
├── setup_database.py       # One-time DB initialisation
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── utils/
    ├── __init__.py
    ├── db_utils.py         # Core database helpers
    ├── db_query_utils.py   # Admin SQL query interface
    ├── db_keyboards.py     # Telegram keyboard layouts
    ├── backup_database.py  # Backup utility
    ├── weather_utils.py    # OpenWeatherMap integration
    ├── markdown_utils.py   # Message formatting
    └── rate_limiter.py     # Anti-spam rate limiting
```

Data generated at runtime lives outside the image:

```
data/       # SQLite database (mounted volume)
backups/    # Automatic DB backups (mounted volume)
logs/       # Application logs (mounted volume)
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features, work in progress, and known issues.

## Credits

Developed with ❤️ by the HiKingsRome team.
Tech by [@montanarisimone](https://github.com/montanarisimone).

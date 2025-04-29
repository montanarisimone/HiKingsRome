# HiKingsRome  
*Nearby Rome, nature awaits!*

Welcome to HiKingsRome, where technology meets trails! This is the home of all the scripts, tools, and quirky code powering our hiking group in and around Rome. Whether it’s managing participant lists, automating reminders, or keeping track of the best routes, this repository has it covered.

## 🌟 What Is HiKingsRome?  
HiKingsRome is all about helping people escape the city, connect with nature, and enjoy the beautiful landscapes around Rome. To make organizing these adventures smoother, I've built a collection of scripts and tools that do everything from managing Google Sheets to automating tasks with Hiky, our friendly bot.

## 🛠️ What’s in This Repository?  
This repo is a mix of scripts, code, and general chaos (but the good kind). Here's what you'll find:

### Google Sheets Automations ✨ [Deprecated]  
A collection of scripts to manage participant data, hike schedules, and all the logistics that keep HiKingsRome running.

### Hiky the Bot 🤖  
Our trusty assistant!
#### Features

- **Event Registration** 🏔️
  * Streamlined sign-up process for hiking events with smart form validation
  * Collects essential information: personal details, medical conditions, equipment status
  * Customizable reminder preferences for each registration
  * Automatic spot availability tracking and waitlist management
 
- **Hike Calendar** 📅
  * Intuitive calendar view with color-coded difficulty levels
  * Real-time updates on available spots and booking status
  * Detailed information on meeting points, distance, and elevation
  * Monthly and upcoming event organization for better planning
 
- **Profile Management** 👤
  * Secure storage of personal information with privacy controls
  * One-time setup that populates registration forms automatically
  * Customizable notification and sharing preferences
  * History of past hikes and upcoming registrations

- **Weather Forecasts** ☀️
  * Automated weather predictions for each hike location
  * Temperature ranges, precipitation probability, and conditions overview
  * Accuracy indicators based on forecast timeframe
  * Integration with OpenWeatherMap for reliable data

- **Admin Tools** 👑
  * Comprehensive dashboard for hiking event management
  * Participant list generation with contact details and special requirements
  * Quick communication channels with registered hikers

- **Maintenance Scheduling** 🔧
  * Advanced planning of bot maintenance periods
  * Automated notifications to users before and during downtime
  * Reason documentation and expected resolution times

- **Reminder System** ⏰
  * Customizable reminders at 5 and/or 2 days before hikes
  * Essential details included: meeting points, required equipment, weather
  * Opt-in/opt-out capability for different types of notifications
  * Special alerts for weather changes or event modifications

- **Car Sharing Coordination** 🚗
  * Geographic matching of drivers and passengers in similar locations
  * Environmental impact reduction statistics (wip)

- **Donation Support** 💖
  * Multiple payment options including Telegram Stars and PayPal

- **Group Membership Verification** 🔐
  * Seamless integration with Telegram group membership
  * Real-time verification of community membership status
  * Automatic invitation links for non-members
  * Protection of community-exclusive features and information

#### Technology Stack

- Python 3.8+
- python-telegram-bot
- SQLite
- Google Cloud Platform
- OpenWeatherMap API (optional)

#### Project Structure

```
Hiky_the_bot/
├── HikyTheBot.py          # Main bot script
├── requirements.txt       # Python dependencies
├── setup_database.py      # Initial database setup
├── utils/
    ├── backup_database.py # Automatic backup utilities
    ├── db_keyboards.py    # Telegram inline keyboards
    ├── db_query_utils.py  # Database query utilities
    ├── db_utils.py        # Core database functions
    ├── markdown_utils.py  # Text formatting utilities
    ├── rate_limiter.py    # Request rate limiting
    └── weather_utils.py   # Weather forecast utilities
```

### Other Tools and Scripts 🛠️  
Anything else that helps us organize hikes, stay connected, and make HiKingsRome more efficient.

## 🤷‍♂️ Why Did I Build This?  
Because organizing a hiking group can be more exhausting than climbing a mountain! With HiKingsRome, I wanted to combine my love for nature with a bit of tech to make things easier for everyone.

Also, let’s be clear: I’m not a professional programmer. These scripts were cobbled together with the help of AI (shoutout to [Claude](https://claude.ai/)!) and a whole lot of trial and error. So if you spot some messy code, remember—I’m better at picking hiking trails than writing elegant algorithms.

## 🖇️ Contributing  
Feel free to explore, laugh at the code, and contribute if you’d like! Whether you’re here to improve a script, fix a bug, or just get inspired for your own hiking group, you’re welcome to join the journey!

## Useful links:
- [Website](https://www.hikingsrome.com/) (wip)
- [Instagram](https://www.instagram.com/hikingsrome/) (wip)
- [Komoot](https://www.komoot.com/it-it/user/3261856743261)

## Credits

Developed with ❤️ by the Hikings Rome team.

> *"In the end, coding is like hiking: it requires patience, planning, and the ability to enjoy the journey despite unexpected obstacles."*

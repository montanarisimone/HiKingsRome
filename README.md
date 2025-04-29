# HiKingsRome  
*Nearby Rome, nature awaits!*

Welcome to HiKingsRome, where technology meets trails! This is the home of all the scripts, tools, and quirky code powering our hiking group in and around Rome. Whether it’s managing participant lists, automating reminders, or keeping track of the best routes, this repository has it covered.

## 🌟 What Is HiKingsRome?  
HiKingsRome is all about helping people escape the city, connect with nature, and enjoy the beautiful landscapes around Rome. To make organizing these adventures smoother, I've built a collection of scripts and tools that do everything from managing Google Sheets to automating tasks with Hiky, our friendly bot.

## 🛠️ What’s in This Repository?  
This repo is a mix of scripts, code, and general chaos (but the good kind). Here's what you'll find...

### Google Sheets Automations ✨ [Deprecated]  
A collection of scripts to manage participant data, hike schedules, and all the logistics that keep HiKingsRome running.

### Hiky the Bot 🤖  
Our trusty digital hiking assistant! Hiky helps manage every aspect of our hiking community.

#### Features

- **Event Registration** 🏔️
  * Streamlined sign-up process with smart form validation
  * Collection of personal details, medical conditions, equipment status
  * Customizable reminder preferences
  * Automatic spot availability tracking
 
- **Hike Calendar** 📅
  * Color-coded difficulty levels
  * Real-time updates on available spots
  * Details on meeting points, distance, elevation
  * Monthly overview for better planning
 
- **Profile Management** 👤
  * Secure storage with privacy controls
  * One-time setup for automatic form population
  * Customizable notification preferences
  * History of past and upcoming hikes

- **Weather Forecasts** ☀️
  * Automated predictions for hike locations
  * Temperature, precipitation probability, conditions
  * Accuracy indicators based on timeframe
  * OpenWeatherMap API integration

- **Admin Tools** 👑
  * Comprehensive event management dashboard
  * Participant lists with contact details
  * Direct communication channels
  * Built-in SQL query interface

- **Reminder System** ⏰
  * Options for 5 and/or 2 days before hikes
  * Essential details about meeting points, equipment
  * Opt-in/opt-out preferences
  * Weather change alerts

- **Car Sharing Coordination** 🚗
  * Location-based driver/passenger matching
  * Environmental impact statistics (WIP)

- **Donation Support** 💖
  * Telegram Stars and PayPal integration
  * Support notifications for admins

- **Security & Maintenance** 🔐
  * Group membership verification
  * Protection of exclusive features
  * Scheduled maintenance management
  * User notifications for downtime
  * Request throttling for stability
  * Smart conversation flow

#### Technology Stack

- Python 3.8+
- python-telegram-bot
- SQLite
- Google Cloud Platform
- OpenWeatherMap API

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
This bot is specifically designed for the HikingsRome community and is not intended to be repurposed for other hiking groups.

However, we welcome contributions that:
- Fix bugs or technical issues
- Enhance existing features
- Improve code quality and documentation
- Add new functionality beneficial to HikingsRome members

If you'd like to contribute, feel free to open an issue describing the bug or improvement.

Note that this code is shared for transparency and educational purposes. All rights are reserved, and unauthorized redistribution or reproduction of this bot for other communities is not permitted. See [LICENSE](LICENSE.md) for details.

## Useful links:
- [Website](https://www.hikingsrome.com/) (WIP)
- [Instagram](https://www.instagram.com/hikingsrome/) (WIP)
- [Komoot](https://www.komoot.com/it-it/user/3261856743261)

## Credits

Developed with ❤️ by the HiKingsRome team.

> *"In the end, coding is like hiking: it requires patience, planning, and the ability to enjoy the journey despite unexpected obstacles."*

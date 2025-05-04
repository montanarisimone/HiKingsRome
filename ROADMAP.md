# 🗺️ Roadmap

This document outlines the development plan for HiKingsRome Bot, tracking completed features and planned enhancements.

## 🚧 In Progress

- **Admin Features**
  - [ ] Payment tracking system: Add flags for tracking payments in the participant list
  - [ ] Access control: Show admin menu only to users with admin privileges

- **User Features**
  - [ ] Waiting list for complete hike
  - [ ] My Hikes section reorganization: Create separate sections for past and upcoming hikes
  - [ ] Hike cost notification: Add cost per person information to the 1-day reminder
  - [ ] In-app payment processing: Add direct payment options within the bot (Telegram stars)
 
## 📝 Planned Features

- **Admin Features**
  - [ ] User feedback collection after hikes
  - [ ] Admin notification system enhancement
  - [ ] Optimize database queries for better performance

- **User Features**
  - [ ] Provide interactive equipment checklist
  - [ ] Gamification system (achievements, badges)
  - [ ] Car sharing matching system based on users location
  - [ ] Environmental impact statistics for car sharing
  - [ ] Hike difficulty recommendation based on user history
  - [ ] Photo sharing capabilities for hikes
  - [ ] LLM/IF..ELSE functionality for unrestricted user-bot interactions
  - [ ] Voice message processing

- **Technical Improvements**
  - [ ] Mobile app companion (Flutter/React Native)
  - [ ] Code refactoring: Improve modularity and maintainability
  - [ ] Enhanced error handling: Improve recovery from unexpected errors

## ✅ Completed Features

### Core Functionality

- **Admin Features**
  - [x] Complete admin dashboard with role-based access control
  - [x] Advanced database query system with:
    - Pre-defined queries for common operations
    - Custom query creation and saving functionality
    - Query execution with safety filters to prevent SQL injection
    - Query result formatting and display
  - [x] Hike management system:
    - Create new hikes with name, date, difficulty levels, locations, and participant limits
    - Manage existing hikes (view, cancel, reactivate)
    - View detailed participant lists with contact information
    - Set different guide quotas for each hike
  - [x] Automatic designation of admins as guides when they register for hikes
  - [x] Maintenance scheduling with:
    - Date, start time, end time, and reason fields
    - Automated notifications to all users before maintenance
    - Ability to edit or cancel scheduled maintenanc
  - [x] Admin user management with ability to promote regular users to admin status
 
- **User Features**
  - [x] Keyboard-based navigation throughout the bot
  - [x] Calendar view of all upcoming hikes with:
    - Month-based organization
    - Difficulty indicators
    - Availability status
  - [x] Privacy consent management system:
    - Basic required consents
    - Optional consents for car sharing, photos, and marketing
    - Consent version tracking
  - [x] Age verification with calendar-based selector to ensure 18+ requirement
  - [x] Complete multi-step hike registration system with:
    - Pre-filled form using profile data
    - Medical conditions reporting
    - Multiple hike selection in one form
    - Equipment confirmation
    - Car sharing preferences
    - Location selection with Rome municipality/neighborhood hierarchy
    - Custom reminder preferences
    - Additional notes field
  - [x] Registration management:
    - View all registered hikes with details
    - Cancel registrations with confirmation
    - Automatic duplicate registration prevention
    - Spot availability checking in real-time
  - [x] Smart automated reminder system:
    - Weather forecasts using OpenWeatherMap API
    - Configurable reminder timing (5 days, 2 days, or both)
    - Temperature, conditions, and precipitation probability
  - [x] Robust user profile management:
    - Name, surname, email, phone, birth date storage
    - Profile completeness verification
    - Edit capabilities for all profile fields
    - Calendar-based date picker for birth date
  - [x] Donation support (PayPal)

- **Technical Features**
  - [x] Group membership verification system
  - [x] Markdown formatting for message aesthetics
  - [x] Comprehensive error handling with user-friendly messages
  - [x] Weather API integration with accuracy indicators based on forecast timeframe
  - [x] Robust SQLite database integration with:
    - Foreign key constraints
    - Transaction support
    - Data validation
    - Parameterized queries for security
  - [x] Automatic database backup functionality
  - [x] Anti-spam protection through rate limiting

## 🐛 Known Issues

- [ ] Telegram stars payments
- [ ] Rate limiter needs fine-tuning for peak usage

---

*Last updated: May 2025*

Note: This roadmap is indicative and subject to change based on community needs and resource availability.

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
  - [x] Inline keyboards for navigation
  - [x] Calendar view for upcoming hikes
  - [x] Privacy consent management
  - [x] Age verification: System ensures only adults (18+) can register
  - [x] Hike registration system
  - [x] Users can cancel their registrations
  - [x] Automated reminders with weather information sent 5 and 2 days before hikes
  - [x] Personal profile management: Users can view and edit their personal information
  - [x] Donation support (PayPal)

- **Technical Features**
  - [x] Weather API integration: Added real-time weather forecasts for hike locations
  - [x] SQLite database integration: Implemented robust database system for storing all bot data
  - [x] Automated database backup
  - [x] Rate limiting: Implemented protection against spam and abuse

## 🐛 Known Issues

- [ ] Telegram stars payments
- [ ] Rate limiter needs fine-tuning for peak usage

---

*Last updated: May 2025*

Note: This roadmap is indicative and subject to change based on community needs and resource availability.

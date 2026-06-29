# HiKingsRome
*Nearby Rome, nature awaits!*

This repository contains everything that powers HiKingsRome — a free, non-profit hiking community for international residents and Erasmus students organising weekend hikes around Rome.

## What's in here

### 🤖 Hiky the Bot — [`Hiky_the_bot/`](Hiky_the_bot/)
A Telegram bot that handles hike registrations, reminders, the hike calendar, user profiles, weather forecasts, and a bunch of admin tooling. It's the operational backbone of the community. See the [bot README](Hiky_the_bot/README.md) for full details.

### 🌐 Website — [`docs/`](docs/)
The static website at [hikingsrome.com](https://www.hikingsrome.com), built with HTML5 + Tailwind CSS and deployed via GitHub Pages. Four pages: home, FAQ, about, and calendar (the last two are still a work in progress).

### ~~Google Script~~ *(deprecated)*
The original Google Sheets automations that managed participant data before the bot existed. Kept for reference, not maintained.

## Tech at a glance

| Component | Stack |
|-----------|-------|
| Bot | Python 3.11, python-telegram-bot, SQLite |
| Website | HTML5, Tailwind CSS v3, vanilla JS |
| Bot hosting | Docker on a home NAS |
| Website hosting | GitHub Pages |
| CI/CD | GitHub Actions |

## Useful links

- [Website](https://www.hikingsrome.com)
- [Instagram](https://www.instagram.com/hikingsrome/)
- [Komoot](https://www.komoot.com/it-it/user/3261856743261)

## Contributing

The bot is built specifically for HiKingsRome and isn't designed to be repurposed for other communities. That said, contributions are welcome if they fix bugs, improve code quality, or add features that benefit HiKingsRome members. Open an issue to start a conversation.

Code is shared for transparency and educational purposes. All rights reserved — see [LICENSE](LICENSE.md).

## Credits

Developed with ❤️ by the HiKingsRome team.
Tech by [@montanarisimone](https://github.com/montanarisimone).

> *"In the end, coding is like hiking: it requires patience, planning, and the ability to enjoy the journey despite unexpected obstacles."*

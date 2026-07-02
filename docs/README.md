# Flight Meet Agent - Documentation

## 🗺 Overview
Flight Meet Agent is a high-performance engine to find the cheapest European meetups between Milan and Riga. It uses a "near-€0" philosophy, leveraging free data for broad scans and paid APIs only for final verification.

## 🏗 Architecture
- **Storage**: SQLite (`flights.db`) with 18-hour "Smart Skip" caching.
- **Providers**: Unified layer for Ryanair, Duffel, Booking.com, Travelpayouts, and Google Flights.
- **Verification**: Tiered verification system that confirms cheap deals using high-quality sources before notifying.
- **Automation**: Designed to run as a Systemd service on AWS EC2.

## 🚀 Key Features
- **Exhaust Mode**: Scans 130+ Schengen destinations across a 4-month horizon.
- **Fair-Deal Ranking**: Prioritizes trips where costs are balanced between both travelers.
- **Mobile UI**: Full bot control with real-time status updates and monthly grouped results.
- **Self-Healing**: Robust retry logic with jitter and automatic health monitoring.

## 📁 File Structure
- `.\main.py`: Core scanning and CLI entry point.
- `.\telegram_bot.py`: Interactive mobile interface.
- `.\src\core\providers.py`: API abstraction and retry logic.
- `.\src\core\airports.py`: Massive list of 130+ Schengen airports.
- `.\src\core\scoring.py`: Ranking and fairness calculation.
- `.\src\clients\`: Raw API clients (Duffel, Booking.com, etc).

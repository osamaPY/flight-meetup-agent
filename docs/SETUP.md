# Setup and Configuration

## 🛠 Prerequisites
- Python 3.11+
- SQLite
- AWS EC2 (t3.micro recommended)

## 📥 Installation
1. `git clone https://github.com/osamaPY/flightAgent.git`
2. `pip install -r requirements.txt`
3. Configure `.env` (use `.env.example` as a base).

## 🔑 Environment Variables
| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot API token from @BotFather |
| `DUFFEL_TOKEN` | Duffel API key |
| `TRAVELPAYOUTS_TOKEN` | Travelpayouts token |
| `RAPIDAPI_KEY` | Key for Booking.com/Kiwi providers |

## 🚀 VPS Deployment
To run 24/7 as an unbreakable service:
```bash
sudo systemctl enable flightbot
sudo systemctl start flightbot
```
Check logs: `journalctl -u flightbot -f`

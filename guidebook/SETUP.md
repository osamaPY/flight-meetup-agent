# Setup And Configuration

Last updated: 2026-07-05

## Prerequisites

- Python 3.11+
- A Telegram bot token from BotFather (to run the bot)
- Optional: a DeepSeek API key for the AI concierge features
- Optional: Travelpayouts/Amadeus keys for extra free/API coverage
- Optional: a Duffel token for paid GDS quotes

SQLite is built in; the app creates `data/flights.db` automatically. It runs
fully free on Ryanair + Google without any paid keys. A free Travelpayouts
token is recommended if you host it on a server (see the note below about
datacenter IPs).

## Install

```bash
pip install -r requirements.txt
copy .env.example .env
```

On Unix-like shells, use `cp .env.example .env`.

## Important Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot only | Token from BotFather |
| `TELEGRAM_CHAT_ID` | Owner/admin | Your numeric Telegram user ID (owner) |
| `REQUIRE_INVITE_CODE` | Optional | `1` makes the bot invite-only |
| `DEFAULT_PARTICIPANT_A_LABEL` / `DEFAULT_PARTICIPANT_B_LABEL` | Optional | Labels for the fallback two-person search |
| `DEFAULT_ORIGINS_A` / `DEFAULT_ORIGINS_B` | Optional | Comma-separated default origin airport codes, e.g. `BGY,MXP,LIN` |
| `DEFAULT_SEARCH_START_OFFSET_DAYS` / `DEFAULT_SEARCH_END_OFFSET_DAYS` | Optional | Default Telegram search window relative to today |
| `DEFAULT_MIN_NIGHTS` / `DEFAULT_MAX_NIGHTS` | Optional | Default trip length range |
| `DEFAULT_LUGGAGE` | Optional | `none`, `carryon_10kg`, or `checked_23kg` |
| `DEFAULT_INCLUDE_TRANSFERS` | Optional | `1` includes airport transfers in all-in pricing |
| `DEFAULT_DIRECT_ONLY` / `DEFAULT_MAX_STOPS` | Optional | Default flight stop policy |
| `DEFAULT_DESTINATION_UNIVERSE` | Optional | `europe`, `schengen`, or `anywhere` |
| `DEEPSEEK_API_KEY` | Optional | Enables the AI concierge; blank disables it |
| `DEEPSEEK_MODEL` | Optional | Defaults to `deepseek-chat` |
| `TRAVELPAYOUTS_TOKEN` | Optional | Free flight-data API; works from a server IP where scraping is blocked |
| `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` | Optional | Enables Amadeus verification provider |
| `AMADEUS_HOSTNAME` | Optional | `test` by default; use `production` only if provisioned |
| `DUFFEL_TOKEN` | Optional | Enables paid Duffel provider for owner searches |
| `DUFFEL_DAILY_BUDGET` | Optional | Daily Duffel safety cap, default 50 |
| `TARGET_PRICE_EUR` | Optional | Price threshold used by older CLI flows |
| `MAX_API_CALLS_PER_RUN` | Optional | Provider-call safety cap for full scans; default 5000, set 0 for unlimited/brute-force |
| `SEARCH_DATE_VARIANT_MODE` | Optional | `auto` by default; capped searches prioritize exact-date breadth, unlimited searches use full flexible dates |

`.env.example` lists exactly these. Copy it to `.env` and fill in what you need;
at minimum the bot needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Never
commit your real `.env` (it is gitignored). Owner checks are based on
`TELEGRAM_CHAT_ID`.

## Make It Yours

For a portfolio fork, keep secrets out of Git and customize via `.env`. The
defaults above control the first search panel users see, plus the fallback CLI
search. Telegram groups remain fully dynamic: users can add their own members,
origin airports, dates, nights, luggage, transfer preference, direct-only mode,
and destination scope without changing code.

## Run The Bot

```bash
python telegram_bot.py
```

Recommended first flow:

1. Send `/start`.
2. Tap New group and type a name.
3. Enter your airports (a city name like `milan` works, or codes like `BGY, MXP`).
4. Add friends: tap Add a friend to enter someone's airports yourself, or tap
   Invite a friend to share a one-tap join link. Manual friends count in the
   search but are never messaged; remove them anytime under More.
5. Tap Find flights for a one-tap search with smart defaults, or Pick dates /
   options first to choose dates, nights, luggage, direct-only, and region.
6. Tap See results, then a city, for the full breakdown; use Check live price
   before booking.
7. Stuck? Tap Ask a question (needs a DeepSeek key) and type in plain words;
   the AI helper answers how-to and travel questions.

If `REQUIRE_INVITE_CODE=1`, only invited users can use the bot.

## Deploy It 24/7 (VPS / AWS Free Tier)

To keep the bot running around the clock on a small Linux server, see
[../deploy/README.md](../deploy/README.md). In short: clone the repo, run
`bash deploy/setup.sh`, add your token to `.env`, and a `systemd` service keeps
it alive across crashes and reboots. The bot polls Telegram, so no inbound
ports are needed.

Server note: flight sources like Google Flights (and some airline sites) block
datacenter IPs, so on a cloud server lean on the API-based sources that are not
IP-sensitive: Ryanair's public API and Travelpayouts (set `TRAVELPAYOUTS_TOKEN`).
See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for the full story.

## Run The Tests

```bash
python -m pytest -q
```

71 offline tests, no network or API keys required (they also run in CI).

## Run CLI

```bash
python main.py
python main.py booking-mode
python main.py health
python main.py inspect-db
python main.py selftest
```

CLI flows are still useful for debugging and for the original default search.

## Run API

```bash
python flight_api_server.py
```

Open `http://127.0.0.1:8000`.

Useful endpoints:

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/search?origin=BGY&destination=VIE&out=2026-07-25&return=2026-07-27"
curl "http://127.0.0.1:8000/groups/<group_id>"
curl "http://127.0.0.1:8000/searches/<search_id>/results"
```

## Operational Scripts

```bash
python scripts/nightly_surface.py
python scripts/canary.py
python scripts/dashboard.py
python scripts/ical_export.py 5
python scripts/backup_db.py
python scripts/kick_vps.py
```

## Clean Slate

To clear search results:

```bash
python -c "from src.core.storage import Storage; s=Storage(); s.clear_results()"
```

This does not necessarily remove all users/groups/search metadata. For a total
database reset, stop the app and remove `data/flights.db` and its WAL/SHM files.

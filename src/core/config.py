import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List, Tuple, Optional

load_dotenv()


def _csv_env(name: str, default: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    values = [part.strip().upper() for part in raw.split(",") if part.strip()]
    return values or default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class DateWindow:
    depart_earliest: str
    depart_latest: str
    min_nights: int
    max_nights: int

class Config:
    # ── v6: no more hardcoded origins ──
    # Origins are now per-search via SearchRequest (src/core/search_request.py).
    # These remain as CONVENIENCE DEFAULTS only - used when no SearchRequest is provided
    # (CLI menu, backward compat, scripts).
    DEFAULT_ORIGINS_A = _csv_env("DEFAULT_ORIGINS_A", ["BGY", "MXP", "LIN"])
    DEFAULT_ORIGINS_B = _csv_env("DEFAULT_ORIGINS_B", ["RIX"])
    DEFAULT_PARTICIPANT_A_LABEL = os.getenv("DEFAULT_PARTICIPANT_A_LABEL", "You")
    DEFAULT_PARTICIPANT_B_LABEL = os.getenv("DEFAULT_PARTICIPANT_B_LABEL", "Friend")

    CURRENCY = "EUR"

    TARGET_PRICE_EUR = _int_env("TARGET_PRICE_EUR", 200)
    # Provider-call budget for one search. The search fans out across date
    # variants, participant origins, and providers, so 300 can stop after only
    # a few real cities. Set 0 for an unlimited/brute-force sweep.
    MAX_API_CALLS_PER_RUN = _int_env("MAX_API_CALLS_PER_RUN", 5000)
    # auto: broad exact-date sweep for finite budgets, full flexible dates when
    # MAX_API_CALLS_PER_RUN=0. Other values: exact, flexible, all.
    SEARCH_DATE_VARIANT_MODE = os.getenv("SEARCH_DATE_VARIANT_MODE", "auto").lower()

    DEFAULT_SEARCH_START_OFFSET_DAYS = _int_env("DEFAULT_SEARCH_START_OFFSET_DAYS", 14)
    DEFAULT_SEARCH_END_OFFSET_DAYS = _int_env("DEFAULT_SEARCH_END_OFFSET_DAYS", 42)
    DEFAULT_MIN_NIGHTS = _int_env("DEFAULT_MIN_NIGHTS", 2)
    DEFAULT_MAX_NIGHTS = _int_env("DEFAULT_MAX_NIGHTS", 4)
    DEFAULT_LUGGAGE = os.getenv("DEFAULT_LUGGAGE", "carryon_10kg")
    DEFAULT_INCLUDE_TRANSFERS = _bool_env("DEFAULT_INCLUDE_TRANSFERS", True)
    DEFAULT_DIRECT_ONLY = _bool_env("DEFAULT_DIRECT_ONLY", False)
    DEFAULT_MAX_STOPS = _int_env("DEFAULT_MAX_STOPS", 2)
    DEFAULT_DESTINATION_UNIVERSE = os.getenv("DEFAULT_DESTINATION_UNIVERSE", "europe")

    # ── Telegram ──
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # ── Travelpayouts / Aviasales (optional, FREE flight-data API) ──
    # Works from a VPS IP where Google/airline sites get blocked. Cached prices.
    # Free affiliate token at travelpayouts.com.
    TRAVELPAYOUTS_TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN", "")

    # ── Duffel (optional paid GDS provider) ──
    DUFFEL_TOKEN = os.getenv("DUFFEL_TOKEN")

    # ── Amadeus Self-Service (optional, FREE test tier - real GDS offers) ──
    # Free key at developers.amadeus.com. HOSTNAME is "test" (free) or "production".
    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", "")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", "")
    AMADEUS_HOSTNAME = os.getenv("AMADEUS_HOSTNAME", "test")

    # ── DeepSeek LLM (optional AI concierge in the Telegram bot) ──
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    REQUIRE_INVITE_CODE = _bool_env("REQUIRE_INVITE_CODE", False)

    @staticmethod
    def generate_date_windows(
        start: str = "2026-07-15",
        end: str = "2026-08-12",
        min_nights: int = 2,
        max_nights: int = 4,
    ) -> List[DateWindow]:
        """Generate 1-week DateWindow chunks for any date range.

        v6: Fully parameterized - no hardcoded dates.
        """
        windows = []
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")

        current = start_dt
        while current <= end_dt:
            chunk_end = current + timedelta(days=6)
            if chunk_end > end_dt:
                chunk_end = end_dt
            windows.append(DateWindow(
                depart_earliest=current.strftime("%Y-%m-%d"),
                depart_latest=chunk_end.strftime("%Y-%m-%d"),
                min_nights=min_nights,
                max_nights=max_nights,
            ))
            current = chunk_end + timedelta(days=1)

        return windows

    @staticmethod
    def generate_holiday_windows() -> List[DateWindow]:
        """Backward-compatible: the original Jul 15 - Aug 12, 2026 holiday windows."""
        return Config.generate_date_windows(
            start="2026-07-15",
            end="2026-08-12",
            min_nights=2,
            max_nights=4,
        )

# Backward-compatible module-level constant (used by scripts that haven't been updated yet)
DATE_WINDOWS = Config.generate_holiday_windows()

# Deprecated aliases - kept for scripts that still reference them.
# New code should use SearchRequest from src.core.search_request.
ORIGINS_A = Config.DEFAULT_ORIGINS_A
ORIGINS_B = Config.DEFAULT_ORIGINS_B

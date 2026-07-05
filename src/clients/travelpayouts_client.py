"""Travelpayouts (Aviasales) flight-data client.

Uses the free Aviasales Data API (`prices_for_dates`), which returns the
cheapest cached fares Aviasales has seen for a route and date. It is a real
HTTP API - not a scrape - so it works from a datacenter/VPS IP where Google
Flights and some airline sites get blocked. Prices are cached (up to ~7 days),
so results are flagged approximate: good for ranking cities, verify before
booking.

Free with a Travelpayouts affiliate account (TRAVELPAYOUTS_TOKEN). Fully
fail-soft: any error returns None/[] so the search never breaks.

Docs: https://support.travelpayouts.com/hc/en-us/sections/201008338
"""

from __future__ import annotations

from typing import List, Optional

import requests

from src.core.scoring import Flight

BASE = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


class TravelpayoutsClient:
    def __init__(self, token: Optional[str] = None):
        from src.core.config import Config
        self.token = token if token is not None else (Config.TRAVELPAYOUTS_TOKEN or "")

    def available(self) -> bool:
        return bool(self.token)

    def _get(self, params: dict) -> list:
        params = {**params, "token": self.token, "currency": "eur"}
        r = requests.get(BASE, params=params, timeout=12)
        if r.status_code != 200:
            return []
        body = r.json()
        if not body.get("success"):
            return []
        return body.get("data", []) or []

    def search_round_trip(self, origin: str, dest: str,
                          out_date: str, in_date: str) -> Optional[Flight]:
        """Cheapest cached round-trip fare for the requested dates.

        The cached Data API is month-granular (exact-date queries come back
        empty), so we query by month and prefer a row that matches the exact
        requested dates. If none matches, we fall back to the cheapest
        round-trip that month as an estimate, stamped with the requested dates
        so it still aligns with the rest of the group. Always approximate.
        """
        if not self.token:
            return None
        try:
            rows = self._get({
                "origin": origin, "destination": dest,
                "departure_at": out_date[:7], "return_at": in_date[:7],
                "one_way": "false", "direct": "false",
                "sorting": "price", "unique": "false", "limit": 100,
            })
            rows = [r for r in rows if r.get("return_at")]   # round trips only
            if not rows:
                return None
            exact = [r for r in rows
                     if (r.get("departure_at", "")[:10] == out_date
                         and r.get("return_at", "")[:10] == in_date)]
            best = min(exact or rows, key=lambda x: x.get("price", 1e9))
            link = best.get("link", "")
            deep = f"https://www.aviasales.com{link}" if link.startswith("/") else link
            return Flight(
                origin=origin,
                destination=dest,
                price=float(best.get("price", 0) or 0),
                # Always the requested dates, so all participants line up for
                # group scoring (the price is a cached estimate either way).
                outbound_date=out_date,
                return_date=in_date,
                stops=int(best.get("transfers", 0) or 0),
                arrival_time="",
                departure_time=(best.get("departure_at", "") or "")[:16].replace("T", " "),
                source="travelpayouts",
                airline=best.get("airline", "") or "",
                flight_number=str(best.get("flight_number", "") or ""),
                currency="EUR",
                is_approximate=True,        # cached price - verify before booking
                cabin_bag_included=False,
                deep_link=deep,
            )
        except Exception:
            return None

    def health(self) -> bool:
        if not self.token:
            return False
        try:
            r = requests.get(BASE, params={
                "origin": "BGY", "destination": "VIE",
                "departure_at": "2026-08", "token": self.token,
                "currency": "eur", "limit": 1,
            }, timeout=8)
            return r.status_code == 200
        except Exception:
            return False

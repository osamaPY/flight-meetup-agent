"""Amadeus Self-Service client - free-tier GDS flight offers.

Amadeus gives real, multi-airline round-trip offers. The test environment is
free (no card) with a monthly quota; sign up at developers.amadeus.com, create
a Self-Service app, and put the API key/secret in .env as AMADEUS_CLIENT_ID /
AMADEUS_CLIENT_SECRET.

Auth is OAuth2 client-credentials; the token is cached until it expires.
Everything fails soft (returns None) so a missing key or an API hiccup never
breaks a search.

Endpoints:
  POST {host}/v1/security/oauth2/token          -> access token
  GET  {host}/v2/shopping/flight-offers         -> priced offers
Host is https://test.api.amadeus.com (free) or https://api.amadeus.com (prod).
"""

from __future__ import annotations

import time
import requests
from typing import Optional

from src.core.config import Config
from src.core.scoring import Flight
from src.core.logger import log_error


class AmadeusClient:
    def __init__(self, client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 hostname: Optional[str] = None, timeout: int = 12):
        self.client_id = client_id or Config.AMADEUS_CLIENT_ID or ""
        self.client_secret = client_secret or Config.AMADEUS_CLIENT_SECRET or ""
        # "test" (free) or "production"
        env = (hostname or Config.AMADEUS_HOSTNAME or "test").strip().lower()
        self.host = ("https://api.amadeus.com" if env == "production"
                     else "https://test.api.amadeus.com")
        self.timeout = timeout
        self._token = ""
        self._token_exp = 0.0
        self._session = requests.Session()

    def available(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _access_token(self) -> Optional[str]:
        """Fetch/reuse an OAuth2 token (cached until ~30s before expiry)."""
        if self._token and time.time() < self._token_exp:
            return self._token
        if not self.available():
            return None
        try:
            r = self._session.post(
                f"{self.host}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
            )
            if r.status_code != 200:
                log_error(f"Amadeus auth HTTP {r.status_code}: {r.text[:160]}")
                return None
            data = r.json()
            self._token = data.get("access_token", "")
            self._token_exp = time.time() + int(data.get("expires_in", 0)) - 30
            return self._token or None
        except Exception as exc:
            log_error(f"Amadeus auth failed: {exc}")
            return None

    def search_round_trip(self, origin: str, destination: str,
                          out_date: str, ret_date: str) -> Optional[Flight]:
        """Cheapest priced round-trip offer, or None."""
        token = self._access_token()
        if not token:
            return None
        try:
            r = self._session.get(
                f"{self.host}/v2/shopping/flight-offers",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDate": out_date,
                    "returnDate": ret_date,
                    "adults": 1,
                    "currencyCode": "EUR",
                    "max": 5,
                },
                timeout=self.timeout,
            )
            if r.status_code != 200:
                log_error(f"Amadeus offers HTTP {r.status_code}: {r.text[:160]}")
                return None
            offers = r.json().get("data", [])
            return self._cheapest_flight(offers, origin, destination,
                                         out_date, ret_date)
        except Exception as exc:
            log_error(f"Amadeus search {origin}->{destination}: {exc}")
            return None

    @staticmethod
    def _cheapest_flight(offers, origin, destination, out_date, ret_date):
        best = None
        best_price = None
        for off in offers:
            try:
                price = float(off.get("price", {}).get("grandTotal")
                              or off.get("price", {}).get("total"))
            except (TypeError, ValueError):
                continue
            if best_price is None or price < best_price:
                best_price, best = price, off
        if not best:
            return None

        itins = best.get("itineraries", [])
        out_segs = itins[0].get("segments", []) if itins else []
        ret_segs = itins[1].get("segments", []) if len(itins) > 1 else []
        stops = max(0, len(out_segs) - 1) + max(0, len(ret_segs) - 1)
        airline = (best.get("validatingAirlineCodes") or [""])[0]
        arr = (out_segs[-1].get("arrival", {}).get("at", "")
               if out_segs else "").replace("T", " ")[:16]
        dep = (out_segs[0].get("departure", {}).get("at", "")
               if out_segs else "").replace("T", " ")[:16]

        return Flight(
            origin=origin, destination=destination, price=best_price,
            outbound_date=out_date, return_date=ret_date, stops=stops,
            arrival_time=arr or f"{out_date} 12:00",
            departure_time=dep or f"{out_date} 06:00",
            source="amadeus", airline=airline, currency="EUR",
            cabin_bag_included=True,   # GDS fares usually include a cabin bag
        )

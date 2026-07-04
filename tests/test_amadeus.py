"""Offline tests for the Amadeus client and provider.

No key and no network: the HTTP session is faked, so we test the OAuth flow,
response parsing (into a Flight), and the fail-soft behaviour. The provider is
only registered when a key is configured, so we test the gate too.

Run:  python -m pytest tests/test_amadeus.py -q
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.utils.compat  # noqa

from src.clients.amadeus_client import AmadeusClient
from src.core import provider_registry as reg


# A trimmed but real-shaped Flight Offers Search v2 response.
OFFERS = {
    "data": [
        {
            "price": {"currency": "EUR", "grandTotal": "175.30", "total": "175.30"},
            "validatingAirlineCodes": ["LH"],
            "itineraries": [
                {"segments": [
                    {"departure": {"iataCode": "BGY", "at": "2026-08-03T20:20:00"},
                     "arrival": {"iataCode": "VIE", "at": "2026-08-03T21:45:00"},
                     "carrierCode": "LH", "number": "111"}]},
                {"segments": [
                    {"departure": {"iataCode": "VIE", "at": "2026-08-06T09:00:00"},
                     "arrival": {"iataCode": "BGY", "at": "2026-08-06T10:25:00"},
                     "carrierCode": "LH", "number": "112"}]},
            ],
        },
        {
            "price": {"currency": "EUR", "grandTotal": "142.00"},
            "validatingAirlineCodes": ["FR"],
            "itineraries": [
                {"segments": [
                    {"departure": {"iataCode": "BGY", "at": "2026-08-03T06:10:00"},
                     "arrival": {"iataCode": "VIE", "at": "2026-08-03T07:35:00"},
                     "carrierCode": "FR", "number": "8001", "numberOfStops": 0}]},
                {"segments": [
                    {"departure": {"iataCode": "VIE", "at": "2026-08-06T22:00:00"},
                     "arrival": {"iataCode": "BGY", "at": "2026-08-06T23:25:00"},
                     "carrierCode": "FR", "number": "8002"}]},
            ],
        },
    ]
}


class _Resp:
    def __init__(self, code, payload):
        self.status_code = code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class _FakeSession:
    """Fakes token POST then offers GET."""
    def __init__(self):
        self.calls = []

    def post(self, url, **kw):
        self.calls.append(("POST", url))
        return _Resp(200, {"access_token": "tok123", "expires_in": 1799})

    def get(self, url, **kw):
        self.calls.append(("GET", url, kw.get("params")))
        return _Resp(200, OFFERS)


def _client_with_fake():
    c = AmadeusClient(client_id="id", client_secret="secret")
    c._session = _FakeSession()
    return c


def test_available_gate():
    assert AmadeusClient(client_id="id", client_secret="s").available()
    assert not AmadeusClient(client_id="", client_secret="").available()


def test_parses_cheapest_offer_into_flight():
    c = _client_with_fake()
    f = c.search_round_trip("BGY", "VIE", "2026-08-03", "2026-08-06")
    assert f is not None
    assert f.price == 142.0                    # cheaper of the two offers
    assert f.airline == "FR"
    assert f.origin == "BGY" and f.destination == "VIE"
    assert f.outbound_date == "2026-08-03" and f.return_date == "2026-08-06"
    assert f.source == "amadeus"
    assert f.stops == 0
    assert f.arrival_time.startswith("2026-08-03")


def test_token_is_cached():
    c = _client_with_fake()
    c.search_round_trip("BGY", "VIE", "2026-08-03", "2026-08-06")
    c.search_round_trip("BGY", "BCN", "2026-08-03", "2026-08-06")
    posts = [x for x in c._session.calls if x[0] == "POST"]
    assert len(posts) == 1, "token should be fetched once and reused"


def test_no_key_returns_none_not_error():
    c = AmadeusClient(client_id="", client_secret="")
    assert c.search_round_trip("BGY", "VIE", "2026-08-03", "2026-08-06") is None


def test_registry_amadeus_disabled_without_key(monkeypatch):
    from src.core.config import Config
    monkeypatch.setattr(Config, "AMADEUS_CLIENT_ID", "", raising=False)
    monkeypatch.setattr(Config, "AMADEUS_CLIENT_SECRET", "", raising=False)
    reg._REGISTRY = None                        # force rebuild with patched config
    names = [p.name() for p in reg.build_verification_providers()]
    assert "Amadeus" not in names
    reg._REGISTRY = None                        # reset for other tests


def test_registry_amadeus_enabled_with_key(monkeypatch):
    from src.core.config import Config
    monkeypatch.setattr(Config, "AMADEUS_CLIENT_ID", "id", raising=False)
    monkeypatch.setattr(Config, "AMADEUS_CLIENT_SECRET", "secret", raising=False)
    reg._REGISTRY = None
    caps = {c.key for c in reg.all_capabilities()}
    assert "amadeus" in caps
    names = [p.name() for p in reg.build_verification_providers()]
    assert "Amadeus" in names
    reg._REGISTRY = None

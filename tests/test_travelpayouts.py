"""Offline tests for the Travelpayouts client + provider. No network:
requests.get is monkeypatched. Verifies parsing, cheapest-pick, fail-soft,
and that the provider is token-gated in the registry.

Run:  python -m pytest tests/test_travelpayouts.py -q
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.utils.compat  # noqa

from src.clients import travelpayouts_client as tp


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


_SAMPLE = {
    "success": True,
    "data": [
        {"origin": "BGY", "destination": "VIE", "price": 210,
         "airline": "OS", "flight_number": "123", "transfers": 1,
         "departure_at": "2026-08-03T20:20:00+02:00",
         "return_at": "2026-08-06T09:00:00+02:00", "link": "/s/BGYVIE"},
        {"origin": "BGY", "destination": "VIE", "price": 96,
         "airline": "W6", "flight_number": "456", "transfers": 0,
         "departure_at": "2026-08-03T06:00:00+02:00",
         "return_at": "2026-08-06T22:00:00+02:00", "link": "/s/cheap"},
    ],
}


def test_round_trip_picks_cheapest_and_parses(monkeypatch):
    monkeypatch.setattr(tp.requests, "get", lambda *a, **k: _Resp(_SAMPLE))
    client = tp.TravelpayoutsClient(token="x")
    f = client.search_round_trip("BGY", "VIE", "2026-08-03", "2026-08-06")
    assert f is not None
    assert f.price == 96.0                 # cheapest of the two
    assert f.airline == "W6"
    assert f.origin == "BGY" and f.destination == "VIE"
    assert f.outbound_date == "2026-08-03" and f.return_date == "2026-08-06"
    assert f.source == "travelpayouts"
    assert f.is_approximate is True        # cached - must be flagged
    assert f.deep_link.startswith("https://www.aviasales.com/s/cheap")


def test_no_token_returns_none(monkeypatch):
    client = tp.TravelpayoutsClient(token="")
    assert client.search_round_trip("BGY", "VIE", "2026-08-03", "2026-08-06") is None
    assert client.available() is False


def test_failsoft_on_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(tp.requests, "get", boom)
    client = tp.TravelpayoutsClient(token="x")
    assert client.search_round_trip("BGY", "VIE", "2026-08-03", "2026-08-06") is None


def test_empty_data_returns_none(monkeypatch):
    monkeypatch.setattr(tp.requests, "get",
                        lambda *a, **k: _Resp({"success": True, "data": []}))
    client = tp.TravelpayoutsClient(token="x")
    assert client.search_round_trip("BGY", "VIE", "2026-08-03", "2026-08-06") is None


def test_provider_token_gated():
    """Registry only builds Travelpayouts when a token is configured."""
    from src.core import provider_registry as reg
    from src.core.config import Config

    names = [c.key for c in reg.all_capabilities()]
    assert "travelpayouts" in names        # registered

    built = [p.name() for p in reg.build_providers(include_paid=False)]
    if Config.TRAVELPAYOUTS_TOKEN:
        assert "Travelpayouts" in built
    else:
        assert "Travelpayouts" not in built  # gated off with no token

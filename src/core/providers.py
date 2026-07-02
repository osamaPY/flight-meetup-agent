import time
import random
from abc import ABC, abstractmethod
from typing import List, Optional, Any
from src.core.scoring import Flight
from src.clients.ryanair_client import RyanairClient
from src.clients.travelpayouts_client import TravelpayoutsClient
from src.clients.serpapi_client import SerpApiClient
from src.clients.rapidapi_client import RapidApiClient
from src.clients.flightapi_client import FlightApiClient
from src.clients.kiwi_rapidapi_client import KiwiRapidApiClient
from src.clients.duffel_client import DuffelClient
from src.clients.booking_com_client import BookingComClient
from src.core.config import Config

class FlightProvider(ABC):
    def __init__(self):
        self._health_reason = "Unknown"

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        pass

    def get_health_reason(self) -> str:
        return self._health_reason

    def _retry_search(self, search_fn, *args, retries=2):
        for i in range(retries + 1):
            try:
                result = search_fn(*args)
                if result: return result
            except Exception as e:
                if i == retries: raise e
                time.sleep(1.0 + random.random())
        return None

class RyanairProvider(FlightProvider):
    def __init__(self):
        super().__init__()
        self.client = RyanairClient(debug=False)
    
    def name(self) -> str:
        return "Ryanair"

    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        try:
            return self._retry_search(self.client.round_trip_fare, origin, destination, out_from, out_to, in_from, in_to)
        except Exception:
            return None

    def is_healthy(self) -> bool:
        import requests
        try:
            res = requests.get("https://services-api.ryanair.com/farfnd/3/oneWayFares", timeout=5)
            if res.status_code in [200, 400]:
                return True
            self._health_reason = f"HTTP {res.status_code}"
            return False
        except Exception as e:
            self._health_reason = str(e)
            return False

class TravelpayoutsProvider(FlightProvider):
    def __init__(self, token: str):
        super().__init__()
        self.client = TravelpayoutsClient(token)
    
    def name(self) -> str:
        return "Travelpayouts"

    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        def do_search():
            fares = self.client.get_cheapest_by_origin(origin)
            matches = [f for f in fares if f.destination == destination and f.outbound_date == out_from]
            if matches:
                best = min(matches, key=lambda x: x.price)
                if best.return_date: return best
            return None
        try:
            return self._retry_search(do_search)
        except Exception:
            return None

    def is_healthy(self) -> bool:
        import requests
        if not self.client.token: 
            self._health_reason = "Missing Token"
            return False
        try:
            res = requests.get(f"https://api.travelpayouts.com/v2/prices/latest?token={self.client.token}", timeout=5)
            if res.status_code in [200, 401]:
                return True
            self._health_reason = f"HTTP {res.status_code}"
            return False
        except Exception as e:
            self._health_reason = str(e)
            return False

class SerpApiProvider(FlightProvider):
    def __init__(self, api_key: str, storage: Any):
        super().__init__()
        self.client = SerpApiClient(api_key, storage)
    
    def name(self) -> str:
        return "GoogleFlights (SerpApi)"

    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        try:
            return self._retry_search(self.client.verify_round_trip, origin, destination, out_from, in_from)
        except Exception:
            return None

    def is_healthy(self) -> bool:
        if not self.client.api_key:
            self._health_reason = "Missing Key"
            return False
        usage = self.client.storage.get_serpapi_usage()
        if usage >= Config.SERPAPI_MONTHLY_BUDGET:
            self._health_reason = f"Budget Exhausted ({usage}/{Config.SERPAPI_MONTHLY_BUDGET})"
            return False
        return True

class RapidApiProvider(FlightProvider):
    def __init__(self, api_key: str):
        super().__init__()
        self.client = RapidApiClient(api_key)
    
    def name(self) -> str:
        return "SkyScrapper (RapidAPI)"

    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        def do_search():
            fares = self.client.search_flights(origin, destination, out_from, in_from)
            return min(fares, key=lambda x: x.price) if fares else None
        try:
            return self._retry_search(do_search)
        except Exception:
            return None

    def is_healthy(self) -> bool:
        if not self.client.api_key:
            self._health_reason = "Missing Key"
            return False
        return True

class DuffelProvider(FlightProvider):
    def __init__(self, token: str):
        super().__init__()
        self.client = DuffelClient(token)
    
    def name(self) -> str:
        return "Duffel"

    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        def do_search():
            fares = self.client.search_round_trip(origin, destination, out_from, in_from)
            return fares[0] if fares else None
        try:
            return self._retry_search(do_search)
        except Exception:
            return None

    def is_healthy(self) -> bool:
        import requests
        if not self.client.token: 
            self._health_reason = "Missing Token"
            return False
        try:
            res = requests.get("https://api.duffel.com/air/airlines", headers=self.client.headers, timeout=5)
            if res.status_code == 200: return True
            self._health_reason = f"HTTP {res.status_code}"
            return False
        except Exception as e:
            self._health_reason = str(e)
            return False

class FlightApiProvider(FlightProvider):
    def __init__(self, api_key: str):
        super().__init__()
        self.client = FlightApiClient(api_key)
    
    def name(self) -> str:
        return "FlightAPI.io"

    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        def do_search():
            fares = self.client.search_round_trip(origin, destination, out_from, in_from)
            return min(fares, key=lambda x: x.price) if fares else None
        try:
            return self._retry_search(do_search)
        except Exception:
            return None

    def is_healthy(self) -> bool:
        if not self.client.api_key:
            self._health_reason = "Missing Key"
            return False
        return True

class KiwiRapidApiProvider(FlightProvider):
    def __init__(self, api_key: str):
        super().__init__()
        self.client = KiwiRapidApiClient(api_key)
    
    def name(self) -> str:
        return "Kiwi (RapidAPI)"

    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        def do_search():
            fares = self.client.search_round_trip(origin, destination, out_from, in_from)
            return min(fares, key=lambda x: x.price) if fares else None
        try:
            return self._retry_search(do_search)
        except Exception:
            return None

    def is_healthy(self) -> bool:
        if not self.client.api_key:
            self._health_reason = "Missing Key"
            return False
        return True

class BookingComProvider(FlightProvider):
    def __init__(self, api_key: str):
        super().__init__()
        self.client = BookingComClient(api_key)
    
    def name(self) -> str:
        return "Booking.com (RapidAPI)"

    def search_round_trip(self, origin: str, destination: str, out_from: str, out_to: str, in_from: str, in_to: str) -> Optional[Flight]:
        def do_search():
            fares = self.client.search_round_trip(origin, destination, out_from, in_from)
            return min(fares, key=lambda x: x.price) if fares else None
        try:
            return self._retry_search(do_search)
        except Exception:
            return None

    def is_healthy(self) -> bool:
        if not self.client.api_key:
            self._health_reason = "Missing Key"
            return False
        return True


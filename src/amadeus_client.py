import time
import logging
import requests

logger = logging.getLogger(__name__)

AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_BASE_URL = "https://test.api.amadeus.com"


class AmadeusAPIError(Exception):
    def __init__(self, status_code: int, message: str, detail: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or {}


class AmadeusClient:
    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def _authenticate(self) -> None:
        resp = requests.post(
            AMADEUS_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise AmadeusAPIError(resp.status_code, f"Auth failed: {resp.text}")
        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + data["expires_in"] - 30

    def _get_headers(self) -> dict[str, str]:
        if self._token is None or time.time() >= self._token_expiry:
            self._authenticate()
        return {"Authorization": f"Bearer {self._token}"}

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        for attempt in range(3):
            try:
                resp = requests.request(method, url, timeout=30, **kwargs)
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("Rate limited, waiting %ds (attempt %d)", wait, attempt + 1)
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    wait = 2 ** attempt
                    logger.warning("Server error %d, retrying in %ds", resp.status_code, wait)
                    time.sleep(wait)
                    continue
                return resp
            except requests.RequestException as exc:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
                logger.warning("Request error, retrying: %s", exc)
        return resp  # type: ignore[return-value]

    def get_cheapest_dates(
        self,
        origin: str,
        destination: str,
        year_month: str,
        min_duration: int = 21,
        max_duration: int = 30,
    ) -> list[dict]:
        """Return cheapest departure/return date pairs for a given month."""
        url = f"{AMADEUS_BASE_URL}/v1/shopping/flight-dates"
        params = {
            "origin": origin,
            "destination": destination,
            "departureDate": year_month,
            "duration": f"{min_duration},{max_duration}",
            "nonStop": "false",
            "viewBy": "DATE",
        }
        resp = self._request_with_retry("GET", url, headers=self._get_headers(), params=params)
        if resp.status_code == 200:
            return resp.json().get("data", [])
        if resp.status_code == 400:
            logger.info("No results for %s→%s in %s", origin, destination, year_month)
            return []
        raise AmadeusAPIError(resp.status_code, resp.text, resp.json() if resp.content else {})

    def search_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        adults: int = 2,
        max_results: int = 5,
        currency_code: str = "BRL",
    ) -> dict:
        """Return detailed flight offers for specific dates."""
        url = f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers"
        body = {
            "currencyCode": currency_code,
            "originDestinations": [
                {
                    "id": "1",
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDateTimeRange": {"date": departure_date},
                },
                {
                    "id": "2",
                    "originLocationCode": destination,
                    "destinationLocationCode": origin,
                    "departureDateTimeRange": {"date": return_date},
                },
            ],
            "travelers": [
                {"id": str(i + 1), "travelerType": "ADULT"} for i in range(adults)
            ],
            "sources": ["GDS"],
            "searchCriteria": {"maxFlightOffers": max_results},
        }
        resp = self._request_with_retry(
            "POST", url, headers=self._get_headers(), json=body
        )
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (400, 404):
            logger.info("No offers for %s→%s on %s", origin, destination, departure_date)
            return {}
        raise AmadeusAPIError(resp.status_code, resp.text, resp.json() if resp.content else {})

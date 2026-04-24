"""
SerpAPI Google Flights provider.

Sign up at serpapi.com - free plan includes ~100 searches/month.
Paid plans start at $75/month for 5,000 searches.

HOW IT WORKS:
  SerpAPI scrapes google.com/flights and returns the results as structured JSON.
  This is completely different from Serper.dev (which scraped Google Search text
  snippets and returned random unrelated prices).

  With deep_search=true, prices are 100% identical to what you see in the Google
  Flights browser UI. Without it, prices can be off by up to 4x on some routes.

Set SERPAPI_KEY in .env to activate.
"""
from __future__ import annotations

import asyncio
from datetime import date
from time import monotonic
from urllib.parse import quote

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.logging import get_logger
from app.providers.base import ProviderResult

log = get_logger(__name__)

_BASE_URL = "https://serpapi.com/search.json"


class ProviderQuotaExhaustedError(RuntimeError):
    """SerpAPI plan has run out of searches for the month."""


class ProviderAuthError(RuntimeError):
    """SerpAPI key is missing, invalid, or revoked."""


class ProviderRateLimitedError(RuntimeError):
    """SerpAPI is temporarily throttling requests; retry later."""


def _extract_body_error(resp: httpx.Response) -> str | None:
    try:
        payload = resp.json()
    except Exception:
        return None
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, str) and err.strip():
            return err.strip()
    return None


def _classify_error_message(message: str) -> type[RuntimeError]:
    """Map a SerpAPI error string to a specific RuntimeError subclass."""
    lowered = message.lower()
    if "run out of searches" in lowered or "plan requires" in lowered or "upgrade" in lowered:
        return ProviderQuotaExhaustedError
    if "invalid api key" in lowered or "missing api_key" in lowered or "unauthorized" in lowered:
        return ProviderAuthError
    if "rate limit" in lowered or "too many requests" in lowered:
        return ProviderRateLimitedError
    return RuntimeError


class SerpApiProvider:
    name = "serpapi"

    def __init__(
        self,
        api_key: str,
        timeout: int = 60,
        deep_search: bool = True,
        max_retries: int = 3,
        concurrency_limit: int = 2,
        min_delay_seconds: float = 1.0,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._deep_search = deep_search
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=self._timeout)
        self._semaphore = asyncio.Semaphore(max(1, concurrency_limit))
        self._min_delay_seconds = max(0.0, min_delay_seconds)
        self._throttle_lock = asyncio.Lock()
        self._next_request_at = 0.0

    def is_configured(self) -> bool:
        return bool(self._api_key)

    # SerpAPI stops param: 0=any, 1=nonstop only, 2=1-stop-or-fewer, 3=2-stops-or-fewer
    _STOPS_MAP: dict[int | None, int] = {None: 0, 0: 1, 1: 2, 2: 3}

    async def search_one_way(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        adults: int = 1,
        cabin: str = "economy",
        currency: str = "USD",
        max_stops: int | None = None,
    ) -> list[ProviderResult]:
        def _should_retry(exc: BaseException) -> bool:
            # Don't waste retries on permanent failures; the caller will surface these.
            return isinstance(exc, RuntimeError) and not isinstance(
                exc, (ProviderQuotaExhaustedError, ProviderAuthError)
            )

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential_jitter(initial=2, max=20),
            retry=retry_if_exception_type(RuntimeError) & retry_if_exception(_should_retry),
            reraise=True,
        ):
            with attempt:
                return await self._search_one_way_once(
                    origin=origin,
                    destination=destination,
                    depart_date=depart_date,
                    adults=adults,
                    cabin=cabin,
                    currency=currency,
                    max_stops=max_stops,
                )

        return []

    async def _wait_for_slot(self) -> None:
        async with self._throttle_lock:
            now = monotonic()
            wait_for = self._next_request_at - now
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._next_request_at = monotonic() + self._min_delay_seconds

    async def _search_one_way_once(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        adults: int = 1,
        cabin: str = "economy",
        currency: str = "USD",
        max_stops: int | None = None,
    ) -> list[ProviderResult]:
        """
        Search Google Flights for origin->destination on depart_date.

        Returns all offers from both "best_flights" and "other_flights" sections,
        sorted by Google's ranking (best first). The caller (PriceCollector) picks
        the cheapest across all providers.
        """
        travel_class_map = {"economy": 1, "premium_economy": 2, "business": 3, "first": 4}
        travel_class = travel_class_map.get(cabin.lower(), 1)

        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": depart_date.isoformat(),
            "currency": currency,
            "adults": adults,
            "type": 2,
            "travel_class": travel_class,
            "stops": self._STOPS_MAP.get(max_stops, 0),
            "deep_search": "true" if self._deep_search else "false",
            "api_key": self._api_key,
        }

        async with self._semaphore:
            await self._wait_for_slot()
            try:
                resp = await self._client.get(_BASE_URL, params=params)
            except httpx.TimeoutException as exc:
                raise RuntimeError("SerpAPI request timed out.") from exc
            except httpx.HTTPError as exc:
                raise RuntimeError("SerpAPI request failed.") from exc

        body_error = _extract_body_error(resp)
        if resp.status_code in (401, 403) or (resp.status_code == 429 and body_error):
            err_cls = _classify_error_message(body_error or "")
            if err_cls is RuntimeError:
                err_cls = ProviderAuthError if resp.status_code in (401, 403) else ProviderRateLimitedError
            log.warning(
                "serpapi_api_error",
                origin=origin,
                destination=destination,
                date=depart_date.isoformat(),
                status_code=resp.status_code,
                error=body_error,
                classification=err_cls.__name__,
            )
            raise err_cls(body_error or f"SerpAPI returned {resp.status_code}.")

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            log.warning(
                "serpapi_rate_limited",
                origin=origin,
                destination=destination,
                date=depart_date.isoformat(),
                retry_after=retry_after,
            )
            raise ProviderRateLimitedError(f"SerpAPI rate limit hit. Retry after {retry_after}s.")

        if resp.status_code >= 400:
            log.warning(
                "serpapi_http_error",
                origin=origin,
                destination=destination,
                date=depart_date.isoformat(),
                status_code=resp.status_code,
            )
            raise RuntimeError(f"SerpAPI request failed with status {resp.status_code}.")

        try:
            data = resp.json()
        except Exception:
            log.warning(
                "serpapi_invalid_json",
                origin=origin,
                destination=destination,
                date=depart_date.isoformat(),
                body_preview=resp.text[:200],
            )
            return []

        # SerpAPI sometimes returns 200 OK with {"error": "..."} for search failures.
        if isinstance(data, dict) and data.get("error"):
            err_cls = _classify_error_message(str(data["error"]))
            log.warning(
                "serpapi_body_error",
                origin=origin,
                destination=destination,
                date=depart_date.isoformat(),
                error=str(data["error"])[:300],
                classification=err_cls.__name__,
            )
            raise err_cls(str(data["error"]))

        results: list[ProviderResult] = []

        for section in ("best_flights", "other_flights"):
            for offer in data.get(section, []):
                price = offer.get("price")
                if not price:
                    continue

                flights = offer.get("flights", [])
                if not flights:
                    continue

                first_leg = flights[0]
                flight_number = first_leg.get("flight_number", "")
                airline_name = first_leg.get("airline", "")
                airline = flight_number.split()[0] if flight_number else airline_name
                total_duration = offer.get("total_duration", 0)
                stops = max(0, len(flights) - 1)

                booking_token = offer.get("booking_token", "")
                if booking_token:
                    deep_link = f"https://www.google.com/travel/flights?tfs={booking_token}"
                else:
                    deep_link = (
                        f"https://www.google.com/flights#search;f={quote(origin)};t={quote(destination)};"
                        f"d={depart_date.isoformat()};tt=o"
                    )

                results.append(
                    ProviderResult(
                        price=float(price),
                        currency=currency,
                        airline=airline,
                        deep_link=deep_link,
                        provider=self.name,
                        stops=stops,
                        duration_minutes=int(total_duration),
                        raw_data={
                            "flight_number": flight_number,
                            "section": section,
                        },
                    )
                )

        log.info(
            "serpapi_search_done",
            origin=origin,
            destination=destination,
            date=depart_date.isoformat(),
            results=len(results),
        )
        return results

    async def close(self) -> None:
        await self._client.aclose()

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import get_logger
from app.core.redaction import redact_text
from app.models.all_flight_result import AllFlightResult
from app.models.scrape_log import ScrapeLog
from app.providers.base import FlightProvider, ProviderResult
from app.utils.airline_codes import normalize_airline

log = get_logger(__name__)


@dataclass
class CollectionResult:
    origin: str
    destination: str
    depart_date: date
    cheapest: ProviderResult | None
    provider_results: dict[str, list[ProviderResult]] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


class PriceCollector:
    """
    Coordinates searches across all configured providers for a single route/date,
    then writes the cheapest result to the database.

    Each collect_single_date() call gets its own DB session (created from
    session_factory) so concurrent calls don't share a session and cause
    transaction conflicts.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        providers: list[FlightProvider],
    ) -> None:
        self.session_factory = session_factory
        self.providers = providers

    async def collect_single_date(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        route_group_id: UUID | None,
        currency: str = "USD",
        max_stops: int | None = None,
    ) -> CollectionResult:
        """Search all providers for origin→destination on depart_date."""
        all_results: list[ProviderResult] = []
        provider_results: dict[str, list[ProviderResult]] = {}
        errors: dict[str, str] = {}

        async with self.session_factory() as session:
            for provider in self.providers:
                start = time.monotonic()
                try:
                    results = await provider.search_one_way(
                        origin, destination, depart_date,
                        currency=currency, max_stops=max_stops,
                    )
                    elapsed_ms = int((time.monotonic() - start) * 1000)

                    provider_results[provider.name] = results
                    all_results.extend(results)

                    log_entry = ScrapeLog(
                        route_group_id=route_group_id,
                        origin=origin,
                        destination=destination,
                        depart_date=depart_date,
                        provider=provider.name,
                        status="success" if results else "no_results",
                        offers_found=len(results),
                        cheapest_price=results[0].price if results else None,
                        duration_ms=elapsed_ms,
                    )
                    session.add(log_entry)

                except Exception as exc:
                    elapsed_ms = int((time.monotonic() - start) * 1000)
                    safe_error = redact_text(str(exc))
                    errors[provider.name] = safe_error
                    log.warning(
                        "provider_error",
                        provider=provider.name,
                        origin=origin,
                        destination=destination,
                        date=str(depart_date),
                        error=safe_error,
                    )
                    log_entry = ScrapeLog(
                        route_group_id=route_group_id,
                        origin=origin,
                        destination=destination,
                        depart_date=depart_date,
                        provider=provider.name,
                        status="error",
                        offers_found=0,
                        error_message=safe_error[:500],
                        duration_ms=elapsed_ms,
                    )
                    session.add(log_entry)

            cheapest = min(all_results, key=lambda r: r.price) if all_results else None

            if cheapest:
                await self._upsert_cheapest(
                    session=session,
                    route_group_id=route_group_id,
                    origin=origin,
                    destination=destination,
                    depart_date=depart_date,
                    result=cheapest,
                )
                await self._save_all_results(
                    session=session,
                    route_group_id=route_group_id,
                    origin=origin,
                    destination=destination,
                    depart_date=depart_date,
                    results=all_results,
                )

            await session.commit()

        return CollectionResult(
            origin=origin,
            destination=destination,
            depart_date=depart_date,
            cheapest=cheapest,
            provider_results=provider_results,
            errors=errors,
        )

    # ── daily_cheapest_prices upsert ─────────────────────────────────────────

    async def _upsert_cheapest(
        self,
        session: AsyncSession,
        route_group_id: UUID,
        origin: str,
        destination: str,
        depart_date: date,
        result: ProviderResult,
    ) -> None:
        stmt = text("""
            INSERT INTO daily_cheapest_prices
                (id, route_group_id, origin, destination, depart_date,
                 airline, price, currency, provider, deep_link,
                 stops, duration_minutes, scraped_at)
            VALUES
                (gen_random_uuid(), :route_group_id, :origin, :destination, :depart_date,
                 :airline, :price, :currency, :provider, :deep_link,
                 :stops, :duration_minutes, now())
            ON CONFLICT (route_group_id, origin, destination, depart_date)
            DO UPDATE SET
                airline          = EXCLUDED.airline,
                price            = EXCLUDED.price,
                currency         = EXCLUDED.currency,
                provider         = EXCLUDED.provider,
                deep_link        = EXCLUDED.deep_link,
                stops            = EXCLUDED.stops,
                duration_minutes = EXCLUDED.duration_minutes,
                scraped_at       = now()
            -- Only update if the new price is cheaper than the stored price
            WHERE daily_cheapest_prices.price > EXCLUDED.price
        """)
        await session.execute(
            stmt,
            {
                "route_group_id": str(route_group_id),
                "origin": origin,
                "destination": destination,
                "depart_date": depart_date,
                "airline": normalize_airline(result.airline),
                "price": result.price,
                "currency": result.currency,
                "provider": result.provider or "unknown",
                "deep_link": result.deep_link[:2048] if result.deep_link else None,
                "stops": result.stops if result.stops is not None else None,
                "duration_minutes": result.duration_minutes or None,
            },
        )

    # ── all_flight_results write (legacy route-group path) ───────────────────

    async def _save_all_results(
        self,
        session: AsyncSession,
        route_group_id: UUID,
        origin: str,
        destination: str,
        depart_date: date,
        results: list[ProviderResult],
    ) -> None:
        """
        Replace-on-collect strategy:
        1. Delete any existing rows for this (route_group_id, origin, destination, depart_date)
        2. Insert one row per result, preserving every airline/price/provider combination.

        This ensures the all_flight_results table always reflects the most recent
        collection run without growing unboundedly.
        """
        # Delete existing rows for this route/date before inserting fresh data
        await session.execute(
            text("""
                DELETE FROM all_flight_results
                WHERE route_group_id = :rg_id
                  AND origin = :origin
                  AND destination = :destination
                  AND depart_date = :depart_date
            """),
            {
                "rg_id": str(route_group_id),
                "origin": origin,
                "destination": destination,
                "depart_date": depart_date,
            },
        )

        # Insert all results sorted cheapest-first for readability
        for result in sorted(results, key=lambda r: r.price):
            row = AllFlightResult(
                route_group_id=route_group_id,
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                airline=normalize_airline(result.airline),
                price=result.price,
                currency=result.currency,
                provider=result.provider or "unknown",
                deep_link=result.deep_link[:2048] if result.deep_link else None,
                stops=result.stops if result.stops is not None else None,
                duration_minutes=result.duration_minutes or None,
            )
            session.add(row)

    async def collect_route_batch(
        self,
        origin: str,
        destinations: list[str],
        dates: list[date],
        route_group_id: UUID,
        batch_size: int = 3,
        delay_seconds: float = 2.0,
        stop_check: Callable[[], bool] | None = None,
        currency: str = "USD",
        max_stops: int | None = None,
    ) -> dict[str, int]:
        """
        Legacy route-group collection path.

        stop_check: optional callable that returns True when the caller wants the
        batch loop to abort early (see collect_leg_batch for details).
        """
        stats: dict[str, int] = {"success": 0, "errors": 0, "skipped": 0}

        for dest in destinations:
            for i in range(0, len(dates), batch_size):
                # Check stop signal before starting each batch
                if stop_check and stop_check():
                    return stats

                batch = dates[i : i + batch_size]
                tasks = [
                    self.collect_single_date(origin, dest, d, route_group_id, currency, max_stops)
                    for d in batch
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        stats["errors"] += 1
                    elif isinstance(result, CollectionResult):
                        if result.cheapest:
                            stats["success"] += 1
                        else:
                            stats["skipped"] += 1

                if i + batch_size < len(dates):
                    await asyncio.sleep(delay_seconds)

        return stats

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.redaction import redact_text
from app.models.collection_run import CollectionRun
from app.models.route_group import RouteGroup
from app.providers.registry import ProviderRegistry
from app.services.alert_service import AlertService
from app.services.price_collector import PriceCollector

log = get_logger(__name__)


class FlightScheduler:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        provider_registry: ProviderRegistry,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.provider_registry = provider_registry
        self.alert_service = AlertService(settings)
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self._is_running = False
        self._stop_requested: bool = False
        self._is_collecting: bool = False
        self._progress: dict = {
            "routes_total": 0,
            "routes_done": 0,
            "routes_failed": 0,
            "dates_scraped": 0,
            "current_origin": "",
        }

    @property
    def is_running(self) -> bool:
        return self._is_running and self.scheduler.running

    @property
    def is_collecting(self) -> bool:
        return self._is_collecting

    @property
    def progress(self) -> dict:
        return dict(self._progress)

    def request_stop(self) -> None:
        if self._is_collecting:
            self._stop_requested = True
            log.info("stop_requested")

    def start(self) -> None:
        if not self.settings.scheduler_enabled:
            log.info("scheduler_disabled")
            return

        self.scheduler.add_job(
            self.run_collection_cycle,
            trigger="interval",
            minutes=self.settings.scheduler_interval_minutes,
            id="flight_collection",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.cleanup_old_data,
            trigger="interval",
            hours=24,
            id="daily_cleanup",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True
        log.info("scheduler_started", interval=self.settings.scheduler_interval_minutes)

    async def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        self._is_running = False
        log.info("scheduler_stopped")

    async def run_collection_cycle(self) -> None:
        if self._is_collecting:
            log.warning("collection_already_running_skipping")
            return

        self._stop_requested = False
        self._is_collecting = True
        log.info("collection_cycle_started")

        async with self.session_factory() as session:
            run = CollectionRun(status="running")
            session.add(run)
            await session.flush()

            try:
                providers = self.provider_registry.get_enabled()
                if not providers:
                    log.warning("no_providers_enabled")
                    run.status = "completed"
                    run.finished_at = func.now()
                    await session.commit()
                    return

                total_success = 0
                total_errors = 0
                total_routes = 0
                error_details: list[str] = []

                groups_result = await session.execute(
                    select(RouteGroup).where(RouteGroup.is_active.is_(True))
                )
                groups = list(groups_result.scalars().all())

                # Pre-calculate total routes for live progress display
                pre_total = sum(len(g.origins) for g in groups)
                for g in groups:
                    main = set(g.origins)
                    pre_total += sum(
                        1 for s in (g.special_sheets or [])
                        if s.get("origin") and s.get("origin") not in main and s.get("destinations")
                    )
                self._progress = {
                    "routes_total": pre_total,
                    "routes_done": 0,
                    "routes_failed": 0,
                    "dates_scraped": 0,
                    "current_origin": "",
                }

                collector = PriceCollector(
                    session_factory=self.session_factory,
                    providers=providers,
                )

                for group in groups:
                    if self._stop_requested:
                        log.info("collection_stopped_between_groups", group=group.name)
                        break

                    dates = self._group_dates(group)
                    for origin in group.origins:
                        if self._stop_requested:
                            break

                        total_routes += 1
                        self._progress["current_origin"] = origin
                        try:
                            remaining = await self._filter_already_scraped(
                                session, origin, group.destinations, dates
                            )
                            if not remaining:
                                total_success += 1
                                self._progress["routes_done"] += 1
                                continue
                            stats = await collector.collect_route_batch(
                                origin=origin,
                                destinations=group.destinations,
                                dates=remaining,
                                route_group_id=group.id,
                                batch_size=self.settings.scrape_batch_size,
                                delay_seconds=self.settings.scrape_delay_seconds,
                                stop_check=lambda: self._stop_requested,
                                currency=group.currency,
                                max_stops=group.max_stops,
                            )
                            total_success += stats["success"]
                            total_errors += stats["errors"]
                            self._progress["routes_done"] += 1
                            self._progress["dates_scraped"] += stats["success"]
                        except Exception as exc:
                            total_errors += 1
                            self._progress["routes_done"] += 1
                            self._progress["routes_failed"] += 1
                            safe_error = redact_text(str(exc))
                            msg = f"{group.name} / {origin}: {safe_error}"
                            error_details.append(msg)
                            log.exception("route_collection_failed", origin=origin, error=safe_error)

                    # Collect data for special sheet origins that are not in the
                    # main origins list (e.g. KIX→Beijing within a Canada→Asia group)
                    main_origins = set(group.origins)
                    for spec in (group.special_sheets or []):
                        spec_origin = spec.get("origin", "")
                        spec_dests = spec.get("destinations", [])
                        if not spec_origin or not spec_dests or spec_origin in main_origins:
                            continue
                        if self._stop_requested:
                            break
                        total_routes += 1
                        self._progress["current_origin"] = spec_origin
                        try:
                            remaining = await self._filter_already_scraped(
                                session, spec_origin, spec_dests, dates
                            )
                            if not remaining:
                                total_success += 1
                                self._progress["routes_done"] += 1
                                continue
                            stats = await collector.collect_route_batch(
                                origin=spec_origin,
                                destinations=spec_dests,
                                dates=remaining,
                                route_group_id=group.id,
                                batch_size=self.settings.scrape_batch_size,
                                delay_seconds=self.settings.scrape_delay_seconds,
                                stop_check=lambda: self._stop_requested,
                                currency=group.currency,
                                max_stops=group.max_stops,
                            )
                            total_success += stats["success"]
                            total_errors += stats["errors"]
                            self._progress["routes_done"] += 1
                            self._progress["dates_scraped"] += stats["success"]
                        except Exception as exc:
                            total_errors += 1
                            self._progress["routes_done"] += 1
                            self._progress["routes_failed"] += 1
                            safe_error = redact_text(str(exc))
                            msg = f"{group.name} / {spec_origin} (special): {safe_error}"
                            error_details.append(msg)
                            log.exception("special_sheet_collection_failed", origin=spec_origin, error=safe_error)

                run.status = "stopped" if self._stop_requested else "completed"
                run.routes_total = total_routes
                run.routes_success = total_success
                run.routes_failed = total_errors
                run.dates_scraped = total_success
                run.errors = error_details if error_details else []
                run.finished_at = func.now()
                await session.commit()

                if not self._stop_requested:
                    summary = (
                        f"Collection complete: {total_success} prices collected, "
                        f"{total_errors} errors across {len(groups)} route groups."
                    )
                    if error_details:
                        summary += f" Failed routes: {'; '.join(error_details[:3])}"
                    await self.alert_service.send_summary(summary)

            except Exception as exc:
                run.status = "failed"
                safe_error = redact_text(str(exc))
                run.errors = [safe_error]
                await session.commit()
                log.exception("collection_cycle_failed", error=safe_error)
                await self.alert_service.send_alert(f"Collection cycle FAILED: {safe_error}")
            finally:
                self._is_collecting = False
                self._stop_requested = False

        log.info("collection_cycle_finished")

    def _group_dates(self, group: RouteGroup) -> list[date]:
        today = date.today()
        start = group.start_date or today
        end = group.end_date or (start + timedelta(days=group.days_ahead))
        return [start + timedelta(days=d) for d in range((end - start).days + 1)]

    async def _filter_already_scraped(
        self,
        session: AsyncSession,
        origin: str,
        destinations: list[str],
        dates: list[date],
    ) -> list[date]:
        today = date.today()
        # A date is "done" only when every destination for this origin was scraped
        # successfully today. Counting distinct destinations per date and comparing
        # against the full destinations list prevents HAN from being skipped just
        # because SGN was already scraped for the same date.
        result = await session.execute(
            text("""
                SELECT depart_date, COUNT(DISTINCT destination) AS dest_count
                FROM scrape_logs
                WHERE origin = :origin
                  AND destination = ANY(:destinations)
                  AND status = 'success'
                  AND created_at::date = :today
                  AND depart_date = ANY(:dates)
                GROUP BY depart_date
            """),
            {
                "origin": origin,
                "destinations": destinations,
                "today": today,
                "dates": dates,
            },
        )
        num_dests = len(destinations)
        already_done = {row[0] for row in result.fetchall() if row[1] >= num_dests}
        return [d for d in dates if d not in already_done]

    async def trigger_single_group(self, group_id: UUID, target_dates: list[date] | None = None) -> dict[str, int]:
        if self._is_collecting:
            log.warning("trigger_single_group_skipped_already_collecting", group_id=str(group_id))
            return {"success": 0, "errors": 0, "skipped": 0}

        self._stop_requested = False
        self._is_collecting = True
        stats: dict[str, int] = {"success": 0, "errors": 0, "skipped": 0}

        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    select(RouteGroup).where(
                        RouteGroup.id == group_id, RouteGroup.is_active.is_(True)
                    )
                )
                group = result.scalar_one_or_none()
                if not group:
                    return stats

                providers = self.provider_registry.get_enabled()
                if not providers:
                    return stats

                dates = target_dates if target_dates is not None else self._group_dates(group)
                collector = PriceCollector(
                    session_factory=self.session_factory,
                    providers=providers,
                )

                for origin in group.origins:
                    if self._stop_requested:
                        break
                    remaining = await self._filter_already_scraped(
                        session, origin, group.destinations, dates
                    )
                    if not remaining:
                        continue
                    part = await collector.collect_route_batch(
                        origin=origin,
                        destinations=group.destinations,
                        dates=remaining,
                        route_group_id=group.id,
                        batch_size=self.settings.scrape_batch_size,
                        delay_seconds=self.settings.scrape_delay_seconds,
                        stop_check=lambda: self._stop_requested,
                        currency=group.currency,
                        max_stops=group.max_stops,
                    )
                    stats["success"] += part["success"]
                    stats["errors"] += part["errors"]
                    stats["skipped"] += part["skipped"]

                # Collect data for special sheet origins not in the main origins list
                main_origins = set(group.origins)
                for spec in (group.special_sheets or []):
                    if self._stop_requested:
                        break
                    spec_origin = spec.get("origin", "")
                    spec_dests = spec.get("destinations", [])
                    if not spec_origin or not spec_dests or spec_origin in main_origins:
                        continue
                    remaining = await self._filter_already_scraped(
                        session, spec_origin, spec_dests, dates
                    )
                    if not remaining:
                        continue
                    part = await collector.collect_route_batch(
                        origin=spec_origin,
                        destinations=spec_dests,
                        dates=remaining,
                        route_group_id=group.id,
                        batch_size=self.settings.scrape_batch_size,
                        delay_seconds=self.settings.scrape_delay_seconds,
                        stop_check=lambda: self._stop_requested,
                        currency=group.currency,
                        max_stops=group.max_stops,
                    )
                    stats["success"] += part["success"]
                    stats["errors"] += part["errors"]
                    stats["skipped"] += part["skipped"]

        except Exception as exc:
            log.exception(
                "trigger_single_group_failed",
                group_id=str(group_id),
                error=redact_text(str(exc)),
            )
        finally:
            self._is_collecting = False
            self._stop_requested = False

        return stats

    async def cleanup_old_data(self) -> None:
        log.info("cleanup_started")
        try:
            async with self.session_factory() as session:
                await session.execute(
                    text("DELETE FROM scrape_logs WHERE created_at < now() - interval '30 days'")
                )
                await session.execute(
                    text("DELETE FROM collection_runs WHERE started_at < now() - interval '30 days'")
                )
                # Remove all_flight_results rows for dates already in the past
                # (keeps 7 days of history for debugging; older rows are never useful)
                await session.execute(
                    text("DELETE FROM all_flight_results WHERE depart_date < current_date - 7")
                )
                await session.commit()
            log.info("cleanup_finished")
        except Exception as exc:
            log.exception("cleanup_failed", error=redact_text(str(exc)))

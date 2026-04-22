from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection_run import CollectionRun
from app.models.daily_cheapest import DailyCheapestPrice
from app.models.route_group import RouteGroup
from app.models.scrape_log import ScrapeLog
from app.models.user import User
from app.providers.registry import ProviderRegistry
from app.schemas.stats import OverviewStats, ProviderStat


async def get_overview(
    session: AsyncSession,
    registry: ProviderRegistry,
    current_user: User,
) -> OverviewStats:
    is_admin = current_user.role == "admin"

    groups_query = select(func.count()).where(RouteGroup.is_active.is_(True))
    if not is_admin:
        groups_query = groups_query.where(RouteGroup.user_id == current_user.id)
    active_groups = (await session.execute(groups_query)).scalar_one() or 0

    price_query = select(func.count(DailyCheapestPrice.id)).join(
        RouteGroup,
        RouteGroup.id == DailyCheapestPrice.route_group_id,
    )
    if not is_admin:
        price_query = price_query.where(RouteGroup.user_id == current_user.id)
    total_prices = (await session.execute(price_query)).scalar_one() or 0

    origins_query = select(func.count(DailyCheapestPrice.origin.distinct())).join(
        RouteGroup,
        RouteGroup.id == DailyCheapestPrice.route_group_id,
    )
    if not is_admin:
        origins_query = origins_query.where(RouteGroup.user_id == current_user.id)
    total_origins = (await session.execute(origins_query)).scalar_one() or 0

    destinations_query = select(func.count(DailyCheapestPrice.destination.distinct())).join(
        RouteGroup,
        RouteGroup.id == DailyCheapestPrice.route_group_id,
    )
    if not is_admin:
        destinations_query = destinations_query.where(RouteGroup.user_id == current_user.id)
    total_destinations = (await session.execute(destinations_query)).scalar_one() or 0

    last_collection_at = None
    last_collection_status = None
    if is_admin:
        last_run = (
            await session.execute(select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(1))
        ).scalar_one_or_none()
        if last_run:
            last_collection_at = last_run.started_at
            last_collection_status = last_run.status
    else:
        last_scrape = (
            await session.execute(
                select(func.max(ScrapeLog.created_at))
                .join(RouteGroup, RouteGroup.id == ScrapeLog.route_group_id)
                .where(RouteGroup.user_id == current_user.id)
            )
        ).scalar_one_or_none()
        if last_scrape:
            last_collection_at = last_scrape
            last_collection_status = "completed"

    provider_status = registry.status()
    provider_stats: dict[str, ProviderStat] = {}

    for name, provider_state in provider_status.items():
        configured = provider_state == "configured"
        last_success = None
        success_rate = None

        if configured:
            last_success_query = select(func.max(ScrapeLog.created_at)).where(
                ScrapeLog.provider == name,
                ScrapeLog.status == "success",
            )
            total_logs_query = select(func.count()).where(ScrapeLog.provider == name)
            success_logs_query = select(func.count()).where(
                ScrapeLog.provider == name,
                ScrapeLog.status == "success",
            )

            if not is_admin:
                last_success_query = last_success_query.join(
                    RouteGroup,
                    RouteGroup.id == ScrapeLog.route_group_id,
                ).where(RouteGroup.user_id == current_user.id)
                total_logs_query = total_logs_query.join(
                    RouteGroup,
                    RouteGroup.id == ScrapeLog.route_group_id,
                ).where(RouteGroup.user_id == current_user.id)
                success_logs_query = success_logs_query.join(
                    RouteGroup,
                    RouteGroup.id == ScrapeLog.route_group_id,
                ).where(RouteGroup.user_id == current_user.id)

            last_success = (await session.execute(last_success_query)).scalar_one()
            total_logs = (await session.execute(total_logs_query)).scalar_one() or 0
            if total_logs > 0:
                success_count = (await session.execute(success_logs_query)).scalar_one() or 0
                success_rate = round(success_count / total_logs, 4)

        provider_stats[name] = ProviderStat(
            configured=configured,
            last_success=last_success,
            success_rate=success_rate,
        )

    return OverviewStats(
        active_route_groups=active_groups,
        total_prices_collected=total_prices,
        total_origins=total_origins,
        total_destinations=total_destinations,
        last_collection_at=last_collection_at,
        last_collection_status=last_collection_status,
        provider_stats=provider_stats,
    )

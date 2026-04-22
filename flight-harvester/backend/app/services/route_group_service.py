from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_cheapest import DailyCheapestPrice
from app.models.route_group import RouteGroup
from app.schemas.route_group import (
    PerOriginProgress,
    RouteGroupCreate,
    RouteGroupProgress,
    RouteGroupUpdate,
)


async def list_all(
    session: AsyncSession,
    active_only: bool = True,
    requesting_user_id: uuid.UUID | None = None,
    is_admin: bool = True,
) -> list[RouteGroup]:
    q = select(RouteGroup)
    if active_only:
        q = q.where(RouteGroup.is_active.is_(True))
    if not is_admin and requesting_user_id is not None:
        q = q.where(RouteGroup.user_id == requesting_user_id)
    result = await session.execute(q.order_by(RouteGroup.name))
    return list(result.scalars().all())


async def get_by_id(
    session: AsyncSession,
    group_id: uuid.UUID,
    requesting_user_id: uuid.UUID | None = None,
    is_admin: bool = True,
) -> RouteGroup | None:
    q = select(RouteGroup).where(RouteGroup.id == group_id)
    if not is_admin and requesting_user_id is not None:
        q = q.where(RouteGroup.user_id == requesting_user_id)
    result = await session.execute(q)
    return result.scalar_one_or_none()


async def create(
    session: AsyncSession,
    data: RouteGroupCreate,
    owner_id: uuid.UUID | None = None,
) -> RouteGroup:
    group = RouteGroup(
        name=data.name,
        destination_label=data.destination_label,
        destinations=data.destinations,
        origins=data.origins,
        nights=data.nights,
        days_ahead=data.days_ahead,
        sheet_name_map=data.sheet_name_map or {o: o for o in data.origins},
        special_sheets=[s.model_dump() for s in data.special_sheets],
        currency=data.currency,
        max_stops=data.max_stops,
        start_date=data.start_date,
        end_date=data.end_date,
        user_id=owner_id,
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


async def update(
    session: AsyncSession,
    group_id: uuid.UUID,
    data: RouteGroupUpdate,
    requesting_user_id: uuid.UUID | None = None,
    is_admin: bool = True,
) -> RouteGroup | None:
    group = await get_by_id(session, group_id, requesting_user_id=requesting_user_id, is_admin=is_admin)
    if not group:
        return None

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "special_sheets" and value is not None:
            value = [s if isinstance(s, dict) else s.model_dump() for s in value]
        setattr(group, field, value)

    await session.commit()
    await session.refresh(group)
    return group


async def delete(
    session: AsyncSession,
    group_id: uuid.UUID,
    requesting_user_id: uuid.UUID | None = None,
    is_admin: bool = True,
) -> bool:
    group = await get_by_id(session, group_id, requesting_user_id=requesting_user_id, is_admin=is_admin)
    if not group:
        return False
    session.delete(group)
    await session.commit()
    return True


async def get_progress(session: AsyncSession, group_id: uuid.UUID) -> RouteGroupProgress | None:
    # get_progress is called after access has already been verified by the router
    group = await get_by_id(session, group_id)
    if not group:
        return None

    total_dates = len(group.origins) * len(group.destinations) * group.days_ahead

    # Total collected
    count_result = await session.execute(
        select(func.count()).where(DailyCheapestPrice.route_group_id == group_id)
    )
    dates_with_data = count_result.scalar_one() or 0

    # Last scraped
    last_result = await session.execute(
        select(func.max(DailyCheapestPrice.scraped_at)).where(
            DailyCheapestPrice.route_group_id == group_id
        )
    )
    last_scraped_at = last_result.scalar_one()

    # Per-origin breakdown
    per_origin: dict[str, PerOriginProgress] = {}
    for origin in group.origins:
        expected = len(group.destinations) * group.days_ahead
        collected_result = await session.execute(
            select(func.count()).where(
                DailyCheapestPrice.route_group_id == group_id,
                DailyCheapestPrice.origin == origin,
            )
        )
        collected = collected_result.scalar_one() or 0
        per_origin[origin] = PerOriginProgress(total=expected, collected=collected)

    coverage = (dates_with_data / total_dates * 100.0) if total_dates > 0 else 0.0

    dates_result = await session.execute(
        select(DailyCheapestPrice.depart_date)
        .where(DailyCheapestPrice.route_group_id == group_id)
        .distinct()
        .order_by(DailyCheapestPrice.depart_date)
    )
    scraped_dates = [d.isoformat() for (d,) in dates_result.fetchall()]

    return RouteGroupProgress(
        route_group_id=group_id,
        name=group.name,
        total_dates=total_dates,
        dates_with_data=dates_with_data,
        coverage_percent=round(coverage, 2),
        last_scraped_at=last_scraped_at,
        per_origin=per_origin,
        scraped_dates=scraped_dates,
    )

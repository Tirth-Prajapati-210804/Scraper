from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tasks.scheduler import FlightScheduler

TODAY = date.today()
D1 = TODAY + timedelta(days=1)
D2 = TODAY + timedelta(days=2)
D3 = TODAY + timedelta(days=3)


def make_scheduler() -> FlightScheduler:
    settings = MagicMock()
    settings.scheduler_enabled = False
    settings.telegram_bot_token = ""
    settings.telegram_chat_id = ""
    settings.sentry_dsn = ""
    return FlightScheduler(
        settings=settings,
        session_factory=MagicMock(),
        provider_registry=MagicMock(),
    )


def make_execute_result(rows: list[tuple]) -> MagicMock:
    result = MagicMock()
    result.fetchall.return_value = rows
    return result


@pytest.mark.asyncio
async def test_partial_destination_not_excluded() -> None:
    """Date with only 1 of 2 destinations scraped must NOT be filtered out."""
    scheduler = make_scheduler()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=make_execute_result([(D1, 1)]))

    remaining = await scheduler._filter_already_scraped(
        session, "YYZ", ["SGN", "HAN"], [D1, D2]
    )

    assert D1 in remaining
    assert D2 in remaining


@pytest.mark.asyncio
async def test_all_destinations_excludes_date() -> None:
    """Date with all destinations scraped IS excluded."""
    scheduler = make_scheduler()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=make_execute_result([(D1, 2)]))

    remaining = await scheduler._filter_already_scraped(
        session, "YYZ", ["SGN", "HAN"], [D1, D2]
    )

    assert D1 not in remaining
    assert D2 in remaining


@pytest.mark.asyncio
async def test_all_dates_fully_scraped_returns_empty() -> None:
    """If every date is fully scraped, the returned list is empty."""
    scheduler = make_scheduler()
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=make_execute_result([(D1, 1), (D2, 1)])
    )

    remaining = await scheduler._filter_already_scraped(
        session, "YYZ", ["SGN"], [D1, D2]
    )

    assert remaining == []


@pytest.mark.asyncio
async def test_no_scrapes_returns_all_dates() -> None:
    """If nothing was scraped yet, all dates are returned unchanged."""
    scheduler = make_scheduler()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=make_execute_result([]))

    dates = [D1, D2, D3]
    remaining = await scheduler._filter_already_scraped(
        session, "YYZ", ["SGN", "HAN"], dates
    )

    assert remaining == dates

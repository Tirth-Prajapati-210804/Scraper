"""Tests for app.providers.registry — provider registry."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.providers.registry import ProviderRegistry


def make_settings(**overrides) -> MagicMock:
    settings = MagicMock()
    settings.demo_mode = False
    settings.serpapi_key = ""
    settings.provider_timeout_seconds = 30
    settings.serpapi_deep_search = True
    settings.provider_max_retries = 3
    settings.provider_concurrency_limit = 2
    settings.provider_min_delay_seconds = 1.0
    for k, v in overrides.items():
        setattr(settings, k, v)
    return settings


def test_no_providers_when_no_key_and_no_demo() -> None:
    registry = ProviderRegistry(make_settings())
    assert registry.get_enabled() == []


def test_demo_mode_creates_mock_provider() -> None:
    registry = ProviderRegistry(make_settings(demo_mode=True))
    providers = registry.get_enabled()
    assert len(providers) == 1
    assert providers[0].name == "demo"


def test_serpapi_key_creates_serpapi_provider() -> None:
    registry = ProviderRegistry(make_settings(serpapi_key="test-key-123"))
    providers = registry.get_enabled()
    assert len(providers) == 1
    assert providers[0].name == "serpapi"


def test_demo_mode_takes_priority_over_serpapi_key() -> None:
    registry = ProviderRegistry(make_settings(demo_mode=True, serpapi_key="test-key"))
    providers = registry.get_enabled()
    assert len(providers) == 1
    assert providers[0].name == "demo"


def test_status_demo_mode() -> None:
    registry = ProviderRegistry(make_settings(demo_mode=True))
    status = registry.status()
    assert status["demo"] == "active"
    assert status["serpapi"] == "disabled"


def test_status_serpapi_configured() -> None:
    registry = ProviderRegistry(make_settings(serpapi_key="test-key"))
    status = registry.status()
    assert status["serpapi"] == "configured"


def test_status_nothing_configured() -> None:
    registry = ProviderRegistry(make_settings())
    status = registry.status()
    assert status["serpapi"] == "disabled"


@pytest.mark.asyncio
async def test_close_all() -> None:
    registry = ProviderRegistry(make_settings(demo_mode=True))
    await registry.close_all()  # should not raise

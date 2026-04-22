from __future__ import annotations

from app.core.config import Settings
from app.providers.base import FlightProvider
from app.providers.serpapi import SerpApiProvider


class ProviderRegistry:
    """Creates, manages, and reports on all providers."""

    def __init__(self, settings: Settings) -> None:
        self.providers: dict[str, FlightProvider] = {}
        self._demo_mode = settings.demo_mode

        if settings.demo_mode:
            from app.providers.mock import MockProvider
            self.providers["demo"] = MockProvider()
        elif settings.serpapi_key:
            self.providers["serpapi"] = SerpApiProvider(
                api_key=settings.serpapi_key,
                timeout=settings.provider_timeout_seconds,
                deep_search=settings.serpapi_deep_search,
                max_retries=settings.provider_max_retries,
                concurrency_limit=settings.provider_concurrency_limit,
                min_delay_seconds=settings.provider_min_delay_seconds,
            )

    def get_enabled(self) -> list[FlightProvider]:
        return list(self.providers.values())

    def status(self) -> dict[str, str]:
        if self._demo_mode:
            return {"demo": "active", "serpapi": "disabled"}
        all_providers: dict[str, str] = {"serpapi": "disabled"}
        for name, provider in self.providers.items():
            all_providers[name] = "configured" if provider.is_configured() else "disabled"
        return all_providers

    async def close_all(self) -> None:
        for provider in self.providers.values():
            await provider.close()

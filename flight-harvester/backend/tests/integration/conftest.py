"""
Integration test fixtures.

These tests require a real PostgreSQL instance. The DATABASE_URL env var
(set in the root conftest.py) points to the test DB. CI provisions PostgreSQL
as a service; locally, run `createdb flight_test` first.

Tables are created once per session via metadata.create_all, then TRUNCATED
between each test so each test starts with a clean slate.
"""
from __future__ import annotations

import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.app_factory import create_app
from app.core.security import hash_password
from app.db.base import Base
from app.models.user import User
# Import all models so their tables are registered in Base.metadata
import app.models  # noqa: F401

# ── Re-use the same DB URL the root conftest exports via env var ──────────────

import os

_DB_URL = os.environ["DATABASE_URL"]

_TEST_SETTINGS = Settings(
    _env_file=None,  # type: ignore[call-arg]
    database_url=_DB_URL,
    jwt_secret_key="integration-test-secret-that-is-32-chars!",
    admin_email="admin@example.com",
    admin_password="CIAdminPassword1!",
    scheduler_enabled=False,
    environment="test",
    debug=False,
    serpapi_key="",
    demo_mode=False,
)

_engine = create_async_engine(_DB_URL, pool_pre_ping=True)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)


# ── Session-scoped: create tables once ───────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Function-scoped: wipe all rows before each test ──────────────────────────

@pytest.fixture(autouse=True)
async def clean_db():
    yield
    async with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))


# ── App + HTTP client ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    return create_app(settings=_TEST_SETTINGS)


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ── Convenience: authenticated client ────────────────────────────────────────

@pytest.fixture
async def auth_client(client):
    """Client pre-authenticated as the default admin."""
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "CIAdminPassword1!"},
    )
    assert res.status_code == 200, f"Login fixture failed: {res.text}"
    token = res.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
async def seed_user():
    async def _seed_user(
        *,
        email: str,
        password: str,
        role: str = "user",
        full_name: str = "Test User",
        is_active: bool = True,
    ) -> User:
        async with _SessionFactory() as session:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                role=role,
                is_active=is_active,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    return _seed_user


@pytest.fixture
async def make_auth_client(app, seed_user):
    clients: list[httpx.AsyncClient] = []

    async def _make_auth_client(
        *,
        email: str,
        password: str,
        role: str = "user",
        full_name: str = "Test User",
        is_active: bool = True,
    ) -> httpx.AsyncClient:
        await seed_user(
            email=email,
            password=password,
            role=role,
            full_name=full_name,
            is_active=is_active,
        )
        client = httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if is_active:
            assert res.status_code == 200, f"Login fixture failed: {res.text}"
            client.headers.update({"Authorization": f"Bearer {res.json()['access_token']}"})
        clients.append(client)
        return client

    yield _make_auth_client

    for client in clients:
        await client.aclose()


@pytest.fixture
def db_session_factory():
    return _SessionFactory

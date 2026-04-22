from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.all_flight_result import AllFlightResult
from app.models.user import User
from app.schemas.route_group import (
    RouteGroupCreate,
    RouteGroupFromTextCreate,
    RouteGroupFromTextResponse,
    RouteGroupProgress,
    RouteGroupResponse,
    RouteGroupUpdate,
)
from app.services import export_service, route_group_service
from app.utils.location_resolver import resolve_location

router = APIRouter(prefix="/route-groups", tags=["route-groups"])

_Auth = Annotated[User, Depends(get_current_user)]
_DB = Annotated[AsyncSession, Depends(get_db_session)]


def _is_admin(user: User) -> bool:
    return user.role == "admin"


@router.get("/", response_model=list[RouteGroupResponse])
async def list_groups(session: _DB, current_user: _Auth, active_only: bool = True) -> list[RouteGroupResponse]:
    groups = await route_group_service.list_all(
        session,
        active_only=active_only,
        requesting_user_id=current_user.id,
        is_admin=_is_admin(current_user),
    )
    return [RouteGroupResponse.model_validate(g) for g in groups]


@router.post(
    "/from-text",
    response_model=RouteGroupFromTextResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create route group from plain-text location names",
)
async def create_group_from_text(
    body: RouteGroupFromTextCreate, session: _DB, current_user: _Auth
) -> RouteGroupFromTextResponse:
    """
    Create a route group by typing location names like 'Canada' and 'Vietnam'.
    The API resolves them to IATA airport codes automatically.

    Examples:
    - origin='Canada'  → YYZ, YVR, YEG, YYC, YHZ, YUL, YOW
    - destination='Vietnam' → SGN, HAN, DAD
    - destination='Tokyo'  → NRT, HND
    - destination='TYO, SHA' → TYO, SHA  (raw IATA pass-through)
    """
    origins = resolve_location(body.origin)
    destinations = resolve_location(body.destination)

    if not origins:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Could not resolve origin '{body.origin}' to any airport codes. "
                "Try a country name (e.g. 'Canada'), city name (e.g. 'Toronto'), "
                "or IATA codes like 'YYZ, YVR'."
            ),
        )
    if not destinations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Could not resolve destination '{body.destination}' to any airport codes. "
                "Try a country name (e.g. 'Vietnam'), city name (e.g. 'Tokyo'), "
                "or IATA codes like 'SGN, HAN'."
            ),
        )

    origin_label = body.origin.title()
    dest_label = body.destination.title()
    name = f"{origin_label} to {dest_label}"
    destination_label = "/".join(destinations) if len(destinations) <= 4 else f"{destinations[0]}+{len(destinations)-1}"

    create_payload = RouteGroupCreate(
        name=name,
        destination_label=destination_label,
        origins=origins,
        destinations=destinations,
        nights=body.nights,
        days_ahead=body.days_ahead,
        sheet_name_map={o: o for o in origins},
        special_sheets=[],
        currency=body.currency,
        max_stops=body.max_stops,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    group = await route_group_service.create(session, create_payload, owner_id=current_user.id)
    return RouteGroupFromTextResponse(
        group=RouteGroupResponse.model_validate(group),
        resolved_origins=origins,
        resolved_destinations=destinations,
    )


@router.post("/", response_model=RouteGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(body: RouteGroupCreate, session: _DB, current_user: _Auth) -> RouteGroupResponse:
    group = await route_group_service.create(session, body, owner_id=current_user.id)
    return RouteGroupResponse.model_validate(group)


@router.get("/{group_id}", response_model=RouteGroupResponse)
async def get_group(group_id: uuid.UUID, session: _DB, current_user: _Auth) -> RouteGroupResponse:
    group = await route_group_service.get_by_id(
        session, group_id,
        requesting_user_id=current_user.id,
        is_admin=_is_admin(current_user),
    )
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    return RouteGroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=RouteGroupResponse)
async def update_group(
    group_id: uuid.UUID, body: RouteGroupUpdate, session: _DB, current_user: _Auth
) -> RouteGroupResponse:
    group = await route_group_service.update(
        session, group_id, body,
        requesting_user_id=current_user.id,
        is_admin=_is_admin(current_user),
    )
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    return RouteGroupResponse.model_validate(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: uuid.UUID, session: _DB, current_user: _Auth) -> None:
    deleted = await route_group_service.delete(
        session, group_id,
        requesting_user_id=current_user.id,
        is_admin=_is_admin(current_user),
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Route group not found")


@router.get("/{group_id}/export")
async def export_group(group_id: uuid.UUID, session: _DB, current_user: _Auth) -> StreamingResponse:
    group = await route_group_service.get_by_id(
        session, group_id,
        requesting_user_id=current_user.id,
        is_admin=_is_admin(current_user),
    )
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")

    all_results_result = await session.execute(
        select(AllFlightResult).where(AllFlightResult.route_group_id == group_id)
    )
    all_results = list(all_results_result.scalars().all())

    excel_bytes = export_service.export_route_group(group, all_results)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", group.name).strip("._") or "route-group"
    filename = f"{safe_name}.xlsx"

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{group_id}/progress", response_model=RouteGroupProgress)
async def get_progress(group_id: uuid.UUID, session: _DB, current_user: _Auth) -> RouteGroupProgress:
    # Verify access first
    group = await route_group_service.get_by_id(
        session, group_id,
        requesting_user_id=current_user.id,
        is_admin=_is_admin(current_user),
    )
    if not group:
        raise HTTPException(status_code=404, detail="Route group not found")
    progress = await route_group_service.get_progress(session, group_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Route group not found")
    return progress

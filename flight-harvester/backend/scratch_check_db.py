
import asyncio
import uuid
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.route_group import RouteGroup
from app.models.user import User

async def check_db():
    async with AsyncSessionLocal() as session:
        groups_res = await session.execute(select(RouteGroup))
        groups = groups_res.scalars().all()
        print(f"Total groups: {len(groups)}")
        for g in groups:
            print(f"Group: {g.name} (ID: {g.id}), UserID: {g.user_id}, Active: {g.is_active}")
        
        users_res = await session.execute(select(User))
        users = users_res.scalars().all()
        print(f"Total users: {len(users)}")
        for u in users:
            print(f"User: {u.email} (ID: {u.id}), Role: {u.role}")

if __name__ == "__main__":
    asyncio.run(check_db())

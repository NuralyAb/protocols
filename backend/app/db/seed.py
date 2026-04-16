"""Seed demo user. Run: python -m app.db.seed"""
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


async def main() -> None:
    async with SessionLocal() as db:
        exists = await db.scalar(select(User).where(User.email == "demo@protocol.ai"))
        if exists:
            print("demo user already present")
            return
        user = User(
            email="demo@protocol.ai",
            hashed_password=hash_password("demo12345"),
            full_name="Demo User",
            is_superuser=True,
        )
        db.add(user)
        await db.commit()
        print("demo user created: demo@protocol.ai / demo12345")


if __name__ == "__main__":
    asyncio.run(main())

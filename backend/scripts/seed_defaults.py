"""Idempotent global seed script.

Creates global (user_id=NULL) skills and agent configs.
Safe to run multiple times — skips existing rows by name.
"""
import asyncio
from app.core.database import get_session
from app.seeds.scholarflow_skills import seed_scholarflow


async def main():
    async with get_session() as db:
        configs = await seed_scholarflow(db, user_id=None)
        print(f"Created {len(configs)} global agent configs.")
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())

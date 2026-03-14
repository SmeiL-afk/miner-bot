import aiosqlite
import asyncio

DB_PATH = "miner_bot.db"

async def fix_db():
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
            await db.execute("ALTER TABLE users ADD COLUMN referral_earnings INTEGER DEFAULT 0")
            await db.commit()
            print("✅ Колонки добавлены")
        except:
            print("❌ Возможно уже есть")

asyncio.run(fix_db())
import asyncio
from backend.bot import main as bot_main

def start_bot():
    asyncio.create_task(bot_main())

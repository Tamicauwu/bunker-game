# run.py
import asyncio
from backend.bot import dp, bot
from backend import main
import uvicorn

async def start_bot():
    print("Бот запущен...")
    await dp.start_polling(bot)

async def start_api():
    config = uvicorn.Config(main.app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main_runner():
    await asyncio.gather(
        start_api(),
        start_bot()
    )

if __name__ == "__main__":
    asyncio.run(main_runner())

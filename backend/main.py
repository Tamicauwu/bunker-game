import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from backend.bot import notify_current_player

from backend.game_logic import (
    connected_players,
    game_state,
    start_round,
    reset_game
)

app = FastAPI()


# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ---
@app.get("/lobby/players")
def get_players():
    return list(connected_players.values())

@app.get("/game_state")
def get_game_state():
    return game_state

@app.post("/game/start_round")
async def api_start_round():
    if not game_state["players_order"]:
        return JSONResponse(
            {"status": "error", "message": "Нет игроков в комнате"},
            status_code=400
        )

    start_round()
    asyncio.create_task(notify_current_player())
    return {
        "status": "ok",
        "message": "Круг запущен",
        "current_player_id": game_state["players_order"][game_state["current_index"]]
    }

@app.post("/game/end")
async def end_game():
    from backend.game_logic import end_game_logic

    try:
        text = await end_game_logic()
        return {"status": "ok", "summary": text}
    except Exception as e:
        print("❌ Ошибка генерации финала:", e)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Ошибка генерации финала"}
        )

@app.post("/game/reset")
def reset_game_api():
    reset_game()
    return {"status": "ok"}

# --- STATIC ---
app.mount("/", StaticFiles(directory="web", html=True), name="web")

@app.on_event("startup")
async def startup_event():
    from backend.bot import main as bot_main
    asyncio.create_task(bot_main())


# --- RENDER ENTRY POINT ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )

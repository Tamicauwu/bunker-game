# backend/game_logic.py
import asyncio
from backend.ai_final import generate_ai_final

# -------------------
# ИГРОКИ
# -------------------
connected_players = {}

# -------------------
# СОСТОЯНИЕ ИГРЫ
# -------------------
game_state = {
    "players_order": [],
    "current_index": 0,
    "phase": "lobby",      # lobby | action | voting | end
    "votes": {},
    "round": 0,
    "opened_this_round": {},
    "voted_players": [],
    "lobby_open": True
}

# ======================================================
# ИГРОКИ
# ======================================================
def add_player(user_id: int, name: str):
    # 🚫 если игра уже началась — не пускаем
    if game_state["phase"] != "lobby":
        return False

    if user_id not in connected_players:
        connected_players[user_id] = {
            "id": user_id,
            "name": name,
            "avatar_url": None,
            "card": None,
            "opened": {
                "profession": False,
                "age": False,
                "health": False,
                "hobby": False,
                "extra": False,
                "condition": False
            },
            "eliminated": False,
            "skipped_vote": False,
            "card_message_id": None
        }

        game_state["players_order"].append(user_id)
        game_state["opened_this_round"][user_id] = False

    return True



def set_card(user_id: int, card: dict):
    if user_id in connected_players:
        connected_players[user_id]["card"] = card


def set_avatar(user_id: int, avatar_url: str):
    if user_id in connected_players:
        connected_players[user_id]["avatar_url"] = avatar_url


# ======================================================
# ХОДЫ
# ======================================================
def open_field(user_id: int, field: str):
    if game_state["phase"] != "action":
        return

    player = connected_players.get(user_id)
    if not player or player["eliminated"]:
        return

    if game_state["opened_this_round"].get(user_id):
        return  # ❗ уже ходил в этом круге

    if field not in player["opened"] or player["opened"][field]:
        return

    player["opened"][field] = True
    game_state["opened_this_round"][user_id] = True

    advance_turn()



def advance_turn():
    if game_state["phase"] != "action":
        return

    active_players = [
        p for p in game_state["players_order"]
        if not connected_players[p]["eliminated"]
    ]

    # ВСЕ ОТКРЫЛИСЬ → ГОЛОСОВАНИЕ
    if all(game_state["opened_this_round"][p] for p in active_players):
        start_voting()
        return

    # СЛЕДУЮЩИЙ ИГРОК
    idx = game_state["current_index"]
    for _ in range(len(game_state["players_order"])):
        idx = (idx + 1) % len(game_state["players_order"])
        pid = game_state["players_order"][idx]
        if not connected_players[pid]["eliminated"]:
            game_state["current_index"] = idx
            return


# ======================================================
# КРУГ
# ======================================================
def start_round():
    game_state["phase"] = "action"
    game_state["votes"].clear()
    game_state["voted_players"].clear()
    
    game_state["opened_this_round"].clear()  # 🔥 ВАЖНО

    for pid in game_state["players_order"]:
        if not connected_players[pid]["eliminated"]:
            game_state["opened_this_round"][pid] = False

    # первый живой игрок
    for i, pid in enumerate(game_state["players_order"]):
        if not connected_players[pid]["eliminated"]:
            game_state["current_index"] = i
            break
        
    for p in connected_players.values():
        p["skipped_vote"] = False
    



# ======================================================
# ГОЛОСОВАНИЕ
# ======================================================
def start_voting():
    game_state["phase"] = "voting"
    game_state["votes"].clear()
    game_state["voted_players"].clear()
    print("🗳️ Переход к голосованию")



def vote(voter_id: int, target_id: int):
    if game_state["phase"] != "voting":
        return

    voter = connected_players.get(voter_id)
    if not voter or voter["eliminated"] or voter["skipped_vote"]:
        return

    if voter_id in game_state["voted_players"]:
        return

    game_state["voted_players"].append(voter_id)
    game_state["votes"][voter_id] = target_id

    check_votes_complete()


def skip_vote(user_id: int):
    player = connected_players.get(user_id)
    if not player or player["skipped_vote"]:
        return False

    player["skipped_vote"] = True
    game_state["votes"][user_id] = None

    if user_id not in game_state["voted_players"]:
        game_state["voted_players"].append(user_id)

    check_votes_complete()
    return True


def check_votes_complete():
    active_players = [
        p for p in game_state["players_order"]
        if not connected_players[p]["eliminated"]
    ]

    if len(game_state["votes"]) >= len(active_players):
        finish_voting()


def finish_voting():
    votes_count = {}

    for target in game_state["votes"].values():
        if target is None:
            continue
        votes_count[target] = votes_count.get(target, 0) + 1

    if votes_count:
        eliminated = max(votes_count.items(), key=lambda x: x[1])[0]
        connected_players[eliminated]["eliminated"] = True
        game_state["opened_this_round"].pop(eliminated, None)

    game_state["votes"] = {}
    game_state["voted_players"] = []
    game_state["round"] += 1
    
    if not check_end_game():
        start_round()


# ======================================================
# КОНЕЦ ИГРЫ
# ======================================================
def check_end_game():
    active = [
        p for p in game_state["players_order"]
        if not connected_players[p]["eliminated"]
    ]

    if len(active) <= 1:
        game_state["phase"] = "end"
        return True

    return False


async def end_game_logic():
    survivors = [p for p in connected_players.values() if not p["eliminated"]]
    dead = [p for p in connected_players.values() if p["eliminated"]]

    loop = asyncio.get_running_loop()
    ai_text = await loop.run_in_executor(
        None,
        generate_ai_final,
        survivors,
        dead
    )

    game_state["phase"] = "end"
    return ai_text

def reset_game():
    connected_players.clear()

    game_state.clear()
    game_state.update({
        "players_order": [],
        "current_index": 0,
        "phase": "lobby",        # ← снова лобби
        "votes": {},
        "round": 0,
        "opened_this_round": {},
        "lobby_open": True,
        "voting_started": False,
        "voted_players": []
    })

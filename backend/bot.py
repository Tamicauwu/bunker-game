import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from backend.game import generate_card
from backend.game_logic import (
    add_player, set_card, open_field, set_avatar,
    game_state, connected_players,
    vote, skip_vote, start_round
)

TOKEN = "8225370912:AAHjI_LQRkLyQLOrJQByhy3QMcIO8GUw3wk"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ------------------------
# КНОПКИ КАРТОЧКИ
# ------------------------
def get_card_keyboard(user_id):
    player = connected_players[user_id]
    opened = player.get("opened", {})

    buttons = []

    def btn(title, field):
        if not opened.get(field):
            return InlineKeyboardButton(text=title, callback_data=f"open_{field}")
        return None

    row1 = list(filter(None, [
        btn("👤 Профессия", "profession"),
        btn("🎂 Возраст", "age")
    ]))

    row2 = list(filter(None, [
        btn("❤️ Здоровье", "health"),
        btn("🎯 Хобби", "hobby")
    ]))

    row3 = list(filter(None, [
        btn("🎒 Багаж", "extra"),
        btn("⚠️ Особое условие", "condition")
    ]))

    if row1:
        buttons.append(row1)
    if row2:
        buttons.append(row2)
    if row3:
        buttons.append(row3)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ------------------------
# УВЕДОМЛЕНИЕ ХОДА
# ------------------------
async def notify_current_player():
    if game_state["phase"] != "action":
        return

    user_id = game_state["players_order"][game_state["current_index"]]
    if connected_players[user_id]["eliminated"]:
        return

    await bot.send_message(
        user_id,
        "🟢 Твой ход! Выбери характеристику:",
        reply_markup=get_card_keyboard(user_id)
    )

# ------------------------
# START
# ------------------------
@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    success = add_player(user_id, user_name)

    if not success:
        await message.answer(
            "🚫 Игра уже началась!\n\n"
            "Ты не можешь подключиться к этой партии.\n"
            "Дождись следующей игры ❤️"
        )
        return

    await message.answer(
        "Добро пожаловать в БУНКЕР 🏚\n\n"
        "/card — получить карточку\n\n"
        "📸 Отправь фото — станет аватаркой\n\n"
        "Когда все игроки в лобби — нажмите «Начать круг» на сайте"
    )


# КАРТОЧКА
# ------------------------
@dp.message(lambda m: m.text == "/card")
async def give_card(message: types.Message):
    if game_state["phase"] != "lobby":
        await message.answer("❌ Карточки можно получать только в лобби")
        return
    user_id = message.from_user.id
    card = generate_card()
    set_card(user_id, card)

    player = connected_players[user_id]

    # 🔴 Удаляем старую карточку
    old_msg_id = player.get("card_message_id")
    if old_msg_id:
        try:
            await bot.delete_message(
                chat_id=message.chat.id,
                message_id=old_msg_id
            )
        except Exception:
            pass  # сообщение могло быть удалено вручную

    text = (
        "🧾 ТВОЯ КАРТОЧКА:\n\n"
        f"👤 Профессия: {card['profession']}\n"
        f"🎂 Возраст: {card['age']} ({card['gender']})\n"
        f"❤️ Здоровье: {card['health']}\n"
        f"🎯 Хобби: {card['hobby']}\n"
        f"🎒 Багаж: {card['extra']}\n\n"
        f"⚠️ Особое условие: {card['condition']}\n\n"
        "🔒 Карточка секретная\n"
        "📌 В ЗАКРЕПЕ"
    )

    sent = await message.answer(text)

    # 📌 Закрепляем новую
    try:
        await bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=sent.message_id,
            disable_notification=True
        )
    except Exception:
        pass

    # 💾 Сохраняем ID новой карточки
    player["card_message_id"] = sent.message_id



# ------------------------
# ОТКРЫТИЕ ПОЛЯ
# ------------------------
@dp.callback_query(lambda c: c.data.startswith("open_"))
async def process_open(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current_id = game_state["players_order"][game_state["current_index"]]

    if user_id != current_id:
        await callback.answer("❌ Не твой ход", show_alert=True)
        return

    field = callback.data.replace("open_", "")
    open_field(user_id, field)

    value = connected_players[user_id]["card"][field]
    await callback.message.answer(f"🔓 {field.capitalize()}: {value}")
    await callback.answer()

    # РЕАГИРУЕМ НА СОСТОЯНИЕ
    if game_state["phase"] == "voting":
        await send_voting()
    else:
        await notify_current_player()

# ------------------------
# НАЧАТЬ КРУГ
# ------------------------
@dp.message(lambda m: m.text == "Начать круг")
async def start_game(message: types.Message):
    if game_state["phase"] != "lobby":
        return

    start_round()
    await message.answer("🟢 Круг начался")
    await notify_current_player()

# ------------------------
# ГОЛОСОВАНИЕ
# ------------------------
def get_vote_keyboard():
    builder = InlineKeyboardBuilder()

    for pid in game_state["players_order"]:
        if not connected_players[pid]["eliminated"]:
            builder.button(text=connected_players[pid]["name"], callback_data=f"vote_{pid}")

    builder.button(text="Пропустить", callback_data="vote_skip")
    builder.adjust(2)
    return builder.as_markup()

async def send_voting():
    for pid in game_state["players_order"]:
        if not connected_players[pid]["eliminated"]:
            await bot.send_message(
                pid,
                "🗳️ Голосование! Кого изгнать?",
                reply_markup=get_vote_keyboard()
            )

@dp.callback_query(lambda c: c.data.startswith("vote_"))
async def process_vote(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.replace("vote_", "")

    if data == "skip":
        skip_vote(user_id)
        await callback.message.answer("⏭ Голос пропущен")
    else:
        vote(user_id, int(data))
        await callback.message.answer("✅ Голос принят")

    await callback.answer()

    if game_state["phase"] == "action":
        await notify_current_player()

# ------------------------
# ЗАПУСК
# ------------------------
async def main():
    print("🤖 Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

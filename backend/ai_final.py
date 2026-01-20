# backend/ai_final.py
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

MODEL = "mistralai/mistral-7b-instruct"

def generate_ai_final(survivors, dead):

    def format_players(players):
        if not players:
            return "— нет"
        return "\n".join([
            f"- {p['name']} ({p['card']['profession']}, "
            f"{p['card']['age']} лет, {p['card']['health']}, "
            f"хобби: {p['card']['hobby']}, "
            f"доп.: {p['card'].get('extra','нет')})"
            for p in players
        ])

    prompt = f"""
Ты — ведущий настольной игры «Бункер».
Твоя задача — подвести итог партии живо и атмосферно.

Стиль:
- как рассказ ведущего после игры
- не сухо, не отчёт
- без философии, метафор и эмодзи

Выжившие:
{format_players(survivors)}

Погибшие:
{format_players(dead)}

Требования:
1) Чётко скажи, кто выжил, а кто погиб
2) Опиши, как выжившие попытались наладить жизнь в бункере
3) Сам реши, была ли концовка успешной или выжить не удалось
4) Допусти небольшое напряжение или конфликт, если это логично
5) Опираться на характеристики персонажей

Пиши простым, живым русским языком.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Ты строгий ведущий настольной игры."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=600  # 🔹 увеличили лимит, чтобы текст не обрезался
    )

    # 🔹 Проверка и возврат результата
    try:
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка генерации финала: {e}"


print("KEY OK:", bool(os.environ.get("OPENROUTER_API_KEY")))

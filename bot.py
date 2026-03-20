import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
STATE_FILE = Path("state.json")

EMOJI_PATTERN = re.compile(
    "[\U00002600-\U000027BF"
    "\U0001F300-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2702-\u27B0]+",
    flags=re.UNICODE,
)


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"remaining": 0}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def remaining_text(n: int) -> str:
    if n == 0:
        return "занятий не осталось"
    elif n % 10 == 1 and n % 100 != 11:
        return f"осталось {n} занятие"
    elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return f"осталось {n} занятия"
    else:
        return f"осталось {n} занятий"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = load_state()
    n = state["remaining"]
    await update.message.reply_text(
        "Привет! Я буду следить за твоим абонементом на йогу.\n\n"
        "Как пользоваться:\n"
        "• Отправь эмодзи 🧘 — отмечу, что ты сходила на занятие\n"
        "• Отправь число (например, 8) — добавлю столько занятий к абонементу\n"
        "• /status — посмотреть сколько занятий осталось\n\n"
        f"Сейчас {remaining_text(n)}."
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = load_state()
    n = state["remaining"]
    if n == 0:
        await update.message.reply_text("Абонемент пуст. Купи новый и отправь число занятий!")
    else:
        await update.message.reply_text(f"В абонементе {remaining_text(n)}.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()

    # Число → пополнение абонемента
    if text.isdigit():
        count = int(text)
        if count <= 0:
            await update.message.reply_text("Отправь положительное число занятий.")
            return
        state = load_state()
        state["remaining"] += count
        save_state(state)
        n = state["remaining"]
        await update.message.reply_text(
            f"Записала! Добавила {count} занятий.\n"
            f"Теперь в абонементе {remaining_text(n)}. 🎉"
        )
        return

    # Эмодзи → отметить занятие
    stripped = text.replace("\u200d", "").replace("\ufe0f", "").strip()
    if stripped and EMOJI_PATTERN.fullmatch(stripped):
        state = load_state()
        n = state["remaining"]

        if n == 0:
            await update.message.reply_text(
                "В абонементе больше нет занятий. Купи новый и отправь число занятий!"
            )
            return

        state["remaining"] = n - 1
        save_state(state)
        remaining = state["remaining"]

        if remaining == 0:
            await update.message.reply_text(
                "Молодец, сходила на йогу! 🧘\n\n"
                "Это было последнее занятие по абонементу.\n"
                "В следующий раз нужно купить новый абонемент!"
            )
        elif remaining == 1:
            await update.message.reply_text(
                f"Молодец, сходила на йогу! 🧘\n"
                f"Осталось {remaining} занятие — последнее! Не забудь купить новый абонемент."
            )
        else:
            await update.message.reply_text(
                f"Молодец, сходила на йогу! 🧘\n{remaining_text(remaining).capitalize()}."
            )
        return

    # Всё остальное игнорируем
    await update.message.reply_text(
        "Не понимаю. Отправь эмодзи, чтобы отметить занятие, или число, чтобы добавить занятия к абонементу."
    )


def main() -> None:
    if not TOKEN:
        raise ValueError("Не задан TELEGRAM_TOKEN в файле .env")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()

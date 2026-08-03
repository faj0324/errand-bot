"""Smart errand planner Telegram bot."""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
# The HTTP library underneath is chatty at INFO; we only want our own logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("errandbot")

WELCOME = (
    "Hi! I'm your errand planner.\n\n"
    "Just tell me what you need to do in plain English and I'll sort it out.\n\n"
    "Commands:\n"
    "/list - see your open items\n"
    "/plan - get an ordered plan\n"
    "/done <item> - mark something complete\n"
    "/clear - wipe completed items"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to /start with a welcome message."""
    log.info("/start from chat_id=%s", update.effective_chat.id)
    await update.message.reply_text(WELCOME)


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Put it in a .env file.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))

    log.info("Bot starting (long polling). Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()

"""Smart errand planner Telegram bot."""

import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import db
from parsing import parse_message

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
# The HTTP library underneath is chatty at INFO; we only want our own logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("errandbot")

WELCOME = (
    "Hi! I'm your errand planner.\n\n"
    "Just tell me what you need to do in plain English and I'll sort it out.\n"
    "For example: milk, eggs and pick up my prescription before 6pm\n\n"
    "Commands:\n"
    "/list - see your open items\n"
    "/plan - get an ordered plan\n"
    "/done <item> - mark something complete\n"
    "/clear - wipe completed items"
)

CATEGORY_LABELS = {
    "groceries": "Groceries",
    "pharmacy": "Pharmacy",
    "errand": "Errands",
}


def format_deadline(deadline, now):
    """Render a stored ISO deadline the way a person would say it."""
    if not deadline:
        return None
    dt = datetime.fromisoformat(deadline)
    time_part = dt.strftime("%H:%M")
    days = (dt.date() - now.date()).days
    if days == 0:
        return "today 23:59" if time_part == "23:59" else f"by {time_part}"
    if days == 1:
        return f"tomorrow {time_part}"
    return dt.strftime("%a %d %b %H:%M")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to /start with a welcome message."""
    log.info("/start from user_id=%s", update.effective_user.id)
    await update.message.reply_text(WELCOME)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse a free-text message into items and store them."""
    now = datetime.now()
    user_id = update.effective_user.id
    items = parse_message(update.message.text, now)

    if not items:
        await update.message.reply_text("I couldn't find anything to add there.")
        return

    lines = []
    for item in items:
        db.add_item(user_id, item["text"], item["category"], item["deadline"], now)
        when = format_deadline(
            item["deadline"].isoformat() if item["deadline"] else None, now
        )
        label = CATEGORY_LABELS[item["category"]]
        lines.append(f"- {item['text']} ({label}{', ' + when if when else ''})")

    log.info("stored %d item(s) for user_id=%s", len(items), user_id)
    await update.message.reply_text(
        f"Added {len(items)} item{'s' if len(items) != 1 else ''}:\n"
        + "\n".join(lines)
    )


async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log and ignore anyone not on the allowlist."""
    user = update.effective_user
    log.warning(
        "ignored message from unauthorised user_id=%s username=%s",
        user.id if user else "?",
        user.username if user else "?",
    )


def load_allowed_users():
    raw = os.getenv("ALLOWED_USER_IDS", "")
    ids = {part.strip() for part in raw.split(",") if part.strip()}
    if not ids:
        raise SystemExit(
            "ALLOWED_USER_IDS is not set. Add your Telegram user id to .env "
            "so the bot does not accept messages from strangers."
        )
    try:
        return {int(i) for i in ids}
    except ValueError:
        raise SystemExit(f"ALLOWED_USER_IDS must be comma-separated numbers, got: {raw}")


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Put it in a .env file.")

    allowed = load_allowed_users()
    db.init_db()

    app = Application.builder().token(token).build()

    # Every real handler is gated on the allowlist. Telegram verifies the
    # sender id for us, so this cannot be spoofed by the client.
    mine = filters.User(user_id=allowed)
    app.add_handler(CommandHandler("start", start, filters=mine))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & mine, handle_text))
    # Registered last, so it only sees what the gated handlers refused.
    app.add_handler(MessageHandler(~mine, reject))

    log.info("Bot starting (long polling), allowed users: %s", sorted(allowed))
    app.run_polling()


if __name__ == "__main__":
    main()

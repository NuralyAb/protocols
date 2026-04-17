"""Entry-point for the Telegram bot. Run: `python -m app.bot`."""
from __future__ import annotations

import logging
import os
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot.handlers import (
    cmd_change,
    cmd_help,
    cmd_insights,
    cmd_lang,
    cmd_last,
    cmd_login,
    cmd_logout,
    cmd_protocol,
    cmd_start,
    cmd_use,
    handle_question,
)


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN is not set", file=sys.stderr)
        raise SystemExit(2)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("logout", cmd_logout))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("last", cmd_last))
    app.add_handler(CommandHandler("use", cmd_use))
    app.add_handler(CommandHandler("change", cmd_change))
    app.add_handler(CommandHandler("protocol", cmd_protocol))
    app.add_handler(CommandHandler("report", cmd_protocol))  # alias
    app.add_handler(CommandHandler("insights", cmd_insights))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

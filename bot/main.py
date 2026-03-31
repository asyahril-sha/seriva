"""Entrypoint Telegram bot untuk SERIVA (polling-based)."""

from __future__ import annotations

import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from seriva.core.llm_client import LLMClient
from seriva.core.orchestrator import Orchestrator
from seriva.storage.inmemory_store import (
    InMemoryUserStateStore,
    InMemoryWorldStateStore,
)
from bot.handlers import (
    start_handler,
    help_handler,
    role_list_handler,
    set_nova_handler,
    set_role_handler,
    end_session_handler,
    status_handler,
    pause_handler,
    resume_handler,
    flashback_handler,
    nego_handler,
    deal_handler,
    mulai_handler,
    message_handler,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_id = os.getenv("SERIVA_ADMIN_ID")

    if not token or not admin_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN dan SERIVA_ADMIN_ID harus di-set di environment."
        )

    # Setup core SERIVA
    user_store = InMemoryUserStateStore()
    world_store = InMemoryWorldStateStore()
    llm = LLMClient()

    orchestrator = Orchestrator(
        user_store=user_store,
        world_store=world_store,
        llm_client=llm,
    )

    # Setup Telegram Application
    app = Application.builder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("help", help_handler(orchestrator, admin_id)))

    # /role tanpa argumen → list role
    app.add_handler(
        CommandHandler(
            "role",
            role_list_handler(orchestrator, admin_id),
            filters=~filters.Regex(r"^/role\\s+"),
        )
    )
    # /role <id> → switch role
    app.add_handler(
        CommandHandler(
            "role",
            set_role_handler(orchestrator, admin_id),
            filters=filters.Regex(r"^/role\\s+"),
        )
    )

    app.add_handler(CommandHandler("nova", set_nova_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("batal", end_session_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("end", end_session_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("status", status_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("pause", pause_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("resume", resume_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("flashback", flashback_handler(orchestrator, admin_id)))

    # Provider commands
    app.add_handler(CommandHandler("nego", nego_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("deal", deal_handler(orchestrator, admin_id)))
    app.add_handler(CommandHandler("mulai", mulai_handler(orchestrator, admin_id)))

    # Message handler (teks biasa)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler(orchestrator, admin_id),
        )
    )

    logger.info("SERIVA Telegram bot starting (polling mode)...")
    app.run_polling()


if __name__ == "__main__":
    main()

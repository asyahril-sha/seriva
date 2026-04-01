"""Entrypoint Telegram bot untuk SERIVA (polling-based).

Versi ini membaca konfigurasi dari config.load_config():
- TELEGRAM_BOT_TOKEN
- SERIVA_ADMIN_ID
- LLM_API_KEY
- LLM_BASE_URL
- LLM_MODEL

Jalankan dengan:
    python -m bot.main
atau:
    python main.py
"""

from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import load_config
from seriva.core.llm_client import LLMClient, LLMConfig
from seriva.core.orchestrator import Orchestrator
from seriva.storage.inmemory_store import (
    InMemoryUserStateStore,
    InMemoryWorldStateStore,
)
from seriva.memory.milestones import MilestoneStore
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
    # Load konfigurasi dari environment via config.py
    cfg = load_config()

    # Setup core SERIVA
    user_store = InMemoryUserStateStore()
    world_store = InMemoryWorldStateStore()
    milestone_store = MilestoneStore()

    # Konfigurasi LLMClient berdasarkan env
    llm_cfg = LLMConfig(
        api_key=cfg.llm.api_key,
        base_url=cfg.llm.base_url,
        model=cfg.llm.model,
    )
    llm = LLMClient(config=llm_cfg)

    orchestrator = Orchestrator(
        user_store=user_store,
        world_store=world_store,
        llm_client=llm,
        milestone_store=milestone_store,
    )

    # Setup Telegram Application
    app = Application.builder().token(cfg.telegram.bot_token).build()

    admin_id = cfg.telegram.admin_id

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

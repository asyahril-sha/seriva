"""SERIVA – Webhook entrypoint untuk Railway.

Menggunakan python-telegram-bot run_webhook, tanpa aiohttp manual.

Env yang dibutuhkan:
- TELEGRAM_BOT_TOKEN
- SERIVA_ADMIN_ID
- LLM_API_KEY      (atau DEEPSEEK_API_KEY, lihat catatan di bawah)
- LLM_BASE_URL
- LLM_MODEL
- WEBHOOK_URL      -> URL publik Railway untuk webhook (https://.../webhook)
- PORT             -> Port yang diberikan Railway (default 8080 jika tidak ada)

Catatan:
- Jika LLM_API_KEY tidak ada tapi DEEPSEEK_API_KEY ada, maka
  DEEPSEEK_API_KEY akan dipakai sebagai LLM_API_KEY.

Jalankan dengan:
    python -m bot.webhook_main
atau melalui run_deploy.py di Railway.
"""

from __future__ import annotations

import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

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


logger = logging.getLogger(__name__)


def _alias_deepseek_to_llm() -> None:
    """Jika LLM_API_KEY kosong tapi DEEPSEEK_API_KEY ada, pakai itu.

    Ini membuat konfigurasi DeepSeek lebih natural: kamu bisa hanya mengisi
    DEEPSEEK_API_KEY di Railway, dan kode akan otomatis mengisinya ke LLM_API_KEY.
    """

    llm_key = os.getenv("LLM_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    if not llm_key and deepseek_key:
        os.environ["LLM_API_KEY"] = deepseek_key
        logger.info("LLM_API_KEY tidak ada, menggunakan DEEPSEEK_API_KEY sebagai gantinya.")


def main() -> None:
    # Alias env DeepSeek ke LLM
    _alias_deepseek_to_llm()

    # Baca env
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_id = os.getenv("SERIVA_ADMIN_ID")
    webhook_url = os.getenv("WEBHOOK_URL")  # contoh: https://seriva.up.railway.app/webhook
    port = int(os.getenv("PORT", "8080"))

    if not bot_token or not admin_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN dan SERIVA_ADMIN_ID harus di-set di environment."
        )

    if not webhook_url:
        raise RuntimeError(
            "WEBHOOK_URL harus di-set di environment untuk mode webhook."
        )

    llm_api_key = os.getenv("LLM_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL")
    llm_model = os.getenv("LLM_MODEL")

    if not llm_api_key or not llm_base_url or not llm_model:
        raise RuntimeError(
            "LLM_API_KEY, LLM_BASE_URL, dan LLM_MODEL harus di-set di environment "
            "(atau DEEPSEEK_API_KEY diisi sehingga LLM_API_KEY otomatis terisi)."
        )

    # Setup core SERIVA
    user_store = InMemoryUserStateStore()
    world_store = InMemoryWorldStateStore()
    milestone_store = MilestoneStore()

    llm_cfg = LLMConfig(
        api_key=llm_api_key,
        base_url=llm_base_url,
        model=llm_model,
    )
    llm = LLMClient(config=llm_cfg)

    orchestrator = Orchestrator(
        user_store=user_store,
        world_store=world_store,
        llm_client=llm,
        milestone_store=milestone_store,
    )

    # Build Telegram Application
    app = Application.builder().token(bot_token).build()

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

    logger.info("SERIVA Telegram bot starting (webhook mode)...")
    logger.info("Webhook URL: %s", webhook_url)
    logger.info("Listening on 0.0.0.0:%d", port)

    # Jalankan webhook built-in telegram-ext
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="/webhook",        # path lokal
        webhook_url=webhook_url,      # URL publik penuh (harus mengandung /webhook)
    )


if __name__ == "__main__":
    main()

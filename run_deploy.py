#!/usr/bin/env python3
"""SERIVA – Deployment Runner for Railway.

Menangani langkah startup sebelum menjalankan bot webhook:
- Cek environment variables penting.
- Cek import modul inti SERIVA.
- Log status.
- Menjalankan bot.webhook_main.main().

Dipakai sebagai start command di Railway:
    python run_deploy.py
"""

from __future__ import annotations

import logging
import os
import sys


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SERIVA-DEPLOY")


def check_env() -> bool:
    """Cek environment variables yang wajib ada."""

    required = [
        "TELEGRAM_BOT_TOKEN",
        "SERIVA_ADMIN_ID",
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "WEBHOOK_URL",
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        logger.error("❌ Missing env vars: %s", missing)
        return False

    logger.info("✅ All required env vars are set.")
    logger.info("TELEGRAM_BOT_TOKEN: %s...", os.getenv("TELEGRAM_BOT_TOKEN")[:10])
    logger.info("SERIVA_ADMIN_ID: %s", os.getenv("SERIVA_ADMIN_ID"))
    logger.info("WEBHOOK_URL: %s", os.getenv("WEBHOOK_URL"))
    return True


def check_core_imports() -> bool:
    """Cek import modul inti SERIVA."""

    logger.info("🔍 Checking core imports...")

    modules = [
        "seriva.core.state_models",
        "seriva.core.emotion_engine",
        "seriva.core.scene_engine",
        "seriva.core.world_engine",
        "seriva.core.orchestrator",
        "seriva.roles.role_registry",
        "bot.webhook_main",
    ]

    failed = []
    for mod in modules:
        try:
            __import__(mod)
            logger.info("✅ Import OK: %s", mod)
        except Exception as e:  # noqa: BLE001
            logger.error("❌ Import failed: %s (%s)", mod, e)
            failed.append(mod)

    if failed:
        logger.error("❌ Some core imports failed: %s", failed)
        return False

    logger.info("✅ All core imports OK.")
    return True


def main() -> None:
    logger.info("=" * 60)
    logger.info("🚀 SERIVA – Deployment Runner (Webhook Mode)")
    logger.info("=" * 60)

    if not check_env():
        sys.exit(1)

    if not check_core_imports():
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("✅ Preflight checks passed, starting SERIVA bot (webhook)...")
    logger.info("=" * 60)

    try:
        from bot.webhook_main import main as bot_main

        bot_main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        logger.error("❌ Bot error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

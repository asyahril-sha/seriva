#!/usr/bin/env python3
"""SERIVA – Deployment Runner for Railway (Webhook Mode).

Menangani langkah startup sebelum menjalankan bot webhook:
- Cek environment variables penting.
- Cek import modul inti SERIVA.
- Log status.
- Menjalankan bot.webhook_main.main().

Mendukung penggunaan DEEPSEEK_API_KEY sebagai alias LLM_API_KEY.

STRUKTUR YANG DIASUMSIKAN (ROOT REPO):
(root)/run_deploy.py
(root)/requirements.txt
(root)/seriva/core/...
(root)/bot/webhook_main.py

Start command di Railway:
    python run_deploy.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SERIVA-DEPLOY")

# ROOT_DIR adalah root project (folder yang berisi run_deploy.py, seriva/, bot/)
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logger.info("Project ROOT_DIR: %s", ROOT_DIR)

# Debug: list isi ROOT_DIR
try:
    entries = [p.name for p in ROOT_DIR.iterdir()]
    logger.info("Root entries: %s", entries)
except Exception as e:  # noqa: BLE001
    logger.error("Tidak bisa melist ROOT_DIR: %s", e)


def _alias_deepseek_to_llm() -> None:
    """Jika LLM_API_KEY belum di-set tapi DEEPSEEK_API_KEY ada, pakai itu."""

    llm_key = os.getenv("LLM_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    if not llm_key and deepseek_key:
        os.environ["LLM_API_KEY"] = deepseek_key
        logger.info("LLM_API_KEY tidak ada, menggunakan DEEPSEEK_API_KEY.")


def check_env() -> bool:
    """Cek environment variables yang wajib ada."""

    _alias_deepseek_to_llm()

    required = [
        "TELEGRAM_BOT_TOKEN",
        "SERIVA_ADMIN_ID",
        "LLM_API_KEY",      # bisa terisi dari DEEPSEEK_API_KEY
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

    if os.getenv("DEEPSEEK_API_KEY"):
        logger.info("DEEPSEEK_API_KEY is set (used as LLM_API_KEY if LLM_API_KEY was empty).")

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

    failed: list[str] = []
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

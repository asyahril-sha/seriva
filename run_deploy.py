import os
import sys
import importlib
from pathlib import Path
from datetime import datetime


def log(level: str, message: str) -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{now} | {level} | SERIVA-DEPLOY | {message}")


def ensure_root_on_sys_path() -> Path:
    """Pastikan root project (/app di Railway) ada di sys.path."""
    root_dir = Path(__file__).resolve().parent
    log("INFO", f"Project ROOT_DIR: {root_dir}")
    log("INFO", f"Root entries: {[p.name for p in root_dir.iterdir()]}")

    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    return root_dir


def alias_deepseek_to_llm_env() -> None:
    """Kalau LLM_API_KEY kosong tapi DEEPSEEK_API_KEY ada, buat alias."""
    llm_key = os.getenv("LLM_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    if not llm_key and deepseek_key:
        os.environ["LLM_API_KEY"] = deepseek_key
        log("INFO", "LLM_API_KEY tidak ada, menggunakan DEEPSEEK_API_KEY.")
    else:
        if llm_key:
            log("INFO", "LLM_API_KEY sudah ter-set secara eksplisit.")
        else:
            log("ERROR", "Tidak ada LLM_API_KEY maupun DEEPSEEK_API_KEY di env.")


def check_env() -> bool:
    required = [
        "TELEGRAM_BOT_TOKEN",
        "SERIVA_ADMIN_ID",
        "WEBHOOK_URL",
        "DEEPSEEK_API_KEY",  # dipakai sebagai sumber LLM_API_KEY
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        log("ERROR", f"Missing required env vars: {missing}")
        return False

    log("INFO", "✅ All required env vars are set.")
    log("INFO", f"TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN')[:10]}...")
    log("INFO", f"SERIVA_ADMIN_ID: {os.getenv('SERIVA_ADMIN_ID')}")
    log("INFO", f"WEBHOOK_URL: {os.getenv('WEBHOOK_URL')}")
    if os.getenv("DEEPSEEK_API_KEY"):
        log("INFO", "DEEPSEEK_API_KEY is set (used as LLM_API_KEY if LLM_API_KEY was empty).")
    return True


def check_core_imports() -> bool:
    """Pastikan semua modul inti bisa di-import dengan ROOT-level path.

    Di sini kita cek *tanpa* prefix `seriva.` karena struktur di Railway adalah
    langsung `/app/core`, `/app/bot`, dst.
    """

    modules_to_check = [
        "core.state_models",
        "core.emotion_engine",
        "core.scene_engine",
        "core.world_engine",
        "core.orchestrator",
        "roles.role_registry",
        "bot.webhook_main",
    ]

    all_ok = True
    log("INFO", "🔍 Checking core imports...")
    for mod_name in modules_to_check:
        try:
            importlib.import_module(mod_name)
        except Exception as e:  # noqa: BLE001
            log("ERROR", f"❌ Import failed: {mod_name} ({e})")
            all_ok = False
    return all_ok


def main() -> None:
    log("INFO", "============================================================")
    log("INFO", "🚀 SERIVA – Deployment Runner (Webhook Mode)")
    log("INFO", "============================================================")

    ensure_root_on_sys_path()
    alias_deepseek_to_llm_env()

    if not check_env():
        log("ERROR", "Environment check failed. Exiting.")
        sys.exit(1)

    if not check_core_imports():
        log(
            "ERROR",
            "❌ Some core imports failed. Pastikan semua import sudah pakai root-level, "
            "contoh: 'from core.state_models import UserState' bukan "
            "'from seriva.core.state_models import UserState'.",
        )
        sys.exit(1)

    # Semua ok, jalankan webhook_main
    try:
        from bot import webhook_main
    except Exception as e:  # noqa: BLE001
        log("ERROR", f"Gagal import bot.webhook_main: {e}")
        sys.exit(1)

    log("INFO", "✅ Starting webhook_main.main() ...")
    webhook_main.main()


if __name__ == "__main__":
    main()

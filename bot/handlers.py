"""Telegram handlers for SERIVA bot.

Menghubungkan Telegram update dengan Orchestrator SERIVA.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from telegram import Update
from telegram.ext import CallbackContext

from seriva.config.constants import list_role_summaries
from seriva.core.orchestrator import Orchestrator, OrchestratorInput
from seriva.core.state_models import SessionMode
from seriva.config.constants import ROLE_ID_NOVA

logger = logging.getLogger(__name__)


# ==============================
# HELPER: ADMIN CHECK
# ==============================


def is_authorized_user(update: Update, admin_id: str) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return str(user.id) == str(admin_id)


def require_admin(admin_id: str) -> Callable:
    """Decorator sederhana untuk memblokir non-admin."""

    def decorator(func: Callable):
        def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
            if not is_authorized_user(update, admin_id):
                chat = update.effective_chat
                if chat is not None:
                    chat.send_message("Maaf, bot ini hanya bisa dipakai oleh admin yang ditentukan.")
                return
            return func(update, context, *args, **kwargs)

        return wrapper

    return decorator


# ==============================
# HANDLERS
# ==============================


def start_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    def _handler(update: Update, context: CallbackContext) -> None:
        chat = update.effective_chat
        if chat is None:
            return
        chat.send_message(
            "Halo Mas, ini SERIVA.\n\n"
            "Ketik aja seperti ngobrol biasa, atau pakai command:\n"
            "- /nova → balik ke Nova\n"
            "- /role → lihat daftar role\n"
            "- /role <id> → pindah ke role tertentu\n"
            "- /batal → akhiri sesi khusus & balik ke chat biasa\n"
            "- /status → lihat ringkasan perasaan & adegan role aktif"
        )

    return _handler


def help_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    def _handler(update: Update, context: CallbackContext) -> None:
        chat = update.effective_chat
        if chat is None:
            return
        chat.send_message(
            "Daftar command SERIVA:\n"
            "- /nova → ngobrol dengan Nova (pasangan utama)\n"
            "- /role → lihat daftar role yang tersedia\n"
            "- /role <id> → pindah ke role tertentu (misal: /role teman_spesial_davina)\n"
            "- /batal atau /end → akhiri sesi khusus dan kembali ke mode normal\n"
            "- /status → lihat ringkasan perasaan & adegan role aktif"
        )

    return _handler


def role_list_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    def _handler(update: Update, context: CallbackContext) -> None:
        chat = update.effective_chat
        if chat is None:
            return

        summaries = list_role_summaries()
        lines = ["Role yang tersedia:"]
        for item in summaries:
            lines.append(f"- {item['role_id']}: {item['label']}")

        chat.send_message("\n".join(lines))

    return _handler


def set_nova_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    def _handler(update: Update, context: CallbackContext) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        user_state = orchestrator._load_or_init_user_state(str(user.id))  # type: ignore[attr-defined]
        user_state.active_role_id = ROLE_ID_NOVA
        orchestrator._save_all(user_state, orchestrator._load_or_init_world_state())  # type: ignore[attr-defined]

        chat.send_message("Sekarang kamu lagi ngobrol sama Nova, Mas.")

    return _handler


def set_role_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    def _handler(update: Update, context: CallbackContext) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        args = context.args or []
        if not args:
            chat.send_message("Contoh: /role teman_spesial_davina")
            return

        role_id = args[0].strip()

        # Validasi role_id via constants list
        summaries = list_role_summaries()
        valid_ids = {item["role_id"] for item in summaries}
        if role_id not in valid_ids:
            chat.send_message("Role tidak ditemukan. Ketik /role untuk lihat daftar role yang ada.")
            return

        user_state = orchestrator._load_or_init_user_state(str(user.id))  # type: ignore[attr-defined]
        user_state.active_role_id = role_id
        orchestrator._save_all(user_state, orchestrator._load_or_init_world_state())  # type: ignore[attr-defined]

        label = next((item["label"] for item in summaries if item["role_id"] == role_id), role_id)
        chat.send_message(f"Sekarang kamu lagi sama {label}.")

    return _handler


def end_session_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    def _handler(update: Update, context: CallbackContext) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        inp = OrchestratorInput(
            user_id=str(user.id),
            text="/batal",
            timestamp=time.time(),
            is_command=True,
            command_name="batal",
        )
        out = orchestrator.handle_input(inp)
        chat.send_message(out.reply_text)

    return _handler


def status_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    def _handler(update: Update, context: CallbackContext) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        user_state = orchestrator._load_or_init_user_state(str(user.id))  # type: ignore[attr-defined]
        role_id = user_state.active_role_id
        role_state = user_state.get_or_create_role_state(role_id)

        e = role_state.emotions
        r = role_state.relationship
        s = role_state.scene

        text_lines = [
            f"Role aktif: {role_id}",
            "",
            "[Emosi]",
            f"- Level hubungan: {r.relationship_level} (1–12)",
            f"- Love: {e.love}",
            f"- Longing (kangen): {e.longing}",
            f"- Jealousy (cemburu): {e.jealousy}",
            f"- Comfort (nyaman): {e.comfort}",
            f"- Intimacy intensity: {e.intimacy_intensity} (1–12)",
            f"- Mood: {e.mood.value}",
            "",
            "[Scene]",
            f"- Lokasi: {s.location or '-'}",
            f"- Posture: {s.posture or '-'}",
            f"- Aktivitas: {s.activity or '-'}",
            f"- Suasana: {s.ambience or '-'}",
            f"- Waktu: {s.time_of_day.value if s.time_of_day else '-'}",
            f"- Jarak fisik: {s.physical_distance or '-'}",
            f"- Sentuhan terakhir: {s.last_touch or '-'}",
        ]

        chat.send_message("\n".join(text_lines))

    return _handler


def message_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    def _handler(update: Update, context: CallbackContext) -> None:
        chat = update.effective_chat
        user = update.effective_user
        msg = update.effective_message
        if chat is None or user is None or msg is None:
            return

        text = msg.text or ""
        now_ts = time.time()

        # Pesan biasa (bukan command khusus END/ROLE dsb.)
        inp = OrchestratorInput(
            user_id=str(user.id),
            text=text,
            timestamp=now_ts,
            is_command=text.startswith("/"),
            command_name=None,
        )

        out = orchestrator.handle_input(inp)
        chat.send_message(out.reply_text)

    return _handler

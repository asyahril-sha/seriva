"""Telegram handlers for SERIVA bot.

Menghubungkan Telegram update dengan Orchestrator SERIVA.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Awaitable, TypeVar, ParamSpec

from telegram import Update
from telegram.ext import ContextTypes

from config.constants import list_role_summaries, ROLE_ID_NOVA
from core.orchestrator import Orchestrator, OrchestratorInput, OrchestratorOutput
from core.state_models import SessionMode

logger = logging.getLogger(__name__)

PROCESSED_UPDATES = set()
P = ParamSpec("P")
R = TypeVar("R")



# ==============================
# HELPER: ADMIN CHECK
# ==============================


def is_authorized_user(update: Update, admin_id: str) -> bool:
    user = update.effective_user
    if user is None:
        return False
    return str(user.id) == str(admin_id)


def require_admin(admin_id: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator sederhana untuk memblokir non-admin (async-compatible)."""

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[override]
            # Expect pola (update, context, ...)
            update: Update = args[0]
            context: ContextTypes.DEFAULT_TYPE = args[1]

            if not is_authorized_user(update, admin_id):
                chat = update.effective_chat
                if chat is not None:
                    await chat.send_message(
                        "Maaf, bot ini hanya bisa dipakai oleh admin yang ditentukan."
                    )
                # type: ignore[return-value]
                return None

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ==============================
# HANDLER COMMAND DASAR
# ==============================


def start_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        if chat is None:
            return
        await chat.send_message(
            "Halo Mas, ini SERIVA.\n\n"
            "Ketik aja seperti ngobrol biasa, atau pakai command:\n"
            "- /nova → balik ke Nova\n"
            "- /role → lihat daftar role\n"
            "- /role <id> → pindah ke role tertentu\n"
            "- /pause → pause sesi intens saat ini\n"
            "- /resume → lanjutkan sesi yang di-pause\n"
            "- /batal → akhiri sesi khusus & balik ke chat biasa\n"
            "- /status → lihat ringkasan perasaan & adegan role aktif\n"
            "- /flashback → minta role cerita ulang momen indah kalian\n"
            "- /nego <harga>, /deal, /mulai → alur khusus untuk terapis & teman spesial"
        )

    return _handler


def help_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        if chat is None:
            return
        await chat.send_message(
            "Daftar command SERIVA:\n"
            "- /nova → ngobrol dengan Nova (pasangan utama)\n"
            "- /role → lihat daftar role yang tersedia\n"
            "- /role <id> → pindah ke role tertentu (misal: /role teman_spesial_davina)\n"
            "- /pause → pause sesi intens saat ini (roleplay/provider)\n"
            "- /resume → lanjutkan sesi yang di-pause dari posisi terakhir\n"
            "- /batal atau /end → akhiri sesi khusus dan kembali ke mode normal\n"
            "- /status → lihat ringkasan perasaan & adegan role aktif\n"
            "- /flashback → minta role cerita ulang satu momen indah/khas dengan Mas\n"
            "- /nego <harga> → nego harga dengan terapis/teman spesial aktif\n"
            "- /deal → konfirmasi setelah nego\n"
            "- /mulai → mulai sesi setelah /deal"
        )

    return _handler


# ==============================
# HANDLER ROLE LIST & SWITCH
# ==============================


def role_list_handler(orchestrator: Orchestrator, admin_id: str):
    """/role tanpa argumen: tampilkan daftar role."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        if chat is None:
            return

        summaries = list_role_summaries()
        lines = ["Role yang tersedia:"]
        for item in summaries:
            lines.append(f"- {item['role_id']}: {item['label']}")

        lines.append("\nGunakan /role <id> untuk pindah ke role tertentu.")

        await chat.send_message("\n".join(lines))

    return _handler


def set_nova_handler(orchestrator: Orchestrator, admin_id: str):
    """/nova: paksa role aktif ke Nova."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        user_state = orchestrator._load_or_init_user_state(str(user.id))  # type: ignore[attr-defined]
        user_state.active_role_id = ROLE_ID_NOVA
        orchestrator._save_all(user_state, orchestrator._load_or_init_world_state())  # type: ignore[attr-defined]

        await chat.send_message("Sekarang kamu lagi ngobrol sama Nova, Mas.")

    return _handler


def set_role_handler(orchestrator: Orchestrator, admin_id: str):
    """/role <id>: pindah role aktif."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        args = context.args or []
        if not args:
            await chat.send_message(
                "Contoh: /role teman_spesial_davina.\n"
                "Ketik /role tanpa argumen untuk lihat daftar role."
            )
            return

        role_id = args[0].strip()

        summaries = list_role_summaries()
        valid_ids = {item["role_id"] for item in summaries}
        if role_id not in valid_ids:
            await chat.send_message(
                "Role tidak ditemukan. Ketik /role untuk lihat daftar role yang ada."
            )
            return

        user_state = orchestrator._load_or_init_user_state(str(user.id))  # type: ignore[attr-defined]
        user_state.active_role_id = role_id
        orchestrator._save_all(user_state, orchestrator._load_or_init_world_state())  # type: ignore[attr-defined]

        label = next((item["label"] for item in summaries if item["role_id"] == role_id), role_id)
        await chat.send_message(f"Sekarang kamu lagi sama {label}.")

    return _handler


# ==============================
# HANDLER END / STATUS
# ==============================


def end_session_handler(orchestrator: Orchestrator, admin_id: str):
    """/batal atau /end: akhiri sesi khusus (pakai logika Orchestrator)."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
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
        out: OrchestratorOutput = orchestrator.handle_input(inp)
        await chat.send_message(out.reply_text)

    return _handler


def status_handler(orchestrator: Orchestrator, admin_id: str):
    """/status: tampilkan ringkasan emosi & scene role aktif."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
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

        await chat.send_message("\n".join(text_lines))

    return _handler


# ==============================
# HANDLER /PAUSE dan /RESUME
# ==============================


def pause_handler(orchestrator: Orchestrator, admin_id: str):
    """/pause: pause sesi intens (tanpa reset state)."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        user_state = orchestrator._load_or_init_user_state(str(user.id))  # type: ignore[attr-defined]
        user_state.global_session_mode = SessionMode.NORMAL
        orchestrator._save_all(user_state, orchestrator._load_or_init_world_state())  # type: ignore[attr-defined]

        await chat.send_message("⏸️ Sesi dihentikan sementara. Ketik /resume untuk lanjut.")

    return _handler


def resume_handler(orchestrator: Orchestrator, admin_id: str):
    """/resume: lanjutkan sesi dari suasana terakhir."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        user_state = orchestrator._load_or_init_user_state(str(user.id))  # type: ignore[attr-defined]
        user_state.global_session_mode = SessionMode.NORMAL
        orchestrator._save_all(user_state, orchestrator._load_or_init_world_state())  # type: ignore[attr-defined]

        await chat.send_message(
            "▶️ Sesi dilanjutkan! Silakan lanjut ngobrol, role akan melanjutkan dari suasana terakhir."
        )

    return _handler


# ==============================
# HANDLER /FLASHBACK
# ==============================


def flashback_handler(orchestrator: Orchestrator, admin_id: str):
    """/flashback: minta role aktif cerita satu momen indah/khas."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        inp = OrchestratorInput(
            user_id=str(user.id),
            text="/flashback",
            timestamp=time.time(),
            is_command=True,
            command_name="flashback",
        )
        out: OrchestratorOutput = orchestrator.handle_input(inp)
        await chat.send_message(out.reply_text)

    return _handler


# ==============================
# HANDLER PROVIDER: /nego, /deal, /mulai
# ==============================


def nego_handler(orchestrator: Orchestrator, admin_id: str):
    """/nego <harga>: nego harga untuk role provider."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        text = update.effective_message.text or ""
        now_ts = time.time()

        inp = OrchestratorInput(
            user_id=str(user.id),
            text=text,
            timestamp=now_ts,
            is_command=True,
            command_name="nego",
        )
        out: OrchestratorOutput = orchestrator.handle_input(inp)
        await chat.send_message(out.reply_text)

    return _handler


def deal_handler(orchestrator: Orchestrator, admin_id: str):
    """/deal: konfirmasi deal setelah nego."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        now_ts = time.time()

        inp = OrchestratorInput(
            user_id=str(user.id),
            text="/deal",
            timestamp=now_ts,
            is_command=True,
            command_name="deal",
        )
        out: OrchestratorOutput = orchestrator.handle_input(inp)
        await chat.send_message(out.reply_text)

    return _handler


def mulai_handler(orchestrator: Orchestrator, admin_id: str):
    """/mulai: mulai sesi provider setelah deal."""

    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None:
            return

        now_ts = time.time()

        inp = OrchestratorInput(
            user_id=str(user.id),
            text="/mulai",
            timestamp=now_ts,
            is_command=True,
            command_name="mulai",
        )
        out: OrchestratorOutput = orchestrator.handle_input(inp)
        await chat.send_message(out.reply_text)

    return _handler


# ==============================
# HANDLER PESAN BIASA
# ==============================


def message_handler(orchestrator: Orchestrator, admin_id: str):
    @require_admin(admin_id)
    async def _handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:

        if update.update_id in PROCESSED_UPDATES:
            return
        PROCESSED_UPDATES.add(update.update_id)
        if len(PROCESSED_UPDATES) > 1000:
            PROCESSED_UPDATES.clear()
        
        chat = update.effective_chat
        user = update.effective_user
        msg = update.effective_message
        if chat is None or user is None or msg is None:
            return

        text = msg.text or ""
        now_ts = time.time()

        inp = OrchestratorInput(
            user_id=str(user.id),
            text=text,
            timestamp=now_ts,
            is_command=text.startswith("/"),
            command_name=None,
        )

        out: OrchestratorOutput = orchestrator.handle_input(inp)
        await chat.send_message(out.reply_text)

    return _handler

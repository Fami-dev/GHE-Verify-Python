#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════╗
║  🎓 GitHub Education Bot — Telethon Edition              ║
║  Features: Verify, Credits, Referral, Daily Check-in     ║
║  Languages: English & Indonesian                         ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import sys
import asyncio
import logging
import base64
import io
import html as html_lib
import sqlite3
import tempfile
import time
import random
from datetime import datetime
from typing import Any
from dotenv import load_dotenv

# ─── Load Environment ───
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import (
    UserNotParticipantError,
    ChatAdminRequiredError,
    FloodWaitError,
    ServerError,
)
from telethon.errors.rpcerrorlist import AuthKeyDuplicatedError
from telethon.errors.rpcerrorlist import MessageNotModifiedError, QueryIdInvalidError

from language import t
from database import (
    get_or_create_user,
    update_user,
    add_credits,
    deduct_credits,
    get_credits,
    record_pending_referral,
    credit_pending_referral,
    get_total_invites,
    do_checkin,
    get_checkin_info,
    add_verify_log,
    get_user,
    get_dashboard_stats,
    get_verify_settings,
    set_verify_enabled,
    get_all_user_ids,
    check_daily_limit,
    increment_daily_verify_count,
    get_daily_verify_count,
    add_daily_verify_bonus,
    set_daily_verify_limit,
    get_daily_verify_limit,
    get_verify_concurrent_limit,
    set_verify_concurrent_limit,
    get_backup_interval_minutes,
    set_backup_interval_minutes,
    get_verify_credit_cost,
    set_verify_credit_cost,
    get_verify_maintenance_mode,
    set_verify_maintenance_mode,
    set_school_mode_override,
    get_all_school_mode_overrides,
    get_verify_task_statuses,
    delete_verify_task_status,
    create_topup_transaction,
    get_topup_transaction,
    get_user_pending_topup,
    list_pending_topup_transactions,
    update_topup_transaction,
    close_pending_topup_transaction,
    complete_pending_topup_success,
    get_topup_cooldown_remaining,
)
from github_session import (
    GitHubSession,
    parse_cookies,
    generate_student_data,
    generate_teacher_data,
    create_id_card_base64,
    create_teacher_documents_base64,
    get_school_profiles,
    get_public_school_profiles,
    get_private_school_profiles,
    get_school_profile,
    toggle_school_mode,
    apply_school_mode_overrides,
    pick_random_public_school,
)
from log import (
    build_precheck_log_text,
    build_queue_update_log_text,
    build_verify_group_log_text,
    build_verify_owner_log_text,
    normalize_log_status,
)
from verification_core import VerificationCore, VerificationContext, VerificationResult, PollingContext
from payment_gateway import AriePulsaClient

TOPUP_PACKAGES_DEFAULT = {
    5: {"name": "Credit 5", "price": 8000, "unit_price": 1600},
    10: {"name": "Credit 10", "price": 15000, "unit_price": 1500},
    25: {"name": "Credit 25", "price": 35000, "unit_price": 1400},
    50: {"name": "Credit 50", "price": 60000, "unit_price": 1200},
    100: {"name": "Credit 100", "price": 100000, "unit_price": 1000},
}


def _parse_topup_packages_from_env(raw: str) -> dict[int, dict[str, int | str]] | None:
    """Parse package string from env.

    Expected format:
    TOPUP_PACKAGES=5:8000,10:15000,25:35000,50:60000,100:100000
    """
    source = str(raw or "").strip()
    if not source:
        return None

    parsed: dict[int, dict[str, int | str]] = {}
    chunks = [chunk.strip() for chunk in source.replace(";", ",").split(",")]
    for chunk in chunks:
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(f"Invalid chunk '{chunk}'")

        credit_text, price_text = chunk.split(":", 1)
        credits = int(credit_text.strip())
        price = int(price_text.strip())
        if credits <= 0 or price <= 0:
            raise ValueError(f"Invalid pair '{chunk}'")

        parsed[credits] = {
            "name": f"Credit {credits}",
            "price": price,
            "unit_price": max(1, int(round(price / credits))),
        }

    if not parsed:
        return None
    return parsed


def _load_topup_packages() -> dict[int, dict[str, int | str]]:
    env_packages = os.getenv("TOPUP_PACKAGES", "")
    if env_packages.strip():
        try:
            parsed = _parse_topup_packages_from_env(env_packages)
            if parsed:
                return parsed
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Invalid TOPUP_PACKAGES format, fallback to default: %s", exc
            )

    return dict(TOPUP_PACKAGES_DEFAULT)


TOPUP_PACKAGES = _load_topup_packages()

# ═══════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "githubedubot")
OWNER_ID = int(os.getenv("OWNER_ID", "1374294212"))

# Required groups
REQUIRED_GROUPS = []
REQUIRED_GROUP_NAMES = []
REQUIRED_GROUP_LINKS = []
for i in range(1, 4):
    gid = os.getenv(f"REQUIRED_GROUP_{i}", "")
    gname = os.getenv(f"REQUIRED_GROUP_{i}_NAME", f"Group {i}")
    glink = os.getenv(f"REQUIRED_GROUP_{i}_LINK", "")
    if gid:
        REQUIRED_GROUPS.append(int(gid))
        REQUIRED_GROUP_NAMES.append(gname)
        REQUIRED_GROUP_LINKS.append(glink)

LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "0"))
CREDITS_PER_INVITE = int(os.getenv("CREDITS_PER_INVITE", "1"))
DAILY_CHECKIN_CREDITS = int(os.getenv("DAILY_CHECKIN_CREDITS", "1"))
INITIAL_CREDITS = int(os.getenv("INITIAL_CREDITS", "0"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
BOT_SESSION_NAME = os.getenv("BOT_SESSION_NAME", "bot_session")
BOT_START_RETRY_DELAY_SECONDS = int(os.getenv("BOT_START_RETRY_DELAY_SECONDS", "5"))
BOT_START_MAX_RETRIES = int(os.getenv("BOT_START_MAX_RETRIES", "0"))
OWNER_CONTACT_USERNAME = (
    os.getenv("OWNER_CONTACT_USERNAME", "arcvour").strip().lstrip("@") or "arcvour"
)

ARIEPULSA_API_KEY = os.getenv("ARIEPULSA_API_KEY", "").strip()
ARIEPULSA_API_URL = os.getenv(
    "ARIEPULSA_API_URL", "https://ariepulsa.my.id/api/qrisrealtime"
).strip()
ARIEPULSA_CHANNEL = os.getenv("ARIEPULSA_CHANNEL", "QRISREALTIME").strip() or "QRISREALTIME"
TOPUP_AUTO_CHECK_SECONDS = max(1, int(os.getenv("TOPUP_AUTO_CHECK_SECONDS", "5")))
TOPUP_TIMEOUT_SECONDS = max(60, int(os.getenv("TOPUP_TIMEOUT_SECONDS", "600")))
TOPUP_COOLDOWN_SECONDS = max(0, int(os.getenv("TOPUP_COOLDOWN_SECONDS", "60")))
TOPUP_CREDIT_EMOJI = os.getenv("TOPUP_CREDIT_EMOJI", "🎫").strip() or "🎫"
TOPUP_PACKAGE_BUTTON_TEMPLATE = (
    os.getenv("TOPUP_PACKAGE_BUTTON_TEMPLATE", "{emoji} {credits} Credit • {price}")
    .strip()
    or "{emoji} {credits} Credit • {price}"
)
TOPUP_PACKAGE_PREVIEW_TEMPLATE = (
    os.getenv("TOPUP_PACKAGE_PREVIEW_TEMPLATE", "• {emoji} {credits} Credit — {price}")
    .strip()
    or "• {emoji} {credits} Credit — {price}"
)
TOPUP_PACKAGE_BUTTON_LABELS_RAW = os.getenv("TOPUP_PACKAGE_BUTTON_LABELS", "").strip()
TOPUP_PACKAGE_PREVIEW_LABELS_RAW = os.getenv("TOPUP_PACKAGE_PREVIEW_LABELS", "").strip()
CRYPTO_PAYMENT_MANUAL_ENABLED = str(
    os.getenv("CRYPTO_PAYMENT_MANUAL_ENABLED", "0")
).strip().lower() in {"1", "true", "yes", "on"}
CRYPTO_PAYMENT_BUTTON_TEXT = (
    os.getenv("CRYPTO_PAYMENT_BUTTON_TEXT", "🌍 Bayar Luar Negeri (Crypto)").strip()
    or "🌍 Bayar Luar Negeri (Crypto)"
)
CRYPTO_PAYMENT_NOTE = (
    os.getenv(
        "CRYPTO_PAYMENT_NOTE",
        "Pembayaran crypto bersifat manual. Setelah transfer, kirim bukti transfer ke owner.",
    )
    .replace("\\n", "\n")
    .strip()
)
CRYPTO_PAYMENT_ADDRESSES_RAW = os.getenv("CRYPTO_PAYMENT_ADDRESSES", "").strip()
TOPUP_ENABLED = bool(ARIEPULSA_API_KEY)
topup_client = AriePulsaClient(
    api_key=ARIEPULSA_API_KEY,
    base_url=ARIEPULSA_API_URL,
)

# ═══════════════════════════════════════════════════════════
#  Logging Setup
# ═══════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log"),
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
#  Bot Client
# ═══════════════════════════════════════════════════════════


def _start_bot_client() -> TelegramClient:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    session_path = os.path.join(base_dir, BOT_SESSION_NAME)
    retry_delay = max(1, BOT_START_RETRY_DELAY_SECONDS)
    max_retries = max(0, BOT_START_MAX_RETRIES)
    attempt = 0

    while True:
        attempt += 1
        try:
            return TelegramClient(session_path, API_ID, API_HASH).start(
                bot_token=BOT_TOKEN
            )
        except AuthKeyDuplicatedError:
            recovery_session_name = (
                f"{BOT_SESSION_NAME}_recovery_{int(datetime.now().timestamp())}"
            )
            session_path = os.path.join(base_dir, recovery_session_name)
            logger.warning(
                "Auth key session terduplikasi. Pakai session baru: '%s'.",
                session_path,
            )
        except (ServerError, ValueError, OSError) as exc:
            # Telegram kadang mengembalikan RPC -500 (No workers running) saat startup.
            # Perlakukan sebagai transient error dan retry.
            is_transient_value_error = isinstance(exc, ValueError) and (
                "Request was unsuccessful" in str(exc)
            )
            is_transient = (
                isinstance(exc, (ServerError, OSError)) or is_transient_value_error
            )

            if not is_transient:
                raise

            if max_retries and attempt >= max_retries:
                logger.error(
                    "Bot gagal start setelah %s percobaan terakhir: %s",
                    attempt,
                    exc,
                )
                raise

            logger.warning(
                "Bot start gagal (attempt %s): %s. Retry dalam %ss...",
                attempt,
                exc,
                retry_delay,
            )
            time.sleep(retry_delay)


bot = _start_bot_client()
logger.info("✅ Bot client started successfully")

# Initialize VerificationCore
verification_core = VerificationCore(owner_id=OWNER_ID)

# Session states: user_id -> {state, data...}
user_sessions = {}

# Verify queue runtime state (non-owner only)
active_verifications: dict[int, dict[str, Any]] = {}
verify_queue_lock = asyncio.Lock()
last_queue_heartbeat_at = 0.0
last_db_backup_at = 0.0

# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════


def get_lang(user_id: int) -> str:
    """Get user language"""
    user = get_user(user_id)
    return user["language"] if user else DEFAULT_LANGUAGE


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def _safe_html_text(value: Any) -> str:
    return html_lib.escape(str(value or ""))


def _active_non_owner_count() -> int:
    return sum(1 for uid in active_verifications if not is_owner(uid))


def _queue_slot_text() -> str:
    limit = get_verify_concurrent_limit()
    active = _active_non_owner_count()
    return f"{active}/{limit}"


def _has_free_non_owner_slot() -> bool:
    return _active_non_owner_count() < get_verify_concurrent_limit()


def _get_verify_credit_cost(verify_type: str) -> int:
    return get_verify_credit_cost(verify_type)


def _verify_maintenance_enabled() -> bool:
    return bool(get_verify_maintenance_mode())


def _verify_maintenance_status_label() -> str:
    return "🔴 ON" if _verify_maintenance_enabled() else "🟢 OFF"


def _verify_maintenance_block_text() -> str:
    return (
        "🛠 <b>Maintenance Mode Aktif</b>\n\n"
        "Verifikasi sedang ditutup sementara untuk user biasa. Silakan coba lagi nanti."
    )


def _format_daily_limit(limit: int, lang: str) -> str:
    if limit == 0:
        return "∞ Unlimited" if lang == "en" else "∞ Tanpa Batas"
    return f"{limit}x / day" if lang == "en" else f"{limit}x / hari"


def _format_rupiah(amount: int) -> str:
    return f"Rp {max(0, int(amount)):,.0f}".replace(",", ".")


def _to_int(value: Any, default: int = 0) -> int:
    try:
        text = str(value or "").strip().replace(".", "")
        return int(float(text))
    except Exception:
        return int(default)


def _format_topup_package_text(template: str, credits: int, price: int) -> str:
    safe_template = str(template or "").strip()
    price_text = _format_rupiah(price)
    if not safe_template:
        safe_template = "{emoji} {credits} Credit • {price}"
    try:
        return safe_template.format(
            emoji=TOPUP_CREDIT_EMOJI,
            credits=int(credits),
            price=price_text,
            price_raw=int(price),
        )
    except Exception:
        return f"{TOPUP_CREDIT_EMOJI} {int(credits)} Credit • {price_text}"


def _parse_topup_label_map(raw: str) -> dict[int, str]:
    """Parse label map with format: 5:Text|10:Text|25:Text."""
    parsed: dict[int, str] = {}
    source = str(raw or "").strip()
    if not source:
        return parsed

    normalized = source.replace("\n", "|").replace(";", "|")
    for chunk in normalized.split("|"):
        item = chunk.strip()
        if not item or ":" not in item:
            continue
        credit_text, label_text = item.split(":", 1)
        try:
            credits = int(credit_text.strip())
        except Exception:
            continue
        label = label_text.strip()
        if credits > 0 and label:
            parsed[credits] = label
    return parsed


def _load_topup_label_map(raw: str, key_prefix: str) -> dict[int, str]:
    """Load labels from compact map and per-package env keys.

    Supported formats:
    1) compact: TOPUP_PACKAGE_BUTTON_LABELS=5:Text|10:Text
    2) vertical: TOPUP_PACKAGE_BUTTON_LABEL_5=Text
                 TOPUP_PACKAGE_BUTTON_LABEL_10=Text
    """
    merged = _parse_topup_label_map(raw)
    for credits in sorted(TOPUP_PACKAGES.keys()):
        key_name = f"{key_prefix}_{credits}"
        label = str(os.getenv(key_name, "")).strip()
        if label:
            merged[credits] = label
    return merged


def _parse_crypto_payment_addresses() -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    raw = str(CRYPTO_PAYMENT_ADDRESSES_RAW or "").strip()
    if raw:
        chunks = [chunk.strip() for chunk in raw.replace(";", ",").split(",")]
        for chunk in chunks:
            if not chunk or ":" not in chunk:
                continue
            network, address = chunk.split(":", 1)
            network_text = network.strip()
            address_text = address.strip()
            if network_text and address_text:
                parsed.append((network_text, address_text))

    fallback_map = [
        ("USDT TRC20", os.getenv("CRYPTO_USDT_TRC20_ADDRESS", "")),
        ("BTC", os.getenv("CRYPTO_BTC_ADDRESS", "")),
        ("ETH", os.getenv("CRYPTO_ETH_ADDRESS", "")),
    ]
    if not parsed:
        for network, address in fallback_map:
            if str(address or "").strip():
                parsed.append((network, str(address).strip()))
    return parsed


def _build_topup_package_buttons(lang: str) -> list:
    rows = []
    row = []
    custom_labels = _load_topup_label_map(
        TOPUP_PACKAGE_BUTTON_LABELS_RAW,
        "TOPUP_PACKAGE_BUTTON_LABEL",
    )
    for credits in sorted(TOPUP_PACKAGES.keys()):
        package = TOPUP_PACKAGES.get(credits) or {}
        price = _to_int(package.get("price"), 0)
        label = custom_labels.get(credits) or _format_topup_package_text(
            TOPUP_PACKAGE_BUTTON_TEMPLATE,
            credits,
            price,
        )
        row.append(Button.inline(label, f"topup_pkg_{credits}".encode("utf-8")))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    if CRYPTO_PAYMENT_MANUAL_ENABLED:
        rows.append([Button.inline(CRYPTO_PAYMENT_BUTTON_TEXT, b"topup_crypto_manual")])
    rows.append([Button.inline(t("btn_back", lang), b"back_home")])
    return rows


def _build_topup_active_buttons(lang: str, tx_id: int) -> list:
    return [
        [
            Button.inline(t("btn_topup_refresh", lang), f"topup_refresh_{tx_id}".encode("utf-8")),
            Button.inline(t("btn_topup_cancel_deposit", lang), f"topup_cancel_{tx_id}".encode("utf-8")),
        ],
        [Button.inline(t("btn_back", lang), b"back_home")],
    ]


def _generate_reff_id(user_id: int) -> str:
    return f"ARC-{random.randint(1000000000, 9999999999)}"


def _build_topup_support_buttons(lang: str) -> list:
    return [
        [
            Button.url(
                t("btn_contact_owner", lang, username=OWNER_CONTACT_USERNAME),
                f"https://t.me/{OWNER_CONTACT_USERNAME}",
            )
        ],
        [Button.inline(t("btn_back", lang), b"back_home")],
    ]


def _build_topup_crypto_buttons(lang: str) -> list:
    return [
        [
            Button.url(
                t("btn_contact_owner", lang, username=OWNER_CONTACT_USERNAME),
                f"https://t.me/{OWNER_CONTACT_USERNAME}",
            )
        ],
        [Button.inline(t("btn_topup_back_menu", lang), b"topup_credit")],
        [Button.inline(t("btn_back", lang), b"back_home")],
    ]


def _build_crypto_manual_text(lang: str) -> str:
    addresses = _parse_crypto_payment_addresses()
    is_en = lang == "en"
    note = _safe_html_text(
        CRYPTO_PAYMENT_NOTE
        or (
            "Crypto payment is manual. After transfer, send payment proof to owner."
            if is_en
            else "Pembayaran crypto bersifat manual. Setelah transfer, kirim bukti transfer ke owner."
        )
    )

    if addresses:
        wallet_lines = "\n".join(
            f"• {_safe_html_text(network)}: <code>{_safe_html_text(address)}</code>"
            for network, address in addresses
        )
        wallets_section = (
            ("<b>Wallet Addresses:</b>\n" if is_en else "<b>Alamat Wallet:</b>\n")
            f"<blockquote>{wallet_lines}</blockquote>"
        )
    else:
        wallets_section = (
            "⚠️ <b>Wallet addresses are not configured yet.</b> Please contact the owner first."
            if is_en
            else "⚠️ <b>Alamat wallet belum dikonfigurasi.</b> Silakan hubungi owner terlebih dahulu."
        )

    return (
        (
            "🌍 <b>International Payment (Manual Crypto)</b>\n"
            if is_en
            else "🌍 <b>Pembayaran Luar Negeri (Crypto Manual)</b>\n"
        )
        f"<blockquote>{note}</blockquote>\n"
        f"{wallets_section}\n"
        (
            "After transfer, send payment proof to owner so credits can be processed manually."
            if is_en
            else "Setelah transfer, kirim bukti transfer ke owner agar credit diproses manual."
        )
    )


def _extract_provider_message(result: dict) -> str:
    data = result.get("data") if isinstance(result, dict) else None
    if isinstance(data, dict):
        message = str(data.get("pesan") or data.get("message") or "").strip()
        if message:
            return message
    return "Permintaan tidak sesuai atau provider menolak request."


def _topup_pending_text(tx: dict, lang: str) -> str:
    is_en = lang == "en"
    now_ts = float(time.time())
    expires_at = float(tx.get("expires_at") or 0)
    remain = max(0, int(expires_at - now_ts))
    rm = remain // 60
    rs = remain % 60
    expires_text = "-"
    if expires_at > 0:
        expires_text = datetime.fromtimestamp(expires_at).strftime("%d-%m-%Y %H:%M:%S")
    last_error = str(tx.get("last_error") or "").strip()
    extra = (
        f"\n⚠️ {'Last Error' if is_en else 'Error Terakhir'}: <code>{_safe_html_text(last_error)}</code>"
        if last_error
        else ""
    )
    status_default = "Pending" if is_en else "Menunggu"
    label_deposit = "Deposit"
    label_reff = "Ref ID" if is_en else "Reff ID"
    label_nominal = "Amount" if is_en else "Nominal"
    label_fee = "Fee"
    label_transfer = "Transfer"
    label_credit = "Credit"
    label_status = "Status"
    label_expired = "Expired At" if is_en else "Kadaluarsa"
    label_timeout = "Timeout"
    return (
        ("💳 <b>QRIS Top Up Active</b>\n\n" if is_en else "💳 <b>QRIS Top Up Aktif</b>\n\n")
        "<blockquote>"
        f"🆔 {label_deposit}: <code>{_safe_html_text(tx.get('kode_deposit') or '-')}</code>\n"
        f"🧾 {label_reff}: <code>{_safe_html_text(tx.get('reff_id') or '-')}</code>\n"
        f"💰 {label_nominal}: <b>{_format_rupiah(_to_int(tx.get('nominal')))}</b>\n"
        f"💸 {label_fee}: <b>{_format_rupiah(_to_int(tx.get('fee')))}</b>\n"
        f"🏦 {label_transfer}: <b>{_format_rupiah(_to_int(tx.get('jumlah_transfer')))}</b>\n"
        f"🎫 {label_credit}: <b>+{_to_int(tx.get('credit_amount'))}</b>\n"
        f"⏳ {label_status}: <b>{_safe_html_text(tx.get('provider_status') or status_default)}</b>\n"
        f"🗓 {label_expired}: <b>{_safe_html_text(expires_text)}</b>\n"
        f"⏱ {label_timeout}: <b>{rm:02d}:{rs:02d}</b>"
        f"{extra}"
        "</blockquote>\n\n"
        (
            "Scan the QR above then wait for automatic checks every 5 seconds."
            if is_en
            else "Scan QR di atas lalu tunggu cek otomatis setiap 5 detik."
        )
    )


def _topup_result_text(tx: dict, total_credits: int, success: bool, lang: str) -> str:
    is_en = lang == "en"
    title = (
        "✅ <b>Top Up Success</b>" if success else "❌ <b>Top Up Failed</b>"
    ) if is_en else (
        "✅ <b>Top Up Berhasil</b>" if success else "❌ <b>Top Up Gagal</b>"
    )
    label_deposit = "Deposit"
    label_reff = "Ref ID" if is_en else "Reff ID"
    label_nominal = "Amount" if is_en else "Nominal"
    label_fee = "Fee"
    label_transfer = "Transfer"
    label_credit = "Credit"
    label_status = "Status"
    label_total_credit = "Current Total Credit" if is_en else "Total Credit Saat Ini"
    status_label = tx.get("provider_status") or tx.get("status") or "-"
    return (
        f"{title}\n\n"
        "<blockquote>"
        f"🆔 {label_deposit}: <code>{_safe_html_text(tx.get('kode_deposit') or '-')}</code>\n"
        f"🧾 {label_reff}: <code>{_safe_html_text(tx.get('reff_id') or '-')}</code>\n"
        f"💰 {label_nominal}: <b>{_format_rupiah(_to_int(tx.get('nominal')))}</b>\n"
        f"💸 {label_fee}: <b>{_format_rupiah(_to_int(tx.get('fee')))}</b>\n"
        f"🏦 {label_transfer}: <b>{_format_rupiah(_to_int(tx.get('jumlah_transfer')))}</b>\n"
        f"🎫 {label_credit}: <b>+{_to_int(tx.get('credit_amount'))}</b>\n"
        f"📌 {label_status}: <b>{_safe_html_text(status_label)}</b>\n"
        f"🎫 {label_total_credit}: <b>{int(total_credits)}</b>"
        "</blockquote>"
    )


async def _edit_topup_message(tx: dict, text: str, buttons: list | None = None) -> None:
    chat_id = int(tx.get("message_chat_id") or 0)
    message_id = int(tx.get("message_id") or 0)
    if chat_id <= 0 or message_id <= 0:
        return
    try:
        await bot.edit_message(
            chat_id,
            message_id,
            text,
            buttons=buttons,
            parse_mode="html",
        )
    except MessageNotModifiedError:
        pass
    except Exception as exc:
        logger.warning("Failed to edit topup message %s/%s: %s", chat_id, message_id, exc)


async def _send_topup_result_logs(tx: dict, total_credits: int, success: bool) -> None:
    user_id = int(tx.get("user_id") or 0)
    tg_username = str(tx.get("telegram_username") or "")
    nominal = _to_int(tx.get("nominal"))
    credit_amount = _to_int(tx.get("credit_amount"))
    status_text = "SUCCESS" if success else "FAILED"
    failure_reason = str(tx.get("last_error") or "").strip()

    group_text = (
        f"💳 <b>TOPUP {status_text}</b>\n\n"
        "<blockquote>"
        f"🆔 Telegram ID: <code>{user_id}</code>\n"
        f"💰 Harga: <b>{_format_rupiah(nominal)}</b>\n"
        f"🎫 Credit: <b>{credit_amount}</b>\n"
        f"🎫 Total Credit: <b>{int(total_credits)}</b>"
        "</blockquote>"
    )

    owner_text = (
        f"💳 <b>TOPUP {status_text}</b>\n\n"
        "<blockquote>"
        f"🆔 Telegram ID: <code>{user_id}</code>\n"
        f"👤 Username: <code>{_safe_html_text(tg_username or '-')}</code>\n"
        f"💰 Harga: <b>{_format_rupiah(nominal)}</b>\n"
        f"🎫 Credit: <b>{credit_amount}</b>\n"
        f"🎫 Total Credit: <b>{int(total_credits)}</b>\n"
        f"🏷 Kode Deposit: <code>{_safe_html_text(tx.get('kode_deposit') or '-')}</code>\n"
        f"🧾 Reff ID: <code>{_safe_html_text(tx.get('reff_id') or '-')}</code>\n"
        f"📌 Provider Status: <b>{_safe_html_text(tx.get('provider_status') or tx.get('status') or '-')}</b>"
        "</blockquote>"
    )

    if not success and failure_reason:
        owner_text += (
            "\n\n"
            "<b>⚠️ Failure Reason</b>\n"
            f"<blockquote><code>{_safe_html_text(failure_reason)}</code></blockquote>"
        )

    # Group log hanya untuk top up sukses.
    if success and LOG_GROUP_ID:
        try:
            await bot.send_message(LOG_GROUP_ID, group_text, parse_mode="html")
        except Exception as exc:
            logger.warning("Failed sending topup group log: %s", exc)

    try:
        await bot.send_message(OWNER_ID, owner_text, parse_mode="html")
    except Exception as exc:
        logger.warning("Failed sending topup owner log: %s", exc)


async def _finalize_topup_success(tx_id: int) -> bool:
    done = await asyncio.to_thread(complete_pending_topup_success, tx_id)
    if not done:
        return False
    tx = done["transaction"]
    total_credits = int(done["total_credits"])
    lang = get_lang(int(tx.get("user_id") or 0))
    await _edit_topup_message(
        tx,
        _topup_result_text(tx, total_credits, success=True, lang=lang),
        buttons=build_back_button(lang),
    )
    await _send_topup_result_logs(tx, total_credits, success=True)
    return True


async def _finalize_topup_failure(
    tx_id: int,
    final_status: str,
    provider_status: str,
    reason: str,
) -> bool:
    tx = await asyncio.to_thread(
        close_pending_topup_transaction,
        tx_id,
        final_status,
        provider_status,
        reason,
    )
    if not tx:
        return False
    owner_view = is_owner(int(tx.get("user_id") or 0))
    total_credits = get_credits(int(tx.get("user_id") or 0))
    lang = get_lang(int(tx.get("user_id") or 0))

    fail_mode = str(final_status or "").strip().lower()
    if not owner_view and fail_mode in {"failed", "error"}:
        user_text = (
            "❌ <b>Terjadi error pembayaran</b>\n\n"
            "Silakan hubungi owner untuk bantuan lebih lanjut."
        )
        await _edit_topup_message(tx, user_text, buttons=_build_topup_support_buttons(lang))
    else:
        await _edit_topup_message(
            tx,
            _topup_result_text(tx, total_credits, success=False, lang=lang),
            buttons=build_back_button(lang),
        )

    await _send_topup_result_logs(tx, total_credits, success=False)
    return True


async def _sync_topup_status(tx: dict, from_manual: bool = False) -> str:
    tx_id = int(tx.get("id") or 0)
    if tx_id <= 0:
        return "invalid"

    now_ts = float(time.time())
    expires_at = float(tx.get("expires_at") or 0)
    kode_deposit = str(tx.get("kode_deposit") or "").strip()

    if expires_at and now_ts >= expires_at:
        if kode_deposit:
            await asyncio.to_thread(topup_client.cancel_deposit, kode_deposit)
        await _finalize_topup_failure(
            tx_id,
            "expired",
            "Error",
            "Deposit timeout 10 menit, auto-cancel.",
        )
        return "expired"

    if not kode_deposit:
        # Jangan langsung fail; tetap pending agar bisa direfresh/ditunggu sampai timeout.
        update_topup_transaction(
            tx_id,
            last_check_at=now_ts,
            last_error="kode_deposit kosong dari provider",
        )
        if from_manual:
            fresh = get_topup_transaction(tx_id)
            if fresh:
                await _edit_topup_message(
                    fresh,
                    _topup_pending_text(fresh, get_lang(int(fresh.get("user_id") or 0))),
                    buttons=_build_topup_active_buttons(
                        get_lang(int(fresh.get("user_id") or 0)),
                        int(fresh.get("id") or 0),
                    ),
                )
        return "pending"

    result = await asyncio.to_thread(topup_client.status_deposit, kode_deposit)
    update_topup_transaction(tx_id, last_check_at=now_ts)

    if not result.get("status"):
        reason = _extract_provider_message(result)
        update_topup_transaction(tx_id, last_error=reason)
        return "pending"

    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    provider_status = str(data.get("status") or "Pending").strip()
    provider_status_lower = provider_status.lower()
    jumlah_transfer = _to_int(data.get("jumlah_transfer"), _to_int(tx.get("jumlah_transfer")))

    update_topup_transaction(
        tx_id,
        provider_status=provider_status,
        jumlah_transfer=jumlah_transfer,
        last_error="",
    )

    if provider_status_lower == "success":
        await _finalize_topup_success(tx_id)
        return "success"

    if provider_status_lower == "error":
        await _finalize_topup_failure(
            tx_id,
            "failed",
            provider_status,
            "Provider mengembalikan status Error",
        )
        return "failed"

    if from_manual:
        fresh = get_topup_transaction(tx_id)
        if fresh:
            await _edit_topup_message(
                fresh,
                _topup_pending_text(fresh, get_lang(int(fresh.get("user_id") or 0))),
                buttons=_build_topup_active_buttons(
                    get_lang(int(fresh.get("user_id") or 0)),
                    int(fresh.get("id") or 0),
                ),
            )
    return "pending"


async def topup_monitor() -> None:
    """Monitor pending top-up transactions every few seconds."""
    await asyncio.sleep(3)
    while True:
        try:
            if not TOPUP_ENABLED:
                await asyncio.sleep(10)
                continue

            pending_rows = list_pending_topup_transactions(limit=100)
            for tx in pending_rows:
                tx_id = int(tx.get("id") or 0)
                if tx_id <= 0:
                    continue

                now_ts = float(time.time())
                last_check_at = float(tx.get("last_check_at") or 0)
                if now_ts - last_check_at < TOPUP_AUTO_CHECK_SECONDS:
                    continue

                try:
                    await _sync_topup_status(tx, from_manual=False)
                except Exception as one_err:
                    logger.warning("Topup monitor error tx=%s: %s", tx_id, one_err)
        except Exception as err:
            logger.warning("Topup monitor loop error: %s", err)

        await asyncio.sleep(TOPUP_AUTO_CHECK_SECONDS)


async def safe_callback_answer(
    event, text: str | None = None, alert: bool = False
) -> bool:
    """Safely answer callback query; ignore expired query errors."""
    try:
        if text is None:
            await event.answer()
        else:
            await event.answer(text, alert=alert)
        return True
    except QueryIdInvalidError:
        return False
    except Exception:
        return False


async def send_queue_log(reason: str, include_waiting: bool = True) -> None:
    slot_text = _queue_slot_text()
    body = build_queue_update_log_text(
        slot_text=slot_text,
        reason=reason,
        timestamp_text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    targets = []
    if OWNER_ID:
        targets.append(OWNER_ID)
    if LOG_GROUP_ID:
        targets.append(LOG_GROUP_ID)

    for target in targets:
        try:
            await bot.send_message(target, body, parse_mode="html")
        except Exception as e:
            logger.warning(f"Failed queue log to {target}: {e}")


async def send_bot_precheck_log(
    user_id: int,
    verify_type: str,
    reason: str,
    telegram_username: str | None = None,
    github_username: str | None = None,
) -> None:
    body = build_precheck_log_text(
        telegram_user_id=user_id,
        verify_type=verify_type,
        reason=reason,
        telegram_username=telegram_username,
        github_username=github_username,
        timestamp_text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    targets = []
    if OWNER_ID:
        targets.append(OWNER_ID)

    for target in targets:
        try:
            await bot.send_message(target, body, parse_mode="html")
        except Exception as e:
            logger.warning(f"Failed precheck log to {target}: {e}")


def touch_active_slot(user_id: int, stage: str = "") -> None:
    if user_id in active_verifications:
        active_verifications[user_id]["last_activity_at"] = time.monotonic()
        if stage:
            active_verifications[user_id]["stage"] = stage


def _create_sqlite_backup(src_path: str, dst_path: str) -> None:
    src_conn = sqlite3.connect(src_path, timeout=30)
    try:
        dst_conn = sqlite3.connect(dst_path, timeout=30)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()


async def create_database_backup(trigger: str = "scheduled") -> str | None:
    try:
        if not OWNER_ID:
            logger.warning("[DB Backup] OWNER_ID is empty, skipping %s backup", trigger)
            return None

        base_dir = os.path.dirname(os.path.abspath(__file__))
        src_path = os.path.join(base_dir, "bot_data.db")
        if not os.path.exists(src_path):
            logger.warning("[DB Backup] source db not found: %s", src_path)
            return None

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f"bot_data_{stamp}_", suffix=".db", delete=False
            ) as tmp:
                temp_path = tmp.name

            await asyncio.to_thread(_create_sqlite_backup, src_path, temp_path)

            caption = (
                "💾 <b>Database Backup</b>\n"
                f"<blockquote>"
                f"🧭 Trigger: <code>{_safe_html_text(trigger)}</code>\n"
                f"⏰ Time: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
                f"</blockquote>"
            )
            await bot.send_file(
                OWNER_ID,
                file=temp_path,
                caption=caption,
                parse_mode="html",
                force_document=True,
            )
            logger.info("[DB Backup] %s backup sent to owner", trigger)
            return temp_path
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as remove_err:
                    logger.warning(
                        "[DB Backup] failed removing temp file %s: %s",
                        temp_path,
                        remove_err,
                    )
    except Exception as e:
        logger.error("[DB Backup] %s backup failed: %s", trigger, e)
        return None


def _build_school_label(school) -> str:
    mode = (school.mode or "public").lower()
    mode_icon = "🌐" if mode == "public" else "🔒"
    return f"{mode_icon} {school.name}"


def build_school_select_buttons(
    lang: str, callback_prefix: str = "pick_school"
) -> list:
    buttons = []
    for school in get_school_profiles():
        callback = f"{callback_prefix}_{school.code}".encode("utf-8")
        buttons.append([Button.inline(_build_school_label(school), callback)])
    buttons.append([Button.inline(t("btn_cancel", lang), b"cancel_op")])
    return buttons


def _school_mode_icon(mode: str) -> str:
    return "🌐" if (mode or "").strip().lower() == "public" else "🔒"


def build_school_mode_manage_buttons(lang: str) -> list:
    buttons = []
    for school in get_school_profiles():
        mode_icon = _school_mode_icon(school.mode)
        next_mode = "private" if school.mode == "public" else "public"
        next_icon = _school_mode_icon(next_mode)
        label = f"{mode_icon} {school.name} → {next_icon}"
        callback = f"toggle_school_mode_{school.code}".encode("utf-8")
        buttons.append([Button.inline(label, callback)])
    buttons.append([Button.inline(t("btn_back", lang), b"owner_menu")])
    return buttons


def build_school_mode_manage_text(lang: str) -> str:
    total = len(get_school_profiles())
    public_count = len(get_public_school_profiles())
    private_count = len(get_private_school_profiles())
    return t(
        "owner_school_mode_text",
        lang,
        total=total,
        public_count=public_count,
        private_count=private_count,
    )


async def send_cookie_prompt(
    user_id: int, lang: str, verify_type: str, school_code: str
) -> None:
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Tutorial.png")
    sent = await bot.send_file(
        user_id,
        img_path,
        caption=t("enter_cookie", lang, credits=_get_verify_credit_cost(verify_type)),
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )
    user_sessions[user_id] = {
        "state": "waiting_cookie",
        "type": verify_type,
        "school_code": school_code,
        "msg_id": sent.id,
    }


async def start_school_or_cookie_flow(
    event, user_id: int, lang: str, verify_type: str
) -> None:
    if is_owner(user_id):
        user_sessions[user_id] = {
            "state": "waiting_school_select",
            "type": verify_type,
        }
        await bot.send_message(
            user_id,
            "🏫 <b>Pilih sekolah untuk verifikasi ini</b>\n"
            "<blockquote>"
            "🌐 Public: bisa dipakai random untuk user publik\n"
            "🔒 Private: hanya owner yang bisa gunakan"
            "</blockquote>",
            buttons=build_school_select_buttons(lang),
            parse_mode="html",
        )
        return

    public_schools = get_public_school_profiles()
    if not public_schools:
        await event.respond(
            "❌ Tidak ada sekolah mode public yang aktif di konfigurasi.",
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        user_sessions.pop(user_id, None)
        return

    selected = pick_random_public_school()
    await send_cookie_prompt(user_id, lang, verify_type, selected.code)


async def check_user_in_group(user_id: int) -> list[bool]:
    """Check if user is in all required groups"""
    results = []
    for gid in REQUIRED_GROUPS:
        try:
            await bot(GetParticipantRequest(gid, user_id))
            results.append(True)
        except (UserNotParticipantError, ChatAdminRequiredError):
            results.append(False)
        except Exception:
            results.append(False)
    return results


# ═══════════════════════════════════════════════════════════
#  Button Builders
# ═══════════════════════════════════════════════════════════


def build_join_buttons(lang: str) -> list:
    """Build group join buttons + check button"""
    buttons = []
    for i, (name, link) in enumerate(zip(REQUIRED_GROUP_NAMES, REQUIRED_GROUP_LINKS)):
        buttons.append([Button.url(t("join_btn", lang, name=name), link)])
    buttons.append([Button.inline(t("check_join", lang), b"check_join")])
    return buttons


def build_dashboard_buttons(lang: str, user_id: int) -> list:
    """Build main dashboard buttons"""
    settings = get_verify_settings()
    can_show_student = (
        settings.get("student_bot", settings.get("student", True))
        or user_id == OWNER_ID
    )
    can_show_teacher = (
        settings.get("teacher_bot", settings.get("teacher", True))
        or user_id == OWNER_ID
    )

    buttons = []
    verify_row = []
    if can_show_student:
        verify_row.append(Button.inline(t("btn_verify", lang), b"verify_student"))
    if can_show_teacher:
        verify_row.append(
            Button.inline(t("btn_verify_teacher", lang), b"verify_teacher")
        )
    if verify_row:
        buttons.append(verify_row)

    buttons.extend(
        [
            [
                Button.inline(t("btn_referral", lang), b"referral"),
                Button.inline(t("btn_checkin", lang), b"checkin"),
            ],
            [Button.inline(t("btn_topup_credit", lang), b"topup_credit")],
            [Button.inline(t("btn_language", lang), b"change_lang")],
        ]
    )

    if user_id == OWNER_ID:
        buttons.append([Button.inline(t("btn_owner", lang), b"owner_menu")])
    return buttons


def build_tos_buttons(lang: str) -> list:
    return [
        [Button.inline(t("tos_accept", lang), b"tos_accept")],
        [Button.inline(t("tos_decline", lang), b"tos_decline")],
    ]


def build_back_button(lang: str) -> list:
    return [[Button.inline(t("btn_back", lang), b"back_home")]]


def build_cancel_button(lang: str) -> list:
    return [[Button.inline(t("btn_cancel", lang), b"cancel")]]


def build_lang_buttons() -> list:
    return [
        [
            Button.inline(t("btn_lang_en", "en"), b"set_lang_en"),
            Button.inline(t("btn_lang_id", "id"), b"set_lang_id"),
        ],
    ]


def build_type_buttons(lang: str) -> list:
    return [
        [
            Button.inline(t("btn_student", lang), b"type_student"),
            Button.inline(t("btn_teacher", lang), b"type_teacher"),
        ],
        [Button.inline(t("btn_back", lang), b"back_home")],
    ]


def build_owner_buttons(lang: str) -> list:
    settings = get_verify_settings()
    student_status = (
        f"B:{'ON' if settings.get('student_bot', True) else 'OFF'} "
        f"W:{'ON' if settings.get('student_web', True) else 'OFF'}"
    )
    teacher_status = (
        f"B:{'ON' if settings.get('teacher_bot', True) else 'OFF'} "
        f"W:{'ON' if settings.get('teacher_web', True) else 'OFF'}"
    )
    limit = settings["daily_limit"]
    queue_limit = settings.get("queue_limit", get_verify_concurrent_limit())
    backup_interval = settings.get(
        "backup_interval_minutes", get_backup_interval_minutes()
    )
    student_credit_cost = settings.get(
        "student_credit_cost", get_verify_credit_cost("student")
    )
    teacher_credit_cost = settings.get(
        "teacher_credit_cost", get_verify_credit_cost("teacher")
    )
    limit_label = _format_daily_limit(limit, lang)
    queue_label = f"{_active_non_owner_count()}/{queue_limit}"
    backup_label = f"{backup_interval}m"

    # Compact 2-column layout for owner menu to improve readability on mobile
    return [
        [
            Button.inline(t("btn_test_log", lang), b"test_log"),
            Button.inline(t("btn_owner_add_credit", lang), b"owner_add_credit"),
        ],
        [
            Button.inline(
                f"🎓 Student Scope {student_status}",
                b"toggle_verify_student",
            ),
            Button.inline(
                f"👨‍🏫 Teacher Scope {teacher_status}",
                b"toggle_verify_teacher",
            ),
        ],
        [
            Button.inline(
                f"🛠 Maintenance: {_verify_maintenance_status_label()}",
                b"toggle_verify_maintenance",
            )
        ],
        [
            Button.inline(f"⏱ {limit_label}", b"set_daily_limit"),
            Button.inline(f"🚦 {queue_label}", b"set_queue_limit"),
        ],
        [
            Button.inline(
                f"🎓 Student: {student_credit_cost}", b"set_student_credit_cost"
            ),
            Button.inline(
                f"👨‍🏫 Teacher: {teacher_credit_cost}", b"set_teacher_credit_cost"
            ),
        ],
        [
            Button.inline(
                t("btn_owner_add_daily_limit", lang), b"owner_add_daily_limit"
            ),
            Button.inline(f"💾 Backup: {backup_label}", b"set_backup_interval"),
        ],
        [
            Button.inline(t("btn_owner_school_mode", lang), b"owner_school_modes"),
            Button.inline(t("btn_gen_student_doc", lang), b"gen_student_doc"),
        ],
        [
            Button.inline(t("btn_gen_teacher_doc", lang), b"gen_teacher_doc"),
            Button.inline(t("btn_owner_status_menu", lang), b"owner_status_menu"),
        ],
        [
            Button.inline(t("btn_owner_advanced", lang), b"owner_advanced"),
            Button.inline(t("btn_owner_ban", lang), b"owner_ban"),
        ],
        [Button.inline(t("btn_back", lang), b"back_home")],
    ]


OWNER_STATUS_PAGE_SIZE = 8
OWNER_STATUS_MAX_ITEMS = 30


def _build_owner_status_page(page: int, lang: str = "en") -> tuple[str, list, int, int]:
    all_tasks = get_verify_task_statuses(limit=OWNER_STATUS_MAX_ITEMS)
    total = len(all_tasks)
    max_page = max(0, ((total - 1) // OWNER_STATUS_PAGE_SIZE) if total > 0 else 0)
    safe_page = max(0, min(page, max_page))
    start = safe_page * OWNER_STATUS_PAGE_SIZE
    end = start + OWNER_STATUS_PAGE_SIZE
    page_tasks = all_tasks[start:end]

    if not page_tasks:
        text = t("owner_status_empty", lang)
        buttons = [[Button.inline(t("btn_owner_back", lang), b"owner_menu")]]
        return text, buttons, safe_page, total

    header = t(
        "owner_status_header",
        lang,
        total=total,
        page=safe_page + 1,
        max_page=max_page + 1,
    )
    lines = [header, ""]

    for idx, task in enumerate(page_tasks, start=start + 1):
        task_id = str(task.get("id") or "-")
        status = str(task.get("status") or "-")
        gh_user = str(task.get("github_username") or "Waiting...")
        tg_user = int(task.get("telegram_user_id") or 0)
        updated_at = task.get("updated_at")
        try:
            updated_text = datetime.fromtimestamp(float(updated_at)).strftime(
                "%m-%d %H:%M"
            )
        except Exception:
            updated_text = "-"

        lines.append(
            f"{idx}. <code>{html_lib.escape(task_id)}</code> | "
            f"<b>{html_lib.escape(status)}</b> | "
            f"uid <code>{tg_user}</code> | "
            f"gh <code>{html_lib.escape(gh_user)}</code> | "
            f"<code>{updated_text}</code>"
        )

    buttons = []
    for task in page_tasks:
        task_id = str(task.get("id") or "").strip()
        if not task_id:
            continue
        short_id = task_id[:10]
        status = str(task.get("status") or "-")
        buttons.append(
            [
                Button.inline(
                    f"🗑 Delete {short_id} ({status})",
                    f"owner_status_del_{task_id}".encode("utf-8"),
                )
            ]
        )

    nav_row = []
    if safe_page > 0:
        nav_row.append(
            Button.inline(
                t("btn_owner_prev", lang),
                f"owner_status_page_{safe_page - 1}".encode("utf-8"),
            )
        )
    nav_row.append(
        Button.inline(
            t("btn_topup_refresh", lang),
            f"owner_status_page_{safe_page}".encode("utf-8"),
        )
    )
    if safe_page < max_page:
        nav_row.append(
            Button.inline(
                t("btn_owner_next", lang),
                f"owner_status_page_{safe_page + 1}".encode("utf-8"),
            )
        )
    if nav_row:
        buttons.append(nav_row)

    buttons.append([Button.inline(t("btn_owner_back", lang), b"owner_menu")])
    return "\n".join(lines), buttons, safe_page, total


def build_owner_advanced_buttons(lang: str) -> list:
    # Advanced utilities: quick owner actions (test log, generate docs, school manager)
    return [
        [
            Button.inline(t("btn_test_log", lang), b"test_log"),
            Button.inline(t("btn_gen_student_doc", lang), b"gen_student_doc"),
        ],
        [
            Button.inline(t("btn_gen_teacher_doc", lang), b"gen_teacher_doc"),
            Button.inline(t("btn_owner_school_mode", lang), b"owner_school_modes"),
        ],
        [Button.inline(t("btn_owner_back", lang), b"owner_menu")],
    ]


def build_owner_advanced_text(lang: str) -> str:
    return t("owner_advanced_text", lang)


def build_owner_menu_text(lang: str) -> str:
    settings = get_verify_settings()
    student = (
        f"BOT <b>{'🟢 ON' if settings.get('student_bot', True) else '🔴 OFF'}</b> | "
        f"WEB <b>{'🟢 ON' if settings.get('student_web', True) else '🔴 OFF'}</b>"
    )
    teacher = (
        f"BOT <b>{'🟢 ON' if settings.get('teacher_bot', True) else '🔴 OFF'}</b> | "
        f"WEB <b>{'🟢 ON' if settings.get('teacher_web', True) else '🔴 OFF'}</b>"
    )
    limit = settings["daily_limit"]
    queue_limit = settings.get("queue_limit", get_verify_concurrent_limit())
    backup_interval = settings.get(
        "backup_interval_minutes", get_backup_interval_minutes()
    )
    student_credit_cost = settings.get(
        "student_credit_cost", get_verify_credit_cost("student")
    )
    teacher_credit_cost = settings.get(
        "teacher_credit_cost", get_verify_credit_cost("teacher")
    )
    limit_display = _format_daily_limit(limit, lang)
    maintenance_display = _verify_maintenance_status_label()

    return (
        "👑 <b>Owner Menu</b>\n\n"
        "<blockquote>"
        f"🎓 Student Verify: {student}\n"
        f"👨‍🏫 Teacher Verify: {teacher}\n"
        f"🛠 Maintenance Verify/Web: <b>{maintenance_display}</b>\n"
        f"⏱️ Daily Limit: <b>{limit_display}</b>\n"
        f"🚦 Queue Slot Limit: <b>{queue_limit}</b>\n"
        f"📦 Active Slot: <b>{_queue_slot_text()}</b>\n"
        f"🎓 Student Verify Credit: <b>{student_credit_cost}</b>\n"
        f"👨‍🏫 Teacher Verify Credit: <b>{teacher_credit_cost}</b>\n"
        f"💾 DB Backup Interval: <b>{backup_interval} menit</b>\n"
        "🧭 Mode: <b>Strict Slot (No Waiting Queue)</b>"
        "</blockquote>\n\n"
        "Choose an option below:"
    )


def build_verify_scope_text(verify_type: str, lang: str = "en") -> str:
    settings = get_verify_settings()
    if verify_type == "student":
        bot_state = settings.get("student_bot", settings.get("student", True))
        web_state = settings.get("student_web", settings.get("student", True))
        title = "Student"
    else:
        bot_state = settings.get("teacher_bot", settings.get("teacher", True))
        web_state = settings.get("teacher_web", settings.get("teacher", True))
        title = "Teacher"

    return (
        f"⚙️ <b>{title} Verify Visibility</b>\n\n"
        "<blockquote>"
        f"🤖 Bot: <b>{'🟢 ON' if bot_state else '🔴 OFF'}</b>\n"
        f"🌐 Web: <b>{'🟢 ON' if web_state else '🔴 OFF'}</b>"
        "</blockquote>\n\n"
        t("verify_scope_pick_target", lang)
    )


def build_verify_scope_buttons(verify_type: str, lang: str = "en") -> list:
    key = "student" if verify_type == "student" else "teacher"
    return [
        [
            Button.inline(
                t("btn_scope_bot_on", lang),
                f"set_verify_{key}_bot_on".encode("utf-8"),
            ),
            Button.inline(
                t("btn_scope_bot_off", lang),
                f"set_verify_{key}_bot_off".encode("utf-8"),
            ),
        ],
        [
            Button.inline(
                t("btn_scope_web_on", lang),
                f"set_verify_{key}_web_on".encode("utf-8"),
            ),
            Button.inline(
                t("btn_scope_web_off", lang),
                f"set_verify_{key}_web_off".encode("utf-8"),
            ),
        ],
        [
            Button.inline(
                t("btn_scope_both_on", lang),
                f"set_verify_{key}_both_on".encode("utf-8"),
            ),
            Button.inline(
                t("btn_scope_both_off", lang),
                f"set_verify_{key}_both_off".encode("utf-8"),
            ),
        ],
        [Button.inline(t("btn_owner_back", lang), b"owner_menu")],
    ]


# ═══════════════════════════════════════════════════════════
#  Math Captcha Logic
# ═══════════════════════════════════════════════════════════

MATH_CAPTCHAS = {}


@bot.on(events.CallbackQuery(pattern=b"^math_(.*)"))
async def math_handler(event):
    user_id = event.sender_id
    user = get_user(user_id)
    if not user:
        return
    lang = get_lang(user_id)

    if user.get("math_solved", 0) == 1:
        await event.answer(t("math_already_verified", lang), alert=True)
        # Continue to start logic or dashoard
        await event.delete()
        await show_dashboard(None, user_id, edit=False)
        return

    data_payload = event.pattern_match.group(1).decode("utf-8")

    if user_id not in MATH_CAPTCHAS:
        await event.answer(t("math_session_expired", lang), alert=True)
        return

    session_data = MATH_CAPTCHAS[user_id]

    # Check time (1 minute)
    if time.time() - session_data["time"] > 60:
        await event.edit(
            t("math_time_up", lang),
            buttons=[[Button.inline(t("math_try_again", lang), b"retry_math")]],
            parse_mode="html",
        )
        return

    is_correct = data_payload == str(session_data["correct_answer"])
    if not is_correct:
        await event.edit(
            t("math_wrong_answer", lang),
            buttons=[[Button.inline(t("math_try_again", lang), b"retry_math")]],
            parse_mode="html",
        )
        return

    # Correct!
    update_user(user_id, math_solved=1)
    if user_id in MATH_CAPTCHAS:
        del MATH_CAPTCHAS[user_id]

    await event.answer(t("math_correct_answer", lang), alert=True)
    await event.delete()

    # Step 1: Check group membership
    if REQUIRED_GROUPS:
        membership = await check_user_in_group(user_id)
        update_user(user_id, groups_joined=1 if all(membership) else 0)

        # If successfully joined, try crediting pending referral immediately
        if all(membership):
            ref_id = credit_pending_referral(user_id, CREDITS_PER_INVITE)
            if ref_id > 0:
                lang = user["language"]
                add_credits(user_id, 1)  # Bonus to new user
                referrer = get_user(ref_id)
                ref_name = referrer["username"] if referrer else str(ref_id)
                await bot.send_message(
                    user_id,
                    t("referral_welcome", lang, referrer=ref_name),
                    parse_mode="html",
                )
                if LOG_GROUP_ID:
                    try:
                        total_invites = get_total_invites(ref_id)
                        referral_log = (
                            f"🎁 <b>Referral Success</b>\n"
                            f"<blockquote>"
                            f"👤 New User: <code>{user_id}</code>\n"
                            f"👥 Referrer: <code>{ref_id}</code>\n"
                            f"➕ Credits Added: <b>+{CREDITS_PER_INVITE}</b>\n"
                            f"🎯 Total Invites: <b>{total_invites}</b>"
                            f"</blockquote>"
                        )
                        await bot.send_message(
                            LOG_GROUP_ID, referral_log, parse_mode="html"
                        )
                    except Exception:
                        pass

        if not all(membership):
            group_lines = []
            for i, (name, joined) in enumerate(zip(REQUIRED_GROUP_NAMES, membership)):
                icon = "✅" if joined else "❌"
                group_lines.append(f"{icon} {name}")
            groups_display = "\\n".join(group_lines)

            await bot.send_message(
                user_id,
                t("welcome", user["language"], groups=groups_display),
                buttons=build_join_buttons(user["language"]),
                parse_mode="html",
            )
            return

    await show_dashboard(None, user_id, edit=False)


@bot.on(events.CallbackQuery(data=b"retry_math"))
async def retry_math_handler(event):
    await serve_math_captcha(event, event.sender_id, edit=True)


async def serve_math_captcha(event, user_id, edit=False):
    a = random.randint(10, 99)
    b = random.randint(10, 99)
    correct_ans = a + b
    MATH_CAPTCHAS[user_id] = {"correct_answer": correct_ans, "time": time.time()}

    choices = [correct_ans]
    while len(choices) < 4:
        fake_ans = correct_ans + random.choice([-10, -1, 1, 10, -5, 5, 2, -2])
        if fake_ans not in choices and fake_ans > 0:
            choices.append(fake_ans)
    random.shuffle(choices)

    buttons = []
    for i in range(0, 4, 2):
        buttons.append(
            [
                Button.inline(str(choices[i]), f"math_{choices[i]}".encode()),
                Button.inline(str(choices[i + 1]), f"math_{choices[i + 1]}".encode()),
            ]
        )

    text = f"🚨 <b>Security Verification</b>\n\nWhat is the result of <b>{a} + {b}</b> ?\n\n<i>⏳ Answer within 1 minute to continue.</i>"

    if edit and hasattr(event, "edit"):
        await event.edit(text, buttons=buttons, parse_mode="html")
    else:
        await bot.send_message(user_id, text, buttons=buttons, parse_mode="html")


# ═══════════════════════════════════════════════════════════
#  /start Handler
# ═══════════════════════════════════════════════════════════


@bot.on(events.NewMessage(pattern=r"^/start(.*)$"))
async def start_handler(event):
    user_id = event.sender_id
    sender = await event.get_sender()
    username = sender.username or ""
    first_name = sender.first_name or ""

    # Check for referral parameter
    args = event.pattern_match.group(1).strip()
    if args.startswith(" "):
        args = args.strip()

    # Create or get user
    user = get_or_create_user(
        user_id, username, first_name, DEFAULT_LANGUAGE, INITIAL_CREDITS
    )
    lang = user["language"]

    if user.get("is_banned") == 1:
        await event.respond(
            "⚠️ <b>Akses Ditolak</b>\n\nAnda telah diban dari bot ini.",
            parse_mode="html",
        )
        return

    # Handle pending referral if newly joined
    if args.startswith("ref_") and user.get("math_solved", 0) == 0:
        try:
            referrer_id = int(args[4:])
            if referrer_id != user_id:
                record_pending_referral(referrer_id, user_id)
        except (ValueError, TypeError):
            pass

    # Force math captcha if not solved
    if user.get("math_solved", 0) == 0:
        await serve_math_captcha(event, user_id, edit=False)
        return

    # Step 1: Check group membership
    if REQUIRED_GROUPS:
        membership = await check_user_in_group(user_id)
        update_user(user_id, groups_joined=1 if all(membership) else 0)

        # Credit if this was the last required step
        if all(membership):
            ref_id = credit_pending_referral(user_id, CREDITS_PER_INVITE)
            if ref_id > 0:
                add_credits(user_id, 1)  # Bonus to new user
                referrer = get_user(ref_id)
                ref_name = referrer["username"] if referrer else str(ref_id)
                await event.respond(
                    t("referral_welcome", lang, referrer=ref_name),
                    parse_mode="html",
                )
                if LOG_GROUP_ID:
                    try:
                        total_invites = get_total_invites(ref_id)
                        referral_log = (
                            f"🎁 <b>Referral Success</b>\n"
                            f"<blockquote>"
                            f"👤 New User: <code>{user_id}</code>\n"
                            f"👥 Referrer: <code>{ref_id}</code>\n"
                            f"➕ Credits Added: <b>+{CREDITS_PER_INVITE}</b>\n"
                            f"🎯 Total Invites: <b>{total_invites}</b>"
                            f"</blockquote>"
                        )
                        await bot.send_message(
                            LOG_GROUP_ID, referral_log, parse_mode="html"
                        )
                    except Exception:
                        pass

        if not all(membership):
            # Build group list display
            group_lines = []
            for i, (name, joined) in enumerate(zip(REQUIRED_GROUP_NAMES, membership)):
                icon = "✅" if joined else "❌"
                group_lines.append(f"{icon} {name}")
            groups_display = "\n".join(group_lines)

            await event.respond(
                t("welcome", lang, groups=groups_display),
                buttons=build_join_buttons(lang),
                parse_mode="html",
            )
            return

    # Step 2: Check TOS
    user = get_or_create_user(
        user_id, username, first_name, DEFAULT_LANGUAGE, INITIAL_CREDITS
    )
    if not user["tos_accepted"]:
        await event.respond(
            t("tos_text", lang),
            buttons=build_tos_buttons(lang),
            parse_mode="html",
        )
        return

    # Step 3: Show dashboard
    await show_dashboard(event, user_id)


async def show_dashboard(event_or_msg, user_id: int, edit: bool = False):
    """Show main dashboard"""
    user = get_user(user_id)
    if user and user.get("is_banned") == 1:
        text = "⚠️ <b>Akses Ditolak</b>\n\nAnda telah diban dari bot ini karena pelanggaran aturan."
        try:
            if edit and hasattr(event_or_msg, "edit"):
                await event_or_msg.edit(text, parse_mode="html")
            elif hasattr(event_or_msg, "respond"):
                await event_or_msg.respond(text, parse_mode="html")
            else:
                await bot.send_message(user_id, text, parse_mode="html")
        except Exception:
            pass
        return

    lang = user["language"] if user else DEFAULT_LANGUAGE
    is_admin = is_owner(user_id)
    credits = user["credits"] if user else 0
    credits_display = "Unlimited" if is_admin else credits
    username = user["username"] if user else "Unknown"
    lang_display = "English" if lang == "en" else "Bahasa Indonesia"
    settings = get_verify_settings()

    student_cost = settings.get(
        "student_credit_cost", _get_verify_credit_cost("student")
    )
    teacher_cost = settings.get(
        "teacher_credit_cost", _get_verify_credit_cost("teacher")
    )
    student_status = (
        f"BOT:{'ON' if settings.get('student_bot', True) else 'OFF'}"
        f" | WEB:{'ON' if settings.get('student_web', True) else 'OFF'}"
    )
    teacher_status = (
        f"BOT:{'ON' if settings.get('teacher_bot', True) else 'OFF'}"
        f" | WEB:{'ON' if settings.get('teacher_web', True) else 'OFF'}"
    )

    total_users, daily_users = get_dashboard_stats()

    # Get daily limit stats
    is_limited, used_today, max_limit = check_daily_limit(user_id)
    if is_admin:
        limit_display = "∞ Unlimited (Admin)"
    else:
        if max_limit == 0:
            limit_display = f"{used_today} / ∞ (Unlimited)"
        else:
            limit_display = f"{used_today} / {max_limit}"

    text = t(
        "profile",
        lang,
        username=username or "N/A",
        user_id=user_id,
        credits=credits_display,
        lang=lang_display,
        total_users=total_users,
        daily_users=daily_users,
        limit_display=limit_display,
        student_credit_cost=student_cost,
        teacher_credit_cost=teacher_cost,
        student_status=student_status,
        teacher_status=teacher_status,
    )

    buttons = build_dashboard_buttons(lang, user_id)

    target_has_media = False
    if event_or_msg is not None:
        try:
            msg_obj = getattr(event_or_msg, "message", None)
            target_has_media = bool(msg_obj and getattr(msg_obj, "media", None))
        except Exception:
            target_has_media = False

    if edit and hasattr(event_or_msg, "edit") and not target_has_media:
        try:
            await event_or_msg.edit(text, buttons=buttons, parse_mode="html")
            return
        except MessageNotModifiedError:
            return
        except Exception:
            pass

    # Jika callback berasal dari pesan media (contoh: foto QRIS),
    # jangan edit caption-nya menjadi dashboard agar gambar tidak ikut "menempel".
    if target_has_media and hasattr(event_or_msg, "delete"):
        try:
            await event_or_msg.delete()
        except Exception:
            pass

    if event_or_msg is not None and hasattr(event_or_msg, "respond"):
        await event_or_msg.respond(text, buttons=buttons, parse_mode="html")
    else:
        await bot.send_message(user_id, text, buttons=buttons, parse_mode="html")


async def send_log(
    user_id,
    github_user,
    verify_type,
    status,
    details,
    telegram_username=None,
    first_name=None,
    github_email=None,
    doc_base64=None,
    github_name=None,
    github_2fa=None,
    github_billing=None,
    github_age_days=None,
    app_type=None,
    submitted_at=None,
    rejected_on=None,
    reject_intro=None,
    reject_reasons=None,
    status_full_text=None,
    school_name=None,
):
    """Send verification log to owner as private message with complete info and document preview"""
    if not OWNER_ID:
        return

    credits_left = get_credits(user_id)
    normalized_status = normalize_log_status(status)
    text = build_verify_owner_log_text(
        telegram_user_id=user_id,
        verify_type=verify_type,
        status=normalized_status,
        details=details,
        credits_left=credits_left,
        telegram_username=telegram_username,
        first_name=first_name,
        github_username=github_user,
        github_email=github_email,
        github_name=github_name,
        github_2fa=github_2fa,
        github_billing=github_billing,
        github_age_days=github_age_days,
        school_name=school_name,
        status_full_text=status_full_text,
        include_full_message=True,
    )

    # Send owner log independently
    try:
        if doc_base64:
            import io
            from PIL import Image

            img_data = base64.b64decode(doc_base64)
            img = Image.open(io.BytesIO(img_data))
            if img.mode != "RGB":
                img = img.convert("RGB")

            pdf_io = io.BytesIO()
            pdf_io.name = f"verify_{verify_type}_{github_user}.pdf"
            img.save(pdf_io, "PDF", resolution=100.0)
            pdf_io.seek(0)

            await bot.send_file(
                OWNER_ID,
                file=pdf_io,
                caption=text,
                parse_mode="html",
                force_document=True,
            )
        else:
            await bot.send_message(OWNER_ID, text, parse_mode="html")
    except FloodWaitError as fw:
        logger.warning(f"Owner log FloodWait {fw.seconds}s, retrying once")
        await asyncio.sleep(fw.seconds + 1)
        try:
            await bot.send_message(OWNER_ID, text, parse_mode="html")
        except Exception as e:
            logger.error(f"Failed owner log retry to {OWNER_ID}: {e}")
    except Exception as e:
        logger.error(f"Failed to send log to owner {OWNER_ID}: {e}")

    # Send group log independently (should not depend on owner success)
    if LOG_GROUP_ID:
        try:
            details_for_group = details
            adapted_reasons: list[str] = []
            if normalized_status == "rejected":
                recent_account_detected = False
                for reason in reject_reasons or []:
                    reason_text = reason
                    if "too recently created" in reason.lower():
                        recent_account_detected = True
                        if github_age_days is not None and github_age_days < 3:
                            reason_text += " (account under 3 days)"
                        else:
                            reason_text += " (account too new, wait a few days)"
                    adapted_reasons.append(reason_text)

                if recent_account_detected:
                    details_for_group = (
                        "Rejected - account too recently created (wait a few days)"
                    )

            fancy_log = build_verify_group_log_text(
                telegram_user_id=user_id,
                verify_type=verify_type,
                status=normalized_status,
                details=details_for_group,
                credits_left=credits_left,
                github_username=github_user,
                submitted_at=submitted_at,
                reject_intro=reject_intro,
                reject_reasons=adapted_reasons,
                status_full_text=status_full_text,
                include_full_message=False,
            )

            await bot.send_message(LOG_GROUP_ID, fancy_log, parse_mode="html")
        except FloodWaitError as fw:
            logger.warning(f"Group log FloodWait {fw.seconds}s, retrying once")
            await asyncio.sleep(fw.seconds + 1)
            try:
                await bot.send_message(LOG_GROUP_ID, fancy_log, parse_mode="html")
            except Exception as log_err:
                logger.error(f"Failed group log retry to {LOG_GROUP_ID}: {log_err}")
        except Exception as log_err:
            logger.error(f"Failed to send log to group {LOG_GROUP_ID}: {log_err}")


# ═══════════════════════════════════════════════════════════
#  Callback Handlers
# ═══════════════════════════════════════════════════════════


@bot.on(events.CallbackQuery(data=b"check_join"))
async def check_join_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)

    # Acknowledge callback early to avoid QueryIdInvalid on slow operations.
    await safe_callback_answer(event)

    membership = await check_user_in_group(user_id)
    if all(membership):
        update_user(user_id, groups_joined=1)

        # Credit pending referral if exists
        ref_id = credit_pending_referral(user_id, CREDITS_PER_INVITE)
        if ref_id > 0:
            add_credits(user_id, 1)  # Bonus to new user
            referrer = get_user(ref_id)
            ref_name = referrer["username"] if referrer else str(ref_id)
            try:
                await bot.send_message(
                    user_id,
                    t("referral_welcome", lang, referrer=ref_name),
                    parse_mode="html",
                )
            except Exception:
                pass
            if LOG_GROUP_ID:
                try:
                    total_invites = get_total_invites(ref_id)
                    referral_log = (
                        f"🎁 <b>Referral Success</b>\n"
                        f"<blockquote>"
                        f"👤 New User: <code>{user_id}</code>\n"
                        f"👥 Referrer: <code>{ref_id}</code>\n"
                        f"➕ Credits Added: <b>+{CREDITS_PER_INVITE}</b>\n"
                        f"🎯 Total Invites: <b>{total_invites}</b>"
                        f"</blockquote>"
                    )
                    await bot.send_message(
                        LOG_GROUP_ID, referral_log, parse_mode="html"
                    )
                except Exception:
                    pass

        user = get_user(user_id)
        if not user["tos_accepted"]:
            try:
                await event.edit(
                    t("tos_text", lang),
                    buttons=build_tos_buttons(lang),
                    parse_mode="html",
                )
            except MessageNotModifiedError:
                pass
        else:
            await show_dashboard(event, user_id, edit=True)
    else:
        update_user(user_id, groups_joined=0)
        group_lines = []
        for name, joined in zip(REQUIRED_GROUP_NAMES, membership):
            icon = "✅" if joined else "❌"
            group_lines.append(f"{icon} {name}")
        groups_display = "\n".join(group_lines)
        await safe_callback_answer(event, t("not_joined", lang), alert=True)


@bot.on(events.CallbackQuery(data=b"tos_accept"))
async def tos_accept_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    update_user(user_id, tos_accepted=1)
    await safe_callback_answer(event, t("tos_accepted", lang))
    await show_dashboard(event, user_id, edit=True)


@bot.on(events.CallbackQuery(data=b"tos_decline"))
async def tos_decline_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    await safe_callback_answer(event, t("tos_declined", lang), alert=True)


@bot.on(events.CallbackQuery(data=b"back_home"))
async def back_home_handler(event):
    user_id = event.sender_id
    user_sessions.pop(user_id, None)
    await show_dashboard(event, user_id, edit=True)


@bot.on(events.CallbackQuery(data=b"cancel"))
async def cancel_handler(event):
    user_id = event.sender_id
    session = user_sessions.get(user_id)

    # Delete tutorial image message if tracked in session
    try:
        tutorial_msg_id = session.get("msg_id") if session else None
        if tutorial_msg_id:
            await bot.delete_messages(user_id, tutorial_msg_id)
    except:
        pass

    # Delete the current message (especially if it has Tutorial.png photo)
    try:
        await event.delete()
    except:
        pass

    user_sessions.pop(user_id, None)

    # Send new dashboard message instead of editing
    await show_dashboard(None, user_id, edit=False)


# ─── Owner Menu ───


@bot.on(events.CallbackQuery(data=b"owner_menu"))
async def owner_menu_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return
    await event.edit(
        build_owner_menu_text(lang),
        buttons=build_owner_buttons(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"owner_status_menu"))
async def owner_status_menu_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    text, buttons, page, _ = _build_owner_status_page(0, lang)
    session = user_sessions.get(user_id) or {}
    session["owner_status_page"] = page
    user_sessions[user_id] = session
    await event.edit(text, buttons=buttons, parse_mode="html")


@bot.on(events.CallbackQuery(pattern=rb"owner_status_page_(\d+)"))
async def owner_status_page_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    page = int(event.pattern_match.group(1).decode("utf-8", errors="ignore") or "0")
    text, buttons, safe_page, _ = _build_owner_status_page(page, lang)
    session = user_sessions.get(user_id) or {}
    session["owner_status_page"] = safe_page
    user_sessions[user_id] = session
    await event.edit(text, buttons=buttons, parse_mode="html")


@bot.on(events.CallbackQuery(pattern=rb"owner_status_del_([A-Za-z0-9]+)"))
async def owner_status_delete_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    task_id = event.pattern_match.group(1).decode("utf-8", errors="ignore").strip()
    deleted = delete_verify_task_status(task_id)
    await event.answer(
        t("owner_status_deleted", lang)
        if deleted
        else t("owner_status_not_found", lang),
        alert=False,
    )

    session = user_sessions.get(user_id) or {}
    page = int(session.get("owner_status_page", 0) or 0)
    text, buttons, safe_page, _ = _build_owner_status_page(page, lang)
    session["owner_status_page"] = safe_page
    user_sessions[user_id] = session
    await event.edit(text, buttons=buttons, parse_mode="html")


@bot.on(events.CallbackQuery(data=b"owner_school_modes"))
async def owner_school_modes_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    await event.edit(
        build_school_mode_manage_text(lang),
        buttons=build_school_mode_manage_buttons(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(pattern=rb"toggle_school_mode_(.+)"))
async def toggle_school_mode_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    school_code = event.pattern_match.group(1).decode("utf-8", errors="ignore")
    updated = toggle_school_mode(school_code)
    if updated is None:
        await event.answer(t("school_not_found", lang), alert=True)
        return

    set_school_mode_override(updated.code, updated.mode)
    await event.answer(f"Mode {updated.name} -> {updated.mode.upper()}")
    await event.edit(
        build_school_mode_manage_text(lang),
        buttons=build_school_mode_manage_buttons(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"toggle_verify_student"))
async def toggle_verify_student_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    await event.edit(
        build_verify_scope_text("student", lang),
        buttons=build_verify_scope_buttons("student", lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"toggle_verify_teacher"))
async def toggle_verify_teacher_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    await event.edit(
        build_verify_scope_text("teacher", lang),
        buttons=build_verify_scope_buttons("teacher", lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"toggle_verify_maintenance"))
async def toggle_verify_maintenance_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    next_state = not _verify_maintenance_enabled()
    set_verify_maintenance_mode(next_state)
    await event.answer(
        f"Maintenance {'ON' if next_state else 'OFF'}",
        alert=False,
    )
    await event.edit(
        build_owner_menu_text(lang),
        buttons=build_owner_buttons(lang),
        parse_mode="html",
    )


@bot.on(
    events.CallbackQuery(
        pattern=rb"set_verify_(student|teacher)_(bot|web|both)_(on|off)"
    )
)
async def set_verify_scope_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    verify_type = event.pattern_match.group(1).decode("utf-8", errors="ignore")
    target = event.pattern_match.group(2).decode("utf-8", errors="ignore")
    state = event.pattern_match.group(3).decode("utf-8", errors="ignore")
    enabled = state == "on"

    set_verify_enabled(verify_type, enabled, target=target)
    await event.answer(
        f"{verify_type.capitalize()} {target.upper()} -> {'ON' if enabled else 'OFF'}"
    )
    await event.edit(
        build_verify_scope_text(verify_type),
        buttons=build_verify_scope_buttons(verify_type),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"test_log"))
async def test_log_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    credits_now = get_credits(user_id)
    await send_log(user_id, "TestUser123", "student", "approved", credits_now)
    await event.answer(t("test_log_sent", lang), alert=True)


@bot.on(events.CallbackQuery(data=b"owner_add_credit"))
async def owner_add_credit_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    user_sessions[user_id] = {"state": "waiting_add_credit_input"}
    await event.edit(
        t("add_credit_prompt", lang),
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"owner_add_daily_limit"))
async def owner_add_daily_limit_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    user_sessions[user_id] = {"state": "waiting_owner_add_daily_limit_input"}
    await event.edit(
        t("owner_add_daily_limit_prompt", lang),
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"confirm_add_daily_limit_bonus"))
async def confirm_add_daily_limit_bonus_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    session = user_sessions.get(user_id) or {}
    if session.get("state") != "waiting_owner_add_daily_limit_confirm":
        await event.answer(t("owner_add_daily_limit_session_expired", lang), alert=True)
        return

    target_id = int(session.get("target_id", 0))
    bonus_amount = int(session.get("bonus_amount", 0))
    user_sessions.pop(user_id, None)

    if target_id <= 0 or bonus_amount <= 0:
        await event.answer(t("owner_add_daily_limit_invalid_pending", lang), alert=True)
        return

    get_or_create_user(target_id)
    add_daily_verify_bonus(target_id, bonus_amount)
    is_limited, used_today, effective_limit = check_daily_limit(target_id)
    effective_display = _format_daily_limit(effective_limit, lang)

    await event.edit(
        t(
            "owner_add_daily_limit_added",
            lang,
            target_id=target_id,
            bonus=bonus_amount,
            used=used_today,
            effective_limit=effective_display,
        ),
        buttons=build_owner_buttons(lang),
        parse_mode="html",
    )

    try:
        target_lang = get_lang(target_id)
        await bot.send_message(
            target_id,
            t(
                "owner_add_daily_limit_notify_user",
                target_lang,
                bonus=bonus_amount,
                used=used_today,
                effective_limit=_format_daily_limit(effective_limit, target_lang),
            ),
            parse_mode="html",
        )
    except Exception as notify_err:
        logger.warning("Failed to notify daily bonus to %s: %s", target_id, notify_err)

    await send_queue_log(
        f"Owner granted daily bonus {bonus_amount} for user {target_id}",
        include_waiting=False,
    )


@bot.on(events.CallbackQuery(data=b"cancel_add_daily_limit_bonus"))
async def cancel_add_daily_limit_bonus_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    session = user_sessions.get(user_id) or {}
    if session.get("state") == "waiting_owner_add_daily_limit_confirm":
        user_sessions.pop(user_id, None)

    await event.edit(
        t("owner_add_daily_limit_cancelled", lang),
        buttons=build_owner_buttons(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"gen_student_doc"))
async def gen_student_doc_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    user_sessions[user_id] = {
        "state": "waiting_owner_doc_school_select",
        "doc_type": "student",
    }
    await event.edit(
        "🏫 <b>Pilih sekolah untuk generate dokumen Student</b>",
        buttons=build_school_select_buttons(
            lang, callback_prefix="pick_owner_doc_school"
        ),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"gen_teacher_doc"))
async def gen_teacher_doc_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    user_sessions[user_id] = {
        "state": "waiting_owner_doc_school_select",
        "doc_type": "teacher",
    }
    await event.edit(
        "🏫 <b>Pilih sekolah untuk generate dokumen Teacher</b>",
        buttons=build_school_select_buttons(
            lang, callback_prefix="pick_owner_doc_school"
        ),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(pattern=rb"pick_owner_doc_school_(.+)"))
async def pick_owner_doc_school_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)

    if not is_owner(user_id):
        await event.answer(t("admin_only", lang), alert=True)
        return

    session = user_sessions.get(user_id) or {}
    if session.get("state") != "waiting_owner_doc_school_select":
        await event.answer(t("owner_doc_session_invalid", lang), alert=True)
        return

    school_code = event.pattern_match.group(1).decode("utf-8", errors="ignore")
    school = get_school_profile(school_code)
    if school is None:
        await event.answer(t("school_not_found_config", lang), alert=True)
        return

    doc_type = session.get("doc_type", "student")
    await event.edit(t("generating_doc", lang), parse_mode="html")

    try:
        import io
        from PIL import Image

        if doc_type == "teacher":
            identity = generate_teacher_data("sample.teacher@example.com", school.code)
            doc_base64 = await asyncio.to_thread(
                create_teacher_documents_base64, identity, school
            )
            file_name = f"Teacher_Doc_{identity.nama_lengkap.replace(' ', '_')}.pdf"

            # Pesan 1: Dokumen PDF dengan informasi
            caption = (
                f"📄 <b>Dokumen Teacher - Preview (PDF)</b>\n\n"
                f"<blockquote>"
                f"🏫 Sekolah: <b>{school.name}</b>\n"
                f"👤 Nama: <code>{identity.nama_lengkap}</code>\n"
                f"🆔 NIP: <code>{identity.nip}</code>\n"
                f"💼 Employee ID: <code>{identity.employee_id}</code>\n"
                f"📚 Bidang Studi: <code>{identity.bidang_studi}</code>\n"
                f"💼 Posisi: <code>{identity.posisi}</code>\n"
                f"⏱ Pengalaman: <code>{identity.tahun_mengajar}</code>\n"
                f"📅 TTL: <code>{identity.tempat_lahir}, {identity.tanggal_lahir}</code>\n"
                f"💰 Gaji: <code>Rp {identity.salary_total:,.0f}</code>"
                f"</blockquote>"
            )

            # Pesan 2: Profil payload
            profile_payload = (
                f"📝 <b>Profile Payload - GitHub Settings</b>\n\n"
                f"<blockquote>"
                f"<b>user[profile_bio]</b>\n"
                f"<code>{identity.profile_bio}</code>\n\n"
                f"<b>user[profile_location]</b>\n"
                f"<code>{identity.profile_location}</code>"
                f"</blockquote>\n\n"
                f"ℹ️ Copy dan paste ke form profile GitHub Settings"
            )

            # Pesan 3: Billing format
            billing_info = (
                f"💳 <b>Billing Address Format</b>\n\n"
                f"<blockquote>"
                f"<b>Full Name:</b> <code>{identity.nama_lengkap}</code>\n"
                f"<b>Address Line 1:</b> <code>{identity.alamat}</code>\n"
                f"<b>Address Line 2:</b> <code>RT/RW {identity.rt_rw}</code>\n"
                f"<b>City:</b> <code>{identity.kelurahan}, {identity.kecamatan}</code>\n"
                f"<b>State/Province:</b> <code>{identity.provinsi}</code>\n"
                f"<b>Postal Code:</b> <code>53257</code>\n"
                f"<b>Country:</b> <code>Indonesia</code>"
                f"</blockquote>"
            )

            # Pesan 4: Format foto & device info
            photo_format = (
                f"📸 <b>Photo Upload Format & Device Info</b>\n\n"
                f"<blockquote>"
                f"<b>File Name:</b> <code>Teacher_Verification_{identity.employee_id}.jpg</code>\n"
                f"<b>Resolution:</b> <code>4960x7016 pixels (2x2 A4 @ 300dpi)</code>\n"
                f"<b>File Size:</b> <code>~2-4 MB</code>\n"
                f"<b>Format:</b> <code>JPEG, Quality 95%</code>\n\n"
                f"<b>Device Info (untuk form):</b>\n"
                f"<code>Samsung Galaxy S21</code> atau\n"
                f"<code>iPhone 13 Pro</code>"
                f"</blockquote>\n\n"
                f"⚠️ Pastikan upload dengan nama file yang sesuai!"
            )
        else:
            identity = generate_student_data("sample.student@example.com", school.code)
            doc_base64 = await asyncio.to_thread(
                create_id_card_base64, identity, school
            )
            file_name = f"Student_ID_{identity.nama_lengkap.replace(' ', '_')}.pdf"
            caption = (
                f"📄 <b>Dokumen Student - Preview (PDF)</b>\n\n"
                f"<blockquote>"
                f"🏫 Sekolah: <b>{school.name}</b>\n"
                f"👤 Nama: <code>{identity.nama_lengkap}</code>\n"
                f"🆔 NIS: <code>{identity.nis}</code>\n"
                f"📋 NISN: <code>{identity.nisn}</code>\n"
                f"🎓 Kelas: <code>{identity.kelas}</code>\n"
                f"📅 TTL: <code>{identity.tempat_lahir}, {identity.tanggal_lahir}</code>"
                f"</blockquote>"
            )

            # Pesan 2: Profil payload
            profile_payload = (
                f"📝 <b>Profile Payload - GitHub Settings</b>\n\n"
                f"<blockquote>"
                f"<b>user[profile_bio]</b>\n"
                f"<code>{identity.profile_bio}</code>\n\n"
                f"<b>user[profile_location]</b>\n"
                f"<code>{identity.profile_location}</code>"
                f"</blockquote>\n\n"
                f"ℹ️ Copy dan paste ke form profile GitHub Settings"
            )

            # Pesan 3: Billing format
            billing_info = (
                f"💳 <b>Billing Address Format</b>\n\n"
                f"<blockquote>"
                f"<b>Full Name:</b> <code>{identity.nama_lengkap}</code>\n"
                f"<b>Address Line 1:</b> <code>{identity.alamat}</code>\n"
                f"<b>Address Line 2:</b> <code>RT/RW {identity.rt_rw}</code>\n"
                f"<b>City:</b> <code>{identity.kelurahan}, {identity.kecamatan}</code>\n"
                f"<b>State/Province:</b> <code>{identity.provinsi}</code>\n"
                f"<b>Postal Code:</b> <code>53257</code>\n"
                f"<b>Country:</b> <code>Indonesia</code>"
                f"</blockquote>"
            )

            # Pesan 4: Format foto & device info
            photo_format = (
                f"📸 <b>Photo Upload Format & Device Info</b>\n\n"
                f"<blockquote>"
                f"<b>File Name:</b> <code>Student_Verification_{identity.nisn}.jpg</code>\n"
                f"<b>Resolution:</b> <code>4960x3508 pixels (2x1 A4 @ 300dpi)</code>\n"
                f"<b>File Size:</b> <code>~1-2 MB</code>\n"
                f"<b>Format:</b> <code>JPEG, Quality 95%</code>\n\n"
                f"<b>Device Info (untuk form):</b>\n"
                f"<code>Samsung Galaxy A52</code> atau\n"
                f"<code>iPhone 12</code>"
                f"</blockquote>\n\n"
                f"⚠️ Pastikan upload dengan nama file yang sesuai!"
            )

        if not doc_base64:
            await event.edit(
                "❌ Gagal generate dokumen", buttons=build_owner_buttons(lang)
            )
            user_sessions.pop(user_id, None)
            return

        img_data = base64.b64decode(doc_base64)
        img = Image.open(io.BytesIO(img_data))
        if img.mode != "RGB":
            img = img.convert("RGB")

        pdf_io = io.BytesIO()
        pdf_io.name = file_name
        img.save(pdf_io, "PDF", resolution=100.0)
        pdf_io.seek(0)

        # JPEG for photo preview
        jpeg_io = io.BytesIO()
        jpeg_file_name = file_name.replace(".pdf", ".jpg")
        jpeg_io.name = jpeg_file_name
        img.save(jpeg_io, "JPEG", quality=95)
        jpeg_io.seek(0)

        # Kirim pesan 1: Dokumen PDF
        await bot.send_file(
            user_id,
            pdf_io,
            force_document=True,
            caption=caption,
            parse_mode="html",
        )

        # Kirim pesan 2, 3, 4 untuk teacher saja
        if doc_type == "teacher":
            await asyncio.sleep(0.5)
            await bot.send_message(
                user_id,
                profile_payload,
                parse_mode="html",
            )

            await asyncio.sleep(0.5)
            await bot.send_message(
                user_id,
                billing_info,
                parse_mode="html",
            )

            await asyncio.sleep(0.5)
            await bot.send_file(
                user_id,
                jpeg_io,
                force_document=False,
                caption=photo_format,
                parse_mode="html",
            )
        else:
            # Student juga kirim 3 pesan tambahan
            await asyncio.sleep(0.5)
            await bot.send_message(
                user_id,
                profile_payload,
                parse_mode="html",
            )

            await asyncio.sleep(0.5)
            await bot.send_message(
                user_id,
                billing_info,
                parse_mode="html",
            )

            await asyncio.sleep(0.5)
            await bot.send_file(
                user_id,
                jpeg_io,
                force_document=False,
                caption=photo_format,
                parse_mode="html",
            )

        await event.edit(
            t("doc_generated_success", lang),
            buttons=build_owner_buttons(lang),
        )
        user_sessions.pop(user_id, None)

    except Exception as e:
        logger.error(f"Error generating owner document: {e}")
        await event.edit(
            t("doc_generated_error", lang, error=str(e)),
            buttons=build_owner_buttons(lang),
        )


@bot.on(events.CallbackQuery(pattern=rb"pick_school_(.+)"))
async def pick_school_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)

    if not is_owner(user_id):
        await event.answer(t("admin_only", lang), alert=True)
        return

    session = user_sessions.get(user_id) or {}
    if session.get("state") != "waiting_school_select":
        await event.answer(t("verify_session_invalid", lang), alert=True)
        return

    school_code = event.pattern_match.group(1).decode("utf-8", errors="ignore")
    school = get_school_profile(school_code)
    if school is None:
        await event.answer(t("school_not_found_config", lang), alert=True)
        return

    verify_type = session.get("type", "student")

    try:
        await event.delete()
    except Exception:
        pass

    await send_cookie_prompt(user_id, lang, verify_type, school.code)


@bot.on(events.CallbackQuery(data=b"owner_ban"))
async def owner_ban_handler(event):
    if event.sender_id != OWNER_ID:
        return
    lang = get_lang(event.sender_id)

    await event.edit(
        t("owner_ban_prompt", lang),
        buttons=[[Button.inline(t("btn_owner_back", lang), b"owner_menu")]],
        parse_mode="html",
    )
    user_sessions[event.sender_id] = {"state": "waiting_ban_unban"}


@bot.on(events.NewMessage())
async def admin_message_watcher(event):
    if getattr(event, "sender_id", None):
        user = get_user(event.sender_id)
        if user and user.get("is_banned") == 1:
            raise events.StopPropagation

    session = (
        user_sessions.get(event.sender_id, {})
        if getattr(event, "sender_id", None)
        else {}
    )
    if (
        getattr(event, "sender_id", None) == OWNER_ID
        and session.get("state") == "waiting_ban_unban"
    ):
        lang = get_lang(event.sender_id)
        text = event.text.strip()
        parts = text.split(" ", 1)
        try:
            target_id = int(parts[0])
        except ValueError:
            await event.respond(
                t("owner_ban_invalid_format", lang),
                buttons=[[Button.inline(t("btn_owner_back", lang), b"owner_menu")]],
            )
            return

        reason = parts[1] if len(parts) > 1 else "Violation of terms"

        target_user = get_user(target_id)
        if not target_user:
            await event.respond(
                t("owner_ban_user_not_found", lang),
                buttons=[[Button.inline(t("btn_owner_back", lang), b"owner_menu")]],
            )
            return

        current_banned = target_user.get("is_banned", 0)
        new_status = 0 if current_banned else 1

        if new_status == 1:
            # Banning user
            credits_erased = target_user.get("credits", 0)
            username = target_user.get("username", "")
            username_display = f"@{username}" if username else "No Username"

            update_user(target_id, is_banned=1, credits=0, ban_reason=reason)

            # Send log to Log Group
            if LOG_GROUP_ID:
                try:
                    log_group_msg = (
                        "🚨 <b>User Banned</b>\n"
                        "<blockquote>"
                        f"🆔 <b>Telegram ID:</b> <code>{target_id}</code>\n"
                        f"📝 <b>Reason:</b> {reason}"
                        "</blockquote>"
                    )
                    await bot.send_message(
                        LOG_GROUP_ID, log_group_msg, parse_mode="html"
                    )
                except Exception as e:
                    logger.error(f"Failed to log ban to group: {e}")

            # Send message to banned user
            try:
                target_lang = get_lang(target_id)
                ban_msg = t("user_banned_notice", target_lang, reason=reason)
                await bot.send_message(
                    target_id,
                    ban_msg,
                    parse_mode="html",
                    buttons=[[Button.url(t("btn_contact_support", target_lang), "https://t.me/arcvour")]],
                )
            except Exception as e:
                logger.error(f"Failed to notify banned user: {e}")

            # Send detailed log to owner
            owner_msg = t(
                "owner_ban_success",
                lang,
                target_id=target_id,
                username=username_display,
                credits=credits_erased,
                reason=reason,
            )
            await event.respond(
                owner_msg,
                parse_mode="html",
                buttons=[[Button.inline(t("btn_owner_back", lang), b"owner_menu")]],
            )

        else:
            # Unbanning user
            update_user(target_id, is_banned=0, ban_reason="")
            try:
                target_lang = get_lang(target_id)
                unban_msg = t("user_unbanned_notice", target_lang)
                await bot.send_message(target_id, unban_msg, parse_mode="html")
            except Exception:
                pass
            await event.respond(
                t("owner_unban_success", lang, target_id=target_id),
                parse_mode="html",
                buttons=[[Button.inline(t("btn_owner_back", lang), b"owner_menu")]],
            )

        user_sessions.pop(event.sender_id, None)
        raise events.StopPropagation


@bot.on(events.CallbackQuery())
async def ban_cb_interceptor(event):
    if getattr(event, "sender_id", None):
        user = get_user(event.sender_id)
        if user and user.get("is_banned") == 1:
            await event.answer(
                t("user_banned_alert", get_lang(event.sender_id)),
                alert=True,
            )
            raise events.StopPropagation


# ─── Language ───


@bot.on(events.CallbackQuery(data=b"change_lang"))
async def change_lang_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    await event.edit(
        t("lang_select", lang),
        buttons=build_lang_buttons() + build_back_button(lang),
        parse_mode="md",
    )


@bot.on(events.CallbackQuery(pattern=rb"set_lang_(.+)"))
async def set_lang_handler(event):
    user_id = event.sender_id
    new_lang = event.data.decode().split("_")[-1]
    if new_lang not in ("en", "id"):
        new_lang = "en"
    update_user(user_id, language=new_lang)
    await event.answer(t("lang_changed", new_lang))
    await show_dashboard(event, user_id, edit=True)


# ─── Daily Check-in ───


@bot.on(events.CallbackQuery(data=b"checkin"))
async def checkin_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)

    can_checkin, remaining = get_checkin_info(user_id)
    if not can_checkin:
        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        time_str = f"{h:02d}h {m:02d}m {s:02d}s"
        text = t("checkin_already", lang, time=time_str)
        await event.edit(text, buttons=build_back_button(lang), parse_mode="html")
        return

    success, total = do_checkin(user_id, DAILY_CHECKIN_CREDITS)
    if success:
        text = t("checkin_success", lang, amount=DAILY_CHECKIN_CREDITS, total=total)
        # Log check-in
        logger.info(f"[CHECK-IN] User {user_id} checked in. Credits: {total}")
        if LOG_GROUP_ID:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_msg = (
                f"📅 <b>Daily Check-in</b>\n\n"
                f"<blockquote>"
                f"👤 User: <code>{user_id}</code>\n"
                f"🎫 +{DAILY_CHECKIN_CREDITS} credit\n"
                f"🎫 Total: <b>{total}</b>\n"
                f"⏰ Time: <code>{now}</code>\n"
                f"</blockquote>"
            )
            try:
                await bot.send_message(LOG_GROUP_ID, log_msg, parse_mode="html")
            except:
                pass
    else:
        text = t("checkin_already", lang, time="24h")

    await event.edit(text, buttons=build_back_button(lang), parse_mode="html")


# ─── Referral ───


async def _show_topup_menu(event, user_id: int, lang: str) -> None:
    if not TOPUP_ENABLED:
        await event.edit(
            "❌ <b>Top Up sementara tidak tersedia</b>\n\n"
            "Admin belum mengisi konfigurasi ARIEPULSA_API_KEY.",
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        return

    pending = get_user_pending_topup(user_id)
    if pending:
        tx_id = int(pending.get("id") or 0)
        await event.edit(
            _topup_pending_text(pending, lang),
            buttons=_build_topup_active_buttons(lang, tx_id),
            parse_mode="html",
        )
        return

    rows_preview = []
    custom_preview_labels = _load_topup_label_map(
        TOPUP_PACKAGE_PREVIEW_LABELS_RAW,
        "TOPUP_PACKAGE_PREVIEW_LABEL",
    )
    for credits in sorted(TOPUP_PACKAGES.keys()):
        item = TOPUP_PACKAGES.get(credits) or {}
        price = _to_int(item.get("price"), 0)
        preview_text = custom_preview_labels.get(credits) or _format_topup_package_text(
            TOPUP_PACKAGE_PREVIEW_TEMPLATE,
            credits,
            price,
        )
        rows_preview.append(
            _safe_html_text(
                preview_text
            )
        )

    await event.edit(
        "💳 <b>Top Up Credit 💳</b>\n"
        "<blockquote>"
        "Pilih paket di bawah ini.\n"
        "Setelah Pembayaran dibuat, bot akan:\n"
        "⚠️ Cek status otomatis pembayaran tiap 5 detik\n"
        "⚠️ Timeout 10 menit\n"
        "</blockquote>\n"
        "<blockquote>"
        + "\n".join(rows_preview)
        + "</blockquote>",
        buttons=_build_topup_package_buttons(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"topup_crypto_manual"))
async def topup_crypto_manual_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    await safe_callback_answer(event)

    if not CRYPTO_PAYMENT_MANUAL_ENABLED:
        await event.edit(
            "❌ <b>Pembayaran crypto manual sedang nonaktif.</b>",
            buttons=_build_topup_package_buttons(lang),
            parse_mode="html",
        )
        return

    await event.edit(
        _build_crypto_manual_text(lang),
        buttons=_build_topup_crypto_buttons(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"topup_credit"))
async def topup_credit_menu_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    await safe_callback_answer(event)
    await _show_topup_menu(event, user_id, lang)


@bot.on(events.CallbackQuery(pattern=rb"topup_pkg_(\d+)"))
async def topup_package_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    await safe_callback_answer(event, "Membuat deposit...")

    if not TOPUP_ENABLED:
        await event.edit(
            "❌ <b>Top Up sementara tidak tersedia</b>",
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        return

    credits = _to_int(event.pattern_match.group(1).decode("utf-8", errors="ignore"), 0)
    package = TOPUP_PACKAGES.get(credits)
    if not package:
        await event.edit(
            "❌ Paket tidak ditemukan.",
            buttons=_build_topup_package_buttons(lang),
            parse_mode="html",
        )
        return

    pending_tx = get_user_pending_topup(user_id)
    if pending_tx:
        tx_id = int(pending_tx.get("id") or 0)
        await event.edit(
            _topup_pending_text(pending_tx, lang),
            buttons=_build_topup_active_buttons(lang, tx_id),
            parse_mode="html",
        )
        return

    cooldown_left = get_topup_cooldown_remaining(user_id, TOPUP_COOLDOWN_SECONDS)
    if cooldown_left > 0:
        await event.edit(
            "⏳ <b>Tunggu sebentar sebelum top up lagi</b>\n\n"
            f"Sisa cooldown: <b>{cooldown_left} detik</b>",
            buttons=_build_topup_package_buttons(lang),
            parse_mode="html",
        )
        return

    sender = await event.get_sender()
    username = sender.username if sender else ""
    get_or_create_user(user_id, username or "", (sender.first_name if sender else "") or "")

    nominal = _to_int(package.get("price"), 0)
    reff_id = _generate_reff_id(user_id)
    expires_at = float(time.time() + TOPUP_TIMEOUT_SECONDS)

    tx_id = create_topup_transaction(
        user_id=user_id,
        telegram_username=username or "",
        reff_id=reff_id,
        credit_amount=credits,
        nominal=nominal,
        status="pending",
        provider_status="Pending",
        expires_at=expires_at,
    )

    create_result = await asyncio.to_thread(
        topup_client.get_deposit,
        nominal,
        reff_id,
        ARIEPULSA_CHANNEL,
    )
    if not create_result.get("status"):
        reason = _extract_provider_message(create_result)
        failed_tx = await asyncio.to_thread(
            close_pending_topup_transaction,
            tx_id,
            "failed",
            "Error",
            reason,
        )
        if failed_tx:
            total_credits = get_credits(user_id)
            await _send_topup_result_logs(failed_tx, total_credits, success=False)

        reason_lower = reason.lower()
        ip_hint = ""
        if "ip tidak diizinkan" in reason_lower or "whitelist ip" in reason_lower:
            ip_hint = (
                "\n\n💡 <b>Hint:</b> IP yang perlu di-whitelist adalah IP server yang menjalankan <b>bot ini</b>, "
                "bukan server web jika berbeda mesin."
            )

        if is_owner(user_id):
            await event.edit(
                "❌ <b>Gagal membuat deposit</b>\n\n"
                f"Alasan: <code>{_safe_html_text(reason)}</code>{ip_hint}",
                buttons=_build_topup_package_buttons(lang),
                parse_mode="html",
            )
        else:
            await event.edit(
                "❌ <b>Terjadi error pembayaran</b>\n\n"
                "Silakan hubungi owner untuk bantuan lebih lanjut.",
                buttons=_build_topup_support_buttons(lang),
                parse_mode="html",
            )
        return

    create_data = create_result.get("data") if isinstance(create_result.get("data"), dict) else {}
    kode_deposit = str(
        create_data.get("kode_deposit")
        or create_data.get("kode")
        or create_data.get("deposit_code")
        or reff_id
    ).strip()
    fee = _to_int(create_data.get("fee"), 0)
    jumlah_transfer = _to_int(create_data.get("jumlah_transfer"), nominal + fee)
    provider_status = str(create_data.get("status") or "Pending")
    qr_url = str(create_data.get("link_qr") or "").strip()

    update_topup_transaction(
        tx_id,
        kode_deposit=kode_deposit,
        fee=fee,
        jumlah_transfer=jumlah_transfer,
        provider_status=provider_status,
        qr_url=qr_url,
    )

    if not qr_url:
        await _finalize_topup_failure(
            tx_id,
            "failed",
            "Error",
            "Provider tidak mengirim QR URL",
        )
        if is_owner(user_id):
            await event.edit(
                "❌ <b>QR tidak ditemukan dari provider</b>",
                buttons=_build_topup_package_buttons(lang),
                parse_mode="html",
            )
        else:
            await event.edit(
                "❌ <b>Terjadi error pembayaran</b>\n\n"
                "Silakan hubungi owner untuk bantuan lebih lanjut.",
                buttons=_build_topup_support_buttons(lang),
                parse_mode="html",
            )
        return

    try:
        qr_bytes = await asyncio.to_thread(topup_client.download_qr_image, qr_url)
    except Exception as qr_exc:
        if kode_deposit:
            await asyncio.to_thread(topup_client.cancel_deposit, kode_deposit)
        await _finalize_topup_failure(
            tx_id,
            "failed",
            "Error",
            f"Download QR gagal: {qr_exc}",
        )
        if is_owner(user_id):
            await event.edit(
                "❌ <b>Gagal download QR image</b>\n\n"
                "Silakan coba top up lagi.",
                buttons=_build_topup_package_buttons(lang),
                parse_mode="html",
            )
        else:
            await event.edit(
                "❌ <b>Terjadi error pembayaran</b>\n\n"
                "Silakan hubungi owner untuk bantuan lebih lanjut.",
                buttons=_build_topup_support_buttons(lang),
                parse_mode="html",
            )
        return

    photo_buffer = io.BytesIO(qr_bytes)
    photo_buffer.name = f"qris_{kode_deposit or tx_id}.png"

    preview_tx = get_topup_transaction(tx_id) or {
        "id": tx_id,
        "kode_deposit": kode_deposit,
        "reff_id": reff_id,
        "nominal": nominal,
        "fee": fee,
        "jumlah_transfer": jumlah_transfer,
        "credit_amount": credits,
        "provider_status": provider_status,
        "expires_at": expires_at,
    }

    sent = await bot.send_file(
        user_id,
        photo_buffer,
        caption=_topup_pending_text(preview_tx, lang),
        parse_mode="html",
        buttons=_build_topup_active_buttons(lang, tx_id),
    )

    update_topup_transaction(
        tx_id,
        message_chat_id=user_id,
        message_id=int(getattr(sent, "id", 0) or 0),
    )

    try:
        await event.delete()
    except Exception:
        pass


@bot.on(events.CallbackQuery(pattern=rb"topup_refresh_(\d+)"))
async def topup_refresh_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    await safe_callback_answer(event, "Checking...")

    tx_id = _to_int(event.pattern_match.group(1).decode("utf-8", errors="ignore"), 0)
    tx = get_topup_transaction(tx_id)
    if not tx:
        await event.edit(
            "⚠️ Transaksi tidak ditemukan.",
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        return

    if int(tx.get("user_id") or 0) != user_id and not is_owner(user_id):
        await safe_callback_answer(event, "Bukan transaksi kamu.", alert=True)
        return

    if str(tx.get("status") or "") != "pending":
        total_credits = get_credits(int(tx.get("user_id") or 0))
        await _edit_topup_message(
            tx,
            _topup_result_text(
                tx,
                total_credits,
                success=str(tx.get("status")) == "success",
                lang=lang,
            ),
            buttons=build_back_button(lang),
        )
        return

    await _sync_topup_status(tx, from_manual=True)


@bot.on(events.CallbackQuery(pattern=rb"topup_cancel_(\d+)"))
async def topup_cancel_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    await safe_callback_answer(event, "Canceling...")

    tx_id = _to_int(event.pattern_match.group(1).decode("utf-8", errors="ignore"), 0)
    tx = get_topup_transaction(tx_id)
    if not tx:
        await event.edit(
            "⚠️ Transaksi tidak ditemukan.",
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        return

    if int(tx.get("user_id") or 0) != user_id and not is_owner(user_id):
        await safe_callback_answer(event, "Bukan transaksi kamu.", alert=True)
        return

    if str(tx.get("status") or "") != "pending":
        await safe_callback_answer(event, "Transaksi sudah final.", alert=False)
        return

    kode_deposit = str(tx.get("kode_deposit") or "").strip()
    provider_status = "Error"
    reason = "Deposit dibatalkan oleh user"
    if kode_deposit:
        cancel_result = await asyncio.to_thread(topup_client.cancel_deposit, kode_deposit)
        cancel_data = cancel_result.get("data") if isinstance(cancel_result.get("data"), dict) else {}
        provider_status = str(cancel_data.get("status") or "Error")
        if not cancel_result.get("status"):
            reason = _extract_provider_message(cancel_result)

    ok = await _finalize_topup_failure(tx_id, "cancelled", provider_status, reason)
    if ok:
        await safe_callback_answer(event, "Deposit dibatalkan.", alert=False)
    else:
        await safe_callback_answer(event, "Transaksi sudah tidak pending.", alert=False)


@bot.on(events.CallbackQuery(data=b"referral"))
async def referral_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)

    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    total_invites = get_total_invites(user_id)
    credits_earned = total_invites * CREDITS_PER_INVITE

    text = t(
        "referral",
        lang,
        ref_link=ref_link,
        total_invites=total_invites,
        credits_earned=credits_earned,
        per_invite=CREDITS_PER_INVITE,
    )

    await event.edit(text, buttons=build_back_button(lang), parse_mode="html")


# ─── Check Status ───


@bot.on(events.CallbackQuery(data=b"check_status"))
async def check_status_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    user_sessions[user_id] = {"state": "waiting_cookie_status"}
    await event.edit(
        t("enter_cookie", lang, credits=0),
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )


# ─── Verify (Student/Teacher) ───


@bot.on(events.CallbackQuery(data=b"verify_student"))
async def verify_student_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    sender = await event.get_sender()
    telegram_username = sender.username if sender else ""

    if not is_owner(user_id) and _verify_maintenance_enabled():
        await event.edit(
            _verify_maintenance_block_text(),
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        await send_bot_precheck_log(
            user_id,
            "student",
            "Blocked by maintenance mode",
            telegram_username=telegram_username,
        )
        return

    if not is_owner(user_id):
        settings = get_verify_settings()
        if not settings.get("student_bot", settings.get("student", True)):
            await event.edit(
                t("verify_maintenance", lang, type="Student"),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                "student",
                "Verify type disabled from owner menu",
                telegram_username=telegram_username,
            )
            return

    # Check daily limit (owner bypass)
    if not is_owner(user_id):
        is_limited, used_today, max_limit = check_daily_limit(user_id)
        if is_limited:
            await event.edit(
                t("daily_limit_reached", lang, used=used_today, max_limit=max_limit),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                "student",
                f"Daily limit reached ({used_today}/{max_limit})",
                telegram_username=telegram_username,
            )
            return

    # Check credits (owner is free)
    if not is_owner(user_id):
        required_credits = _get_verify_credit_cost("student")
        credits = get_credits(user_id)
        if credits < required_credits:
            await event.edit(
                t("no_credits", lang, credits=credits)
                + t("required_student_credits", lang, required=required_credits),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                "student",
                f"Not enough credits ({credits}/{required_credits})",
                telegram_username=telegram_username,
            )
            return

        # Strict slot gate: if full, stop before TOS/cookie flow.
        if not _has_free_non_owner_slot():
            await event.edit(
                "🚫 <b>Slot Verify Sedang Penuh</b>\n\n"
                f"Slot aktif saat ini: <b>{_queue_slot_text()}</b>\n"
                "Silakan coba lagi beberapa saat.",
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_queue_log(
                "Blocked new student verify request (slot full)", include_waiting=False
            )
            return

    # Show TOS confirmation before proceeding
    user_sessions[user_id] = {
        "state": "waiting_tos",
        "type": "student",
        "tos_lang": lang,
    }
    tos_text = t("verify_tos", lang)
    lang_toggle_btn = (
        t("btn_tos_switch_id", lang) if lang == "en" else t("btn_tos_switch_en", lang)
    )

    await event.edit(
        tos_text,
        buttons=[
            [Button.inline(t("btn_tos_agree", lang), data=b"tos_agree_student")],
            [Button.inline(t("btn_tos_disagree", lang), data=b"cancel_op")],
            [Button.inline(lang_toggle_btn, data=b"tos_toggle_lang_student")],
        ],
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"verify_teacher"))
async def verify_teacher_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    sender = await event.get_sender()
    telegram_username = sender.username if sender else ""

    if not is_owner(user_id) and _verify_maintenance_enabled():
        await event.edit(
            _verify_maintenance_block_text(),
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        await send_bot_precheck_log(
            user_id,
            "teacher",
            "Blocked by maintenance mode",
            telegram_username=telegram_username,
        )
        return

    if not is_owner(user_id):
        settings = get_verify_settings()
        if not settings.get("teacher_bot", settings.get("teacher", True)):
            await event.edit(
                t("verify_maintenance", lang, type="Teacher"),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                "teacher",
                "Verify type disabled from owner menu",
                telegram_username=telegram_username,
            )
            return

    # Check daily limit (owner bypass)
    if not is_owner(user_id):
        is_limited, used_today, max_limit = check_daily_limit(user_id)
        if is_limited:
            await event.edit(
                t("daily_limit_reached", lang, used=used_today, max_limit=max_limit),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                "teacher",
                f"Daily limit reached ({used_today}/{max_limit})",
                telegram_username=telegram_username,
            )
            return

    # Check credits (owner is free)
    if not is_owner(user_id):
        required_credits = _get_verify_credit_cost("teacher")
        credits = get_credits(user_id)
        if credits < required_credits:
            await event.edit(
                t("no_credits", lang, credits=credits)
                + t("required_teacher_credits", lang, required=required_credits),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                "teacher",
                f"Not enough credits ({credits}/{required_credits})",
                telegram_username=telegram_username,
            )
            return

        # Strict slot gate: if full, stop before TOS/cookie flow.
        if not _has_free_non_owner_slot():
            await event.edit(
                "🚫 <b>Slot Verify Sedang Penuh</b>\n\n"
                f"Slot aktif saat ini: <b>{_queue_slot_text()}</b>\n"
                "Silakan coba lagi beberapa saat.",
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_queue_log(
                "Blocked new teacher verify request (slot full)", include_waiting=False
            )
            return

    # Show TOS before proceeding
    user_sessions[user_id] = {
        "state": "waiting_tos",
        "type": "teacher",
        "tos_lang": lang,
    }
    tos_text = t("verify_tos", lang)
    lang_toggle_btn = (
        t("btn_tos_switch_id", lang) if lang == "en" else t("btn_tos_switch_en", lang)
    )

    await event.edit(
        tos_text,
        buttons=[
            [Button.inline(t("btn_tos_agree", lang), b"tos_agree_teacher")],
            [Button.inline(t("btn_tos_disagree", lang), b"cancel_op")],
            [Button.inline(lang_toggle_btn, b"tos_toggle_lang_teacher")],
        ],
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"set_daily_limit"))
async def set_daily_limit_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return
    current = get_daily_verify_limit()
    current_display = _format_daily_limit(current, lang)
    user_sessions[user_id] = {"state": "waiting_daily_limit_input"}
    await event.edit(
        t("set_daily_limit_prompt", lang, current_display=current_display),
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"set_queue_limit"))
async def set_queue_limit_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    current = get_verify_concurrent_limit()
    user_sessions[user_id] = {"state": "waiting_queue_limit_input"}
    await event.edit(
        "🚦 <b>Set Concurrent Verify Slot</b>\n\n"
        f"Slot saat ini: <b>{current}</b>\n\n"
        "Kirim angka baru (misal: <code>2</code> atau <code>3</code>).\n"
        "Minimal <b>1</b>.",
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"set_backup_interval"))
async def set_backup_interval_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    current = get_backup_interval_minutes()
    user_sessions[user_id] = {"state": "waiting_backup_interval_input"}
    await event.edit(
        "💾 <b>Set Database Backup Interval</b>\n\n"
        f"Interval saat ini: <b>{current} menit</b>\n\n"
        "Kirim angka menit baru (contoh: <code>10</code>, <code>15</code>, <code>30</code>).\n"
        "Minimal <b>1</b> menit.",
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"set_student_credit_cost"))
async def set_student_credit_cost_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    current = get_verify_credit_cost("student")
    user_sessions[user_id] = {"state": "waiting_student_credit_cost_input"}
    await event.edit(
        "🎓 <b>Set Student Verify Credit</b>\n\n"
        f"Credit saat ini: <b>{current}</b>\n\n"
        "Kirim angka baru (contoh: <code>1</code>, <code>2</code>, <code>3</code>).\n"
        "Minimal <b>0</b>.",
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )


@bot.on(events.CallbackQuery(data=b"set_teacher_credit_cost"))
async def set_teacher_credit_cost_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    if user_id != OWNER_ID:
        await event.answer(t("admin_only", lang), alert=True)
        return

    current = get_verify_credit_cost("teacher")
    user_sessions[user_id] = {"state": "waiting_teacher_credit_cost_input"}
    await event.edit(
        "👨‍🏫 <b>Set Teacher Verify Credit</b>\n\n"
        f"Credit saat ini: <b>{current}</b>\n\n"
        "Kirim angka baru (contoh: <code>1</code>, <code>2</code>, <code>3</code>).\n"
        "Minimal <b>0</b>.",
        buttons=build_cancel_button(lang),
        parse_mode="html",
    )


# ═══════════════════════════════════════════════════════════
#  Message Handler (Cookie & Process)
# ═══════════════════════════════════════════════════════════


@bot.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith("/")))
async def message_handler(event):
    user_id = event.sender_id
    session = user_sessions.get(user_id)
    if not session:
        return

    lang = get_lang(user_id)
    text = event.text.strip()
    state = session.get("state", "")

    # ─── Status Check Flow ───
    if state == "waiting_cookie_status":
        cookies = parse_cookies(text)
        if not any(k in cookies for k in ["user_session", "_gh_sess", "_octo"]):
            await event.respond(t("invalid_cookie", lang), parse_mode="html")
            return

        # Delete user's cookie message for safety
        try:
            await event.delete()
        except:
            pass

        msg = await event.respond(t("checking_account", lang), parse_mode="html")

        gh = GitHubSession(cookies)
        status = await asyncio.to_thread(gh.check_application_status)

        status_key = f"status_{status}"
        await msg.edit(
            t(status_key, lang), buttons=build_back_button(lang), parse_mode="html"
        )
        user_sessions.pop(user_id, None)
        return


# ═══════════════════════════════════════════════════════════
#  Background Status Poller
# ═══════════════════════════════════════════════════════════


# ─── Verify Flow (message handler continuation) ───
@bot.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith("/")))
async def verify_cookie_handler(event):
    user_id = event.sender_id
    session = user_sessions.get(user_id)
    if not session:
        return

    lang = get_lang(user_id)
    text = event.text.strip()
    state = session.get("state", "")

    if state == "waiting_add_credit_input":
        if user_id != OWNER_ID:
            user_sessions.pop(user_id, None)
            return

        parts = text.split()
        target_id = None
        amount = 1

        if len(parts) == 1 and parts[0].isdigit():
            target_id = int(parts[0])
        elif len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            target_id = int(parts[0])
            amount = int(parts[1])
        else:
            await event.respond(t("add_credit_invalid", lang), parse_mode="html")
            return

        if amount <= 0:
            await event.respond(t("add_credit_invalid", lang), parse_mode="html")
            return

        get_or_create_user(target_id)
        add_credits(target_id, amount)
        new_total = get_credits(target_id)

        owner_msg = t(
            "add_credit_owner_done",
            lang,
            target_id=target_id,
            amount=amount,
            new_total=new_total,
        )
        await event.respond(owner_msg, parse_mode="html")

        try:
            user_lang = get_lang(target_id)
            user_msg = t(
                "add_credit_user_notice",
                user_lang,
                amount=amount,
                new_total=new_total,
            )
            await bot.send_message(target_id, user_msg, parse_mode="html")
        except Exception as notify_err:
            logger.warning(f"Failed to notify target user {target_id}: {notify_err}")

        user_sessions.pop(user_id, None)
        await show_dashboard(event, user_id, edit=False)
        return

    if state == "waiting_daily_limit_input":
        if user_id != OWNER_ID:
            user_sessions.pop(user_id, None)
            return
        if not text.isdigit():
            await event.respond(
                "❌ Angka tidak valid. Kirim angka (contoh: <code>2</code>) atau <code>0</code> untuk unlimited.",
                parse_mode="html",
            )
            return
        new_limit = int(text)
        set_daily_verify_limit(new_limit)
        limit_display = _format_daily_limit(new_limit, lang)
        await event.respond(
            f"✅ <b>Daily Limit Updated!</b>\n\nLimit baru: <b>{limit_display}</b>",
            parse_mode="html",
        )
        user_sessions.pop(user_id, None)
        await show_dashboard(event, user_id, edit=False)
        return

    if state == "waiting_owner_add_daily_limit_input":
        if user_id != OWNER_ID:
            user_sessions.pop(user_id, None)
            return

        parts = text.split()
        if len(parts) != 2 or (not parts[0].isdigit()) or (not parts[1].isdigit()):
            await event.respond(
                t("owner_add_daily_limit_invalid_format", lang),
                parse_mode="html",
            )
            return

        target_id = int(parts[0])
        bonus_amount = int(parts[1])
        if target_id <= 0 or bonus_amount <= 0:
            await event.respond(
                t("owner_add_daily_limit_invalid_numbers", lang),
                parse_mode="html",
            )
            return

        global_limit = get_daily_verify_limit()
        if global_limit > 0 and bonus_amount > global_limit:
            user_sessions[user_id] = {
                "state": "waiting_owner_add_daily_limit_confirm",
                "target_id": target_id,
                "bonus_amount": bonus_amount,
            }
            await event.respond(
                t(
                    "owner_add_daily_limit_warning",
                    lang,
                    global_limit=global_limit,
                    bonus=bonus_amount,
                ),
                buttons=[
                    [
                        Button.inline(
                            t("btn_confirm", lang),
                            b"confirm_add_daily_limit_bonus",
                        ),
                        Button.inline(
                            t("btn_cancel", lang),
                            b"cancel_add_daily_limit_bonus",
                        ),
                    ]
                ],
                parse_mode="html",
            )
            return

        get_or_create_user(target_id)
        add_daily_verify_bonus(target_id, bonus_amount)
        is_limited, used_today, effective_limit = check_daily_limit(target_id)
        effective_display = _format_daily_limit(effective_limit, lang)

        await event.respond(
            t(
                "owner_add_daily_limit_added",
                lang,
                target_id=target_id,
                bonus=bonus_amount,
                used=used_today,
                effective_limit=effective_display,
            ),
            parse_mode="html",
        )

        try:
            target_lang = get_lang(target_id)
            await bot.send_message(
                target_id,
                t(
                    "owner_add_daily_limit_notify_user",
                    target_lang,
                    bonus=bonus_amount,
                    used=used_today,
                    effective_limit=_format_daily_limit(effective_limit, target_lang),
                ),
                parse_mode="html",
            )
        except Exception as notify_err:
            logger.warning(
                "Failed to notify daily bonus to %s: %s", target_id, notify_err
            )

        user_sessions.pop(user_id, None)
        await show_dashboard(event, user_id, edit=False)
        return

    if state == "waiting_queue_limit_input":
        if user_id != OWNER_ID:
            user_sessions.pop(user_id, None)
            return
        if not text.isdigit() or int(text) < 1:
            await event.respond(
                "❌ Angka tidak valid. Kirim angka minimal <code>1</code>.",
                parse_mode="html",
            )
            return

        new_limit = int(text)
        set_verify_concurrent_limit(new_limit)
        await event.respond(
            f"✅ <b>Queue Limit Updated!</b>\n\nSlot baru: <b>{new_limit}</b>",
            parse_mode="html",
        )
        user_sessions.pop(user_id, None)
        await send_queue_log("Owner updated queue slot limit", include_waiting=False)
        await show_dashboard(event, user_id, edit=False)
        return

    if state == "waiting_backup_interval_input":
        if user_id != OWNER_ID:
            user_sessions.pop(user_id, None)
            return
        if not text.isdigit() or int(text) < 1:
            await event.respond(
                "❌ Angka tidak valid. Kirim angka menit minimal <code>1</code>.",
                parse_mode="html",
            )
            return

        new_interval = int(text)
        set_backup_interval_minutes(new_interval)
        await event.respond(
            "✅ <b>Backup Interval Updated!</b>\n\n"
            f"Backup otomatis sekarang tiap <b>{new_interval} menit</b>.",
            parse_mode="html",
        )
        user_sessions.pop(user_id, None)
        await show_dashboard(event, user_id, edit=False)
        return

    if state == "waiting_student_credit_cost_input":
        if user_id != OWNER_ID:
            user_sessions.pop(user_id, None)
            return
        if not text.isdigit() or int(text) < 0:
            await event.respond(
                "❌ Angka tidak valid. Kirim angka minimal <code>0</code>.",
                parse_mode="html",
            )
            return

        new_cost = int(text)
        set_verify_credit_cost("student", new_cost)
        await event.respond(
            "✅ <b>Student Credit Updated!</b>\n\n"
            f"Biaya verify student sekarang: <b>{new_cost}</b> kredit.",
            parse_mode="html",
        )
        user_sessions.pop(user_id, None)
        await show_dashboard(event, user_id, edit=False)
        return

    if state == "waiting_teacher_credit_cost_input":
        if user_id != OWNER_ID:
            user_sessions.pop(user_id, None)
            return
        if not text.isdigit() or int(text) < 0:
            await event.respond(
                "❌ Angka tidak valid. Kirim angka minimal <code>0</code>.",
                parse_mode="html",
            )
            return

        new_cost = int(text)
        set_verify_credit_cost("teacher", new_cost)
        await event.respond(
            "✅ <b>Teacher Credit Updated!</b>\n\n"
            f"Biaya verify teacher sekarang: <b>{new_cost}</b> kredit.",
            parse_mode="html",
        )
        user_sessions.pop(user_id, None)
        await show_dashboard(event, user_id, edit=False)
        return

    if state != "waiting_cookie":
        return

    if state == "waiting_cookie":
        cookies = parse_cookies(text)
        if not any(k in cookies for k in ["user_session", "_gh_sess", "_octo"]):
            await event.respond(t("invalid_cookie", lang), parse_mode="html")
            return

        sender = await event.get_sender()
        telegram_username = sender.username if sender else ""

        school_code = session.get("school_code")
        if not school_code:
            if is_owner(user_id):
                fallback_school = get_school_profiles()[0]
            else:
                fallback_school = pick_random_public_school()
            school_code = fallback_school.code

        # Delete cookie message
        try:
            await event.delete()
        except:
            pass

        # Delete tutorial image message to avoid media leaking into dashboard/edit flow
        try:
            tutorial_msg_id = session.get("msg_id")
            if tutorial_msg_id:
                await bot.delete_messages(user_id, tutorial_msg_id)
        except:
            pass

        verify_type = session.get("type", "student")

        # ═══ PRE-CHECK: Application Status ═══
        msg = await event.respond(t("process_profile", lang), parse_mode="html")
        await asyncio.sleep(0.5)

        gh = GitHubSession(cookies)

        app_status = await asyncio.to_thread(gh.check_application_status)
        current_status = app_status.get("status", "none")

        if current_status == "pending":
            app_type_str = app_status.get("app_type") or "Unknown"
            submitted_at = app_status.get("submitted_at") or "recently"
            await msg.edit(
                "<blockquote>"
                "⏳ <b>Aplikasi Sedang Diproses</b>\n\n"
                f"Akun ini sudah memiliki aplikasi <b>{app_type_str}</b> yang sedang pending review.\n"
                f"Dikirim: <code>{submitted_at}</code>\n\n"
                "Kamu tidak bisa submit ulang sebelum aplikasi ini selesai diproses oleh GitHub."
                "</blockquote>",
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                verify_type,
                f"Existing application status: pending ({app_type_str}, submitted {submitted_at})",
                telegram_username=telegram_username,
            )
            user_sessions.pop(user_id, None)
            return

        if current_status == "approved":
            app_type_str = app_status.get("app_type") or "Unknown"
            submitted_at = app_status.get("submitted_at") or "recently"
            await msg.edit(
                "<blockquote>"
                "✅ <b>Akun Sudah Terverifikasi!</b>\n\n"
                f"Aplikasi <b>{app_type_str}</b> sudah disetujui GitHub.\n"
                f"Dikirim: <code>{submitted_at}</code>\n\n"
                "Akun ini sudah mendapat GitHub Education. Tidak perlu submit lagi."
                "</blockquote>",
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                verify_type,
                f"Existing application status: approved ({app_type_str}, submitted {submitted_at})",
                telegram_username=telegram_username,
            )
            user_sessions.pop(user_id, None)
            return

        # ═══ STEP 1: Fetch Profile ═══
        uinfo = await asyncio.to_thread(gh.get_user_info)

        if not uinfo:
            await msg.edit(
                t("login_failed", lang),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                verify_type,
                "Login failed. Cookie may be expired.",
                telegram_username=telegram_username,
            )
            user_sessions.pop(user_id, None)
            return

        if not uinfo["has_2fa"]:
            await msg.edit(
                t("no_2fa", lang), buttons=build_back_button(lang), parse_mode="html"
            )
            await send_bot_precheck_log(
                user_id,
                verify_type,
                "2FA is not enabled on this GitHub account",
                telegram_username=telegram_username,
                github_username=uinfo.get("username"),
            )
            user_sessions.pop(user_id, None)
            return

        age_days = uinfo.get("age_days", 0)

        # Block accounts younger than 3 days
        if age_days < 3:
            days_left = 3 - age_days
            twofa_display = "✅ Enabled" if uinfo["has_2fa"] else "❌ Disabled"
            await msg.edit(
                t(
                    "account_too_young",
                    lang,
                    username=uinfo["username"],
                    email=uinfo.get("email") or "N/A",
                    twofa=twofa_display,
                    age_days=age_days,
                    days_left=days_left,
                ),
                buttons=[[Button.inline(t("btn_cancel", lang), data=b"cancel_op")]],
                parse_mode="html",
            )
            await send_bot_precheck_log(
                user_id,
                verify_type,
                f"Account too young ({age_days} days, wait {days_left} more day(s))",
                telegram_username=telegram_username,
                github_username=uinfo.get("username"),
            )
            user_sessions.pop(user_id, None)
            return

        twofa_display = "✅ Enabled" if uinfo["has_2fa"] else "❌ Disabled"
        msg_3days = "Riskan Ditolak" if lang == "id" else "Risky"
        age_display = (
            f"✅ {age_days} Hari"
            if age_days >= 3
            else f"⚠️ {age_days} Hari ({msg_3days})"
        )

        await msg.edit(
            t(
                "process_profile_done",
                lang,
                username=uinfo["username"],
                email=uinfo.get("email") or "N/A",
                twofa=twofa_display,
                age_display=age_display,
            ),
            buttons=[
                [Button.inline(t("btn_confirm", lang), data=b"continue_verify")],
                [Button.inline(t("btn_cancel", lang), data=b"cancel_op")],
            ],
            parse_mode="html",
        )

        # Store for continuation
        user_sessions[user_id] = {
            "state": "waiting_verify_confirm",
            "cookies": cookies,
            "verify_type": verify_type,
            "school_code": school_code,
            "uinfo": uinfo,
            "twofa_display": twofa_display,
            "age_display": age_display,
        }
        return


@bot.on(events.CallbackQuery(data=b"cancel_op"))
async def cancel_op_handler(event):
    user_id = event.sender_id
    user_sessions.pop(user_id, None)

    try:
        await event.delete()
    except:
        pass

    await show_dashboard(None, user_id, edit=False)


async def release_verify_slot(user_id: int, reason: str) -> None:
    removed = False
    async with verify_queue_lock:
        removed = user_id in active_verifications
        if removed:
            active_verifications.pop(user_id, None)
    if removed:
        await send_queue_log(reason, include_waiting=False)


async def allocate_verify_slot(job: dict[str, Any]) -> bool:
    user_id = job["user_id"]

    async with verify_queue_lock:
        if user_id in active_verifications:
            return True

        limit = get_verify_concurrent_limit()
        active_count = _active_non_owner_count()
        if active_count < limit:
            active_verifications[user_id] = {
                "user_id": user_id,
                "username": job["uinfo"].get("username", ""),
                "verify_type": job["verify_type"],
                "started_at": time.monotonic(),
                "last_activity_at": time.monotonic(),
                "stage": "start",
            }
            return True

        return False


async def handle_bot_polling_completion(
    user_id: int,
    username: str,
    verify_type: str,
    final_status: str,
    app_status: dict,
    telegram_username: str,
    first_name: str,
    uinfo: dict,
    school_name: str,
    doc_base64: str,
):
    """Handle completion dari polling (approved/rejected)."""
    lang = get_lang(user_id)
    type_label = "Student" if verify_type == "student" else "Teacher"
    status_full_text = app_status.get("status_full_text", "")
    submitted_at = app_status.get("submitted_at") or "-"
    app_type = app_status.get("app_type") or type_label
    
    if final_status == "approved":
        msg_text = (
            "<blockquote>"
            f"✅ <b>Aplikasi {type_label} Disetujui!</b>\n\n"
            f"👤 Akun: <code>@{username}</code>\n"
            f"🧾 Tipe Aplikasi: <b>{app_type}</b>\n"
            f"📅 Disubmit: <code>{submitted_at}</code>\n\n"
            "GitHub Education sudah aktif di akun ini."
            "</blockquote>"
        )
        await bot.send_message(user_id, msg_text, parse_mode="html")
        await send_log(
            user_id,
            username,
            verify_type,
            "approved",
            status_full_text or "Approved by GitHub",
            telegram_username=telegram_username,
            first_name=first_name,
            github_email=uinfo.get("email"),
            doc_base64=doc_base64,
            github_name=uinfo.get("name"),
            github_2fa=uinfo.get("has_2fa"),
            github_billing=uinfo.get("has_billing"),
            github_age_days=uinfo.get("age_days"),
            app_type=app_type,
            submitted_at=submitted_at,
            status_full_text=status_full_text,
            school_name=school_name,
        )
        await release_verify_slot(user_id, f"Verify approved for {username}")
        logger.info(f"[Poller] {username} → APPROVED")
    
    elif final_status == "rejected":
        reject_intro = app_status.get("reject_intro") or ""
        reject_reasons = app_status.get("reject_reasons") or []
        age_days = uinfo.get("age_days")
        
        reasons_for_user = []
        for reason in reject_reasons:
            reason_line = reason
            if (
                "too recently created" in reason.lower()
                and age_days is not None
                and age_days < 3
            ):
                reason_line += (
                    " (akun belum 3 hari, tunggu beberapa hari lalu apply lagi)"
                )
            reasons_for_user.append(f"• {reason_line}")
        
        msg_text = (
            "<blockquote>"
            f"❌ <b>Aplikasi {type_label} Ditolak</b>\n\n"
            f"👤 Akun: <code>@{username}</code>\n"
            f"🧾 Tipe Aplikasi: <b>{app_type}</b>\n"
            f"📅 Disubmit: <code>{submitted_at}</code>\n\n"
            + (f"{reject_intro}\n\n" if reject_intro else "")
            + (
                "\n".join(reasons_for_user)
                if reasons_for_user
                else "GitHub menolak verifikasi ini. Kamu bisa coba submit lagi."
            )
            + "</blockquote>"
        )
        await bot.send_message(user_id, msg_text, parse_mode="html")
        await send_log(
            user_id,
            username,
            verify_type,
            "rejected",
            status_full_text or "Rejected by GitHub",
            telegram_username=telegram_username,
            first_name=first_name,
            github_email=uinfo.get("email"),
            doc_base64=doc_base64,
            github_name=uinfo.get("name"),
            github_2fa=uinfo.get("has_2fa"),
            github_billing=uinfo.get("has_billing"),
            github_age_days=age_days,
            submitted_at=submitted_at,
            reject_intro=reject_intro,
            reject_reasons=reject_reasons,
            status_full_text=status_full_text,
            school_name=school_name,
        )
        await release_verify_slot(user_id, f"Verify rejected for {username}")
        logger.info(f"[Poller] {username} → REJECTED")
    
    elif final_status == "session_expired":
        await bot.send_message(
            user_id,
            "<blockquote>"
            "⚠️ <b>Session Expired</b>\n\n"
            "Cookie GitHub kamu sudah expired saat polling status.\n"
            "Silakan kirim cookie baru untuk lanjut cek status."
            "</blockquote>",
            parse_mode="html",
        )
        await release_verify_slot(user_id, f"Poller session expired for {username}")
    
    elif final_status == "timeout":
        await bot.send_message(
            user_id,
            "<blockquote>"
            "⏳ <b>Update Status Verifikasi</b>\n\n"
            f"Aplikasi <b>{type_label}</b> untuk <code>@{username}</code> masih dalam antrian review GitHub setelah 2 jam.\n\n"
            "GitHub biasanya memproses dalam 1–3 hari. Kamu bisa cek lagi nanti dengan mengirim cookies yang sama."
            "</blockquote>",
            parse_mode="html",
        )
        await release_verify_slot(user_id, f"Poller timeout release for {username}")


async def run_verify_job(job: dict[str, Any]) -> None:
    """Refactored to use verification_core.py"""
    user_id = job["user_id"]
    lang = job["lang"]
    msg_id = job["msg_id"]
    verify_type = job["verify_type"]
    cookies = job["cookies"]
    school_profile = job.get("school_profile")  # Pre-selected (owner) or None
    school_name = school_profile.name if school_profile else "N/A"
    uinfo = job["uinfo"]
    twofa_display = job["twofa_display"]
    age_display = job.get("age_display", "✅ OK")
    telegram_username = job.get("telegram_username") or ""
    telegram_first_name = job.get("telegram_first_name") or ""
    
    # Display initial profile info
    prefix = (
        t(
            "process_profile_done",
            lang,
            username=uinfo["username"],
            email=uinfo.get("email") or "N/A",
            twofa=twofa_display,
            age_display=age_display,
        )
        + "\n\n"
    )

    try:
        if not is_owner(user_id) and _verify_maintenance_enabled():
            await bot.edit_message(
                user_id,
                msg_id,
                prefix + _verify_maintenance_block_text(),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await release_verify_slot(user_id, "Verify blocked by maintenance mode")
            return

        # Setup context
        ctx = VerificationContext(
            user_id=user_id,
            verify_type=verify_type,
            cookies=cookies,
            is_owner=is_owner(user_id),
            telegram_username=telegram_username,
            telegram_first_name=telegram_first_name,
            source="bot",  # Bot source
            school_profile=school_profile,  # Pre-selected atau None
            skip_cookie_validation=True,  # Sudah di-validate di verify_cookie_handler
            log_callback=None,  # Tidak perlu, kita handle UI sendiri
            progress_callback=lambda stage, data: touch_active_slot(user_id, stage),
        )
        
        # Step 1: Deduct credit SEBELUM submit (user sudah confirm dengan klik Continue)
        touch_active_slot(user_id, "deduct_credit")
        deduct_success, deduct_msg = await asyncio.to_thread(
            verification_core.deduct_credits_before_submit, ctx
        )
        
        if not deduct_success:
            await bot.edit_message(
                user_id,
                msg_id,
                prefix + f"❌ <b>Credit Deduction Failed</b>\n\n<blockquote>{deduct_msg}</blockquote>",
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await release_verify_slot(user_id, deduct_msg)
            return
        
        # Step 2: Pre-check (seharusnya sudah di-check sebelumnya, tapi kita butuh object-nya)
        precheck = await asyncio.to_thread(verification_core.precheck_verification, ctx)
        
        if not precheck.success:
            # Seharusnya tidak terjadi karena sudah di-check sebelumnya
            # Tapi jika terjadi, refund credit
            await asyncio.to_thread(
                verification_core.refund_credits_on_certain_failure,
                ctx,
                VerificationResult(status="rejected", success=False, message=precheck.reason, credit_cost=_get_verify_credit_cost(verify_type))
            )
            await bot.edit_message(
                user_id,
                msg_id,
                prefix + f"❌ <b>Pre-check Failed</b>\n\n<blockquote>{precheck.reason}</blockquote>",
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            await release_verify_slot(user_id, f"Pre-check failed: {precheck.reason}")
            return
        
        # Update UI: Generate identity
        touch_active_slot(user_id, "generate_identity")
        await bot.edit_message(
            user_id,
            msg_id,
            prefix + t("process_identity", lang),
            parse_mode="html",
        )
        
        # Step 3: Execute verification
        result = await asyncio.to_thread(
            verification_core.execute_verification, ctx, precheck
        )
        
        # Step 4: Handle result
        if not result or not result.success:
            error_msg = result.message if result else "Unknown error"
            
            # Check if need refund
            if result and result.status == "rejected":
                # Pasti gagal → refund
                await asyncio.to_thread(
                    verification_core.refund_credits_on_certain_failure, ctx, result
                )
                error_display = (
                    "❌ Ditolak oleh GitHub. Foto dokumen tidak valid, coba lagi."
                    if "rejected" in error_msg.lower()
                    else error_msg
                )
            elif result and result.status == "submit_uncertain":
                # Uncertain → TIDAK refund
                error_display = (
                    "⚠️ <b>Submit Uncertain</b>\n\n"
                    "Aplikasi mungkin sudah masuk ke GitHub atau mungkin gagal. "
                    "Owner akan cek manual. Credit tidak di-refund karena aplikasi mungkin sudah masuk."
                )
            else:
                error_display = error_msg
            
            await bot.edit_message(
                user_id,
                msg_id,
                prefix + t("result_failed", lang, error=error_display),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
            
            # Send log
            await send_log(
                user_id,
                uinfo["username"],
                verify_type,
                result.status if result else "failed",
                error_msg,
                telegram_username=telegram_username,
                first_name=telegram_first_name,
                github_email=uinfo.get("email"),
                doc_base64=result.document_base64 if result else None,
                github_name=uinfo.get("name"),
                github_2fa=uinfo.get("has_2fa"),
                github_billing=uinfo.get("has_billing"),
                github_age_days=uinfo.get("age_days"),
                school_name=school_name,
            )
            
            await release_verify_slot(user_id, f"Verify failed: {error_msg}")
            return
        
        # Success! (approved or pending)
        status_display = "✅ Approved" if result.status == "approved" else "⏳ Pending Review"
        
        final_text = (
            prefix
            + t("process_identity_done", lang)
            + "\n"
            + t("process_billing_done", lang)
            + "\n"
            + t("process_submit_done", lang)
            + "\n\n"
            + "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + t(
                "result_success",
                lang,
                username=uinfo["username"],
                type="Student" if verify_type == "student" else "Teacher",
                elapsed="0m 0s",
            )
            + f"\n<blockquote>📋 Status: <b>{status_display}</b></blockquote>"
        )
        
        await bot.edit_message(
            user_id,
            msg_id,
            final_text,
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        
        # Send log
        await send_log(
            user_id,
            uinfo["username"],
            verify_type,
            result.status,
            "Initial Submission",
            telegram_username=telegram_username,
            first_name=telegram_first_name,
            github_email=uinfo.get("email"),
            doc_base64=result.document_base64,
            github_name=uinfo.get("name"),
            github_2fa=uinfo.get("has_2fa"),
            github_billing=uinfo.get("has_billing"),
            github_age_days=uinfo.get("age_days"),
            school_name=school_name,
        )
        
        # Handle pending status
        if result.status == "pending":
            touch_active_slot(user_id, "pending_review")
            
            # Use new unified poller from verification_core
            async def run_poller_async():
                # Setup polling context
                polling_ctx = PollingContext(
                    user_id=user_id,
                    verify_type=verify_type,
                    cookies=cookies,
                    github_username=uinfo["username"],
                    is_owner=is_owner(user_id),
                    charged_credits=result.credit_cost,
                    telegram_username=telegram_username,
                    telegram_first_name=telegram_first_name,
                    github_email=uinfo.get("email"),
                    github_name=uinfo.get("name"),
                    github_2fa=uinfo.get("has_2fa"),
                    github_billing=uinfo.get("has_billing"),
                    github_age_days=uinfo.get("age_days"),
                    school_name=school_name,
                    document_base64=result.document_base64,
                    submitted_at=result.submitted_at,
                    log_callback=lambda msg: logger.info(msg),
                    on_tick_callback=lambda elapsed: touch_active_slot(user_id, f"pending_{elapsed}s"),
                    on_completed_callback=lambda status, app_status: asyncio.create_task(
                        handle_bot_polling_completion(
                            user_id, uinfo["username"], verify_type, status, app_status,
                            telegram_username, telegram_first_name, uinfo, school_name,
                            result.document_base64
                        )
                    ),
                    max_wait_seconds=7200,  # 2 hours
                )
                
                # Run polling in thread
                poll_result = await asyncio.to_thread(verification_core.poll_pending_application, polling_ctx)
                if poll_result.final_status == "timeout":
                    await handle_bot_polling_completion(
                        user_id,
                        uinfo["username"],
                        verify_type,
                        poll_result.final_status,
                        poll_result.app_status or {},
                        telegram_username,
                        telegram_first_name,
                        uinfo,
                        school_name,
                        result.document_base64,
                    )
            
            asyncio.create_task(run_poller_async())
        else:
            # Approved → release slot
            await release_verify_slot(
                user_id,
                f"Verify finished (approved) for {uinfo.get('username')}"
            )
    
    except Exception as e:
        logger.error(f"Error in verify job for {user_id}: {e}")
        try:
            await bot.edit_message(
                user_id,
                msg_id,
                prefix + t("result_failed", lang, error=str(e)),
                buttons=build_back_button(lang),
                parse_mode="html",
            )
        except Exception:
            pass
        await release_verify_slot(user_id, f"Verify exception: {str(e)}")


async def verify_queue_monitor() -> None:
    global last_queue_heartbeat_at
    while True:
        await asyncio.sleep(60)
        now = time.monotonic()

        stale_users = []
        async with verify_queue_lock:
            for uid, meta in list(active_verifications.items()):
                if is_owner(uid):
                    continue
                if now - meta.get("last_activity_at", now) >= 600:
                    stale_users.append(uid)
            for uid in stale_users:
                active_verifications.pop(uid, None)

        if stale_users:
            await send_queue_log(
                "Auto-release slot (no activity for 10 minutes)",
                include_waiting=False,
            )

        if now - last_queue_heartbeat_at >= 900:
            last_queue_heartbeat_at = now
            # Only send the periodic queue heartbeat if there are active non-owner verifications.
            # This avoids noisy 15-minute heartbeats when the queue is idle.
            if _active_non_owner_count() > 0:
                await send_queue_log("Queue heartbeat (15 min)", include_waiting=False)


async def database_backup_monitor() -> None:
    global last_db_backup_at
    last_db_backup_at = time.monotonic()

    while True:
        await asyncio.sleep(20)
        now = time.monotonic()
        interval_minutes = get_backup_interval_minutes()
        interval_seconds = max(60, interval_minutes * 60)

        if now - last_db_backup_at >= interval_seconds:
            await create_database_backup(trigger="scheduled")
            last_db_backup_at = now


@bot.on(events.CallbackQuery(data=b"continue_verify"))
async def continue_verify_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)
    session = user_sessions.get(user_id)

    if not session or session.get("state") != "waiting_verify_confirm":
        return

    if not is_owner(user_id) and _verify_maintenance_enabled():
        user_sessions.pop(user_id, None)
        await event.edit(
            _verify_maintenance_block_text(),
            buttons=build_back_button(lang),
            parse_mode="html",
        )
        return

    cookies = session["cookies"]
    verify_type = session["verify_type"]
    school_code = session.get("school_code")
    school_profile = get_school_profile(school_code) if school_code else None
    uinfo = session["uinfo"]
    twofa_display = session["twofa_display"]
    age_display = session.get("age_display", "✅ OK")
    credit_cost = _get_verify_credit_cost(verify_type)

    sender = await event.get_sender()
    telegram_username = sender.username or ""
    telegram_first_name = sender.first_name or ""

    source_message = None
    try:
        source_message = await event.get_message()
    except Exception:
        source_message = None

    msg_id = (
        getattr(source_message, "id", None)
        or getattr(event, "message_id", None)
        or getattr(event, "_message_id", None)
    )

    if msg_id is None:
        fallback_msg = await event.respond(t("verify_starting", lang))
        msg_id = fallback_msg.id

    user_sessions.pop(user_id, None)

    job = {
        "user_id": user_id,
        "lang": lang,
        "msg_id": msg_id,
        "cookies": cookies,
        "verify_type": verify_type,
        "school_profile": school_profile,
        "uinfo": uinfo,
        "twofa_display": twofa_display,
        "age_display": age_display,
        "credit_cost": credit_cost,
        "telegram_username": telegram_username,
        "telegram_first_name": telegram_first_name,
    }

    if is_owner(user_id):
        asyncio.create_task(run_verify_job(job))
        return

    started = await allocate_verify_slot(job)
    if started:
        await send_queue_log(
            f"New verify started for {uinfo.get('username')}", include_waiting=False
        )
        asyncio.create_task(run_verify_job(job))
        return

    await event.edit(
        t("slot_full", lang, slots=_queue_slot_text()),
        buttons=build_back_button(lang),
        parse_mode="html",
    )
    await send_queue_log(
        f"Blocked continue_verify for {uinfo.get('username')} (slot full)",
        include_waiting=False,
    )


# ═══════════════════════════════════════════════════════════
#  TOS Agreement & Language Toggle Handlers
# ═══════════════════════════════════════════════════════════


@bot.on(events.CallbackQuery(data=b"tos_agree_student"))
async def tos_agree_student_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)

    try:
        await event.delete()
    except Exception:
        pass

    await start_school_or_cookie_flow(event, user_id, lang, "student")


@bot.on(events.CallbackQuery(data=b"tos_agree_teacher"))
async def tos_agree_teacher_handler(event):
    user_id = event.sender_id
    lang = get_lang(user_id)

    try:
        await event.delete()
    except Exception:
        pass

    await start_school_or_cookie_flow(event, user_id, lang, "teacher")


@bot.on(events.CallbackQuery(data=b"tos_toggle_lang_student"))
async def tos_toggle_lang_student_handler(event):
    user_id = event.sender_id
    session = user_sessions.get(user_id) or {}
    current_lang = session.get("tos_lang", get_lang(user_id))

    # Toggle language temporarily (don't save to DB)
    temp_lang = "id" if current_lang == "en" else "en"
    if session.get("state") == "waiting_tos":
        session["tos_lang"] = temp_lang
        user_sessions[user_id] = session

    # Re-display TOS in new language
    tos_text = t("verify_tos", temp_lang)
    lang_toggle_btn = (
        t("btn_tos_switch_id", temp_lang)
        if temp_lang == "en"
        else t("btn_tos_switch_en", temp_lang)
    )

    try:
        await event.edit(
            tos_text,
            buttons=[
                [Button.inline(t("btn_tos_agree", temp_lang), b"tos_agree_student")],
                [Button.inline(t("btn_tos_disagree", temp_lang), b"cancel_op")],
                [Button.inline(lang_toggle_btn, b"tos_toggle_lang_student")],
            ],
            parse_mode="html",
        )
    except Exception:
        # Message not modified (content is the same), silently ignore
        pass


@bot.on(events.CallbackQuery(data=b"tos_toggle_lang_teacher"))
async def tos_toggle_lang_teacher_handler(event):
    user_id = event.sender_id
    session = user_sessions.get(user_id) or {}
    current_lang = session.get("tos_lang", get_lang(user_id))

    # Toggle language temporarily (don't save to DB)
    temp_lang = "id" if current_lang == "en" else "en"
    if session.get("state") == "waiting_tos":
        session["tos_lang"] = temp_lang
        user_sessions[user_id] = session

    # Re-display TOS in new language
    tos_text = t("verify_tos", temp_lang)
    lang_toggle_btn = (
        t("btn_tos_switch_id", temp_lang)
        if temp_lang == "en"
        else t("btn_tos_switch_en", temp_lang)
    )

    try:
        await event.edit(
            tos_text,
            buttons=[
                [Button.inline(t("btn_tos_agree", temp_lang), b"tos_agree_teacher")],
                [Button.inline(t("btn_tos_disagree", temp_lang), b"cancel_op")],
                [Button.inline(lang_toggle_btn, b"tos_toggle_lang_teacher")],
            ],
            parse_mode="html",
        )
    except Exception:
        # Message not modified (content is the same), silently ignore
        pass


# ═══════════════════════════════════════════════════════════
#  Admin Commands
# ═══════════════════════════════════════════════════════════


@bot.on(events.NewMessage(pattern=r"^/topup$"))
async def topup_cmd(event):
    user_id = event.sender_id
    lang = get_lang(user_id)

    if user_id == OWNER_ID:
        await event.respond(
            t("topup_owner_hint", lang),
            parse_mode="html",
        )
        return

    if not TOPUP_ENABLED:
        await event.respond(
            t("topup_not_configured", lang),
            parse_mode="html",
        )
        return

    pending = get_user_pending_topup(user_id)
    if pending:
        tx_id = int(pending.get("id") or 0)
        await event.respond(
            _topup_pending_text(pending, lang),
            buttons=_build_topup_active_buttons(lang, tx_id),
            parse_mode="html",
        )
        return

    rows_preview = []
    for credits in sorted(TOPUP_PACKAGES.keys()):
        item = TOPUP_PACKAGES.get(credits) or {}
        rows_preview.append(
            f"• <b>{credits} credit</b> — {_format_rupiah(_to_int(item.get('price')))}"
        )

    await event.respond(
        t("topup_intro", lang)
        + "\n\n"
        + "\n".join(rows_preview),
        buttons=_build_topup_package_buttons(lang),
        parse_mode="html",
    )


@bot.on(events.NewMessage(pattern=r"^/addcredit (\d+) (\d+)$"))
async def add_credit_cmd(event):
    lang = get_lang(event.sender_id)
    if event.sender_id != OWNER_ID:
        await event.respond(t("admin_only", lang))
        return
    target_id = int(event.pattern_match.group(1))
    amount = int(event.pattern_match.group(2))
    user = get_or_create_user(target_id)
    add_credits(target_id, amount)
    new_total = get_credits(target_id)
    await event.respond(
        t("addcredit_done", lang, amount=amount, target_id=target_id, new_total=new_total),
        parse_mode="md",
    )
    logger.info(
        f"[ADMIN] Owner added {amount} credits to {target_id}. New total: {new_total}"
    )


@bot.on(events.NewMessage(pattern=r"^/broadcast$"))
async def broadcast_cmd(event):
    lang = get_lang(event.sender_id)
    if event.sender_id != OWNER_ID:
        await event.respond(t("admin_only", lang))
        return

    if not event.is_reply:
        await event.respond(t("broadcast_usage", lang), parse_mode="md")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.message:
        await event.respond(t("broadcast_reply_missing", lang), parse_mode="md")
        return

    broadcast_text = reply_msg.message
    user_ids = get_all_user_ids(include_banned=False)

    sent_count = 0
    fail_count = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, broadcast_text, parse_mode="md")
            sent_count += 1
        except Exception:
            fail_count += 1

    await event.respond(
        t("broadcast_done", lang, sent=sent_count, failed=fail_count, total=len(user_ids)),
        parse_mode="md",
    )


@bot.on(events.NewMessage(pattern=r"^/stats$"))
async def stats_cmd(event):
    lang = get_lang(event.sender_id)
    if event.sender_id != OWNER_ID:
        await event.respond(t("admin_only", lang))
        return

    import sqlite3 as _sql

    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.db")
    conn = _sql.connect(db_path)
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_verifies = conn.execute("SELECT COUNT(*) FROM verify_logs").fetchone()[0]
    total_approved = conn.execute(
        "SELECT COUNT(*) FROM verify_logs WHERE status='approved'"
    ).fetchone()[0]
    total_pending = conn.execute(
        "SELECT COUNT(*) FROM verify_logs WHERE status='pending'"
    ).fetchone()[0]
    total_rejected = conn.execute(
        "SELECT COUNT(*) FROM verify_logs WHERE status='rejected'"
    ).fetchone()[0]
    conn.close()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await event.respond(
        t(
            "stats_text",
            lang,
            total_users=total_users,
            total_verifies=total_verifies,
            approved=total_approved,
            pending=total_pending,
            rejected=total_rejected,
            updated=now,
        ),
        parse_mode="md",
    )


@bot.on(events.NewMessage(pattern=r"^/setlog (-?\d+)$"))
async def set_log_cmd(event):
    global LOG_GROUP_ID
    lang = get_lang(event.sender_id)
    if event.sender_id != OWNER_ID:
        await event.respond(t("admin_only", lang))
        return
    LOG_GROUP_ID = int(event.pattern_match.group(1))
    await event.respond(
        t("setlog_done", lang, log_group_id=LOG_GROUP_ID),
        parse_mode="md",
    )


@bot.on(events.NewMessage(pattern=r"^/liststatus(?: (\d+))?$"))
async def list_status_cmd(event):
    lang = get_lang(event.sender_id)
    if event.sender_id != OWNER_ID:
        await event.respond(t("admin_only", lang))
        return

    limit_raw = event.pattern_match.group(1)
    limit = int(limit_raw) if limit_raw else 20
    limit = max(1, min(limit, 30))

    tasks = get_verify_task_statuses(limit=limit)
    if not tasks:
        await event.respond(t("liststatus_empty", lang), parse_mode="md")
        return

    lines = [t("liststatus_header", lang, limit=limit), ""]
    for idx, task in enumerate(tasks, start=1):
        task_id = str(task.get("id") or "-")
        status = str(task.get("status") or "-")
        gh_user = str(task.get("github_username") or "Waiting...")
        tg_user = int(task.get("telegram_user_id") or 0)
        updated_at = task.get("updated_at")
        try:
            updated_text = datetime.fromtimestamp(float(updated_at)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except Exception:
            updated_text = "-"

        lines.append(
            f"{idx}. `{task_id}` | `{status}` | uid `{tg_user}` | gh `{gh_user}` | `{updated_text}`"
        )

    lines.append("")
    lines.append(t("liststatus_delete_hint", lang))
    await event.respond("\n".join(lines), parse_mode="md")


@bot.on(events.NewMessage(pattern=r"^/delstatus (\S+)$"))
async def delete_status_cmd(event):
    lang = get_lang(event.sender_id)
    if event.sender_id != OWNER_ID:
        await event.respond(t("admin_only", lang))
        return

    task_id = (event.pattern_match.group(1) or "").strip()
    if not task_id:
        await event.respond(t("delstatus_usage", lang), parse_mode="md")
        return

    deleted = delete_verify_task_status(task_id)
    if deleted:
        await event.respond(
            t("delstatus_deleted", lang, task_id=task_id), parse_mode="md"
        )
    else:
        await event.respond(t("delstatus_not_found", lang, task_id=task_id), parse_mode="md")


@bot.on(events.NewMessage(pattern=r"^/help$"))
async def help_cmd(event):
    lang = get_lang(event.sender_id)
    if is_owner(event.sender_id):
        admin_cmds = t("help_admin_cmds", lang)
    else:
        admin_cmds = ""

    await event.respond(
        t("help_text", lang, admin_cmds=admin_cmds),
        parse_mode="md",
    )


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════


async def main():
    logger.info("═" * 50)
    logger.info("🎓 GitHub Education Bot — Starting...")
    logger.info(f"🤖 Bot: @{BOT_USERNAME}")
    logger.info(f"👑 Owner: {OWNER_ID}")
    logger.info(f"📢 Required Groups: {len(REQUIRED_GROUPS)}")
    logger.info(f"📋 Log Group: {LOG_GROUP_ID}")
    logger.info(f"🌐 Default Language: {DEFAULT_LANGUAGE}")
    logger.info("═" * 50)

    apply_school_mode_overrides(get_all_school_mode_overrides())
    logger.info(
        "🏫 School mode overrides applied (public=%s, private=%s)",
        len(get_public_school_profiles()),
        len(get_private_school_profiles()),
    )

    asyncio.create_task(verify_queue_monitor())
    logger.info("🚦 Verify queue monitor started")

    asyncio.create_task(database_backup_monitor())
    logger.info(
        "💾 DB backup monitor started (interval: %s minutes)",
        get_backup_interval_minutes(),
    )

    asyncio.create_task(topup_monitor())
    logger.info(
        "💳 Topup monitor started (interval: %ss, timeout: %ss)",
        TOPUP_AUTO_CHECK_SECONDS,
        TOPUP_TIMEOUT_SECONDS,
    )

    await bot.run_until_disconnected()


if __name__ == "__main__":
    bot.loop.run_until_complete(main())

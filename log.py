"""Shared Telegram log formatting utilities for API and bot flows."""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Iterable


def safe_html_text(value) -> str:
    return html.escape(str(value or ""))


def trim_for_log(text: str, max_len: int = 1400) -> str:
    clean = (text or "").strip()
    if len(clean) <= max_len:
        return clean
    return clean[:max_len] + "\n...(truncated)..."


def normalize_log_status(status: str | None) -> str:
    normalized = (status or "pending").strip().lower()
    if normalized in {"approved", "rejected", "pending"}:
        return normalized
    return "pending"


def normalize_status_full_text(
    status: str,
    status_full_text: str | None,
    details: str | None = None,
) -> str:
    raw = (status_full_text or "").strip()
    if not raw:
        return ""

    lowered = raw.lower()
    generic_values = {
        "pending",
        "approved",
        "rejected",
        "none",
        "pending review",
        "in review",
        "submitted",
        "application submitted",
        "application submitted and waiting for review",
    }
    if lowered in generic_values:
        return ""

    details_value = (details or "").strip().lower()
    if details_value and lowered == details_value:
        return ""

    return trim_for_log(raw, 2400)


def mask_github_username(username: str) -> str:
    username = (username or "").strip()
    if not username:
        return "N/A"
    if len(username) <= 3:
        return username + "\u00b7"
    return username[:3] + ("\u00b7" * min(8, max(1, len(username) - 3)))


def mask_queue_reason_usernames(reason: str) -> str:
    text = (reason or "").strip()
    if not text:
        return text

    pattern = re.compile(r"(\bfor\s+)(@?[A-Za-z0-9][A-Za-z0-9-]{0,38})", re.IGNORECASE)

    def _replace(match: re.Match) -> str:
        prefix = match.group(1)
        raw_user = match.group(2)
        has_at = raw_user.startswith("@")
        username = raw_user[1:] if has_at else raw_user
        masked = mask_github_username(username)
        if has_at:
            masked = "@" + masked
        return prefix + masked

    return pattern.sub(_replace, text)


def _status_display(normalized_status: str) -> tuple[str, str, str, str]:
    if normalized_status == "approved":
        return "✅", "✅ APPROVED", "✅", "Github Education Pack - APPROVED"
    if normalized_status == "rejected":
        return "❌", "❌ REJECTED", "❌", "Github Education Pack - REJECTED"
    return "✅", "⏳ PENDING REVIEW", "⏳", "Github Education Pack - PENDING REVIEW"


def build_verify_owner_log_text(
    telegram_user_id: int,
    verify_type: str,
    status: str,
    details: str,
    credits_left: str | int,
    telegram_username: str | None = None,
    first_name: str | None = None,
    github_username: str | None = None,
    github_email: str | None = None,
    github_name: str | None = None,
    github_2fa: bool | None = None,
    github_billing: bool | None = None,
    github_age_days: int | None = None,
    school_name: str | None = None,
    status_full_text: str | None = None,
    timestamp_text: str | None = None,
    include_full_message: bool = True,
) -> str:
    normalized_status = normalize_log_status(status)
    emoji, status_display, _, _ = _status_display(normalized_status)
    masked_github = mask_github_username(github_username or "")
    details_safe = trim_for_log(details, 1000)
    status_full_safe = normalize_status_full_text(
        normalized_status, status_full_text, details
    )
    timestamp = timestamp_text or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = (
        f"{'=' * 40}\n"
        f"{emoji} <b>VERIFICATION LOG - {verify_type.upper()}</b>\n"
        f"{'=' * 40}\n\n"
        f"<b>📱 TELEGRAM INFO</b>\n"
        f"<blockquote>"
        f"👤 User ID: <code>{telegram_user_id}</code>\n"
    )

    if telegram_username:
        text += f"📝 Username: @{safe_html_text(telegram_username)}\n"
    if first_name:
        text += f"👨‍🎓 Display Name: {safe_html_text(first_name)}\n"

    text += "</blockquote>\n\n"

    text += (
        f"<b>🐙 GITHUB ACCOUNT</b>\n"
        f"<blockquote>"
        f"👤 Username: <code>{safe_html_text(masked_github)}</code>\n"
    )

    if github_name:
        text += f"📝 Profile Name: {safe_html_text(github_name)}\n"
    if github_email:
        text += f"📧 Email: <code>{safe_html_text(github_email)}</code>\n"
    if github_age_days is not None:
        age_status = "✅" if github_age_days >= 3 else "⚠️"
        text += f"{age_status} Account Age: {github_age_days} days\n"
    if github_2fa is not None:
        text += f"🔐 2FA: {'✅ Enabled' if github_2fa else '❌ Disabled'}\n"
    if github_billing is not None:
        text += f"💳 Billing: {'✅ Configured' if github_billing else '⚠️ Not Set'}\n"

    text += "</blockquote>\n\n"

    text += (
        f"<b>📋 VERIFICATION DETAILS</b>\n"
        f"<blockquote>"
        f"📚 Type: <b>{safe_html_text(verify_type.capitalize())}</b>\n"
        f"🏫 School: <b>{safe_html_text(school_name or 'N/A')}</b>\n"
        f"📝 Status: <b>{status_display}</b>\n"
        f"💬 Details: <code>{safe_html_text(details_safe)}</code>\n"
        f"🎫 Credits Left: <b>{credits_left}</b>\n"
        f"⏰ Timestamp: <code>{safe_html_text(timestamp)}</code>\n"
        f"</blockquote>\n"
    )

    if include_full_message and status_full_safe:
        text += (
            "\n<b>📜 GitHub Full Message</b>\n"
            f"<blockquote>{safe_html_text(status_full_safe)}</blockquote>"
        )

    return text


def build_verify_group_log_text(
    telegram_user_id: int,
    verify_type: str,
    status: str,
    details: str,
    credits_left: str | int,
    github_username: str | None = None,
    submitted_at: str | None = None,
    reject_intro: str | None = None,
    reject_reasons: Iterable[str] | None = None,
    status_full_text: str | None = None,
    include_full_message: bool = False,
) -> str:
    normalized_status = normalize_log_status(status)
    _, _, status_emoji, title_text = _status_display(normalized_status)
    masked_github = mask_github_username(github_username or "")
    details_safe = trim_for_log(details, 1000)
    status_full_safe = normalize_status_full_text(
        normalized_status, status_full_text, details
    )

    text = (
        f"{status_emoji} <b>{title_text}</b>\n"
        f"<blockquote>"
        f"👤 User: <code>{telegram_user_id}</code>\n"
        f"🐙 GitHub: <code>{safe_html_text(masked_github)}</code>\n"
        f"📚 Type: <b>{safe_html_text(verify_type.capitalize())}</b>\n"
        f"🎫 Credit Remaining: <b>{credits_left}</b>\n"
        f"📅 Submitted: <code>{safe_html_text(submitted_at or '-')}</code>\n"
        f"📋 Status: <code>{safe_html_text(details_safe)}</code>"
        f"</blockquote>"
    )

    if normalized_status == "rejected":
        lines = [f"• {safe_html_text(reason)}" for reason in (reject_reasons or [])]
        if reject_intro:
            text += (
                "\n\n<b>❗ GitHub Message</b>\n"
                f"<blockquote>{safe_html_text(reject_intro)}</blockquote>"
            )
        if lines:
            text += (
                "\n\n<b>🧠 GitHub Reasons</b>\n"
                f"<blockquote>{'\n'.join(lines)}</blockquote>"
            )

    if include_full_message and status_full_safe:
        text += (
            "\n\n<b>📜 GitHub Full Message</b>\n"
            f"<blockquote>{safe_html_text(status_full_safe)}</blockquote>"
        )

    return text


def build_queue_update_log_text(
    slot_text: str,
    reason: str,
    timestamp_text: str | None = None,
) -> str:
    masked_reason = mask_queue_reason_usernames(reason)
    timestamp = timestamp_text or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🚦 <b>Verify Queue Update</b>\n"
        "<blockquote>"
        f"📦 Slots: <b>{safe_html_text(slot_text)}</b>\n"
        f"💬 Reason: {safe_html_text(masked_reason)}\n"
        f"⏰ Time: <code>{safe_html_text(timestamp)}</code>"
        "</blockquote>"
    )


def build_precheck_log_text(
    telegram_user_id: int,
    verify_type: str,
    reason: str,
    telegram_username: str | None = None,
    github_username: str | None = None,
    timestamp_text: str | None = None,
) -> str:
    masked_github = mask_github_username(github_username or "")
    timestamp = timestamp_text or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = (
        "⚠️ <b>Verify Precheck Blocked</b>\n"
        "<blockquote>"
        f"👤 User ID: <code>{telegram_user_id}</code>\n"
    )

    if telegram_username:
        text += f"📝 Username: @{safe_html_text(telegram_username)}\n"

    text += (
        f"🐙 GitHub: <code>{safe_html_text(masked_github)}</code>\n"
        f"📚 Type: <b>{safe_html_text(verify_type.capitalize())}</b>\n"
        f"💬 Reason: <code>{safe_html_text(trim_for_log(reason, 700))}</code>\n"
        f"⏰ Time: <code>{safe_html_text(timestamp)}</code>"
        "</blockquote>"
    )

    return text


def build_poller_issue_log_text(
    telegram_user_id: int,
    verify_type: str,
    stage: str,
    issue: str,
    task_id: str | None = None,
    telegram_username: str | None = None,
    github_username: str | None = None,
    timestamp_text: str | None = None,
) -> str:
    masked_github = mask_github_username(github_username or "")
    timestamp = timestamp_text or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = (
        "🚨 <b>Poller Issue Detected</b>\n"
        "<blockquote>"
        f"🆔 Task: <code>{safe_html_text(task_id or '-')}</code>\n"
        f"👤 User ID: <code>{telegram_user_id}</code>\n"
    )

    if telegram_username:
        text += f"📝 Username: @{safe_html_text(telegram_username)}\n"

    text += (
        f"🐙 GitHub: <code>{safe_html_text(masked_github)}</code>\n"
        f"📚 Type: <b>{safe_html_text(verify_type.capitalize())}</b>\n"
        f"🧭 Stage: <code>{safe_html_text(stage)}</code>\n"
        f"💬 Issue: <code>{safe_html_text(trim_for_log(issue, 900))}</code>\n"
        f"⏰ Time: <code>{safe_html_text(timestamp)}</code>"
        "</blockquote>"
    )

    return text

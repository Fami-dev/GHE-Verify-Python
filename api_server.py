"""Flask API server that bridges Next.js WebApp with bot verification logic."""

from __future__ import annotations

import base64
import io
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request
import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from database import (
    add_credits,
    add_verify_log,
    check_daily_limit,
    get_all_school_mode_overrides,
    get_verify_maintenance_mode,
    get_verify_task_status,
    get_verify_task_statuses,
    deduct_credits,
    get_or_create_user,
    get_user,
    get_verify_credit_cost,
    get_verify_settings,
    increment_daily_verify_count,
    upsert_verify_task_status,
)
from github_session import (
    GitHubSession,
    apply_school_mode_overrides,
    create_id_card_base64,
    create_teacher_documents_base64,
    generate_student_data,
    generate_teacher_data,
    get_application_status_poll_interval,
    get_school_profiles,
    parse_cookies,
)
from verification_core import (
    PreCheckResult,
    VerificationCore,
    VerificationContext,
    PollingContext,
)
from log import (
    build_poller_issue_log_text,
    build_precheck_log_text,
    build_queue_update_log_text,
    build_verify_group_log_text,
    build_verify_owner_log_text,
    trim_for_log,
)

app = Flask(__name__)

MAINTENANCE_ERROR_TEXT = "Verification sedang maintenance. Silakan coba lagi nanti."

API_SECRET = os.getenv("API_SECRET", "changeme_in_production")
OWNER_ID = int(os.getenv("OWNER_ID", "1374294212"))
LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "0") or "0")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ENABLE_API_TELEGRAM_LOGS = os.getenv(
    "ENABLE_API_TELEGRAM_LOGS", "1"
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
# Web flow must always stop at profile confirmation before charging credits.
WEB_REQUIRE_CONFIRMATION = True

verification_tasks: dict[str, dict] = {}
task_lock = threading.Lock()

NO_INFO_TIMEOUT_SECONDS = 600
POLL_STOP_SECONDS = 3600

# Initialize VerificationCore
verification_core = VerificationCore(owner_id=OWNER_ID)


def refresh_school_mode_overrides() -> None:
    try:
        apply_school_mode_overrides(get_all_school_mode_overrides())
    except Exception:
        pass


def now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def check_auth(req) -> bool:
    auth_header = (req.headers.get("Authorization") or "").strip()
    expected_token = API_SECRET.strip().strip("'\"")
    return auth_header == f"Bearer {expected_token}"


def sanitize_username(username: str | None) -> str:
    raw = (username or "").strip()
    if not raw:
        return "N/A"
    return f"{raw[:3]}***"


def is_verify_maintenance_active() -> bool:
    return bool(get_verify_maintenance_mode())


def get_ban_state(user_id: int) -> tuple[bool, str]:
    db_user = get_user(user_id) or {}
    is_banned = bool(db_user.get("is_banned", 0))
    ban_reason = str(db_user.get("ban_reason") or "").strip()
    return is_banned, ban_reason


def build_banned_response(ban_reason: str) -> tuple[object, int]:
    reason_text = ban_reason or "Violation of terms"
    return (
        jsonify(
            {
                "success": False,
                "error": f"Access blocked. Reason: {reason_text}",
                "banned": True,
                "ban_reason": reason_text,
                "appeal_contact": "@arcvour",
            }
        ),
        403,
    )


def is_disk_full_error(exc: Exception) -> bool:
    return "database or disk is full" in str(exc).lower()


def send_telegram_html(chat_id: int, text: str) -> None:
    if not BOT_TOKEN or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": str(chat_id),
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            },
            timeout=15,
        )
    except Exception:
        # Telegram logging failure must not break verification flow.
        pass


def send_telegram_document_bytes(
    chat_id: int,
    filename: str,
    file_bytes: bytes,
    caption: str,
    mime_type: str = "application/pdf",
    parse_mode: str | None = "HTML",
) -> None:
    if not BOT_TOKEN or not chat_id or not file_bytes:
        return
    try:
        payload = {
            "chat_id": str(chat_id),
            "caption": caption,
            "disable_web_page_preview": "true",
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
            data=payload,
            files={"document": (filename, file_bytes, mime_type)},
            timeout=30,
        )
    except Exception:
        pass


def convert_base64_image_to_pdf_bytes(doc_base64: str) -> bytes | None:
    if not doc_base64:
        return None
    try:
        raw = base64.b64decode(doc_base64)
    except Exception:
        return None

    if raw[:4] == b"%PDF":
        return raw

    try:
        from PIL import Image

        image = Image.open(io.BytesIO(raw))
        if image.mode != "RGB":
            image = image.convert("RGB")
        out = io.BytesIO()
        image.save(out, "PDF", resolution=100.0)
        out.seek(0)
        return out.getvalue()
    except Exception:
        return None


def send_bot_style_verify_log(
    telegram_user_id: int,
    verify_type: str,
    status: str,
    details: str,
    telegram_username: str | None = None,
    first_name: str | None = None,
    github_username: str | None = None,
    github_email: str | None = None,
    github_name: str | None = None,
    github_2fa: bool | None = None,
    github_billing: bool | None = None,
    github_age_days: int | None = None,
    school_name: str | None = None,
    submitted_at: str | None = None,
    reject_intro: str | None = None,
    reject_reasons: list[str] | None = None,
    status_full_text: str | None = None,
    doc_base64: str | None = None,
) -> None:
    if not ENABLE_API_TELEGRAM_LOGS or not BOT_TOKEN:
        return

    db_user = get_user(telegram_user_id) or {}
    credits_left = (
        "Unlimited" if telegram_user_id == OWNER_ID else int(db_user.get("credits", 0))
    )
    owner_text = build_verify_owner_log_text(
        telegram_user_id=telegram_user_id,
        verify_type=verify_type,
        status=status,
        details=details,
        credits_left=credits_left,
        telegram_username=telegram_username,
        first_name=first_name,
        github_username=github_username,
        github_email=github_email,
        github_name=github_name,
        github_2fa=github_2fa,
        github_billing=github_billing,
        github_age_days=github_age_days,
        school_name=school_name,
        status_full_text=status_full_text,
        include_full_message=False,
    )

    if OWNER_ID:
        pdf_bytes = (
            convert_base64_image_to_pdf_bytes(doc_base64) if doc_base64 else None
        )
        if pdf_bytes:
            safe_name = (github_username or "user").replace("/", "_").replace("\\", "_")
            filename = f"verify_{verify_type}_{safe_name}.pdf"
            send_telegram_document_bytes(
                OWNER_ID,
                filename,
                pdf_bytes,
                trim_for_log(owner_text, 1000),
                parse_mode="HTML",
            )
        else:
            send_telegram_html(OWNER_ID, owner_text)

    # Send Group Log
    if LOG_GROUP_ID:
        try:
            fancy_log = build_verify_group_log_text(
                telegram_user_id=telegram_user_id,
                verify_type=verify_type,
                status=status,
                details=details,
                credits_left=credits_left,
                github_username=github_username,
                submitted_at=submitted_at,
                reject_intro=reject_intro,
                reject_reasons=reject_reasons,
                status_full_text=status_full_text,
                include_full_message=False,
            )
            send_telegram_html(LOG_GROUP_ID, fancy_log)
        except Exception:
            pass


def notify_owner_and_group(text: str) -> None:
    # API-side Telegram logs are disabled by default so users only get bot-native logs.
    if not ENABLE_API_TELEGRAM_LOGS:
        return

    if OWNER_ID:
        send_telegram_html(OWNER_ID, text)


def _api_queue_slot_text() -> str:
    settings = get_verify_settings()
    queue_limit = int(settings.get("queue_limit", 2))
    now_value = now_ts()

    with task_lock:
        all_tasks = [clone_task_snapshot(t) for t in verification_tasks.values()]

    queue_active = count_active_non_owner_queue_slots(all_tasks, now_value)
    return f"{queue_active}/{queue_limit}"


def send_api_queue_log(reason: str) -> None:
    if not ENABLE_API_TELEGRAM_LOGS or not BOT_TOKEN:
        return

    body = build_queue_update_log_text(
        slot_text=_api_queue_slot_text(),
        reason=reason,
        timestamp_text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    if OWNER_ID:
        send_telegram_html(OWNER_ID, body)
    if LOG_GROUP_ID:
        send_telegram_html(LOG_GROUP_ID, body)


def send_api_precheck_log(
    telegram_user_id: int,
    verify_type: str,
    reason: str,
    telegram_username: str | None = None,
    github_username: str | None = None,
) -> None:
    if not ENABLE_API_TELEGRAM_LOGS or not BOT_TOKEN:
        return

    body = build_precheck_log_text(
        telegram_user_id=telegram_user_id,
        verify_type=verify_type,
        reason=reason,
        telegram_username=telegram_username,
        github_username=github_username,
        timestamp_text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    if OWNER_ID:
        send_telegram_html(OWNER_ID, body)


def send_api_poller_issue_log(
    telegram_user_id: int,
    verify_type: str,
    stage: str,
    issue: str,
    task_id: str | None = None,
    telegram_username: str | None = None,
    github_username: str | None = None,
) -> None:
    if not ENABLE_API_TELEGRAM_LOGS or not BOT_TOKEN:
        return

    body = build_poller_issue_log_text(
        telegram_user_id=telegram_user_id,
        verify_type=verify_type,
        stage=stage,
        issue=issue,
        task_id=task_id,
        telegram_username=telegram_username,
        github_username=github_username,
        timestamp_text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    if OWNER_ID:
        send_telegram_html(OWNER_ID, body)


def clone_task_snapshot(task: dict) -> dict:
    snapshot = dict(task)
    logs = task.get("logs", [])
    if isinstance(logs, list):
        snapshot["logs"] = list(logs)
    profile = task.get("profile")
    if isinstance(profile, dict):
        snapshot["profile"] = dict(profile)
    elif isinstance(profile, list):
        snapshot["profile"] = list(profile)
    else:
        snapshot["profile"] = profile
    snapshot["id"] = str(snapshot.get("id") or snapshot.get("task_id") or "")
    return snapshot


def persist_task_snapshot(task: dict) -> None:
    if not task:
        return
    try:
        upsert_verify_task_status(task)
    except Exception:
        # Persistence failure must not break verification flow.
        pass


def persist_task_by_id(task_id: str) -> None:
    with task_lock:
        task = verification_tasks.get(task_id)
        if not task:
            return
        snapshot = clone_task_snapshot(task)
    persist_task_snapshot(snapshot)


def task_add_log(task_id: str, message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] {message}"
    with task_lock:
        task = verification_tasks.get(task_id)
        if not task:
            return
        task.setdefault("logs", []).append(line)
        task["updated_at"] = now_ts()
        snapshot = clone_task_snapshot(task)
    persist_task_snapshot(snapshot)


def task_update(task_id: str, **kwargs) -> None:
    with task_lock:
        task = verification_tasks.get(task_id)
        if not task:
            return
        task.update(kwargs)
        task["updated_at"] = now_ts()
        snapshot = clone_task_snapshot(task)
    persist_task_snapshot(snapshot)


def get_pending_elapsed(task: dict, current_ts: float | None = None) -> float:
    now_value = current_ts if current_ts is not None else now_ts()
    baseline = task.get("pending_since") or task.get("started_at") or now_value
    try:
        elapsed = now_value - float(baseline)
    except (TypeError, ValueError):
        elapsed = 0.0
    return max(0.0, elapsed)


def is_non_owner_task(task: dict) -> bool:
    try:
        telegram_user_id = int(task.get("telegram_user_id") or 0)
    except (TypeError, ValueError):
        telegram_user_id = 0
    return telegram_user_id != OWNER_ID


def is_active_non_owner_queue_task(task: dict, current_ts: float) -> bool:
    status = str(task.get("status") or "").strip().lower()
    if status not in {"pending", "awaiting_confirm"}:
        return False
    if not is_non_owner_task(task):
        return False
    if bool(task.get("slot_released", False)):
        return False
    return get_pending_elapsed(task, current_ts) <= NO_INFO_TIMEOUT_SECONDS


def count_active_non_owner_queue_slots(tasks: list[dict], current_ts: float) -> int:
    return sum(1 for task in tasks if is_active_non_owner_queue_task(task, current_ts))


def get_visual_status(task: dict, current_ts: float | None = None) -> tuple[str, str]:
    current_status = str(task.get("status") or "none")
    if current_status != "pending":
        if current_status == "session_expired":
            return (
                current_status,
                "GitHub session expired. Resend cookies to continue polling.",
            )
        if current_status == "precheck_failed":
            return current_status, "Pre-check failed before application submission."
        if current_status == "awaiting_confirm":
            return current_status, "Waiting for user confirmation (Continue/Cancel)."
        if current_status == "cancelled":
            return current_status, "Canceled by user."
        if current_status == "approved":
            return current_status, "Approved by GitHub."
        if current_status == "rejected":
            return current_status, "Rejected by GitHub or failed validation."
        return current_status, "-"

    elapsed = get_pending_elapsed(task, current_ts)
    polling_active = bool(task.get("polling_active", False))

    if elapsed > NO_INFO_TIMEOUT_SECONDS:
        if elapsed >= POLL_STOP_SECONDS or not polling_active:
            return (
                "timeout",
                "No updates for >10 minutes (slot released). Poller inactive after 1 hour.",
            )
        if elapsed >= 1800:
            return (
                "timeout",
                "No updates for >10 minutes (slot released). Poller checks every 10 minutes until 1 hour.",
            )
        return (
            "timeout",
            "No updates for >10 minutes (slot released). Poller checks every 5 minutes until 30 minutes.",
        )

    return (
        "pending",
        "In review queue. Poller checks every 30 seconds (first 10 minutes).",
    )


def run_pending_status_poller(
    task_id: str,
    cookies_raw: str,
    telegram_user_id: int,
    telegram_username: str | None,
    verify_type: str,
    github_username: str | None,
    credit_cost: int,
    is_owner: bool,
) -> None:
    try:
        parsed_cookies = parse_cookies(cookies_raw)
    except Exception as exc:
        task_add_log(task_id, f"[POLL] Failed to initialize poller: {exc}")
        task_update(task_id, polling_active=False)
        send_api_poller_issue_log(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            verify_type=verify_type,
            stage="poller_init",
            issue=f"Failed to initialize poller client: {exc}",
            task_id=task_id,
            github_username=github_username,
        )
        return

    with task_lock:
        task = verification_tasks.get(task_id)
        if not task:
            return
        task_github_username = str(
            task.get("github_username_raw")
            or task.get("github_username")
            or github_username
            or ""
        )
        task_github_email = task.get("github_email")
        task_github_name = task.get("github_name")
        task_school_name = task.get("school_name")
        task_github_2fa = task.get("github_2fa")
        if isinstance(task_github_2fa, str):
            task_github_2fa = task_github_2fa.strip().lower() in {"1", "true", "yes", "on"}
        elif task_github_2fa is not None:
            task_github_2fa = bool(task_github_2fa)
        task_github_billing = task.get("github_billing")
        if isinstance(task_github_billing, str):
            task_github_billing = task_github_billing.strip().lower() in {"1", "true", "yes", "on"}
        elif task_github_billing is not None:
            task_github_billing = bool(task_github_billing)
        task_github_age_days = task.get("github_age_days")
        if task_github_age_days is not None:
            try:
                task_github_age_days = int(task_github_age_days)
            except (TypeError, ValueError):
                task_github_age_days = None
        task_submitted_at = task.get("submitted_at")
        doc_base64 = str(task.get("document_base64") or "")

    task_add_log(
        task_id,
        "[POLL] Poller active via verification_core: 30s (0-10m), 5m (10-30m), 10m (30-60m).",
    )

    def on_tick(elapsed: int) -> None:
        if elapsed >= NO_INFO_TIMEOUT_SECONDS:
            with task_lock:
                current = verification_tasks.get(task_id)
                already_released = bool(current and current.get("slot_released"))
            if not already_released:
                task_update(task_id, slot_released=True)
                task_add_log(
                    task_id,
                    "[QUEUE] No status update for >10 minutes. Queue slot released, monitoring continues.",
                )
                send_api_queue_log("Web queue slot released after 10m without status update")

    completed = {"handled": False}

    def on_completed(status: str, app_status: dict) -> None:
        completed["handled"] = True
        if status == "session_expired":
            status_error = str(app_status.get("error") or "login required")
            task_add_log(
                task_id,
                "[POLL] GitHub session expired/login required. Waiting for new cookies from user.",
            )
            task_update(
                task_id,
                status="session_expired",
                polling_active=False,
                slot_released=True,
            )
            send_api_poller_issue_log(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                verify_type=verify_type,
                stage="session_expired",
                issue=f"GitHub session expired during poller: {status_error}",
                task_id=task_id,
                github_username=task_github_username,
            )
            return

        handle_polling_completion(
            task_id,
            status,
            app_status,
            telegram_user_id,
            telegram_username,
            verify_type,
            task_github_username,
            type(
                "PreCheckSnapshot",
                (),
                {
                    "github_email": task_github_email,
                    "github_name": task_github_name,
                    "has_2fa": task_github_2fa,
                    "has_billing": task_github_billing,
                    "age_days": task_github_age_days,
                    "school_name": task_school_name,
                },
            )(),
            doc_base64,
        )

    polling_ctx = PollingContext(
        user_id=telegram_user_id,
        verify_type=verify_type,
        cookies=parsed_cookies,
        github_username=task_github_username or (github_username or ""),
        is_owner=is_owner,
        charged_credits=credit_cost,
        telegram_username=telegram_username,
        github_email=task_github_email,
        github_name=task_github_name,
        github_2fa=task_github_2fa,
        github_billing=task_github_billing,
        github_age_days=task_github_age_days,
        school_name=task_school_name,
        document_base64=doc_base64,
        submitted_at=task_submitted_at,
        on_tick_callback=on_tick,
        on_completed_callback=on_completed,
        log_callback=lambda msg: task_add_log(task_id, msg),
        max_wait_seconds=POLL_STOP_SECONDS,
    )

    result = verification_core.poll_pending_application(polling_ctx)
    if result.final_status == "timeout" and not completed["handled"]:
        task_update(task_id, polling_active=False, slot_released=True)
        task_add_log(task_id, "[POLL] No final status after 1 jam. Poller nonaktif.")


def load_persisted_tasks() -> None:
    persisted_tasks = get_verify_task_statuses(limit=0)
    if not persisted_tasks:
        return

    resume_candidates: list[tuple[str, str, int, str | None, str, str, int, bool]] = []

    with task_lock:
        for persisted in persisted_tasks:
            task_id = str(persisted.get("id") or persisted.get("task_id") or "").strip()
            if not task_id:
                continue
            persisted["id"] = task_id
            verification_tasks[task_id] = persisted

            if (
                persisted.get("status") == "pending"
                and bool(persisted.get("application_submitted", False))
                and bool(persisted.get("polling_active", False))
                and bool(persisted.get("cookies_raw"))
            ):
                verify_type = str(persisted.get("verify_type") or "student")
                telegram_user_id = int(persisted.get("telegram_user_id") or 0)
                resume_candidates.append(
                    (
                        task_id,
                        str(persisted.get("cookies_raw") or ""),
                        telegram_user_id,
                        persisted.get("telegram_username"),
                        verify_type,
                        str(
                            persisted.get("github_username_raw")
                            or persisted.get("github_username")
                            or "N/A"
                        ),
                        get_verify_credit_cost(verify_type),
                        telegram_user_id == OWNER_ID,
                    )
                )

    for candidate in resume_candidates:
        task_add_log(candidate[0], "[POLL] Poller resumed after API restart.")
        poller = threading.Thread(
            target=run_pending_status_poller,
            args=candidate,
            daemon=True,
        )
        poller.start()


def handle_polling_completion(
    task_id: str,
    final_status: str,
    app_status: dict,
    telegram_user_id: int,
    telegram_username: str | None,
    verify_type: str,
    github_username: str,
    precheck,
    doc_base64: str,
):
    """Handle completion dari polling (approved/rejected)."""
    status_full_text = app_status.get("status_full_text", "")
    submitted_at = app_status.get("submitted_at") or "-"
    
    if final_status == "approved":
        task_update(
            task_id,
            status="approved",
            polling_active=False,
            slot_released=True,
            application_submitted=True,
            submitted_at=submitted_at,
            status_full_text=status_full_text,
            polled_final_at=now_ts(),
        )
        task_add_log(task_id, "[POLL] Status changed to APPROVED.")
        
        send_bot_style_verify_log(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            github_username=github_username,
            github_email=precheck.github_email,
            github_name=precheck.github_name,
            github_2fa=precheck.has_2fa,
            github_billing=precheck.has_billing,
            github_age_days=precheck.age_days,
            school_name=precheck.school_name,
            verify_type=verify_type,
            status="approved",
            details=status_full_text or "Approved by GitHub",
            status_full_text=status_full_text,
            submitted_at=submitted_at,
            doc_base64=doc_base64,
        )
        send_api_queue_log(f"Web verify finished APPROVED for {github_username}")
    
    elif final_status == "rejected":
        task_update(
            task_id,
            status="rejected",
            polling_active=False,
            slot_released=True,
            application_submitted=True,
            submitted_at=submitted_at,
            status_full_text=status_full_text,
            polled_final_at=now_ts(),
        )
        task_add_log(task_id, "[POLL] Status changed to REJECTED.")
        
        send_bot_style_verify_log(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            github_username=github_username,
            github_email=precheck.github_email,
            github_name=precheck.github_name,
            github_2fa=precheck.has_2fa,
            github_billing=precheck.has_billing,
            github_age_days=precheck.age_days,
            school_name=precheck.school_name,
            verify_type=verify_type,
            status="rejected",
            details=status_full_text or "Rejected by GitHub",
            status_full_text=status_full_text,
            submitted_at=submitted_at,
            doc_base64=doc_base64,
        )
        send_api_queue_log(f"Web verify finished REJECTED for {github_username}")


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _resolve_school_profile_by_code(school_code: str | None):
    code = str(school_code or "").strip().lower()
    if not code:
        return None

    refresh_school_mode_overrides()
    for school in get_school_profiles():
        if str(getattr(school, "code", "")).strip().lower() == code:
            return school
    return None


def _build_precheck_from_profile_cache(
    profile: dict | None,
    fallback_school_profile,
) -> PreCheckResult | None:
    if not isinstance(profile, dict):
        return None

    github_username = str(profile.get("github_username_raw") or "").strip()
    if not github_username:
        return None

    github_email = str(
        profile.get("github_email_raw")
        or profile.get("email")
        or ""
    ).strip()
    if github_email.upper() == "N/A":
        github_email = ""

    github_name = str(profile.get("github_name") or "").strip()
    has_2fa = _parse_bool(profile.get("has_2fa"))
    has_billing = _parse_bool(profile.get("has_billing"))

    try:
        age_days = int(profile.get("age_days") or 0)
    except (TypeError, ValueError):
        age_days = 0

    school_profile = fallback_school_profile
    if school_profile is None:
        school_profile = _resolve_school_profile_by_code(profile.get("school_code"))
    if school_profile is None:
        return None

    school_name = str(profile.get("school_name") or getattr(school_profile, "name", "N/A"))

    return PreCheckResult(
        success=True,
        reason="Reused precheck snapshot",
        github_username=github_username,
        github_email=github_email,
        github_name=github_name,
        has_2fa=has_2fa,
        has_billing=has_billing,
        age_days=age_days,
        school_profile=school_profile,
        school_name=school_name,
    )


def run_verify_background(
    task_id: str,
    cookies_raw: str,
    telegram_user_id: int,
    telegram_username: str | None,
    verify_type: str,
    require_confirmation: bool = True,
) -> None:
    """Refactored to use verification_core.py"""
    is_owner = telegram_user_id == OWNER_ID
    credit_cost = get_verify_credit_cost(verify_type)

    try:
        # Get school_id dari task (jika ada)
        with task_lock:
            task = verification_tasks.get(task_id)
            school_id = task.get("school_id") if task else None
        
        # Fetch school profile jika owner dan school_id provided
        school_profile = None
        if is_owner and school_id:
            try:
                refresh_school_mode_overrides()
                all_schools = get_school_profiles()
                school_id_str = str(school_id).strip().lower()

                # Match by school code (preferred), fallback to 1-based index for compatibility.
                for index, school in enumerate(all_schools, start=1):
                    school_code = str(getattr(school, "code", "")).strip().lower()
                    if school_id_str in {school_code, str(index)}:
                        school_profile = school
                        break
                
                if school_profile:
                    task_add_log(task_id, f"[SCHOOL] Using selected school: {school_profile.name}")
                else:
                    task_add_log(task_id, f"[SCHOOL] School ID {school_id} not found, using random")
            except Exception as exc:
                task_add_log(task_id, f"[SCHOOL] Failed to fetch school: {exc}, using random")
        
        # Parse cookies
        try:
            parsed_cookies = parse_cookies(cookies_raw)
        except Exception as e:
            task_add_log(task_id, f"[ERROR] Failed to parse cookies: {e}")
            task_update(
                task_id,
                status="precheck_failed",
                application_submitted=False,
                polling_active=False,
                slot_released=True,
            )
            send_api_precheck_log(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                verify_type=verify_type,
                reason="Invalid cookie format",
            )
            return

        # Setup context
        ctx = VerificationContext(
            user_id=telegram_user_id,
            verify_type=verify_type,
            cookies=parsed_cookies,
            is_owner=is_owner,
            telegram_username=telegram_username,
            source="web",  # Web API
            school_profile=school_profile,  # Gunakan selected school atau None (random)
            skip_cookie_validation=False,  # Validate cookies
            log_callback=lambda msg: task_add_log(task_id, msg),
            progress_callback=lambda stage, data: task_update(task_id, current_stage=stage),
        )

        precheck = None
        if not require_confirmation:
            cached_profile = None
            with task_lock:
                task = verification_tasks.get(task_id)
                if task:
                    cached_profile = task.get("profile")
            precheck = _build_precheck_from_profile_cache(cached_profile, school_profile)
            if precheck:
                task_add_log(task_id, "[PRECHECK] Reusing confirmed profile snapshot.")
            else:
                task_add_log(task_id, "[PRECHECK] Snapshot unavailable, running pre-check again.")

        if precheck is None:
            # Step 1: Pre-check validation
            precheck = verification_core.precheck_verification(ctx)

            if not precheck.success:
                # Pre-check failed
                task_update(
                    task_id,
                    status="precheck_failed",
                    application_submitted=False,
                    polling_active=False,
                    slot_released=True,
                )
                send_api_precheck_log(
                    telegram_user_id=telegram_user_id,
                    telegram_username=telegram_username,
                    verify_type=verify_type,
                    reason=precheck.reason,
                    github_username=precheck.github_username,
                )
                return

        # Update task dengan info dari precheck
        github_username = precheck.github_username or ""
        task_update(
            task_id,
            github_username=sanitize_username(github_username),
            github_username_raw=github_username,
            github_name=precheck.github_name,
            github_email=precheck.github_email,
            github_2fa=precheck.has_2fa,
            github_billing=precheck.has_billing,
            github_age_days=precheck.age_days,
            school_name=precheck.school_name,
        )

        # Step 2: Wait for user confirmation (if required)
        if require_confirmation:
            school_code = ""
            if precheck.school_profile is not None:
                school_code = str(getattr(precheck.school_profile, "code", "") or "").strip().lower()

            task_add_log(
                task_id, "Click Continue to start verification, or Cancel to stop."
            )
            task_update(
                task_id,
                status="awaiting_confirm",
                profile={
                    "github_username": sanitize_username(github_username),
                    "email": precheck.github_email or "N/A",
                    "github_username_raw": github_username,
                    "github_email_raw": precheck.github_email or "",
                    "github_name": precheck.github_name or "",
                    "has_2fa": precheck.has_2fa,
                    "has_billing": precheck.has_billing,
                    "age_days": precheck.age_days,
                    "school_code": school_code,
                    "school_name": precheck.school_name or "",
                    "criteria_ok": precheck.has_2fa and precheck.age_days >= 3,
                },
            )
            return  # Stop here, wait for user to click Continue

        # Step 3: User confirmed → Deduct credit BEFORE submit
        deduct_success, deduct_msg = verification_core.deduct_credits_before_submit(ctx)
        if not deduct_success:
            task_add_log(task_id, f"[ERROR] {deduct_msg}")
            task_update(
                task_id,
                status="credit_deduction_failed",
                application_submitted=False,
                polling_active=False,
                slot_released=True,
            )
            send_api_precheck_log(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                verify_type=verify_type,
                reason=deduct_msg,
                github_username=github_username,
            )
            return

        # Step 4: Execute verification
        result = verification_core.execute_verification(ctx, precheck)

        # Update task dengan document
        if result.document_base64:
            task_update(task_id, document_base64=result.document_base64)

        # Step 5: Handle result
        if not result.success:
            # Failed or rejected
            if result.status == "rejected":
                # Pasti gagal → refund credit
                verification_core.refund_credits_on_certain_failure(ctx, result)
                task_update(
                    task_id,
                    status="rejected",
                    application_submitted=False,
                    polling_active=False,
                    slot_released=True,
                )
            elif result.status == "submit_uncertain":
                # Uncertain → TIDAK refund, owner manual check
                task_add_log(
                    task_id,
                    "[WARNING] Submit uncertain - application may or may not have been submitted. "
                    "Owner needs to manually check GitHub. Credit NOT refunded."
                )
                task_update(
                    task_id,
                    status="submit_uncertain",
                    application_submitted=False,
                    polling_active=False,
                    slot_released=True,
                )
            else:
                # Other failure
                task_update(
                    task_id,
                    status="rejected",
                    application_submitted=False,
                    polling_active=False,
                    slot_released=True,
                )

            # Send log
            send_bot_style_verify_log(
                telegram_user_id=telegram_user_id,
                telegram_username=telegram_username,
                github_username=github_username,
                github_email=precheck.github_email,
                github_name=precheck.github_name,
                github_2fa=precheck.has_2fa,
                github_billing=precheck.has_billing,
                github_age_days=precheck.age_days,
                verify_type=verify_type,
                status=result.status,
                details=result.message,
                school_name=precheck.school_name,
                status_full_text=result.status_full_text,
                doc_base64=result.document_base64,
            )
            return

        # Success! (approved or pending)
        submitted_at_text = result.submitted_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if result.status == "approved":
            task_add_log(task_id, "Verification approved!")
            task_update(
                task_id,
                status="approved",
                polling_active=False,
                slot_released=True,
                application_submitted=True,
                submitted_at=submitted_at_text,
                status_full_text=result.status_full_text,
            )
        else:  # pending
            task_add_log(task_id, "Application submitted and waiting for review.")
            pending_since = now_ts()
            task_update(
                task_id,
                status="pending",
                pending_since=pending_since,
                polling_active=True,
                slot_released=False,
                application_submitted=True,
                submitted_at=submitted_at_text,
                status_full_text=result.status_full_text,
            )
            send_api_queue_log(
                f"Web verify entered pending review for {github_username}"
            )

        # Send log
        send_bot_style_verify_log(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            github_username=github_username,
            github_email=precheck.github_email,
            github_name=precheck.github_name,
            github_2fa=precheck.has_2fa,
            github_billing=precheck.has_billing,
            github_age_days=precheck.age_days,
            verify_type=verify_type,
            status=result.status,
            details=(
                "Approved by GitHub"
                if result.status == "approved"
                else "Application submitted and waiting for review"
            ),
            school_name=precheck.school_name,
            submitted_at=submitted_at_text,
            status_full_text=result.status_full_text,
            doc_base64=result.document_base64,
        )

        # Start poller if pending
        if result.status == "pending":
            poller = threading.Thread(
                target=run_pending_status_poller,
                args=(
                    task_id,
                    cookies_raw,
                    telegram_user_id,
                    telegram_username,
                    verify_type,
                    github_username,
                    credit_cost,
                    is_owner,
                ),
                daemon=True,
            )
            poller.start()

    except Exception as exc:
        task_add_log(task_id, f"[ERROR] Unexpected failure: {exc}")
        task_update(
            task_id,
            status="rejected",
            application_submitted=False,
            polling_active=False,
            slot_released=True,
        )
        send_bot_style_verify_log(
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
            verify_type=verify_type,
            status="rejected",
            details=f"Runtime error: {exc}",
            status_full_text=str(exc),
        )


refresh_school_mode_overrides()
load_persisted_tasks()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


@app.get("/api/schools/list")
def list_schools():
    """
    List available schools for verification (owner only).
    
    Query params:
        - type: "student" or "teacher"
        - telegram_user_id: user ID (must be owner)
    
    Returns:
        {
            "schools": [
                {"id": int, "name": str, "type": str},
                ...
            ]
        }
    """
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get parameters
    verify_type = request.args.get("type", "student").strip().lower()
    telegram_user_id_raw = request.args.get("telegram_user_id")
    
    if verify_type not in {"student", "teacher"}:
        verify_type = "student"
    
    # Check if user is owner
    try:
        telegram_user_id = int(telegram_user_id_raw) if telegram_user_id_raw else 0
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid telegram_user_id"}), 400
    
    if telegram_user_id != OWNER_ID:
        return jsonify({"error": "Only owner can list schools"}), 403
    
    # Get school profiles
    try:
        refresh_school_mode_overrides()
        all_schools = get_school_profiles()
        
        schools_list = []
        for school in all_schools:
            schools_list.append({
                "id": school.code,
                "code": school.code,
                "name": school.name,
                "mode": school.mode,
                "type": verify_type,
                "address": getattr(school, "address", ""),
            })
        
        return jsonify({"schools": schools_list})
    
    except Exception as exc:
        return jsonify({"error": f"Failed to fetch schools: {exc}"}), 500


@app.post("/api/verify/start")
def start_verify():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    telegram_user_id_raw = data.get("telegram_user_id")
    telegram_username = data.get("telegram_username")
    cookies = data.get("cookies")
    verify_type = (data.get("verify_type") or "student").strip().lower()
    school_id = data.get("school_id")  # Optional: school ID untuk owner

    if verify_type not in {"student", "teacher"}:
        verify_type = "student"

    if not cookies or telegram_user_id_raw is None:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        telegram_user_id = int(telegram_user_id_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid telegram_user_id"}), 400

    if telegram_user_id != OWNER_ID and is_verify_maintenance_active():
        return (
            jsonify(
                {
                    "success": False,
                    "error": MAINTENANCE_ERROR_TEXT,
                    "maintenance_mode": True,
                }
            ),
            503,
        )

    # Ensure user record exists for consistent credit checks.
    get_or_create_user(telegram_user_id)

    if telegram_user_id != OWNER_ID:
        is_banned, ban_reason = get_ban_state(telegram_user_id)
        if is_banned:
            return build_banned_response(ban_reason)

    settings = get_verify_settings()
    queue_limit = int(settings.get("queue_limit", 2))
    task_id = secrets.token_hex(8)
    started = now_ts()
    queue_block_response = None
    snapshot = None

    with task_lock:
        now_value = now_ts()
        active_slots = count_active_non_owner_queue_slots(
            [clone_task_snapshot(t) for t in verification_tasks.values()],
            now_value,
        )

        if telegram_user_id != OWNER_ID and active_slots >= queue_limit:
            queue_block_response = (
                jsonify(
                    {
                        "success": False,
                        "error": f"Queue is full ({active_slots}/{queue_limit}). Please wait.",
                        "queue_full": True,
                    }
                ),
                429,
            )
        else:
            verification_tasks[task_id] = {
                "id": task_id,
                "telegram_user_id": telegram_user_id,
                "telegram_username": telegram_username,
                "verify_type": verify_type,
                "cookies_raw": cookies,
                "school_id": school_id,  # Store school_id untuk pass ke run_verify_background
                "github_username": "Waiting...",
                "status": "pending",
                "pending_since": started,
                "slot_released": False,
                "polling_active": False,
                "application_submitted": False,
                "logs": ["[INIT] Verification job created."],
                "started_at": started,
                "updated_at": started,
            }
            snapshot = clone_task_snapshot(verification_tasks[task_id])

    if queue_block_response is not None:
        return queue_block_response

    if snapshot is None:
        return jsonify({"success": False, "error": "Failed to create verification task"}), 500

    persist_task_snapshot(snapshot)

    worker = threading.Thread(
        target=run_verify_background,
        args=(
            task_id,
            cookies,
            telegram_user_id,
            telegram_username,
            verify_type,
            WEB_REQUIRE_CONFIRMATION,
        ),
        daemon=True,
    )
    worker.start()

    return jsonify({"success": True, "task_id": task_id, "status": "pending"})


@app.post("/api/verify/continue/<task_id>")
def continue_verify(task_id: str):
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    with task_lock:
        task = verification_tasks.get(task_id)
        if not task:
            persisted = get_verify_task_status(task_id)
            if persisted:
                persisted["id"] = task_id
                verification_tasks[task_id] = persisted
                task = persisted
        if not task:
            return jsonify({"success": False, "error": "Task not found"}), 404

        current_status = str(task.get("status") or "none")
        if current_status != "awaiting_confirm":
            if current_status in {
                "pending",
                "approved",
                "rejected",
                "cancelled",
                "precheck_failed",
                "session_expired",
                "timeout",
            }:
                return jsonify(
                    {
                        "success": True,
                        "task_id": task_id,
                        "status": current_status,
                        "already_started": True,
                    }
                )
            return jsonify(
                {
                    "success": False,
                    "error": f"Task is not awaiting confirmation ({current_status})",
                }
            ), 400

        cookies = task.get("cookies_raw")
        telegram_user_id = int(task.get("telegram_user_id"))
        telegram_username = task.get("telegram_username")
        verify_type = task.get("verify_type", "student")

        if telegram_user_id != OWNER_ID and is_verify_maintenance_active():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": MAINTENANCE_ERROR_TEXT,
                        "maintenance_mode": True,
                    }
                ),
                503,
            )

        if telegram_user_id != OWNER_ID:
            is_banned, ban_reason = get_ban_state(telegram_user_id)
            if is_banned:
                return build_banned_response(ban_reason)

        task["status"] = "pending"
        task["pending_since"] = now_ts()
        task["slot_released"] = False
        task["polling_active"] = False
        task["application_submitted"] = False
        task.setdefault("logs", []).append("[ACTION] Continue requested by user.")
        task["updated_at"] = now_ts()
        snapshot = clone_task_snapshot(task)

    persist_task_snapshot(snapshot)

    worker = threading.Thread(
        target=run_verify_background,
        args=(
            task_id,
            cookies,
            telegram_user_id,
            telegram_username,
            verify_type,
            False,
        ),
        daemon=True,
    )
    worker.start()

    return jsonify({"success": True, "task_id": task_id, "status": "pending"})


@app.post("/api/verify/cancel/<task_id>")
def cancel_verify(task_id: str):
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    with task_lock:
        task = verification_tasks.get(task_id)
        if not task:
            persisted = get_verify_task_status(task_id)
            if persisted:
                persisted["id"] = task_id
                verification_tasks[task_id] = persisted
                task = persisted
        if not task:
            return jsonify({"success": False, "error": "Task not found"}), 404
        was_submitted = bool(task.get("application_submitted", False))
        task.setdefault("logs", []).append("[ACTION] Verification canceled by user.")
        task["status"] = "cancelled"
        task["updated_at"] = now_ts()
        task_telegram_user_id = int(task.get("telegram_user_id") or 0)
        task_telegram_username = task.get("telegram_username")
        task_verify_type = str(task.get("verify_type") or "student")
        task_github_username = task.get("github_username")
        snapshot = clone_task_snapshot(task)

    persist_task_snapshot(snapshot)
    if task_telegram_user_id:
        cancel_reason = (
            "Monitoring canceled by user after submission. Credits are not refunded."
            if was_submitted
            else "Verification canceled by user before submit."
        )
        send_api_precheck_log(
            telegram_user_id=task_telegram_user_id,
            verify_type=task_verify_type,
            reason=cancel_reason,
            telegram_username=task_telegram_username,
            github_username=task_github_username,
        )

    return jsonify(
        {
            "success": True,
            "task_id": task_id,
            "status": "cancelled",
            "credit_charged": bool(was_submitted),
        }
    )


@app.post("/api/verify/resend_cookies/<task_id>")
def resend_cookies(task_id: str):
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    cookies = str(data.get("cookies") or "").strip()
    if not cookies:
        return jsonify({"success": False, "error": "Cookies are required"}), 400

    with task_lock:
        task = verification_tasks.get(task_id)
        if not task:
            persisted = get_verify_task_status(task_id)
            if persisted:
                persisted["id"] = task_id
                verification_tasks[task_id] = persisted
                task = persisted
        if not task:
            return jsonify({"success": False, "error": "Task not found"}), 404

        if not bool(task.get("application_submitted", False)):
            return jsonify(
                {"success": False, "error": "Application not submitted yet"}
            ), 400

        status_now = str(task.get("status") or "").strip().lower()
        if status_now not in {"session_expired", "pending"}:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Task is not resumable with cookies ({status_now})",
                    }
                ),
                400,
            )

        if status_now == "pending" and bool(task.get("polling_active", False)):
            return jsonify({"success": False, "error": "Poller is already active"}), 400

        expected_username = str(
            task.get("github_username_raw") or task.get("github_username") or ""
        ).strip()
        expected_email = str(task.get("github_email") or "").strip()

    try:
        gh = GitHubSession(parse_cookies(cookies))
        uinfo = gh.get_user_info()
    except Exception as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Unable to validate cookies: {exc}",
                }
            ),
            400,
        )

    if not uinfo:
        return jsonify(
            {"success": False, "error": "Cookies are invalid or expired"}
        ), 400

    incoming_username = str(uinfo.get("username") or "").strip()
    incoming_email = str(uinfo.get("email") or "").strip()
    if (
        expected_email
        and incoming_email
        and expected_email.lower() != incoming_email.lower()
    ):
        return (
            jsonify(
                {
                    "success": False,
                    "error": (
                        "Cookie account mismatch. "
                        f"Expected email: {expected_email}, got: {incoming_email}"
                    ),
                }
            ),
            400,
        )

    with task_lock:
        task = verification_tasks.get(task_id)
        if not task:
            persisted = get_verify_task_status(task_id)
            if persisted:
                persisted["id"] = task_id
                verification_tasks[task_id] = persisted
                task = persisted
        if not task:
            return jsonify({"success": False, "error": "Task not found"}), 404

        status_now = str(task.get("status") or "").strip().lower()
        if status_now not in {"session_expired", "pending"}:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Task is not resumable with cookies ({status_now})",
                    }
                ),
                400,
            )
        if status_now == "pending" and bool(task.get("polling_active", False)):
            return jsonify({"success": False, "error": "Poller is already active"}), 400

        task["cookies_raw"] = cookies
        task["status"] = "pending"
        task["pending_since"] = now_ts()
        task["polling_active"] = True
        task["slot_released"] = False
        task.setdefault("logs", []).append(
            "[ACTION] New cookies received from web. Poller resumed."
        )
        task["github_username"] = sanitize_username(
            incoming_username or expected_username
        )
        task["github_username_raw"] = incoming_username or expected_username
        task["github_email"] = incoming_email or expected_email
        task["updated_at"] = now_ts()

        telegram_user_id = int(task.get("telegram_user_id") or 0)
        telegram_username = task.get("telegram_username")
        verify_type = str(task.get("verify_type") or "student")
        if telegram_user_id != OWNER_ID and is_verify_maintenance_active():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": MAINTENANCE_ERROR_TEXT,
                        "maintenance_mode": True,
                    }
                ),
                503,
            )
        if telegram_user_id != OWNER_ID:
            is_banned, ban_reason = get_ban_state(telegram_user_id)
            if is_banned:
                return build_banned_response(ban_reason)
        github_username = str(
            task.get("github_username_raw") or task.get("github_username") or "N/A"
        )
        is_owner = telegram_user_id == OWNER_ID
        credit_cost = get_verify_credit_cost(verify_type)
        snapshot = clone_task_snapshot(task)

    persist_task_snapshot(snapshot)

    poller = threading.Thread(
        target=run_pending_status_poller,
        args=(
            task_id,
            cookies,
            telegram_user_id,
            telegram_username,
            verify_type,
            github_username,
            credit_cost,
            is_owner,
        ),
        daemon=True,
    )
    poller.start()

    return jsonify({"success": True, "task_id": task_id, "status": "pending"})


@app.get("/api/verify/logs/<task_id>")
def verify_logs(task_id: str):
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    task = get_verify_task_status(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404

    logs = list(task.get("logs", []))
    status, indicator = get_visual_status(task)
    github_username = task.get("github_username", "Waiting...")
    github_username_raw = task.get("github_username_raw") or github_username
    github_email = task.get("github_email") or "N/A"
    profile = task.get("profile")

    return jsonify(
        {
            "success": True,
            "task_id": task_id,
            "status": status,
            "indicator": indicator,
            "github_username": github_username,
            "github_username_raw": github_username_raw,
            "github_email": github_email,
            "profile": profile,
            "logs": logs,
        }
    )


@app.get("/api/user/<int:user_id>")
def get_user_info(user_id: int):
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    settings = get_verify_settings()
    maintenance_mode = is_verify_maintenance_active()
    db_user = get_user(user_id)
    is_owner = user_id == OWNER_ID

    if not db_user:
        db_user = {
            "credits": 0,
            "total_invites": 0,
            "last_checkin": None,
        }

    if is_owner:
        credits_value = "Unlimited"
        used_today = 0
        max_limit = 0
        remaining = "Unlimited"
        daily_display = "Unlimited"
    else:
        credits_value = int(db_user.get("credits", 0))
        _, used_today, max_limit = check_daily_limit(user_id)
        if max_limit == 0:
            remaining = "Unlimited"
            daily_display = f"{used_today} / Unlimited"
        else:
            remaining = max(0, max_limit - used_today)
            daily_display = f"{used_today} / {max_limit}"

    is_banned = bool(db_user.get("is_banned", 0)) if not is_owner else False
    ban_reason = str(db_user.get("ban_reason") or "").strip()

    return jsonify(
        {
            "success": True,
            "data": {
                "is_owner": is_owner,
                "is_banned": is_banned,
                "ban_reason": ban_reason,
                "credits": credits_value,
                "credits_raw": int(db_user.get("credits", 0)),
                "total_invites": int(db_user.get("total_invites", 0)),
                "last_checkin": db_user.get("last_checkin"),
                "groups_joined": int(db_user.get("groups_joined", 0)),
                "math_solved": int(db_user.get("math_solved", 0)),
                "daily_limit": {
                    "used": used_today,
                    "max": max_limit,
                    "remaining": remaining,
                    "display": daily_display,
                },
                "verify": {
                    "student_enabled": bool(
                        settings.get("student_web", settings.get("student", True))
                    ),
                    "teacher_enabled": bool(
                        settings.get("teacher_web", settings.get("teacher", True))
                    ),
                    "maintenance_mode": maintenance_mode,
                    "blocked_by_maintenance": bool(maintenance_mode and not is_owner),
                    "student_credit_cost": int(
                        settings.get(
                            "student_credit_cost", get_verify_credit_cost("student")
                        )
                    ),
                    "teacher_credit_cost": int(
                        settings.get(
                            "teacher_credit_cost", get_verify_credit_cost("teacher")
                        )
                    ),
                },
            },
        }
    )


@app.get("/api/verify/status")
def global_status():
    if not check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    # Avoid unbounded reads; status UI only needs recent snapshots.
    try:
        all_tasks = get_verify_task_statuses(limit=300)
    except sqlite3.OperationalError as exc:
        if not is_disk_full_error(exc):
            raise

        settings = get_verify_settings()
        queue_limit = int(settings.get("queue_limit", 2))
        return jsonify(
            {
                "success": True,
                "maintenance_mode": is_verify_maintenance_active(),
                "tasks": [],
                "stats": {
                    "success_rate": 0,
                    "total_processed": 0,
                    "queue_active": 0,
                    "queue_limit": queue_limit,
                },
                "warning": "storage_full_fallback",
            }
        )

    settings = get_verify_settings()
    queue_limit = int(settings.get("queue_limit", 2))

    sorted_tasks = sorted(all_tasks, key=lambda x: x.get("started_at", 0), reverse=True)
    recent_tasks = []
    now = now_ts()

    for task in sorted_tasks:
        if not bool(task.get("application_submitted", False)):
            continue
        status, indicator = get_visual_status(task, now)
        item = {
            "id": task.get("id"),
            "telegram_user_id": task.get("telegram_user_id"),
            "github_username": task.get("github_username", "Waiting..."),
            "started_at": task.get("started_at", 0),
            "status": status,
            "indicator": indicator,
            "polling_active": bool(task.get("polling_active", False)),
        }
        recent_tasks.append(item)
        if len(recent_tasks) >= 100:
            break

    approved_count = sum(
        1
        for t in all_tasks
        if bool(t.get("application_submitted", False)) and t.get("status") == "approved"
    )
    total_finished = sum(
        1
        for t in all_tasks
        if bool(t.get("application_submitted", False))
        and t.get("status") in {"approved", "rejected"}
    )
    queue_active = count_active_non_owner_queue_slots(all_tasks, now)
    success_rate = (
        round((approved_count / total_finished * 100), 2) if total_finished > 0 else 0
    )

    return jsonify(
        {
            "success": True,
            "maintenance_mode": is_verify_maintenance_active(),
            "tasks": recent_tasks,
            "stats": {
                "success_rate": success_rate,
                "total_processed": total_finished,
                "queue_active": queue_active,
                "queue_limit": queue_limit,
            },
        }
    )


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    ptero_port = os.getenv("SERVER_PORT")
    port_env = os.getenv("PORT")

    if ptero_port:
        port = int(ptero_port)
    elif port_env:
        port = int(port_env)
    else:
        port = 5000

    app.run(host=host, port=port)

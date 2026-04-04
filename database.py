#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 Database Module — SQLite for user data, credits, referrals, check-ins
"""

import sqlite3
import os
import json
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.db")
VERIFY_TASK_STATUS_MAX_ROWS = 500


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            language TEXT DEFAULT 'en',
            credits INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT 0,
            total_invites INTEGER DEFAULT 0,
            tos_accepted INTEGER DEFAULT 0,
            groups_joined INTEGER DEFAULT 0,
            created_at TEXT DEFAULT '',
            last_checkin TEXT DEFAULT '',
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT DEFAULT '',
            math_solved INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            credited INTEGER DEFAULT 0,
            created_at TEXT DEFAULT '',
            UNIQUE(referred_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS verify_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            github_username TEXT DEFAULT '',
            verify_type TEXT DEFAULT 'student',
            status TEXT DEFAULT 'pending',
            credits_used INTEGER DEFAULT 1,
            created_at TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_verify_counts (
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_verify_bonus (
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            bonus INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS verify_task_status (
            task_id TEXT PRIMARY KEY,
            telegram_user_id INTEGER DEFAULT 0,
            telegram_username TEXT DEFAULT '',
            verify_type TEXT DEFAULT 'student',
            cookies_raw TEXT DEFAULT '',
            github_username TEXT DEFAULT 'Waiting...',
            status TEXT DEFAULT 'pending',
            pending_since REAL DEFAULT 0,
            slot_released INTEGER DEFAULT 0,
            polling_active INTEGER DEFAULT 0,
            application_submitted INTEGER DEFAULT 0,
            started_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0,
            document_base64 TEXT DEFAULT '',
            profile_json TEXT DEFAULT '',
            logs_json TEXT DEFAULT '[]'
        )
    """)

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS topup_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            telegram_username TEXT DEFAULT '',
            reff_id TEXT DEFAULT '',
            kode_deposit TEXT DEFAULT '',
            credit_amount INTEGER DEFAULT 0,
            nominal INTEGER DEFAULT 0,
            fee INTEGER DEFAULT 0,
            jumlah_transfer INTEGER DEFAULT 0,
            qr_url TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            provider_status TEXT DEFAULT 'Pending',
            created_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0,
            expires_at REAL DEFAULT 0,
            finished_at REAL DEFAULT 0,
            credited INTEGER DEFAULT 0,
            last_check_at REAL DEFAULT 0,
            last_error TEXT DEFAULT '',
            message_chat_id INTEGER DEFAULT 0,
            message_id INTEGER DEFAULT 0
        )
        """
    )

    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topup_transactions_user_status
        ON topup_transactions (user_id, status, created_at DESC)
        """
    )
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topup_transactions_kode
        ON topup_transactions (kode_deposit)
        """
    )

    # Backward-compatible migration for existing databases.
    try:
        c.execute(
            "ALTER TABLE verify_task_status ADD COLUMN document_base64 TEXT DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass

    # Ensure persisted indicator rows never exceed retention target.
    # Prioritize keeping rows that were actually submitted to GitHub.
    c.execute(
        """
        DELETE FROM verify_task_status
        WHERE task_id NOT IN (
            SELECT task_id
            FROM verify_task_status
            ORDER BY application_submitted DESC, updated_at DESC, task_id DESC
            LIMIT ?
        )
        """,
        (VERIFY_TASK_STATUS_MAX_ROWS,),
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value, updated_at)
        VALUES ('verify_student_enabled', '1', ?)
        """,
        (now,),
    )
    c.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value, updated_at)
        VALUES ('verify_teacher_enabled', '1', ?)
        """,
        (now,),
    )
    c.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value, updated_at)
        VALUES ('daily_verify_limit', '0', ?)
        """,
        (now,),
    )
    c.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value, updated_at)
        VALUES ('verify_concurrent_limit', '2', ?)
        """,
        (now,),
    )
    c.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value, updated_at)
        VALUES ('db_backup_interval_minutes', '10', ?)
        """,
        (now,),
    )
    c.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value, updated_at)
        VALUES ('verify_student_credit_cost', '1', ?)
        """,
        (now,),
    )
    c.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value, updated_at)
        VALUES ('verify_teacher_credit_cost', '1', ?)
        """,
        (now,),
    )
    c.execute(
        """
        INSERT OR IGNORE INTO app_settings (key, value, updated_at)
        VALUES ('verify_maintenance_mode', '0', ?)
        """,
        (now,),
    )

    try:
        c.execute("ALTER TABLE users ADD COLUMN math_solved INTEGER DEFAULT 0")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT DEFAULT ''")
    except Exception:
        pass

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════
#  User Management
# ═══════════════════════════════════════════


def get_user(user_id: int) -> dict | None:
    """Get user data"""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def create_user(
    user_id: int,
    username: str = "",
    first_name: str = "",
    language: str = "en",
    initial_credits: int = 0,
):
    """Create new user"""
    conn = get_db()
    conn.execute(
        """
        INSERT OR IGNORE INTO users (user_id, username, first_name, language, credits, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            user_id,
            username,
            first_name,
            language,
            initial_credits,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def update_user(user_id: int, **kwargs):
    """Update user fields"""
    if not kwargs:
        return
    conn = get_db()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    conn.execute(f"UPDATE users SET {sets} WHERE user_id = ?", values)
    conn.commit()
    conn.close()


def get_or_create_user(
    user_id: int,
    username: str = "",
    first_name: str = "",
    language: str = "en",
    initial_credits: int = 0,
) -> dict:
    """Get existing user or create new one"""
    user = get_user(user_id)
    if not user:
        create_user(user_id, username, first_name, language, initial_credits)
        user = get_user(user_id)
    else:
        # Update username/first_name if changed
        updates = {}
        if username and username != user.get("username"):
            updates["username"] = username
        if first_name and first_name != user.get("first_name"):
            updates["first_name"] = first_name
        if updates:
            update_user(user_id, **updates)
            user.update(updates)
    return user if user is not None else {}


# ═══════════════════════════════════════════
#  Credits
# ═══════════════════════════════════════════


def add_credits(user_id: int, amount: int):
    """Add credits to user"""
    conn = get_db()
    conn.execute(
        "UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id)
    )
    conn.commit()
    conn.close()


def deduct_credits(user_id: int, amount: int) -> bool:
    """Deduct credits, return True if successful"""
    user = get_user(user_id)
    if not user or user["credits"] < amount:
        return False
    conn = get_db()
    conn.execute(
        "UPDATE users SET credits = credits - ? WHERE user_id = ?", (amount, user_id)
    )
    conn.commit()
    conn.close()
    return True


def get_credits(user_id: int) -> int:
    """Get user credits"""
    user = get_user(user_id)
    return user["credits"] if user else 0


# ═══════════════════════════════════════════
#  Credit Top Up (QRIS)
# ═══════════════════════════════════════════


def _topup_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": int(row["id"] or 0),
        "user_id": int(row["user_id"] or 0),
        "telegram_username": str(row["telegram_username"] or ""),
        "reff_id": str(row["reff_id"] or ""),
        "kode_deposit": str(row["kode_deposit"] or ""),
        "credit_amount": int(row["credit_amount"] or 0),
        "nominal": int(row["nominal"] or 0),
        "fee": int(row["fee"] or 0),
        "jumlah_transfer": int(row["jumlah_transfer"] or 0),
        "qr_url": str(row["qr_url"] or ""),
        "status": str(row["status"] or "pending"),
        "provider_status": str(row["provider_status"] or "Pending"),
        "created_at": float(row["created_at"] or 0),
        "updated_at": float(row["updated_at"] or 0),
        "expires_at": float(row["expires_at"] or 0),
        "finished_at": float(row["finished_at"] or 0),
        "credited": int(row["credited"] or 0),
        "last_check_at": float(row["last_check_at"] or 0),
        "last_error": str(row["last_error"] or ""),
        "message_chat_id": int(row["message_chat_id"] or 0),
        "message_id": int(row["message_id"] or 0),
    }


def create_topup_transaction(
    user_id: int,
    telegram_username: str,
    reff_id: str,
    credit_amount: int,
    nominal: int,
    status: str = "pending",
    provider_status: str = "Pending",
    expires_at: float = 0,
) -> int:
    """Create a top-up transaction and return its ID."""
    now_ts = datetime.now().timestamp()
    conn = get_db()
    cur = conn.execute(
        """
        INSERT INTO topup_transactions (
            user_id,
            telegram_username,
            reff_id,
            credit_amount,
            nominal,
            status,
            provider_status,
            created_at,
            updated_at,
            expires_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(user_id),
            str(telegram_username or ""),
            str(reff_id or ""),
            max(0, int(credit_amount)),
            max(0, int(nominal)),
            str(status or "pending"),
            str(provider_status or "Pending"),
            float(now_ts),
            float(now_ts),
            float(expires_at or 0),
        ),
    )
    conn.commit()
    tx_id = int(cur.lastrowid or 0)
    conn.close()
    return tx_id


def get_topup_transaction(tx_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM topup_transactions WHERE id = ?",
        (int(tx_id),),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return _topup_row_to_dict(row)


def get_user_pending_topup(user_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute(
        """
        SELECT *
        FROM topup_transactions
        WHERE user_id = ? AND status = 'pending'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (int(user_id),),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return _topup_row_to_dict(row)


def list_pending_topup_transactions(limit: int = 100) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """
        SELECT *
        FROM topup_transactions
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (max(1, int(limit)),),
    ).fetchall()
    conn.close()
    return [_topup_row_to_dict(r) for r in rows]


def update_topup_transaction(tx_id: int, **kwargs):
    """Update top-up transaction fields by ID."""
    if not kwargs:
        return

    allowed = {
        "telegram_username",
        "reff_id",
        "kode_deposit",
        "credit_amount",
        "nominal",
        "fee",
        "jumlah_transfer",
        "qr_url",
        "status",
        "provider_status",
        "created_at",
        "updated_at",
        "expires_at",
        "finished_at",
        "credited",
        "last_check_at",
        "last_error",
        "message_chat_id",
        "message_id",
    }

    payload = {k: v for k, v in kwargs.items() if k in allowed}
    if not payload:
        return

    payload["updated_at"] = float(datetime.now().timestamp())
    sets = ", ".join(f"{k} = ?" for k in payload)
    values = list(payload.values()) + [int(tx_id)]

    conn = get_db()
    conn.execute(f"UPDATE topup_transactions SET {sets} WHERE id = ?", values)
    conn.commit()
    conn.close()


def close_pending_topup_transaction(
    tx_id: int,
    final_status: str,
    provider_status: str,
    last_error: str = "",
) -> dict | None:
    """Move a pending top-up transaction to final state once."""
    now_ts = float(datetime.now().timestamp())
    status_value = str(final_status or "failed").strip().lower()
    if status_value not in {"failed", "cancelled", "expired", "error"}:
        status_value = "failed"

    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM topup_transactions WHERE id = ?",
            (int(tx_id),),
        ).fetchone()
        if not row:
            conn.rollback()
            return None
        if str(row["status"] or "") != "pending":
            conn.rollback()
            return None

        conn.execute(
            """
            UPDATE topup_transactions
            SET
                status = ?,
                provider_status = ?,
                last_error = ?,
                finished_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                status_value,
                str(provider_status or "Error"),
                str(last_error or ""),
                now_ts,
                now_ts,
                int(tx_id),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return get_topup_transaction(tx_id)


def complete_pending_topup_success(tx_id: int) -> dict | None:
    """Finalize a pending top-up as success and credit user exactly once."""
    now_ts = float(datetime.now().timestamp())
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM topup_transactions WHERE id = ?",
            (int(tx_id),),
        ).fetchone()
        if not row:
            conn.rollback()
            return None
        if str(row["status"] or "") != "pending":
            conn.rollback()
            return None

        user_id = int(row["user_id"] or 0)
        credit_amount = max(0, int(row["credit_amount"] or 0))
        credited = int(row["credited"] or 0)

        if user_id <= 0:
            conn.rollback()
            return None

        if credited == 0 and credit_amount > 0:
            conn.execute(
                "UPDATE users SET credits = credits + ? WHERE user_id = ?",
                (credit_amount, user_id),
            )

        conn.execute(
            """
            UPDATE topup_transactions
            SET
                status = 'success',
                provider_status = 'Success',
                credited = 1,
                finished_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now_ts, now_ts, int(tx_id)),
        )

        user_row = conn.execute(
            "SELECT credits FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        total_credits = int(user_row["credits"] or 0) if user_row else 0
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    tx = get_topup_transaction(tx_id)
    if not tx:
        return None
    return {
        "transaction": tx,
        "total_credits": total_credits,
    }


def get_topup_cooldown_remaining(user_id: int, cooldown_seconds: int = 60) -> int:
    """Get remaining cooldown seconds after latest finalized top-up."""
    cooldown = max(0, int(cooldown_seconds))
    if cooldown == 0:
        return 0

    conn = get_db()
    row = conn.execute(
        """
        SELECT finished_at
        FROM topup_transactions
        WHERE user_id = ?
          AND status IN ('success', 'failed', 'cancelled', 'expired', 'error')
          AND finished_at > 0
        ORDER BY finished_at DESC
        LIMIT 1
        """,
        (int(user_id),),
    ).fetchone()
    conn.close()
    if not row:
        return 0

    finished_at = float(row["finished_at"] or 0)
    elapsed = int(datetime.now().timestamp() - finished_at)
    remaining = cooldown - elapsed
    return remaining if remaining > 0 else 0


# ═══════════════════════════════════════════
#  Referrals
# ═══════════════════════════════════════════


def record_pending_referral(referrer_id: int, referred_id: int) -> bool:
    """Record a pending referral without giving credits yet, return True if new"""
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO referrals (referrer_id, referred_id, credited, created_at)
            VALUES (?, ?, 0, ?)
        """,
            (referrer_id, referred_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True


def credit_pending_referral(referred_id: int, credit_amount: int = 1) -> int:
    """Find pending referral for referred_id and credit the referrer.
    Returns the referrer_id if successful, 0 if not applied.
    """
    conn = get_db()
    referrer_id = 0
    try:
        row = conn.execute(
            "SELECT referrer_id, credited FROM referrals WHERE referred_id = ?",
            (referred_id,),
        ).fetchone()
        if row and row["credited"] == 0:
            referrer_id = row["referrer_id"]
            conn.execute(
                "UPDATE referrals SET credited = 1 WHERE referred_id = ?",
                (referred_id,),
            )
            conn.execute(
                "UPDATE users SET credits = credits + ?, total_invites = total_invites + 1 WHERE user_id = ?",
                (credit_amount, referrer_id),
            )
            conn.execute(
                "UPDATE users SET referrer_id = ? WHERE user_id = ?",
                (referrer_id, referred_id),
            )
            conn.commit()
    except Exception as e:
        print(f"Error crediting referral: {e}")
    finally:
        conn.close()
    return referrer_id


def add_referral(referrer_id: int, referred_id: int, credit_amount: int = 1) -> bool:
    """Legacy function, no longer directly used for immediate credits."""
    return False


def get_total_invites(user_id: int) -> int:
    """Get total invites for user"""
    user = get_user(user_id)
    return user["total_invites"] if user else 0


# ═══════════════════════════════════════════
#  Daily Check-in
# ═══════════════════════════════════════════


def do_checkin(user_id: int, credit_amount: int = 1) -> tuple[bool, int]:
    """
    Do daily check-in. Returns (success, new_total_credits).
    success=False means already checked in within 24h.
    """
    user = get_user(user_id)
    if not user:
        return False, 0

    now = datetime.now()
    if user["last_checkin"]:
        try:
            last = datetime.strptime(user["last_checkin"], "%Y-%m-%d %H:%M:%S")
            if (now - last).total_seconds() < 86400:
                return False, user["credits"]
        except ValueError:
            pass  # Old format or empty

    conn = get_db()
    conn.execute(
        """
        UPDATE users SET credits = credits + ?, last_checkin = ? WHERE user_id = ?
    """,
        (credit_amount, now.strftime("%Y-%m-%d %H:%M:%S"), user_id),
    )
    conn.commit()
    conn.close()

    return True, user["credits"] + credit_amount


def get_checkin_info(user_id: int) -> tuple[bool, int]:
    """Returns (can_checkin, seconds_remaining)"""
    user = get_user(user_id)
    if not user or not user["last_checkin"]:
        return True, 0

    try:
        last = datetime.strptime(user["last_checkin"], "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - last
        remaining = 86400 - int(diff.total_seconds())
        if remaining > 0:
            return False, remaining
    except ValueError:
        pass

    return True, 0


# ═══════════════════════════════════════════
#  Verify Logs
# ═══════════════════════════════════════════


def add_verify_log(
    user_id: int,
    github_username: str,
    verify_type: str = "student",
    status: str = "pending",
    credits_used: int = 1,
):
    """Add verification log"""
    conn = get_db()
    conn.execute(
        """
        INSERT INTO verify_logs (user_id, github_username, verify_type, status, credits_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            user_id,
            github_username,
            verify_type,
            status,
            credits_used,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def update_verify_status(log_id: int, status: str):
    """Update verification status"""
    conn = get_db()
    conn.execute("UPDATE verify_logs SET status = ? WHERE id = ?", (status, log_id))
    conn.commit()
    conn.close()


def get_user_logs(user_id: int, limit: int = 10) -> list:
    """Get user's verification logs"""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT * FROM verify_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?
    """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dashboard_stats():
    """Get total users and daily total users (active)"""
    conn = get_db()
    c = conn.cursor()

    # Total users
    c.execute("SELECT COUNT(user_id) FROM users")
    total_users = c.fetchone()[0]

    # Daily users (joined today)
    today_str = datetime.now().strftime("%Y-%m-%d")
    c.execute(
        "SELECT COUNT(user_id) FROM users WHERE created_at LIKE ?", (f"{today_str}%",)
    )
    daily_users = c.fetchone()[0]

    conn.close()
    return total_users, daily_users


def get_all_user_ids(include_banned: bool = False) -> list[int]:
    """Get all registered user IDs for broadcast."""
    conn = get_db()
    if include_banned:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
    else:
        rows = conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
    conn.close()
    return [int(r["user_id"]) for r in rows]


# ═══════════════════════════════════════════
#  App Settings
# ═══════════════════════════════════════════


def get_setting(key: str, default: str = "") -> str:
    """Get app setting value by key"""
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    if not row:
        return default
    return str(row["value"])


def set_setting(key: str, value: str):
    """Set app setting value"""
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, value, now),
    )
    conn.commit()
    conn.close()


def get_verify_settings() -> dict:
    """Get verify feature flags + daily limit"""
    legacy_student = get_setting("verify_student_enabled", "1") == "1"
    legacy_teacher = get_setting("verify_teacher_enabled", "1") == "1"

    student_bot = (
        get_setting("verify_student_enabled_bot", "1" if legacy_student else "0") == "1"
    )
    student_web = (
        get_setting("verify_student_enabled_web", "1" if legacy_student else "0") == "1"
    )
    teacher_bot = (
        get_setting("verify_teacher_enabled_bot", "1" if legacy_teacher else "0") == "1"
    )
    teacher_web = (
        get_setting("verify_teacher_enabled_web", "1" if legacy_teacher else "0") == "1"
    )

    return {
        # Legacy compatibility keys kept for existing callers.
        "student": student_bot,
        "teacher": teacher_bot,
        "student_bot": student_bot,
        "student_web": student_web,
        "teacher_bot": teacher_bot,
        "teacher_web": teacher_web,
        "maintenance_mode": get_verify_maintenance_mode(),
        "daily_limit": int(get_setting("daily_verify_limit", "0")),
        "queue_limit": int(get_setting("verify_concurrent_limit", "2")),
        "backup_interval_minutes": int(get_setting("db_backup_interval_minutes", "10")),
        "student_credit_cost": int(get_setting("verify_student_credit_cost", "1")),
        "teacher_credit_cost": int(get_setting("verify_teacher_credit_cost", "1")),
    }


def set_verify_enabled(verify_type: str, enabled: bool, target: str = "both"):
    """Enable/disable student or teacher verification by target: bot|web|both."""
    verify_type = "student" if verify_type == "student" else "teacher"
    target = (target or "both").strip().lower()
    if target not in {"bot", "web", "both"}:
        target = "both"

    value = "1" if enabled else "0"

    if target in {"bot", "both"}:
        set_setting(f"verify_{verify_type}_enabled_bot", value)
    if target in {"web", "both"}:
        set_setting(f"verify_{verify_type}_enabled_web", value)

    # Keep legacy global key in sync for compatibility with older code.
    current = get_verify_settings()
    if verify_type == "student":
        legacy_on = current.get("student_bot", True) or current.get("student_web", True)
    else:
        legacy_on = current.get("teacher_bot", True) or current.get("teacher_web", True)

    set_setting(f"verify_{verify_type}_enabled", "1" if legacy_on else "0")


def get_verify_maintenance_mode() -> bool:
    """Get global maintenance flag for verify/web access (non-owner users)."""
    return get_setting("verify_maintenance_mode", "0") == "1"


def set_verify_maintenance_mode(enabled: bool):
    """Set global maintenance flag for verify/web access (non-owner users)."""
    set_setting("verify_maintenance_mode", "1" if enabled else "0")


# ═══════════════════════════════════════════
#  Daily Verify Limit
# ═══════════════════════════════════════════


def get_daily_verify_limit() -> int:
    """Get max daily verify per user (0 = unlimited)"""
    return int(get_setting("daily_verify_limit", "0"))


def set_daily_verify_limit(limit: int):
    """Set max daily verify per user (0 = unlimited)"""
    set_setting("daily_verify_limit", str(max(0, limit)))


def get_verify_concurrent_limit() -> int:
    """Get concurrent active verify limit for non-owner users."""
    value = int(get_setting("verify_concurrent_limit", "2"))
    return max(1, value)


def set_verify_concurrent_limit(limit: int):
    """Set concurrent active verify limit for non-owner users."""
    set_setting("verify_concurrent_limit", str(max(1, limit)))


def get_backup_interval_minutes() -> int:
    """Get scheduled database backup interval in minutes."""
    value = int(get_setting("db_backup_interval_minutes", "10"))
    return max(1, value)


def set_backup_interval_minutes(minutes: int):
    """Set scheduled database backup interval in minutes."""
    set_setting("db_backup_interval_minutes", str(max(1, minutes)))


def get_school_mode_override(school_code: str) -> str | None:
    """Get persisted school mode override (public/private), if any."""
    code = (school_code or "").strip().lower()
    if not code:
        return None

    value = get_setting(f"school_mode_{code}", "").strip().lower()
    if value in {"public", "private"}:
        return value
    return None


def set_school_mode_override(school_code: str, mode: str):
    """Persist school mode override (public/private)."""
    code = (school_code or "").strip().lower()
    mode_value = (mode or "").strip().lower()
    if not code:
        return
    if mode_value not in {"public", "private"}:
        return

    set_setting(f"school_mode_{code}", mode_value)


def get_all_school_mode_overrides() -> dict[str, str]:
    """Return all persisted school mode overrides keyed by school code."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT key, value
        FROM app_settings
        WHERE key LIKE 'school_mode_%'
        """
    ).fetchall()
    conn.close()

    result: dict[str, str] = {}
    for row in rows:
        key = str(row["key"])
        value = str(row["value"]).strip().lower()
        if value not in {"public", "private"}:
            continue
        code = key[len("school_mode_") :].strip().lower()
        if code:
            result[code] = value

    return result


def get_verify_credit_cost(verify_type: str) -> int:
    """Get credit cost for verify type (student/teacher)."""
    key = (
        "verify_student_credit_cost"
        if verify_type == "student"
        else "verify_teacher_credit_cost"
    )
    value = int(get_setting(key, "1"))
    return max(0, value)


def set_verify_credit_cost(verify_type: str, cost: int):
    """Set credit cost for verify type (student/teacher)."""
    key = (
        "verify_student_credit_cost"
        if verify_type == "student"
        else "verify_teacher_credit_cost"
    )
    set_setting(key, str(max(0, cost)))


def get_daily_verify_count(user_id: int) -> int:
    """Get how many verifications user has done today"""
    today = date.today().isoformat()
    conn = get_db()
    row = conn.execute(
        "SELECT count FROM daily_verify_counts WHERE user_id = ? AND date = ?",
        (user_id, today),
    ).fetchone()
    conn.close()
    return row["count"] if row else 0


def increment_daily_verify_count(user_id: int):
    """Increment today's verify count for user"""
    today = date.today().isoformat()
    conn = get_db()
    conn.execute(
        """
        INSERT INTO daily_verify_counts (user_id, date, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1
        """,
        (user_id, today),
    )
    conn.commit()
    conn.close()


def get_daily_verify_bonus(user_id: int) -> int:
    """Get today's extra verify allowance for user (owner grants)."""
    today = date.today().isoformat()
    conn = get_db()
    row = conn.execute(
        "SELECT bonus FROM daily_verify_bonus WHERE user_id = ? AND date = ?",
        (user_id, today),
    ).fetchone()
    conn.close()
    return max(0, int(row["bonus"])) if row else 0


def add_daily_verify_bonus(user_id: int, amount: int):
    """Add today's extra verify allowance for user."""
    if amount <= 0:
        return
    today = date.today().isoformat()
    conn = get_db()
    conn.execute(
        """
        INSERT INTO daily_verify_bonus (user_id, date, bonus)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET bonus = bonus + excluded.bonus
        """,
        (user_id, today, amount),
    )
    conn.commit()
    conn.close()


def check_daily_limit(user_id: int) -> tuple[bool, int, int]:
    """
    Check if user has hit daily verify limit.
    Returns (is_limited, used_today, max_limit).
    is_limited=False means user can still verify.
    """
    limit = get_daily_verify_limit()
    used = get_daily_verify_count(user_id)
    if limit == 0:  # 0 = unlimited
        return False, used, 0

    bonus = get_daily_verify_bonus(user_id)
    effective_limit = limit + bonus
    return used >= effective_limit, used, effective_limit


# ═══════════════════════════════════════════
#  Verify Task Status Persistence (Web/API)
# ═══════════════════════════════════════════


def _to_json(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return ""


def _from_json(value: str, default):
    text = (value or "").strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def upsert_verify_task_status(task: dict):
    """Insert/update persisted verification task state."""
    if not task:
        return

    task_id = str(task.get("id") or task.get("task_id") or "").strip()
    if not task_id:
        return

    conn = get_db()
    conn.execute(
        """
        INSERT INTO verify_task_status (
            task_id,
            telegram_user_id,
            telegram_username,
            verify_type,
            cookies_raw,
            github_username,
            status,
            pending_since,
            slot_released,
            polling_active,
            application_submitted,
            started_at,
            updated_at,
            document_base64,
            profile_json,
            logs_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
            telegram_user_id = excluded.telegram_user_id,
            telegram_username = excluded.telegram_username,
            verify_type = excluded.verify_type,
            cookies_raw = excluded.cookies_raw,
            github_username = excluded.github_username,
            status = excluded.status,
            pending_since = excluded.pending_since,
            slot_released = excluded.slot_released,
            polling_active = excluded.polling_active,
            application_submitted = excluded.application_submitted,
            started_at = excluded.started_at,
            updated_at = excluded.updated_at,
            document_base64 = excluded.document_base64,
            profile_json = excluded.profile_json,
            logs_json = excluded.logs_json
        """,
        (
            task_id,
            int(task.get("telegram_user_id") or 0),
            str(task.get("telegram_username") or ""),
            str(task.get("verify_type") or "student"),
            str(task.get("cookies_raw") or ""),
            str(task.get("github_username") or "Waiting..."),
            str(task.get("status") or "pending"),
            float(task.get("pending_since") or 0),
            1 if bool(task.get("slot_released", False)) else 0,
            1 if bool(task.get("polling_active", False)) else 0,
            1 if bool(task.get("application_submitted", False)) else 0,
            float(task.get("started_at") or 0),
            float(task.get("updated_at") or 0),
            str(task.get("document_base64") or ""),
            _to_json(task.get("profile")),
            _to_json(task.get("logs", [])),
        ),
    )

    # Keep only latest N status rows (global retention), while prioritizing
    # records that were really submitted so precheck failures do not evict
    # visible indicator history.
    conn.execute(
        """
        DELETE FROM verify_task_status
        WHERE task_id NOT IN (
            SELECT task_id
            FROM verify_task_status
            ORDER BY application_submitted DESC, updated_at DESC, task_id DESC
            LIMIT ?
        )
        """,
        (VERIFY_TASK_STATUS_MAX_ROWS,),
    )

    conn.commit()
    conn.close()


def _parse_verify_task_row(row: sqlite3.Row) -> dict:
    profile = _from_json(str(row["profile_json"] or ""), None)
    logs = _from_json(str(row["logs_json"] or ""), [])

    return {
        "id": str(row["task_id"]),
        "task_id": str(row["task_id"]),
        "telegram_user_id": int(row["telegram_user_id"] or 0),
        "telegram_username": str(row["telegram_username"] or ""),
        "verify_type": str(row["verify_type"] or "student"),
        "cookies_raw": str(row["cookies_raw"] or ""),
        "github_username": str(row["github_username"] or "Waiting..."),
        "status": str(row["status"] or "pending"),
        "pending_since": float(row["pending_since"] or 0),
        "slot_released": bool(row["slot_released"]),
        "polling_active": bool(row["polling_active"]),
        "application_submitted": bool(row["application_submitted"]),
        "started_at": float(row["started_at"] or 0),
        "updated_at": float(row["updated_at"] or 0),
        "document_base64": str(row["document_base64"] or ""),
        "profile": profile,
        "logs": logs if isinstance(logs, list) else [],
    }


def get_verify_task_status(task_id: str) -> dict | None:
    """Get one persisted verification task by task_id."""
    normalized = (task_id or "").strip()
    if not normalized:
        return None

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM verify_task_status WHERE task_id = ?",
        (normalized,),
    ).fetchone()
    conn.close()

    if not row:
        return None
    return _parse_verify_task_row(row)


def get_verify_task_statuses(limit: int = 200) -> list[dict]:
    """Get persisted verification task snapshots ordered by newest first."""
    conn = get_db()
    try:
        if limit and limit > 0:
            rows = conn.execute(
                """
                SELECT * FROM verify_task_status
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM verify_task_status
                ORDER BY updated_at DESC
                """
            ).fetchall()
    except sqlite3.OperationalError as exc:
        # On near-full disks, ORDER BY can fail when SQLite cannot allocate temp space.
        # Fallback to a bounded unordered read so status endpoint still responds.
        if "database or disk is full" not in str(exc).lower():
            conn.close()
            raise

        safe_limit = int(limit) if limit and int(limit) > 0 else 100
        try:
            rows = conn.execute(
                """
                SELECT * FROM verify_task_status
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
    finally:
        conn.close()

    return [_parse_verify_task_row(r) for r in rows]


def delete_verify_task_status(task_id: str) -> bool:
    """Delete one persisted verification task snapshot."""
    normalized = (task_id or "").strip()
    if not normalized:
        return False

    conn = get_db()
    cur = conn.execute(
        "DELETE FROM verify_task_status WHERE task_id = ?",
        (normalized,),
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# Initialize DB on import
init_db()

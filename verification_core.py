"""
╔══════════════════════════════════════════════════════════╗
║  Verification Core — Unified Verification Logic          ║
║  Shared by both Telegram Bot and Web API                 ║
╚══════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional

from database import (
    add_credits,
    add_verify_log,
    check_daily_limit,
    deduct_credits,
    get_all_school_mode_overrides,
    get_user,
    get_verify_credit_cost,
    get_verify_maintenance_mode,
    get_verify_settings,
    increment_daily_verify_count,
)
from github_session import (
    GitHubSession,
    apply_school_mode_overrides,
    create_id_card_base64,
    create_teacher_documents_base64,
    generate_student_data,
    generate_teacher_data,
    get_application_status_poll_interval,
    get_public_school_profiles,
    pick_random_public_school,
)


@dataclass
class VerificationContext:
    """Context object untuk menyimpan informasi verification."""
    user_id: int
    verify_type: str  # "student" or "teacher"
    cookies: dict[str, str]
    is_owner: bool = False
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    
    # Source: "web" atau "bot" (untuk check enable settings yang berbeda)
    source: str = "both"  # "web", "bot", or "both"
    
    # Pre-selected school profile (None = random pick)
    school_profile: Optional[Any] = None
    
    # Skip cookie validation jika sudah di-validate sebelumnya
    skip_cookie_validation: bool = False
    
    # Callback functions untuk logging/UI updates
    log_callback: Optional[Callable[[str], None]] = None
    progress_callback: Optional[Callable[[str, Any], None]] = None


@dataclass
class PreCheckResult:
    """Result dari pre-check validation."""
    success: bool
    reason: str = ""
    
    # Profile info (jika success)
    github_username: Optional[str] = None
    github_email: Optional[str] = None
    github_name: Optional[str] = None
    has_2fa: bool = False
    has_billing: bool = False
    age_days: int = 0
    school_profile: Optional[Any] = None
    school_name: Optional[str] = None
    
    # Full user info dari GitHub
    user_info: Optional[dict] = None


@dataclass
class VerificationResult:
    """Result dari verification process."""
    success: bool
    status: str  # "approved", "pending", "rejected", "failed"
    message: str = ""
    
    # Details
    github_username: Optional[str] = None
    school_name: Optional[str] = None
    submitted_at: Optional[str] = None
    credit_cost: int = 0
    
    # Generated documents
    document_base64: Optional[str] = None
    identity_data: Optional[Any] = None
    
    # Additional info
    status_full_text: Optional[str] = None
    reject_intro: Optional[str] = None
    reject_reasons: Optional[list[str]] = None


@dataclass
class PollingContext:
    """Context untuk polling application status."""
    user_id: int
    verify_type: str  # "student" or "teacher"
    cookies: dict[str, str]
    github_username: str
    is_owner: bool = False
    
    # Credit info untuk refund jika rejected
    charged_credits: int = 0
    
    # Profile info untuk logging
    telegram_username: Optional[str] = None
    telegram_first_name: Optional[str] = None
    github_email: Optional[str] = None
    github_name: Optional[str] = None
    github_2fa: Optional[bool] = None
    github_billing: Optional[bool] = None
    github_age_days: Optional[int] = None
    school_name: Optional[str] = None
    document_base64: Optional[str] = None
    submitted_at: Optional[str] = None
    
    # Callbacks untuk UI updates dan logging
    # on_tick_callback(elapsed_seconds) → untuk update UI elapsed time
    on_tick_callback: Optional[Callable[[int], None]] = None
    
    # on_completed_callback(status, app_status_dict) → ketika approved/rejected
    on_completed_callback: Optional[Callable[[str, dict], None]] = None
    
    # log_callback(message) → untuk logging pesan
    log_callback: Optional[Callable[[str], None]] = None
    
    # Max wait time (default 2 hours)
    max_wait_seconds: int = 7200


@dataclass
class PollingResult:
    """Result dari polling process."""
    final_status: str  # "approved", "rejected", "timeout", "session_expired", "error"
    elapsed_seconds: int
    app_status: Optional[dict] = None
    error_message: Optional[str] = None
    credits_refunded: int = 0


class VerificationCore:
    """Core verification logic yang bisa digunakan oleh bot dan API."""
    
    def __init__(self, owner_id: int):
        self.owner_id = owner_id
    
    def _is_owner(self, user_id: int) -> bool:
        return user_id == self.owner_id
    
    def _log(self, ctx: VerificationContext, message: str) -> None:
        """Helper untuk logging."""
        if ctx.log_callback:
            ctx.log_callback(message)
    
    def _update_progress(self, ctx: VerificationContext, stage: str, data: Any = None) -> None:
        """Helper untuk update progress."""
        if ctx.progress_callback:
            ctx.progress_callback(stage, data)
    
    def refresh_school_overrides(self) -> None:
        """Refresh school mode overrides dari database."""
        try:
            apply_school_mode_overrides(get_all_school_mode_overrides())
        except Exception:
            pass
    
    def precheck_verification(self, ctx: VerificationContext) -> PreCheckResult:
        """
        Pre-check validation sebelum verification.
        Returns PreCheckResult dengan success=True jika bisa lanjut.
        """
        self._log(ctx, "[0/4] Starting pre-check validation...")

        # 0. Maintenance gate (owner bypass)
        if not ctx.is_owner and get_verify_maintenance_mode():
            return PreCheckResult(
                success=False,
                reason="Verification is under maintenance. Please try again later.",
            )
        
        # 1. Check if verification type is enabled (berdasarkan source)
        settings = get_verify_settings()
        
        if ctx.source == "web":
            # Web: check student_web/teacher_web dulu, fallback ke student/teacher
            if ctx.verify_type == "student":
                is_enabled = settings.get("student_web", settings.get("student", True))
            else:
                is_enabled = settings.get("teacher_web", settings.get("teacher", True))
        else:
            # Bot atau both: check student/teacher biasa
            if ctx.verify_type == "student":
                is_enabled = settings.get("student", True)
            else:
                is_enabled = settings.get("teacher", True)
        
        if not ctx.is_owner and not is_enabled:
            return PreCheckResult(
                success=False,
                reason=f"{ctx.verify_type} verification is disabled by owner"
            )
        
        # 2. Validate cookies format (jika belum di-validate)
        if not ctx.skip_cookie_validation:
            required_keys = ("user_session", "_gh_sess", "_octo")
            if not any(k in ctx.cookies for k in required_keys):
                return PreCheckResult(
                    success=False,
                    reason="Invalid cookie format (missing required keys)"
                )
        
        # 3. Create GitHub session
        gh = GitHubSession(ctx.cookies)
        
        self._log(ctx, "[0/4] Fetching GitHub profile...")
        user_info = gh.get_user_info()
        
        if not user_info:
            return PreCheckResult(
                success=False,
                reason="Login failed. Cookie may be expired or invalid."
            )
        
        github_username = user_info.get("username", "")
        github_email = user_info.get("email", "") or f"{github_username}@gmail.com"
        github_name = user_info.get("name", "")
        has_2fa = bool(user_info.get("has_2fa", False))
        has_billing = bool(user_info.get("has_billing", False))
        age_days = int(user_info.get("age_days", 0))
        
        self._log(ctx, f"GitHub: {github_username}")
        self._log(ctx, f"Email: {github_email}")
        self._log(ctx, f"2FA: {'Enabled' if has_2fa else 'Disabled'}")
        self._log(ctx, f"Age: {age_days} days")
        
        # 4. Check existing application status
        self._log(ctx, "[0/4] Checking existing application status...")
        app_status = gh.check_application_status()
        current_status = str(app_status.get("status", "none") or "none").strip().lower()
        status_confident = bool(app_status.get("status_confident", False))
        
        if current_status in {"pending", "approved"}:
            pending_full = str(app_status.get("status_full_text") or "").lower()
            pending_has_evidence = bool(app_status.get("submitted_at")) or (
                "current pending application" in pending_full
                or "currently pending review" in pending_full
                or ("pending" in pending_full and "application" in pending_full)
            )
            
            should_block = (current_status == "approved" and status_confident) or (
                current_status == "pending"
                and status_confident
                and pending_has_evidence
            )
            
            if should_block:
                app_type = app_status.get("app_type", "Unknown")
                submitted_at = app_status.get("submitted_at", "recently")
                return PreCheckResult(
                    success=False,
                    reason=f"Existing application status: {current_status} ({app_type}, submitted {submitted_at})"
                )
            
            self._log(ctx, f"[0/4] Existing status ignored (low confidence): {current_status}")
        
        # 5. Check 2FA requirement
        if not has_2fa:
            return PreCheckResult(
                success=False,
                reason="2FA is not enabled on this GitHub account"
            )
        
        # 6. Check account age
        if age_days < 3:
            days_left = 3 - age_days
            return PreCheckResult(
                success=False,
                reason=f"Account too young ({age_days} days, wait {days_left} more day(s))"
            )
        
        # 7. Check daily limit (non-owner only)
        if not ctx.is_owner:
            is_limited, used_today, max_limit = check_daily_limit(ctx.user_id)
            if is_limited:
                return PreCheckResult(
                    success=False,
                    reason=f"Daily limit reached ({used_today}/{max_limit})"
                )
        
        # 8. Check credits (non-owner only)
        credit_cost = get_verify_credit_cost(ctx.verify_type)
        if not ctx.is_owner:
            db_user = get_user(ctx.user_id) or {}
            credits = int(db_user.get("credits", 0))
            if credits < credit_cost:
                return PreCheckResult(
                    success=False,
                    reason=f"Not enough credits ({credits}/{credit_cost})"
                )
        
        # 9. Get school profile (pre-selected atau random)
        if ctx.school_profile is not None:
            # Use pre-selected school (untuk bot owner yang bisa pilih)
            school_profile = ctx.school_profile
            school_name = getattr(school_profile, "name", "N/A")
            if ctx.is_owner:
                self._log(ctx, f"Using pre-selected school: {school_name}")
            else:
                self._log(ctx, "Using pre-selected school.")
        else:
            # Random pick dari public schools (untuk web atau bot user biasa)
            self.refresh_school_overrides()
            public_schools = get_public_school_profiles()
            if not public_schools:
                return PreCheckResult(
                    success=False,
                    reason="No public school is available. Ask owner to enable at least one public school."
                )
            
            school_profile = pick_random_public_school()
            if school_profile is None:
                return PreCheckResult(
                    success=False,
                    reason="No school profile is available"
                )
            
            school_name = getattr(school_profile, "name", "N/A")
            if ctx.is_owner:
                self._log(ctx, f"Randomly selected school: {school_name}")
            else:
                self._log(ctx, "Randomly selected school.")
        
        self._log(ctx, "[1/4] Pre-check completed successfully")
        
        return PreCheckResult(
            success=True,
            reason="All checks passed",
            github_username=github_username,
            github_email=github_email,
            github_name=github_name,
            has_2fa=has_2fa,
            has_billing=has_billing,
            age_days=age_days,
            school_profile=school_profile,
            school_name=school_name,
            user_info=user_info,
        )
    
    def execute_verification(
        self,
        ctx: VerificationContext,
        precheck: PreCheckResult
    ) -> VerificationResult:
        """
        Execute verification process setelah pre-check passed dan user confirm.
        
        PENTING: Credit HARUS sudah di-deduct SEBELUM panggil function ini!
        Function ini assume user sudah klik "Continue" dan credit sudah dikurangi.
        
        Returns VerificationResult dengan status verification.
        """
        if not precheck.success:
            return VerificationResult(
                success=False,
                status="failed",
                message=f"Pre-check failed: {precheck.reason}"
            )
        
        try:
            gh = GitHubSession(ctx.cookies)
            gh.username = precheck.github_username
            
            credit_cost = get_verify_credit_cost(ctx.verify_type)
            school_profile = precheck.school_profile
            school_code = getattr(school_profile, "code", "sma_negeri_1_majenang")
            
            # STEP 2: Generate Identity
            self._log(ctx, "[2/4] Generating identity...")
            self._update_progress(ctx, "generate_identity")
            
            if ctx.verify_type == "teacher":
                identity_data = generate_teacher_data(precheck.github_email, school_code)
                id_card_b64 = create_teacher_documents_base64(identity_data, school_profile)
            else:
                identity_data = generate_student_data(precheck.github_email, school_code)
                id_card_b64 = create_id_card_base64(identity_data, school_profile)
            
            if not id_card_b64:
                return VerificationResult(
                    success=False,
                    status="rejected",
                    message="Failed to generate verification document"
                )
            
            self._log(ctx, "[2/4] Identity created")
            
            # STEP 3: Update Profile & Billing
            self._log(ctx, "[3/4] Updating GitHub profile...")
            self._update_progress(ctx, "update_profile")
            
            try:
                profile_location = f"{identity_data.alamat}, {identity_data.kelurahan}, {identity_data.kabupaten}"
            except Exception:
                profile_location = None
            
            profile_ok, profile_msg = gh.update_profile_name(
                identity_data.nama_lengkap,
                profile_location,
                "Jakarta",
                True,
                getattr(identity_data, "profile_bio", None),
                getattr(identity_data, "jenis_kelamin", None),
            )
            
            if profile_ok:
                self._log(ctx, "Profile updated")
            else:
                self._log(ctx, f"Profile update warning: {profile_msg}")
            
            self._log(ctx, "[3/4] Setting up billing...")
            self._update_progress(ctx, "billing")
            
            billing_ok, billing_msg = gh.update_billing_info(identity_data)
            if not billing_ok:
                return VerificationResult(
                    success=False,
                    status="rejected",
                    message=f"Billing setup failed: {billing_msg}",
                    github_username=precheck.github_username,
                    school_name=precheck.school_name,
                    document_base64=id_card_b64,
                    identity_data=identity_data,
                )
            
            self._log(ctx, "[3/4] Billing configured")
            
            # STEP 4: Submit Application
            self._log(ctx, "[4/4] Submitting application to GitHub...")
            self._update_progress(ctx, "submit")
            
            submit_ok, submit_msg = gh.submit_application(
                identity_data,
                id_card_b64,
                ctx.verify_type,
                school_profile,
            )
            
            if not submit_ok:
                # Submit gagal - tapi mungkin aplikasi sudah masuk ke GitHub
                # (network issue, timeout, dll)
                error_msg = (
                    "Application rejected by GitHub. Document may be invalid."
                    if submit_msg == "rejected"
                    else submit_msg
                )
                
                # Tentukan status berdasarkan error type
                # "rejected" = pasti gagal (document invalid)
                # lainnya = uncertain (network issue, timeout, dll)
                status = "rejected" if submit_msg == "rejected" else "submit_uncertain"
                
                return VerificationResult(
                    success=False,
                    status=status,
                    message=error_msg,
                    github_username=precheck.github_username,
                    school_name=precheck.school_name,
                    document_base64=id_card_b64,
                    identity_data=identity_data,
                    status_full_text=submit_msg,
                    credit_cost=credit_cost if not ctx.is_owner else 0,
                )
            
            # Determine final status
            final_status = "approved" if submit_msg == "approved" else "pending"
            
            # NOTE: Credit sudah di-deduct SEBELUM execute_verification dipanggil!
            # Kita tidak deduct di sini lagi.
            
            # Increment daily verify count (non-owner only, if approved)
            if final_status == "approved" and not ctx.is_owner:
                increment_daily_verify_count(ctx.user_id)
            
            # Add verify log
            add_verify_log(
                ctx.user_id,
                precheck.github_username,
                ctx.verify_type,
                final_status,
                credit_cost if not ctx.is_owner else 0,
            )
            
            submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if final_status == "approved":
                self._log(ctx, "[4/4] Application approved!")
                message = "Application approved by GitHub"
            else:
                self._log(ctx, "[4/4] Application submitted, waiting for review")
                message = "Application submitted and pending review"
            
            return VerificationResult(
                success=True,
                status=final_status,
                message=message,
                github_username=precheck.github_username,
                school_name=precheck.school_name,
                submitted_at=submitted_at,
                credit_cost=credit_cost if not ctx.is_owner else 0,
                document_base64=id_card_b64,
                identity_data=identity_data,
                status_full_text=submit_msg,
            )
            
        except Exception as exc:
            self._log(ctx, f"[ERROR] Unexpected failure: {exc}")
            return VerificationResult(
                success=False,
                status="failed",
                message=f"Runtime error: {exc}",
                status_full_text=str(exc),
            )
    
    def deduct_credits_before_submit(self, ctx: VerificationContext) -> tuple[bool, str]:
        """
        Deduct credits SETELAH user confirm, SEBELUM submit.
        
        Returns:
            (success: bool, message: str)
            - (True, "") jika berhasil atau is_owner
            - (False, error_msg) jika gagal
        """
        if ctx.is_owner:
            return (True, "Owner: no credit deduction needed")
        
        credit_cost = get_verify_credit_cost(ctx.verify_type)
        if credit_cost <= 0:
            return (True, "No credit cost")
        
        # Deduct credits
        deducted = deduct_credits(ctx.user_id, credit_cost)
        if not deducted:
            return (False, f"Failed to deduct {credit_cost} credits. Please try again.")
        
        self._log(ctx, f"Credit deducted: {credit_cost}")
        return (True, f"Deducted {credit_cost} credits")
    
    def refund_credits_on_certain_failure(
        self, 
        ctx: VerificationContext, 
        result: VerificationResult
    ) -> bool:
        """
        Refund credits jika submit PASTI gagal (rejected, bukan uncertain).
        
        Returns:
            True jika di-refund atau tidak perlu refund
            False jika gagal refund
        """
        if ctx.is_owner:
            return True  # Owner tidak perlu refund
        
        # Hanya refund jika status "rejected" (pasti gagal)
        # Jangan refund jika "submit_uncertain" (mungkin sudah masuk)
        if result.status != "rejected":
            return True  # Tidak perlu refund
        
        credit_cost = result.credit_cost
        if credit_cost <= 0:
            return True  # Tidak ada yang perlu di-refund
        
        # Refund
        try:
            added = add_credits(ctx.user_id, credit_cost)
            if added:
                self._log(ctx, f"Credit refunded: {credit_cost}")
                return True
            else:
                self._log(ctx, f"[WARNING] Failed to refund {credit_cost} credits!")
                return False
        except Exception as exc:
            self._log(ctx, f"[ERROR] Failed to refund credits: {exc}")
            return False
    
    def poll_pending_application(self, polling_ctx: PollingContext) -> PollingResult:
        """
        Unified polling method untuk bot dan web.
        
        Polls GitHub Education application status sampai:
        - Status berubah ke "approved" atau "rejected"
        - Timeout (max_wait_seconds)
        - Error yang fatal
        
        Args:
            polling_ctx: PollingContext dengan callbacks untuk UI updates
        
        Returns:
            PollingResult dengan final status dan info
        """
        elapsed = 0
        gh = GitHubSession(polling_ctx.cookies)
        
        if polling_ctx.log_callback:
            polling_ctx.log_callback(f"[Poller] Started for {polling_ctx.github_username}")
        
        while elapsed < polling_ctx.max_wait_seconds:
            interval = get_application_status_poll_interval(elapsed)
            
            # Callback untuk update UI (elapsed time)
            if polling_ctx.on_tick_callback:
                try:
                    polling_ctx.on_tick_callback(elapsed)
                except Exception:
                    pass
            
            # Sleep sebelum check
            time.sleep(interval)
            elapsed += interval
            
            # Check application status
            try:
                app_status = gh.check_application_status()
                status = str(app_status.get("status", "none") or "none").strip().lower()
                status_error = str(app_status.get("error") or "").strip()
                
                # Status: APPROVED
                if status == "approved":
                    # Increment daily count jika bukan owner
                    if not polling_ctx.is_owner:
                        increment_daily_verify_count(polling_ctx.user_id)
                    
                    if polling_ctx.log_callback:
                        polling_ctx.log_callback(f"[Poller] {polling_ctx.github_username} → APPROVED after {elapsed}s")
                    
                    # Callback untuk completion
                    if polling_ctx.on_completed_callback:
                        try:
                            polling_ctx.on_completed_callback("approved", app_status)
                        except Exception:
                            pass
                    
                    return PollingResult(
                        final_status="approved",
                        elapsed_seconds=elapsed,
                        app_status=app_status,
                    )
                
                # Status: REJECTED
                elif status == "rejected":
                    # Refund credit jika bukan owner
                    credits_refunded = 0
                    if not polling_ctx.is_owner and polling_ctx.charged_credits > 0:
                        add_credits(polling_ctx.user_id, polling_ctx.charged_credits)
                        credits_refunded = polling_ctx.charged_credits
                        
                        if polling_ctx.log_callback:
                            polling_ctx.log_callback(
                                f"[Refund] User {polling_ctx.user_id} refunded {credits_refunded} credits after rejection"
                            )
                    
                    if polling_ctx.log_callback:
                        polling_ctx.log_callback(f"[Poller] {polling_ctx.github_username} → REJECTED after {elapsed}s")
                    
                    # Callback untuk completion
                    if polling_ctx.on_completed_callback:
                        try:
                            polling_ctx.on_completed_callback("rejected", app_status)
                        except Exception:
                            pass
                    
                    return PollingResult(
                        final_status="rejected",
                        elapsed_seconds=elapsed,
                        app_status=app_status,
                        credits_refunded=credits_refunded,
                    )
                
                # Session expired / login required
                elif status == "error":
                    status_error_lower = status_error.lower()
                    if "session expired" in status_error_lower or "login required" in status_error_lower:
                        if polling_ctx.log_callback:
                            polling_ctx.log_callback(
                                "[Poller] Session expired/login required while polling."
                            )
                        if polling_ctx.on_completed_callback:
                            try:
                                polling_ctx.on_completed_callback("session_expired", app_status)
                            except Exception:
                                pass
                        return PollingResult(
                            final_status="session_expired",
                            elapsed_seconds=elapsed,
                            app_status=app_status,
                            error_message=status_error or "Session expired",
                        )
                    continue
                
                # Status lainnya: pending/none → continue polling
                elif status in ["none", "pending"]:
                    continue
                
            except Exception as exc:
                if polling_ctx.log_callback:
                    polling_ctx.log_callback(f"[Poller] Status check error: {exc}")
                # Continue polling, mungkin network issue temporary
                continue
        
        # Timeout
        if polling_ctx.log_callback:
            polling_ctx.log_callback(
                f"[Poller] Timeout after {elapsed}s for {polling_ctx.github_username}"
            )
        
        return PollingResult(
            final_status="timeout",
            elapsed_seconds=elapsed,
            error_message=f"Polling timeout after {elapsed}s",
        )
    
    def run_full_verification(self, ctx: VerificationContext) -> tuple[PreCheckResult, Optional[VerificationResult]]:
        """
        Run full verification flow: precheck -> execute.
        
        PENTING: Caller harus handle credit deduction!
        Flow yang benar:
        1. precheck = core.precheck_verification(ctx)
        2. Show profile to user
        3. User click "Continue"
        4. success, msg = core.deduct_credits_before_submit(ctx)  ← DEDUCT DI SINI
        5. result = core.execute_verification(ctx, precheck)
        6. If result.status == "rejected": core.refund_credits_on_certain_failure(...)
        
        Returns (PreCheckResult, VerificationResult or None)
        """
        # Step 1: Pre-check
        precheck = self.precheck_verification(ctx)
        
        if not precheck.success:
            return (precheck, None)
        
        # Step 2: Execute (credit HARUS sudah di-deduct oleh caller!)
        result = self.execute_verification(ctx, precheck)
        
        return (precheck, result)

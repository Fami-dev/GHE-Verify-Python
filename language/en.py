#!/usr/bin/env python3
# -*- coding: utf-8 -*-

TEXTS = {
# ─── Welcome & Join ───
        "welcome": (
            "👋 <b>Welcome to GitHub Education Bot!</b>\n\n"
            "🔐 Before you start, you must join our communities:\n\n"
            "{groups}\n\n"
            "✅ After joining all groups, press /start again."
        ),
        "join_btn": "📢 Join {name}",
        "check_join": "✅ I've Joined All",
        "not_joined": "❌ You haven't joined all required groups yet!\n\nPlease join all groups above and try again.",
        "joined_success": "✅ Great! You've joined all required groups.",
        # ─── TOS ───
        "tos_title": "📜 <b>Terms of Service</b>",
        "tos_text": (
            "📜 <b>Terms of Service</b>\n\n"
            "By using this bot, you agree to:\n\n"
            "1️⃣ Not abuse or resell the service\n"
            "2️⃣ Use only your own GitHub cookies\n"
            "3️⃣ Understand that results are not guaranteed\n"
            "4️⃣ Not hold the bot responsible for any account issues\n"
            "5️⃣ Follow all community rules\n\n"
            "⚠️ Violation may result in permanent ban."
        ),
        "tos_accept": "✅ I Accept TOS",
        "tos_decline": "❌ Decline",
        "tos_declined": "❌ You must accept the TOS to use this bot.",
        "tos_accepted": "✅ TOS accepted! Welcome aboard!",
        # ─── Profile / Dashboard ───
        "profile": (
            "🏠 <b>Dashboard</b>\n\n"
            "<blockquote>"
            "👤 User: <code>{username}</code>\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🎫 Credits: <b>{credits}</b>\n"
            "⏱ Daily Limit: <b>{limit_display}</b>\n"
            "🎓 Student Cost: <b>{student_credit_cost}</b> (<b>{student_status}</b>)\n"
            "👨‍🏫 Teacher Cost: <b>{teacher_credit_cost}</b> (<b>{teacher_status}</b>)\n"
            "🌐 Language: <b>{lang}</b>\n"
            "👥 Total Users: <b>{total_users}</b>\n"
            "📈 Daily Users: <b>{daily_users}</b>"
            "</blockquote>\n\n"
            "Choose an action below:"
        ),
        "btn_verify": "🎓 Verify GitHub Student",
        "btn_verify_teacher": "👨‍🏫 Verify as Teacher",
        "btn_referral": "👥 Referral Program",
        "btn_checkin": "📅 Daily Check-in",
        "btn_language": "🌐 Change Language",
        "btn_help": "❓ Help",
        "btn_owner": "👑 Owner Menu",
        "btn_tos_agree": "✅ I Agree",
        "btn_tos_disagree": "❌ Cancel",
        "btn_tos_switch_id": "🇮🇩 Bahasa Indonesia",
        "btn_tos_switch_en": "🇬🇧 English",
        "owner_menu": (
            "👑 <b>Owner Menu</b>\n\n"
            "<blockquote>"
            "🎓 Student Verify: <b>{student_status}</b>\n"
            "👨‍🏫 Teacher Verify: <b>{teacher_status}</b>\n"
            "⏱ Daily Limit: <b>{daily_limit}</b>"
            "</blockquote>\n\n"
            "Choose an option below:"
        ),
        "btn_test_log": "🧪 Test Log Message",
        "btn_gen_student_doc": "📄 Generate Student Doc",
        "btn_gen_teacher_doc": "📄 Generate Teacher Doc",
        "btn_owner_add_credit": "➕ Add Credit",
        "btn_owner_add_daily_limit": "🎁 Add User Daily Limit",
        "btn_owner_school_mode": "🏫 School Mode Manager",
        "generating_doc": "⏳ Generating document preview...",
        "btn_toggle_student_verify": "🎓 Student Verify: {status}",
        "btn_toggle_teacher_verify": "👨‍🏫 Teacher Verify: {status}",
        "verify_toggle_done": "✅ {type} verification switched to {status}",
        "verify_maintenance": "🚧 <b>Maintenance</b>\n\n{type} verification is currently disabled. Please try again later.",
        "add_credit_prompt": (
            "➕ <b>Add Credit</b>\n\n"
            "<blockquote>"
            "Send target Telegram User ID.\n"
            "You can also send: <code>user_id amount</code>\n"
            "Example: <code>123456789 2</code>"
            "</blockquote>"
        ),
        "add_credit_invalid": "❌ Invalid format. Send <code>user_id</code> or <code>user_id amount</code>.",
        "add_credit_owner_done": (
            "✅ <b>Credit Added Successfully</b>\n\n"
            "<blockquote>"
            "👤 Target: <code>{target_id}</code>\n"
            "➕ Added: <b>{amount}</b>\n"
            "🎫 New Balance: <b>{new_total}</b>"
            "</blockquote>"
        ),
        "add_credit_user_notice": (
            "🎁 <b>You Received Credits</b>\n\n"
            "<blockquote>"
            "➕ Added: <b>{amount}</b>\n"
            "🎫 Current Balance: <b>{new_total}</b>\n"
            "✨ Added by admin"
            "</blockquote>"
        ),
        "owner_add_daily_limit_prompt": (
            "🎁 <b>Add User Daily Limit Bonus</b>\n\n"
            "Send: <code>user_id amount</code>\n"
            "Example: <code>123456789 1</code>\n\n"
            "This adds extra daily quota for today only."
        ),
        "owner_add_daily_limit_invalid_format": "❌ Invalid format. Use: <code>user_id amount</code>",
        "owner_add_daily_limit_invalid_numbers": "❌ User ID and amount must be positive numbers.",
        "owner_add_daily_limit_warning": (
            "⚠️ <b>Warning: Bonus exceeds global daily limit</b>\n\n"
            "Global limit: <b>{global_limit}</b>\n"
            "Requested bonus: <b>{bonus}</b>\n\n"
            "Do you want to continue?"
        ),
        "owner_add_daily_limit_added": (
            "✅ <b>Daily Limit Bonus Added</b>\n\n"
            "👤 User ID: <code>{target_id}</code>\n"
            "➕ Bonus Added: <b>{bonus}</b>\n"
            "📊 Current Usage: <b>{used}</b>\n"
            "🎯 Effective Limit Today: <b>{effective_limit}</b>"
        ),
        "owner_add_daily_limit_notify_user": (
            "🎁 <b>Daily Limit Bonus Added</b>\n\n"
            "➕ Bonus: <b>{bonus}</b>\n"
            "📊 Usage Today: <b>{used}</b>\n"
            "🎯 Effective Limit Today: <b>{effective_limit}</b>"
        ),
        "owner_add_daily_limit_cancelled": "❌ Daily bonus addition cancelled.",
        "owner_add_daily_limit_session_expired": "Session expired.",
        "owner_add_daily_limit_invalid_pending": "Invalid pending data.",
        "set_daily_limit_prompt": (
            "⏱ <b>Set Daily Verify Limit</b>\n\n"
            "Current limit: <b>{current_display}</b>\n\n"
            "Send a new number (example: <code>2</code> for max 2x/day).\n"
            "Send <code>0</code> for <b>Unlimited</b>."
        ),
        "owner_school_mode_text": (
            "🏫 <b>School Mode Manager</b>\n\n"
            "Click a school button to toggle <b>public/private</b>.\n"
            "Every click is saved instantly.\n\n"
            "<blockquote>"
            "📚 Total School: <b>{total}</b>\n"
            "🌐 Public: <b>{public_count}</b>\n"
            "🔒 Private: <b>{private_count}</b>"
            "</blockquote>"
        ),
        "school_not_found": "School not found.",
        "school_not_found_config": "School not found in configuration.",
        # ─── Referral ───
        "referral": (
            "👥 <b>Referral Program</b>\n\n"
            "📎 Your Referral Link:\n"
            "<code>{ref_link}</code>\n\n"
            "<blockquote>"
            "👥 Total Invites: <b>{total_invites}</b>\n"
            "🎫 Credits Earned: <b>{credits_earned}</b>\n"
            "</blockquote>\n"
            "💡 Share your link! Each invite = <b>{per_invite} credit</b>"
        ),
        "referral_welcome": "🎉 You joined via referral from user <code>{referrer}</code>! You both get a bonus credit!",
        # ─── Daily Check-in ───
        "checkin_success": (
            "📅 <b>Daily Check-in</b>\n\n"
            "✅ Check-in successful!\n"
            "🎫 +{amount} credit added\n"
            "🎫 Total Credits: <b>{total}</b>\n"
            "📅 Next check-in: Tomorrow"
        ),
        "checkin_already": (
            "📅 <b>Daily Check-in</b>\n\n"
            "⏳ You already checked in today!\n"
            "📅 Next check-in in: <b>{time}</b>"
        ),
        # ─── Verification TOS (Terms of Service) ───
        "verify_tos_title": "📋 <b>Terms & Guidelines for GitHub Education Verification</b>",
        "verify_tos": (
            "📋 <b>Terms & Guidelines for GitHub Education Verification</b>\n\n"
            "<blockquote>"
            "📌 <b>Requirements for Approval:</b>\n\n"
            "1️⃣ <b>Email Address</b>\n"
            "   • Use <code>@gmail.com</code> email for higher approval rate\n\n"
            "2️⃣ <b>Account Age</b>\n"
            "   • Minimum: 3 days old (enforced by bot)\n"
            "   • Recommended: 7+ days for better approval chance\n"
            "   • Older accounts have significantly higher success rate\n\n"
            "3️⃣ <b>Two-Factor Authentication (2FA)</b>\n"
            "   • Must be enabled (required by GitHub)\n"
            "   • Configure in Settings → Security\n\n"
            "4️⃣ <b>During Review Period</b>\n"
            "   • <b>DO NOT</b> refresh GitHub Education page\n"
            "   • <b>DO NOT</b> check status manually on GitHub\n"
            "   • Wait patiently - approval takes 1 minute - 1 day\n\n"
            "5️⃣ <b>After Rejection</b>\n"
            "   • Wait at least 10 minutes before retry\n"
            "   • If requirements met, you can verify again\n\n"
            "6️⃣ <b>After Approval</b>\n"
            "   • <b>DO NOT</b> change profile name immediately\n"
            "   • <b>DO NOT</b> modify billing information\n"
            "   • Wait 7+ days before making profile changes\n"
            "   • Hold benefits usage - avoid suspicious activity\n\n"
            "⚠️ <b>IMPORTANT WARNINGS:</b>\n\n"
            "🔴 This service uses automated methods\n"
            "🔴 GitHub may suspend/ban accounts for abuse\n"
            "🔴 <b>DO NOT</b> use your main GitHub account\n"
            "🔴 Education benefits can be revoked anytime\n"
            "🔴 Owner takes <b>NO RESPONSIBILITY</b> for any consequences\n\n"
            "✅ By clicking <b>I Agree</b>, you acknowledge:\n"
            "   • You understand all risks involved\n"
            "   • You accept full responsibility for outcomes\n"
            "   • You agree to follow all guidelines above\n"
            "   • Owner is not liable for any issues\n"
            "</blockquote>\n\n"
            "💡 <i>Read carefully before proceeding!</i>"
        ),
        # ─── Verify Flow ───
        "enter_cookie": (
            "🍪 <b>Enter GitHub Cookie</b>\n\n"
            "<blockquote>"
            "Please send your full GitHub cookies.\n"
            "🎫 Cost: <b>{credits}</b> credit"
            "</blockquote>"
        ),
        "invalid_cookie": "❌ Invalid cookie! Must contain <code>user_session</code> or <code>_gh_sess</code>.",
        "checking_account": "⏳ Checking GitHub account...",
        "login_failed": "❌ Login failed. Cookie may be expired.",
        "no_2fa": "❌ 2FA is not enabled! Please enable it first in GitHub Security settings.",
        "no_credits": "❌ You don't have enough credits!\n\n🎫 Credits: <b>{credits}</b>\n\nEarn credits via referrals or daily check-in.",
        "required_student_credits": "\n\nRequired: <b>{required}</b> credits for student verify.",
        "required_teacher_credits": "\n\nRequired: <b>{required}</b> credits for teacher verify.",
        "daily_limit_reached": (
            "⏱ <b>Daily Limit Reached</b>\n\n"
            "You already used <b>{used}x</b> today (max: <b>{max_limit}x</b>).\n"
            "Limit resets at 00:00 server time."
        ),
        "account_too_young": "⚠️ <b>Account Age Requirement Not Met</b>\n\n<blockquote>👤 <b>{username}</b>\n📧 {email}\n🔐 2FA: {twofa}\n📅 Account Age: <b>{age_days} days</b></blockquote>\n\n❌ Your GitHub account must be <b>at least 3 days old</b> to use this service.\n\n⏳ Please wait <b>{days_left} more day(s)</b> and try again.",
        # ─── Process Steps ───
        "process_profile": "⚙️ <code>[1/4]</code> Fetching profile info...",
        "process_profile_done": "✅ <code>[1/4]</code> Profile loaded!\n\n<blockquote>👤 <b>{username}</b>\n📧 {email}\n🔐 2FA: {twofa}\n📅 Account Age: {age_display}</blockquote>\n\n⚠️ By proceeding, you agree to our <b>S&K</b>.",
        "process_identity": "⚙️ <code>[2/4]</code> Generating identity...",
        "process_identity_done": "✅ <code>[2/4]</code> Identity created!",
        "process_billing": "⚙️ <code>[3/4]</code> Setting up billing address...",
        "process_billing_done": "✅ <code>[3/4]</code> Billing configured!",
        "process_submit": "⚙️ <code>[4/4]</code> Submitting application...",
        "process_submit_done": "✅ <code>[4/4]</code> Application submitted!",
        "process_failed": "❌ Process failed at step {step}: {error}",
        # ─── Status ───
        "status_approved": "✅ <b>APPROVED</b> - Your application has been approved by GitHub!",
        "status_pending": "⏳ <b>PENDING</b> - Your application is under review.",
        "status_rejected": "❌ <b>REJECTED</b> - Your application was rejected.",
        "status_not_found": "ℹ️ No application found. You may not have applied yet.",
        "status_unknown": "❓ Status unknown. Please check manually.",
        "status_waiting": "⏳ Waiting for GitHub response...",
        # ─── Results ───
        "result_success": (
            "🎉 <b>Application Submitted Successfully!</b>\n\n"
            "👤 GitHub: <code>{username}</code>\n"
            "📚 Type: {type}\n"
            "📝 Status: Pending Review\n\n"
            "⏰ Estimated review time: 1 minute - 1 day\n"
            "⏳ Elapsed time: <b>{elapsed}</b>\n\n"
            "Use /start to check status anytime."
        ),
        "result_failed": "❌ <b>Submission Failed</b>\n\n{error}",
        # ─── Language ───
        "lang_select": "🌐 **Select Language:**",
        "lang_changed": "✅ Language changed to English!",
        # ─── Misc ───
        "btn_back": "🔙 Back",
        "btn_confirm": "✅ Confirm",
        "btn_cancel": "❌ Cancel",
        "cancelled": "❌ Operation cancelled.",
        "admin_only": "⛔ Admin only command.",
        "choose_type": "📚 <b>Choose verification type:</b>",
        "teacher_maintenance": "👨‍🏫 <b>Maintenance</b>\n\nTeacher verification is currently under maintenance. Please use Student verification for now.",
        "btn_student": "🎓 Student",
        "btn_teacher": "👨‍🏫 Teacher",
        "btn_topup_credit": "💳 Top Up Credit",
        "btn_topup_refresh": "🔄 Refresh",
        "btn_topup_cancel_deposit": "❌ Cancel Deposit",
        "btn_topup_back_menu": "◀️ Back to Top Up Menu",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_id": "🇮🇩 Indonesia",
        "btn_owner_status_menu": "🧾 Status Indicators",
        "btn_owner_advanced": "⚙️ Advanced",
        "btn_owner_ban": "🔨 Ban/Unban",
        "btn_owner_back": "◀ Back",
        "btn_owner_prev": "⬅ Prev",
        "btn_owner_next": "Next ➡",
        "btn_scope_bot_on": "🤖 Bot ON",
        "btn_scope_bot_off": "🤖 Bot OFF",
        "btn_scope_web_on": "🌐 Web ON",
        "btn_scope_web_off": "🌐 Web OFF",
        "btn_scope_both_on": "✅ Both ON",
        "btn_scope_both_off": "⛔ Both OFF",
        "owner_status_empty": "🧾 <b>Status Indicators</b>\n\n<blockquote>No persisted status.\nAuto retention: max 30 latest items.</blockquote>",
        "owner_status_header": "🧾 <b>Status Indicators</b>\n\n<blockquote>Total saved: <b>{total}</b> (auto cleanup max 30)\nPage: <b>{page}</b>/<b>{max_page}</b></blockquote>",
        "owner_advanced_text": "⚙️ <b>Advanced Tools</b>\n\nUse these tools with caution. Some actions may affect live data.\n\nAvailable:\n• Backup Now\n• Export/Restore DB\n• School Modes manager\n\nPress Back to return to Owner Menu.",
        "verify_scope_pick_target": "Choose target visibility to enable/disable.",
        "math_already_verified": "You have already completed the math verification.",
        "math_session_expired": "Verification session expired. Please type /start again.",
        "math_time_up": "⏱ Time is up (maximum 1 minute). Please try again.",
        "math_wrong_answer": "❌ Wrong answer! Please try again.",
        "math_try_again": "Try Again",
        "math_correct_answer": "✅ Correct answer!",
        "test_log_sent": "Test log sent!",
        "owner_doc_session_invalid": "Invalid session, repeat from Owner Menu.",
        "verify_session_invalid": "Invalid session, restart verify flow.",
        "doc_generated_success": "✅ Document generated successfully!\nCheck private chat for preview.",
        "doc_generated_error": "❌ Error: {error}",
        "owner_ban_prompt": "🔨 <b>Ban / Unban User</b>\n\nSend Telegram User ID to ban/unban (optional reason after ID). Example:\n<code>12345678 Spamming</code>",
        "owner_ban_invalid_format": "❌ Invalid format. User ID must be a number.",
        "owner_ban_user_not_found": "❌ User not found in database.",
        "owner_ban_success": "✅ <b>User BANNED Successfully 🚷</b>\n<blockquote>🆔 <b>ID:</b> <code>{target_id}</code>\n👤 <b>Username:</b> {username}\n💰 <b>Credits Removed:</b> {credits}\n📝 <b>Reason:</b> {reason}</blockquote>",
        "owner_unban_success": "✅ User <code>{target_id}</code> successfully UNBANNED ✅.",
        "user_banned_notice": "🚫 <b>You have been banned from using this bot!</b>\n<blockquote>📝 <b>Reason:</b> {reason}\n\nIf this is a mistake, please contact support below.</blockquote>",
        "user_unbanned_notice": "✅ <b>You have been unbanned.</b> You can now use the bot again.",
        "user_banned_alert": "⚠️ You are banned from this bot.",
        "btn_contact_support": "Contact Support",
        "btn_contact_owner": "📩 Contact Owner (@{username})",
        "owner_status_deleted": "Status deleted.",
        "owner_status_not_found": "Status not found.",
        "verify_starting": "⏳ Starting verification process...",
        "slot_full": "🚫 <b>Verification Slots Are Full</b>\n\nCurrent active slots: <b>{slots}</b>\n\nPlease retry when slots are available.",
        "topup_owner_hint": "💳 Use the Top Up Credit button in dashboard to simulate user flow.",
        "topup_not_configured": "❌ <b>Top Up is not configured by admin yet.</b>",
        "topup_intro": "💳 <b>Automatic Credit Top Up (QRIS)</b>\n\n<blockquote>Choose a package then scan the QR image sent by bot.</blockquote>",
        "addcredit_done": "✅ Added **{amount}** credits to user `{target_id}`\n🎫 New total: **{new_total}**",
        "broadcast_usage": "Use /broadcast by replying to a message. The replied text will be sent as Markdown.",
        "broadcast_reply_missing": "Reply must contain text message for broadcast.",
        "broadcast_done": "📣 *Broadcast Completed*\n\n✅ Sent: *{sent}*\n❌ Failed: *{failed}*\n👥 Total: *{total}*",
        "stats_text": "📊 **Bot Statistics**\n\n👥 Total Users: **{total_users}**\n📝 Total Verifications: **{total_verifies}**\n✅ Approved: **{approved}**\n⏳ Pending: **{pending}**\n❌ Rejected: **{rejected}**\n\n⏰ Updated: `{updated}`",
        "setlog_done": "✅ Log group set to: `{log_group_id}`",
        "liststatus_empty": "📭 No persisted status found.",
        "liststatus_header": "📌 **Persisted Verify Status (max {limit})**",
        "liststatus_delete_hint": "Delete one status with: `/delstatus <task_id>`",
        "delstatus_usage": "Usage: `/delstatus <task_id>`",
        "delstatus_deleted": "✅ Status `{task_id}` deleted from persisted storage.",
        "delstatus_not_found": "⚠️ Status `{task_id}` not found.",
        "help_admin_cmds": "\n\n**🔧 Admin Commands:**\n`/addcredit <user_id> <amount>` — Add credits\n`/stats` — Bot statistics\n`/setlog <group_id>` — Set log group\n`/liststatus [limit]` — List persisted verify status\n`/delstatus <task_id>` — Delete one persisted status\n",
        "help_text": "❓ **Help**\n\n🎓 This bot helps you apply for **GitHub Education Pack**.\n\n**Commands:**\n`/start` — Main menu & dashboard\n`/topup` — Buy credit via QRIS\n`/help` — Show this help\n\n**Features:**\n🎓 Verify as Student or Teacher\n👥 Referral program (earn credits)\n📅 Daily check-in (earn credits)\n💳 Auto top-up credit via QRIS\n📊 Check application status\n🌐 Multi-language (EN/ID){admin_cmds}",
}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 Language Module — English & Indonesian
"""

LANG = {
    "en": {
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
    },
    "id": {
        # ─── Welcome & Join ───
        "welcome": (
            "👋 <b>Selamat datang di GitHub Education Bot!</b>\n\n"
            "🔐 Sebelum mulai, kamu harus bergabung ke komunitas kami:\n\n"
            "{groups}\n\n"
            "✅ Setelah bergabung, tekan /start lagi."
        ),
        "join_btn": "📢 Gabung {name}",
        "check_join": "✅ Sudah Bergabung Semua",
        "not_joined": "❌ Kamu belum bergabung ke semua grup!\n\nSilakan gabung ke semua grup di atas dan coba lagi.",
        "joined_success": "✅ Keren! Kamu sudah bergabung ke semua grup.",
        # ─── TOS ───
        "tos_title": "📜 <b>Syarat & Ketentuan</b>",
        "tos_text": (
            "📜 <b>Syarat & Ketentuan</b>\n\n"
            "Dengan menggunakan bot ini, kamu setuju untuk:\n\n"
            "1️⃣ Tidak menyalahgunakan atau menjual kembali layanan\n"
            "2️⃣ Hanya menggunakan cookie GitHub milik sendiri\n"
            "3️⃣ Memahami bahwa hasil tidak dijamin\n"
            "4️⃣ Tidak menyalahkan bot atas masalah akun\n"
            "5️⃣ Mematuhi semua aturan komunitas\n\n"
            "⚠️ Pelanggaran dapat mengakibatkan banned permanen."
        ),
        "tos_accept": "✅ Saya Setuju",
        "tos_decline": "❌ Tolak",
        "tos_declined": "❌ Kamu harus menyetujui S&K untuk menggunakan bot ini.",
        "tos_accepted": "✅ S&K diterima! Selamat bergabung!",
        # ─── Profile / Dashboard ───
        "profile": (
            "🏠 <b>Dashboard</b>\n\n"
            "<blockquote>"
            "👤 User: <code>{username}</code>\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "🎫 Kredit: <b>{credits}</b>\n"
            "⏱ Limit Harian: <b>{limit_display}</b>\n"
            "🎓 Biaya Student: <b>{student_credit_cost}</b> (<b>{student_status}</b>)\n"
            "👨‍🏫 Biaya Teacher: <b>{teacher_credit_cost}</b> (<b>{teacher_status}</b>)\n"
            "🌐 Bahasa: <b>{lang}</b>\n"
            "👥 Total Pengguna: <b>{total_users}</b>\n"
            "📈 Pengguna Hari Ini: <b>{daily_users}</b>"
            "</blockquote>\n\n"
            "Pilih aksi di bawah:"
        ),
        "btn_verify": "🎓 Verifikasi GitHub Student",
        "btn_verify_teacher": "👨‍🏫 Verifikasi sebagai Guru",
        "btn_referral": "👥 Program Referral",
        "btn_checkin": "📅 Absen Harian",
        "btn_language": "🌐 Ganti Bahasa",
        "btn_help": "❓ Bantuan",
        "btn_owner": "👑 Menu Pemilik",
        "btn_tos_agree": "✅ Saya Setuju",
        "btn_tos_disagree": "❌ Batal",
        "btn_tos_switch_id": "🇮🇩 Bahasa Indonesia",
        "btn_tos_switch_en": "🇬🇧 English",
        "owner_menu": (
            "👑 <b>Menu Pemilik</b>\n\n"
            "<blockquote>"
            "🎓 Verifikasi Student: <b>{student_status}</b>\n"
            "👨‍🏫 Verifikasi Teacher: <b>{teacher_status}</b>\n"
            "⏱ Daily Limit: <b>{daily_limit}</b>"
            "</blockquote>\n\n"
            "Pilih aksi di bawah:"
        ),
        "btn_test_log": "🧪 Test Log Message",
        "btn_gen_student_doc": "📄 Generate Dokumen Siswa",
        "btn_gen_teacher_doc": "📄 Generate Dokumen Guru",
        "btn_owner_add_credit": "➕ Tambah Kredit",
        "btn_owner_add_daily_limit": "🎁 Tambah Daily Limit User",
        "btn_owner_school_mode": "🏫 Atur Mode Sekolah",
        "generating_doc": "⏳ Membuat preview dokumen...",
        "btn_toggle_student_verify": "🎓 Verifikasi Student: {status}",
        "btn_toggle_teacher_verify": "👨‍🏫 Verifikasi Teacher: {status}",
        "verify_toggle_done": "✅ Verifikasi {type} sekarang {status}",
        "verify_maintenance": "🚧 <b>Maintenance</b>\n\nVerifikasi {type} sedang dimatikan. Silakan coba lagi nanti.",
        "add_credit_prompt": (
            "➕ <b>Tambah Kredit</b>\n\n"
            "<blockquote>"
            "Kirim ID Telegram target user.\n"
            "Bisa juga kirim: <code>user_id jumlah</code>\n"
            "Contoh: <code>123456789 2</code>"
            "</blockquote>"
        ),
        "add_credit_invalid": "❌ Format salah. Kirim <code>user_id</code> atau <code>user_id jumlah</code>.",
        "add_credit_owner_done": (
            "✅ <b>Kredit Berhasil Ditambahkan</b>\n\n"
            "<blockquote>"
            "👤 Target: <code>{target_id}</code>\n"
            "➕ Ditambah: <b>{amount}</b>\n"
            "🎫 Saldo Baru: <b>{new_total}</b>"
            "</blockquote>"
        ),
        "add_credit_user_notice": (
            "🎁 <b>Kamu Menerima Kredit</b>\n\n"
            "<blockquote>"
            "➕ Ditambah: <b>{amount}</b>\n"
            "🎫 Saldo Saat Ini: <b>{new_total}</b>\n"
            "✨ Ditambahkan oleh admin"
            "</blockquote>"
        ),
        "owner_add_daily_limit_prompt": (
            "🎁 <b>Tambah Bonus Daily Limit User</b>\n\n"
            "Kirim: <code>user_id jumlah</code>\n"
            "Contoh: <code>123456789 1</code>\n\n"
            "Ini menambah kuota harian ekstra untuk hari ini saja."
        ),
        "owner_add_daily_limit_invalid_format": "❌ Format tidak valid. Gunakan: <code>user_id jumlah</code>",
        "owner_add_daily_limit_invalid_numbers": "❌ User ID dan jumlah harus angka positif.",
        "owner_add_daily_limit_warning": (
            "⚠️ <b>Peringatan: Bonus melebihi limit harian global</b>\n\n"
            "Limit global: <b>{global_limit}</b>\n"
            "Bonus diminta: <b>{bonus}</b>\n\n"
            "Lanjutkan penambahan?"
        ),
        "owner_add_daily_limit_added": (
            "✅ <b>Bonus Daily Limit Ditambahkan</b>\n\n"
            "👤 User ID: <code>{target_id}</code>\n"
            "➕ Bonus Ditambah: <b>{bonus}</b>\n"
            "📊 Pemakaian Saat Ini: <b>{used}</b>\n"
            "🎯 Limit Efektif Hari Ini: <b>{effective_limit}</b>"
        ),
        "owner_add_daily_limit_notify_user": (
            "🎁 <b>Bonus Daily Limit Ditambahkan</b>\n\n"
            "➕ Bonus: <b>{bonus}</b>\n"
            "📊 Pemakaian Hari Ini: <b>{used}</b>\n"
            "🎯 Limit Efektif Hari Ini: <b>{effective_limit}</b>"
        ),
        "owner_add_daily_limit_cancelled": "❌ Penambahan bonus daily dibatalkan.",
        "owner_add_daily_limit_session_expired": "Session sudah kadaluarsa.",
        "owner_add_daily_limit_invalid_pending": "Data pending tidak valid.",
        "set_daily_limit_prompt": (
            "⏱ <b>Set Daily Verify Limit</b>\n\n"
            "Limit saat ini: <b>{current_display}</b>\n\n"
            "Kirim angka baru (contoh: <code>2</code> untuk max 2x/hari).\n"
            "Kirim <code>0</code> untuk <b>Tanpa Batas</b>."
        ),
        "owner_school_mode_text": (
            "🏫 <b>Pengatur Mode Sekolah</b>\n\n"
            "Klik tombol sekolah untuk toggle mode <b>public/private</b>.\n"
            "Setiap klik akan langsung disimpan.\n\n"
            "<blockquote>"
            "📚 Total Sekolah: <b>{total}</b>\n"
            "🌐 Public: <b>{public_count}</b>\n"
            "🔒 Private: <b>{private_count}</b>"
            "</blockquote>"
        ),
        "school_not_found": "Sekolah tidak ditemukan.",
        "school_not_found_config": "Sekolah tidak ditemukan di konfigurasi.",
        # ─── Referral ───
        "referral": (
            "👥 <b>Program Referral</b>\n\n"
            "📎 Link Referral Kamu:\n"
            "<code>{ref_link}</code>\n\n"
            "<blockquote>"
            "👥 Total Undangan: <b>{total_invites}</b>\n"
            "🎫 Kredit Didapat: <b>{credits_earned}</b>\n"
            "</blockquote>\n"
            "💡 Bagikan linkmu! Setiap undangan = <b>{per_invite} kredit</b>"
        ),
        "referral_welcome": "🎉 Kamu bergabung via referral dari user <code>{referrer}</code>! Kalian berdua mendapat bonus kredit!",
        # ─── Daily Check-in ───
        "checkin_success": (
            "📅 <b>Absen Harian</b>\n\n"
            "✅ Absen berhasil!\n"
            "🎫 +{amount} kredit ditambahkan\n"
            "🎫 Total Kredit: <b>{total}</b>\n"
            "📅 Absen berikutnya: <b>24 jam lagi</b>"
        ),
        "checkin_already": (
            "📅 <b>Absen Harian</b>\n\n"
            "⏳ Kamu sudah absen hari ini!\n"
            "📅 Absen berikutnya dalam: <b>{time}</b>"
        ),
        # ─── Verification TOS (Terms of Service) ───
        "verify_tos_title": "📋 <b>Syarat & Panduan Verifikasi GitHub Education</b>",
        "verify_tos": (
            "📋 <b>Syarat & Panduan Verifikasi GitHub Education</b>\n\n"
            "<blockquote>"
            "📌 <b>Persyaratan Agar Di-Approve:</b>\n\n"
            "1️⃣ <b>Alamat Email</b>\n"
            "   • Gunakan email <code>@gmail.com</code> untuk peluang approve lebih tinggi\n\n"
            "2️⃣ <b>Umur Akun GitHub</b>\n"
            "   • Minimum: 3 hari (dipaksa oleh bot)\n"
            "   • Rekomendasi: 7+ hari untuk peluang lebih besar\n"
            "   • Akun lebih lama = peluang approve jauh lebih tinggi\n\n"
            "3️⃣ <b>Two-Factor Authentication (2FA)</b>\n"
            "   • Wajib diaktifkan (diperlukan GitHub)\n"
            "   • Aktifkan di Settings → Security\n\n"
            "4️⃣ <b>Saat Periode Review (Pending)</b>\n"
            "   • <b>JANGAN</b> refresh halaman GitHub Education\n"
            "   • <b>JANGAN</b> cek status manual di website GitHub\n"
            "   • Tunggu dengan sabar - approve butuh 1 menit - 1 hari\n\n"
            "5️⃣ <b>Setelah Ditolak (Rejected)</b>\n"
            "   • Tunggu minimal 10 menit sebelum coba lagi\n"
            "   • Jika syarat terpenuhi, boleh verify ulang\n\n"
            "6️⃣ <b>Setelah Di-Approve</b>\n"
            "   • <b>JANGAN</b> ganti profile name langsung\n"
            "   • <b>JANGAN</b> ubah informasi billing\n"
            "   • Tunggu 7+ hari sebelum ubah profil\n"
            "   • Tahan dulu penggunaan benefit - hindari aktivitas mencurigakan\n\n"
            "⚠️ <b>PERINGATAN PENTING:</b>\n\n"
            "🔴 Layanan ini menggunakan metode otomatis\n"
            "🔴 GitHub bisa suspend/ban akun jika terdeteksi abuse\n"
            "🔴 <b>JANGAN</b> pakai akun GitHub utama kamu\n"
            "🔴 Benefit Education bisa dicabut kapan saja (revoke)\n"
            "🔴 Owner <b>TIDAK BERTANGGUNG JAWAB</b> atas konsekuensi apapun\n\n"
            "✅ Dengan klik <b>Saya Setuju</b>, kamu mengakui:\n"
            "   • Kamu memahami semua risiko yang ada\n"
            "   • Kamu bertanggung jawab penuh atas hasilnya\n"
            "   • Kamu setuju ikuti semua panduan di atas\n"
            "   • Owner tidak bertanggung jawab atas masalah apapun\n"
            "</blockquote>\n\n"
            "💡 <i>Baca dengan teliti sebelum melanjutkan!</i>"
        ),
        # ─── Verify Flow ───
        "enter_cookie": (
            "🍪 <b>Masukkan Cookie GitHub</b>\n\n"
            "<blockquote>"
            "Silakan kirim cookie lengkap GitHub kamu.\n"
            "🎫 Biaya: <b>{credits}</b> kredit"
            "</blockquote>"
        ),
        "invalid_cookie": "❌ Cookie tidak valid! Harus mengandung <code>user_session</code>, <code>_gh_sess</code>, atau <code>_octo</code>.",
        "checking_account": "⏳ Mengecek akun GitHub...",
        "login_failed": "❌ Login gagal. Cookie mungkin sudah expired.",
        "no_2fa": "❌ 2FA belum aktif! Aktifkan dulu di pengaturan Security GitHub.",
        "no_credits": "❌ Kredit kamu tidak cukup!\n\n🎫 Kredit: <b>{credits}</b>\n\nDapatkan kredit via referral atau absen harian.",
        "required_student_credits": "\n\nDibutuhkan: <b>{required}</b> kredit untuk verify student.",
        "required_teacher_credits": "\n\nDibutuhkan: <b>{required}</b> kredit untuk verify teacher.",
        "daily_limit_reached": (
            "⏱ <b>Daily Limit Tercapai</b>\n\n"
            "Kamu sudah memakai <b>{used}x</b> hari ini (max: <b>{max_limit}x</b>).\n"
            "Limit akan reset pukul 00:00 waktu server."
        ),
        "account_too_young": "⚠️ <b>Syarat Umur Akun Belum Terpenuhi</b>\n\n<blockquote>👤 <b>{username}</b>\n📧 {email}\n🔐 2FA: {twofa}\n📅 Umur Akun: <b>{age_days} hari</b></blockquote>\n\n❌ Akun GitHub kamu harus berumur <b>minimal 3 hari</b> untuk menggunakan layanan ini.\n\n⏳ Harap tunggu <b>{days_left} hari lagi</b> dan coba kembali.",
        # ─── Process Steps ───
        "process_profile": "⚙️ <code>[1/4]</code> Mengambil info profil...",
        "process_profile_done": "✅ <code>[1/4]</code> Profil dimuat!\n\n<blockquote>👤 <b>{username}</b>\n📧 {email}\n🔐 2FA: {twofa}\n📅 Umur Akun: {age_display}</blockquote>\n\n⚠️ Dengan menekan tombol di bawah, kamu menyetujui <b>Syarat & Ketentuan</b> kami.",
        "process_identity": "⚙️ <code>[2/4]</code> Membuat identitas...",
        "process_identity_done": "✅ <code>[2/4]</code> Identitas selesai!",
        "process_billing": "⚙️ <code>[3/4]</code> Mengatur alamat billing...",
        "process_billing_done": "✅ <code>[3/4]</code> Billing dikonfigurasi!",
        "process_submit": "⚙️ <code>[4/4]</code> Mengirim aplikasi...",
        "process_submit_done": "✅ <code>[4/4]</code> Aplikasi terkirim!",
        "process_failed": "❌ Proses gagal di langkah {step}: {error}",
        # ─── Status ───
        "status_approved": "✅ <b>DISETUJUI</b> - Aplikasi kamu telah disetujui oleh GitHub!",
        "status_pending": "⏳ <b>MENUNGGU</b> - Aplikasi kamu sedang ditinjau.",
        "status_rejected": "❌ <b>DITOLAK</b> - Aplikasi kamu ditolak.",
        "status_not_found": "ℹ️ Tidak ditemukan aplikasi. Kamu mungkin belum mendaftar.",
        "status_unknown": "❓ Status tidak diketahui. Silakan cek manual.",
        "status_waiting": "⏳ Menunggu respons dari GitHub...",
        # ─── Results ───
        "result_success": (
            "🎉 <b>Aplikasi Berhasil Dikirim!</b>\n\n"
            "👤 GitHub: <code>{username}</code>\n"
            "📚 Tipe: {type}\n"
            "📝 Status: Menunggu Review\n\n"
            "⏰ Estimasi waktu review: 1 menit - 1 hari\n"
            "⏳ Waktu tunggu: <b>{elapsed}</b>\n\n"
            "Gunakan /start untuk cek status kapan saja."
        ),
        "result_failed": "❌ <b>Pengiriman Gagal</b>\n\n{error}",
        # ─── Language ───
        "lang_select": "🌐 **Pilih Bahasa:**",
        "lang_changed": "✅ Bahasa diubah ke Bahasa Indonesia!",
        # ─── Misc ───
        "btn_back": "🔙 Kembali",
        "btn_confirm": "✅ Konfirmasi",
        "btn_cancel": "❌ Batal",
        "cancelled": "❌ Operasi dibatalkan.",
        "admin_only": "⛔ Khusus admin.",
        "choose_type": "📚 <b>Pilih tipe verifikasi:</b>",
        "teacher_maintenance": "👨‍🏫 <b>Pemeliharaan</b>\n\nVerifikasi Guru sedang dalam pemeliharaan. Silakan gunakan verifikasi Siswa untuk saat ini.",
        "btn_student": "🎓 Pelajar",
        "btn_teacher": "👨‍🏫 Guru",
    },
}


def t(key: str, _l: str = "en", **kwargs) -> str:
    """Get translated text"""
    text = LANG.get(_l, LANG["en"]).get(key, LANG["en"].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text

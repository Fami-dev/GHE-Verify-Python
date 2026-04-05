#!/usr/bin/env python3
# -*- coding: utf-8 -*-

TEXTS = {
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
        "btn_topup_credit": "💳 Top Up Kredit",
        "btn_topup_refresh": "🔄 Muat Ulang",
        "btn_topup_cancel_deposit": "❌ Batalkan Deposit",
        "btn_topup_back_menu": "◀️ Kembali ke Menu Top Up",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_id": "🇮🇩 Indonesia",
        "btn_owner_status_menu": "🧾 Indikator Status",
        "btn_owner_advanced": "⚙️ Lanjutan",
        "btn_owner_ban": "🔨 Ban/Unban",
        "btn_owner_back": "◀ Kembali",
        "btn_owner_prev": "⬅ Sebelumnya",
        "btn_owner_next": "Berikutnya ➡",
        "btn_scope_bot_on": "🤖 Bot ON",
        "btn_scope_bot_off": "🤖 Bot OFF",
        "btn_scope_web_on": "🌐 Web ON",
        "btn_scope_web_off": "🌐 Web OFF",
        "btn_scope_both_on": "✅ Keduanya ON",
        "btn_scope_both_off": "⛔ Keduanya OFF",
        "owner_status_empty": "🧾 <b>Indikator Status</b>\n\n<blockquote>Belum ada status tersimpan.\nRetensi otomatis: maksimal 30 item terbaru.</blockquote>",
        "owner_status_header": "🧾 <b>Indikator Status</b>\n\n<blockquote>Total tersimpan: <b>{total}</b> (auto cleanup max 30)\nHalaman: <b>{page}</b>/<b>{max_page}</b></blockquote>",
        "owner_advanced_text": "⚙️ <b>Tools Lanjutan</b>\n\nGunakan tools ini dengan hati-hati. Beberapa aksi bisa memengaruhi data live.\n\nTersedia:\n• Backup Sekarang\n• Export/Restore DB\n• Manager mode sekolah\n\nTekan Kembali untuk kembali ke Menu Owner.",
        "verify_scope_pick_target": "Pilih target visibilitas yang ingin diaktifkan/dimatikan.",
        "math_already_verified": "Kamu sudah menyelesaikan verifikasi matematika.",
        "math_session_expired": "Sesi verifikasi kadaluarsa. Silakan ketik /start lagi.",
        "math_time_up": "⏱ Waktu habis (maksimal 1 menit). Silakan coba lagi.",
        "math_wrong_answer": "❌ Jawaban salah! Silakan coba lagi.",
        "math_try_again": "Coba Lagi",
        "math_correct_answer": "✅ Jawaban benar!",
        "test_log_sent": "Log test berhasil dikirim!",
        "owner_doc_session_invalid": "Sesi tidak valid, ulangi dari Menu Owner.",
        "verify_session_invalid": "Sesi tidak valid, mulai ulang alur verifikasi.",
        "doc_generated_success": "✅ Dokumen berhasil digenerate!\nCek chat pribadi untuk melihat preview.",
        "doc_generated_error": "❌ Error: {error}",
        "owner_ban_prompt": "🔨 <b>Ban / Unban User</b>\n\nKirim User ID Telegram yang ingin di-ban/unban (boleh tambah alasan setelah ID). Contoh:\n<code>12345678 Spamming</code>",
        "owner_ban_invalid_format": "❌ Format tidak valid. User ID harus berupa angka.",
        "owner_ban_user_not_found": "❌ Pengguna tidak ditemukan di database.",
        "owner_ban_success": "✅ <b>Pengguna Berhasil DIBAN 🚷</b>\n<blockquote>🆔 <b>ID:</b> <code>{target_id}</code>\n👤 <b>Username:</b> {username}\n💰 <b>Kredit Dihapus:</b> {credits}\n📝 <b>Alasan:</b> {reason}</blockquote>",
        "owner_unban_success": "✅ Pengguna <code>{target_id}</code> berhasil DI-UNBAN ✅.",
        "user_banned_notice": "🚫 <b>Kamu telah diban dari bot ini!</b>\n<blockquote>📝 <b>Alasan:</b> {reason}\n\nJika ini kesalahan, silakan hubungi support di bawah.</blockquote>",
        "user_unbanned_notice": "✅ <b>Kamu sudah di-unban.</b> Sekarang kamu bisa menggunakan bot lagi.",
        "user_banned_alert": "⚠️ Kamu telah diban dari bot.",
        "btn_contact_support": "Hubungi Support",
        "btn_contact_owner": "📩 Hubungi Owner (@{username})",
        "owner_status_deleted": "Status berhasil dihapus.",
        "owner_status_not_found": "Status tidak ditemukan.",
        "verify_starting": "⏳ Memulai proses verifikasi...",
        "slot_full": "🚫 <b>Slot Verifikasi Sedang Penuh</b>\n\nSlot aktif saat ini: <b>{slots}</b>\n\nSilakan coba lagi saat slot kosong.",
        "topup_owner_hint": "💳 Gunakan tombol Top Up Credit di dashboard untuk simulasi flow user.",
        "topup_not_configured": "❌ <b>Top Up belum dikonfigurasi admin.</b>",
        "topup_intro": "💳 <b>Top Up Kredit Otomatis (QRIS)</b>\n\n<blockquote>Pilih paket lalu scan QR yang dikirim sebagai gambar.</blockquote>",
        "addcredit_done": "✅ Menambahkan **{amount}** kredit ke user `{target_id}`\n🎫 Total baru: **{new_total}**",
        "broadcast_usage": "Gunakan /broadcast dengan me-reply sebuah pesan. Teks reply akan dikirim sebagai Markdown.",
        "broadcast_reply_missing": "Pesan reply harus berisi teks untuk broadcast.",
        "broadcast_done": "📣 *Broadcast Selesai*\n\n✅ Terkirim: *{sent}*\n❌ Gagal: *{failed}*\n👥 Total: *{total}*",
        "stats_text": "📊 **Statistik Bot**\n\n👥 Total User: **{total_users}**\n📝 Total Verifikasi: **{total_verifies}**\n✅ Disetujui: **{approved}**\n⏳ Pending: **{pending}**\n❌ Ditolak: **{rejected}**\n\n⏰ Diperbarui: `{updated}`",
        "setlog_done": "✅ Grup log diset ke: `{log_group_id}`",
        "liststatus_empty": "📭 Tidak ada status tersimpan.",
        "liststatus_header": "📌 **Status Verifikasi Tersimpan (maks {limit})**",
        "liststatus_delete_hint": "Hapus satu status dengan: `/delstatus <task_id>`",
        "delstatus_usage": "Penggunaan: `/delstatus <task_id>`",
        "delstatus_deleted": "✅ Status `{task_id}` dihapus dari penyimpanan.",
        "delstatus_not_found": "⚠️ Status `{task_id}` tidak ditemukan.",
        "help_admin_cmds": "\n\n**🔧 Perintah Admin:**\n`/addcredit <user_id> <amount>` — Tambah kredit\n`/stats` — Statistik bot\n`/setlog <group_id>` — Atur grup log\n`/liststatus [limit]` — Lihat status verifikasi tersimpan\n`/delstatus <task_id>` — Hapus satu status tersimpan\n",
        "help_text": "❓ **Bantuan**\n\n🎓 Bot ini membantu kamu mendaftar **GitHub Education Pack**.\n\n**Perintah:**\n`/start` — Menu utama & dashboard\n`/topup` — Beli kredit via QRIS\n`/help` — Tampilkan bantuan ini\n\n**Fitur:**\n🎓 Verifikasi Student atau Teacher\n👥 Program referral (dapat kredit)\n📅 Absen harian (dapat kredit)\n💳 Top-up kredit otomatis via QRIS\n📊 Cek status aplikasi\n🌐 Multi-bahasa (EN/ID){admin_cmds}",
}

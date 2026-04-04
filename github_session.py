#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 GitHub Session Module — Cookie auth, profile checking, application submission
Extracted from original bot.py and adapted for Telethon bot
"""

import json
import html
import re
import random
import string
import time
import requests
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from identity_profiles import (
    generate_indonesian_name,
    generate_realistic_filename,
    get_random_phone_model,
)

TIMEOUT = 30

POLL_FAST_WINDOW_SECONDS = 600
POLL_MEDIUM_WINDOW_SECONDS = 1800

DEFAULT_SCHOOL_NAME = "SMA Negeri 1 Majenang"
DEFAULT_SCHOOL_ID = "129398"
DEFAULT_SCHOOL_ADDRESS = "Jl Raya Pahonjean KP 07, Majenang, Cilacap 53257"
DEFAULT_SCHOOL_PHONE = "(0280) 623016"
DEFAULT_PRINCIPAL_NAME = "Drs. HARYONO, M.Pd"
DEFAULT_PRINCIPAL_NIP = "196305121988031015"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")


def get_application_status_poll_interval(elapsed_seconds: float) -> int:
    """Return adaptive polling interval (seconds) for GitHub application checks."""
    if elapsed_seconds < POLL_FAST_WINDOW_SECONDS:
        return 30
    if elapsed_seconds < POLL_MEDIUM_WINDOW_SECONDS:
        return 300
    return 600


@dataclass
class SchoolProfile:
    code: str
    mode: str
    name: str
    github_school_id: str
    address: str
    phone: str
    principal_name: str
    principal_nip: str
    city: str
    province: str
    logo_path: str
    latitude: str
    longitude: str
    email: str = ""


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_logo_path(path_value: str) -> str:
    logo_path = (path_value or "").strip()
    if not logo_path:
        return os.path.join(BASE_DIR, "logo", "logosmansa.png")
    if os.path.isabs(logo_path):
        return logo_path

    direct_path = os.path.join(BASE_DIR, logo_path)
    if os.path.exists(direct_path):
        return direct_path

    return os.path.join(BASE_DIR, "logo", os.path.basename(logo_path))


def _load_schools_from_env() -> list[SchoolProfile]:
    try:
        count = int(os.getenv("SCHOOL_COUNT", "0"))
    except Exception:
        count = 0

    default_logo = _resolve_logo_path("logo/logosmansa.png")
    schools: list[SchoolProfile] = []

    for i in range(1, max(count, 0) + 1):
        if not _env_bool(f"SCHOOL_{i}_ENABLED", True):
            continue

        mode = (os.getenv(f"SCHOOL_{i}_MODE", "public") or "public").strip().lower()
        if mode not in {"public", "private"}:
            mode = "public"

        logo_path = _resolve_logo_path(
            (os.getenv(f"SCHOOL_{i}_LOGO_PATH", "") or default_logo).strip()
        )

        schools.append(
            SchoolProfile(
                code=(os.getenv(f"SCHOOL_{i}_CODE", "") or f"school{i}")
                .strip()
                .lower(),
                mode=mode,
                name=(os.getenv(f"SCHOOL_{i}_NAME", "") or DEFAULT_SCHOOL_NAME).strip(),
                github_school_id=(
                    os.getenv(f"SCHOOL_{i}_GITHUB_SCHOOL_ID", "") or DEFAULT_SCHOOL_ID
                ).strip(),
                address=(
                    os.getenv(f"SCHOOL_{i}_ADDRESS", "") or DEFAULT_SCHOOL_ADDRESS
                ).strip(),
                phone=(
                    os.getenv(f"SCHOOL_{i}_PHONE", "") or DEFAULT_SCHOOL_PHONE
                ).strip(),
                principal_name=(
                    os.getenv(f"SCHOOL_{i}_PRINCIPAL_NAME", "")
                    or DEFAULT_PRINCIPAL_NAME
                ).strip(),
                principal_nip=(
                    os.getenv(f"SCHOOL_{i}_PRINCIPAL_NIP", "") or DEFAULT_PRINCIPAL_NIP
                ).strip(),
                city=(os.getenv(f"SCHOOL_{i}_CITY", "") or "Majenang").strip(),
                province=(
                    os.getenv(f"SCHOOL_{i}_PROVINCE", "") or "Jawa Tengah"
                ).strip(),
                logo_path=logo_path,
                latitude=(os.getenv(f"SCHOOL_{i}_LAT", "") or "-7.294431").strip(),
                longitude=(os.getenv(f"SCHOOL_{i}_LON", "") or "108.736366").strip(),
                email=(os.getenv(f"SCHOOL_{i}_EMAIL", "") or "").strip(),
            )
        )

    if schools:
        return schools

    return [
        SchoolProfile(
            code="smansa_majenang",
            mode="public",
            name=DEFAULT_SCHOOL_NAME,
            github_school_id=DEFAULT_SCHOOL_ID,
            address=DEFAULT_SCHOOL_ADDRESS,
            phone=DEFAULT_SCHOOL_PHONE,
            principal_name=DEFAULT_PRINCIPAL_NAME,
            principal_nip=DEFAULT_PRINCIPAL_NIP,
            city="Majenang",
            province="Jawa Tengah",
            logo_path=default_logo,
            latitude="-7.294431",
            longitude="108.736366",
            email="",
        )
    ]


_SCHOOL_PROFILES = _load_schools_from_env()


def get_school_profiles() -> list[SchoolProfile]:
    return list(_SCHOOL_PROFILES)


def get_public_school_profiles() -> list[SchoolProfile]:
    return [s for s in _SCHOOL_PROFILES if s.mode == "public"]


def get_private_school_profiles() -> list[SchoolProfile]:
    return [s for s in _SCHOOL_PROFILES if s.mode == "private"]


def get_school_profile(code: str) -> Optional[SchoolProfile]:
    needle = (code or "").strip().lower()
    for school in _SCHOOL_PROFILES:
        if school.code == needle:
            return school
    return None


def set_school_mode(code: str, mode: str) -> Optional[SchoolProfile]:
    """Set school mode in runtime profile list."""
    school = get_school_profile(code)
    if school is None:
        return None

    next_mode = (mode or "").strip().lower()
    if next_mode not in {"public", "private"}:
        return None

    school.mode = next_mode
    return school


def toggle_school_mode(code: str) -> Optional[SchoolProfile]:
    """Toggle school mode between public and private."""
    school = get_school_profile(code)
    if school is None:
        return None

    school.mode = "private" if school.mode == "public" else "public"
    return school


def apply_school_mode_overrides(overrides: dict[str, str]) -> None:
    """Apply persisted school mode overrides into runtime profiles."""
    if not overrides:
        return

    for code, mode in overrides.items():
        mode_value = (mode or "").strip().lower()
        if mode_value in {"public", "private"}:
            set_school_mode(code, mode_value)


def pick_random_public_school() -> SchoolProfile:
    public_schools = get_public_school_profiles()
    if public_schools:
        return random.choice(public_schools)
    return _SCHOOL_PROFILES[0]


def resolve_school_profile(
    school_profile: Optional[SchoolProfile] = None,
    school_code: Optional[str] = None,
    prefer_public: bool = False,
) -> SchoolProfile:
    if school_profile is not None:
        return school_profile
    if school_code:
        selected = get_school_profile(school_code)
        if selected is not None:
            return selected
    if prefer_public:
        return pick_random_public_school()
    return _SCHOOL_PROFILES[0]


def human_delay(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def random_think_time() -> None:
    human_delay(1.0, 3.0)


def _optimize_proof_image_base64(
    image_b64: str,
    max_image_bytes: int = 1400000,
    max_dimension: int = 2600,
) -> str:
    """Shrink proof image to safer upload size while preserving readability."""
    if not image_b64:
        return image_b64

    try:
        import io
        import base64
        from PIL import Image

        raw = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(raw)).convert("RGB")

        def _save_jpeg_bytes(src_img, quality: int) -> bytes:
            buf = io.BytesIO()
            src_img.save(buf, format="JPEG", quality=quality, optimize=True)
            return buf.getvalue()

        work = img.copy()
        if max(work.size) > max_dimension:
            scale = max_dimension / float(max(work.size))
            work = work.resize(
                (max(1, int(work.width * scale)), max(1, int(work.height * scale))),
                Image.Resampling.LANCZOS,
            )

        best_bytes = _save_jpeg_bytes(work, 90)
        if len(best_bytes) <= max_image_bytes:
            return base64.b64encode(best_bytes).decode("utf-8")

        # Progressive compression + resize fallback
        for _ in range(4):
            for q in (85, 78, 72, 66, 60, 54):
                out = _save_jpeg_bytes(work, q)
                if len(out) <= max_image_bytes:
                    return base64.b64encode(out).decode("utf-8")
                best_bytes = out

            # Still too large: shrink dimensions and retry
            work = work.resize(
                (max(1, int(work.width * 0.85)), max(1, int(work.height * 0.85))),
                Image.Resampling.LANCZOS,
            )

        return base64.b64encode(best_bytes).decode("utf-8")
    except Exception:
        return image_b64


def _load_doc_font(size: int, bold: bool = False):
    """Load bundled document font (works on Windows/Linux servers)."""
    from PIL import ImageFont

    preferred = [
        os.path.join(FONTS_DIR, "arialbd.ttf" if bold else "arial.ttf"),
        "arialbd.ttf" if bold else "arial.ttf",
        # Windows system fonts
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        # Linux system fonts
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]

    for font_name in preferred:
        try:
            if os.path.isabs(font_name) and not os.path.exists(font_name):
                continue
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue

    # Try loaded from system by name only
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except:
        pass

    return ImageFont.load_default()


def _fit_doc_font(
    draw,
    text: str,
    max_width: int,
    start_size: int,
    bold: bool = False,
    min_size: int = 22,
):
    """Return the largest font size that fits max_width."""
    size = max(start_size, min_size)
    while size >= min_size:
        font = _load_doc_font(size, bold=bold)
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
        except Exception:
            w = len(text) * size * 0.55
        if w <= max_width:
            return font
        size -= 2
    return _load_doc_font(min_size, bold=bold)


def _wrap_text_to_width(draw, text: str, font, max_width: int) -> list[str]:
    """Wrap text into multiple lines that fit max_width."""
    words = (text or "").split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        try:
            bbox = draw.textbbox((0, 0), candidate, font=font)
            width = bbox[2] - bbox[0]
        except Exception:
            width = len(candidate) * 10
        if width <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


@dataclass
class StudentData:
    nama_lengkap: str
    nis: str
    nisn: str
    tempat_lahir: str
    tanggal_lahir: str
    jenis_kelamin: str
    alamat: str
    rt_rw: str
    kelurahan: str
    kecamatan: str
    kabupaten: str
    provinsi: str
    kelas: str
    tahun_ajaran: str
    github_email: str
    nim: str = ""
    fakultas: str = ""
    program_studi: str = ""
    profile_bio: str = ""
    profile_location: str = ""


@dataclass
class TeacherData:
    nama_lengkap: str
    nip: str
    employee_id: str
    tempat_lahir: str
    tanggal_lahir: str
    jenis_kelamin: str
    alamat: str
    rt_rw: str
    kelurahan: str
    kecamatan: str
    kabupaten: str
    provinsi: str
    bidang_studi: str
    posisi: str
    tahun_mengajar: str
    github_email: str
    profile_bio: str = ""
    profile_location: str = ""
    salary_base: int = 0
    salary_allowances: int = 0
    salary_total: int = 0
    salary_period: str = ""


def generate_student_data(
    github_email: str, school_code: str = "sma_negeri_1_majenang"
) -> StudentData:
    from location_data import get_locations_for_school

    nama, gender = generate_indonesian_name()
    nis = "".join(random.choices(string.digits, k=5))
    nisn = "00" + "".join(random.choices(string.digits, k=8))
    cities = [
        "Cilacap",
        "Majenang",
        "Purwokerto",
        "Yogyakarta",
        "Semarang",
        "Bandung",
        "Jakarta",
        "Surabaya",
    ]
    tempat = random.choice(cities)
    year = random.randint(2006, 2009)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    tanggal = f"{day:02d}-{month:02d}-{year}"
    jalan = random.choice(
        [
            "Jl. Raya Majenang",
            "Jl. Ahmad Yani",
            "Jl. Sudirman",
            "Jl. Diponegoro",
            "Jl. Gatot Subroto",
            "Jl. Pahlawan",
            "Jl. Merdeka",
        ]
    )
    alamat = f"{jalan} No.{random.randint(1, 150)}"
    rt_rw = f"{random.randint(1, 15):03d}/{random.randint(1, 10):03d}"

    # Generate location based on school proximity
    locations = get_locations_for_school(school_code)
    location = random.choice(locations)
    kelurahan = location["kelurahan"]
    kecamatan = location["kecamatan"]
    kabupaten = location["kabupaten"]
    provinsi = location["provinsi"]

    kelas = random.choice(["X", "XI", "XII"])

    # Generate profile bio
    current_year = 2026
    birth_year = year
    age = current_year - birth_year
    profile_bio = f"High school student (Grade {kelas}). Interested in technology and coding. Age {age}."

    # Generate profile location using the selected location data
    profile_location = f"{alamat}, {kelurahan}, {kabupaten}"

    return StudentData(
        nama_lengkap=nama,
        nis=nis,
        nisn=nisn,
        tempat_lahir=tempat,
        tanggal_lahir=tanggal,
        jenis_kelamin=gender,
        alamat=alamat,
        rt_rw=rt_rw,
        kelurahan=kelurahan,
        kecamatan=kecamatan,
        kabupaten=kabupaten,
        provinsi=provinsi,
        kelas=kelas,
        tahun_ajaran="2025/2026",
        github_email=github_email,
        profile_bio=profile_bio,
        profile_location=profile_location,
    )


UNY_STUDY_PROGRAMS: list[tuple[str, str]] = [
    ("Faculty of Education and Psychology", "Guidance and Counseling"),
    ("Faculty of Education and Psychology", "Educational Technology"),
    ("Faculty of Mathematics and Natural Sciences", "Mathematics Education"),
    ("Faculty of Mathematics and Natural Sciences", "Biology Education"),
    ("Faculty of Engineering", "Informatics Engineering Education"),
    ("Faculty of Engineering", "Electronics Engineering Education"),
    ("Faculty of Economics and Business", "Management"),
    ("Faculty of Economics and Business", "Accounting"),
    ("Faculty of Social Sciences", "Public Administration"),
    ("Faculty of Languages, Arts, and Culture", "English Language Education"),
    ("Faculty of Sports Sciences and Health", "Sports Coaching Education"),
]


def generate_university_student_data(
    github_email: str,
    university_code: str = "uny",
) -> StudentData:
    """Generate university-student profile for local manual testing only."""
    nama, gender = generate_indonesian_name()
    fakultas, program_studi = random.choice(UNY_STUDY_PROGRAMS)

    # 2026 range requested: first-year (~2007-2008), final-year (~2004-2005)
    birth_year = random.randint(2004, 2008)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    tanggal_lahir = f"{birth_day:02d}/{birth_month:02d}/{birth_year}"

    if birth_year >= 2007:
        intake_year = 2026
    elif birth_year <= 2005:
        intake_year = random.choice([2023, 2024])
    else:
        intake_year = 2025

    nim = f"{intake_year}{random.randint(1000, 9999)}"
    jalan = random.choice(
        [
            "Jl. Colombo",
            "Jl. Affandi",
            "Jl. Cempaka",
            "Jl. Anggrek",
            "Jl. Kenanga",
        ]
    )
    alamat = f"{jalan} No.{random.randint(1, 220)}"
    rt_rw = f"{random.randint(1, 15):03d}/{random.randint(1, 12):03d}"

    profile_bio = (
        f"University student at Universitas Negeri Yogyakarta. "
        f"{program_studi}, intake {intake_year}."
    )

    if university_code.strip().lower() == "uny":
        tempat_lahir = random.choice(
            ["Yogyakarta", "Sleman", "Bantul", "Kulon Progo", "Gunungkidul"]
        )
        kelurahan = "Caturtunggal"
        kecamatan = "Depok"
        kabupaten = "Sleman"
        provinsi = "DI Yogyakarta"
        profile_location = f"{alamat}, {kelurahan}, {kabupaten}"
    else:
        tempat_lahir = random.choice(["Yogyakarta", "Semarang", "Surakarta"])
        kelurahan = "Caturtunggal"
        kecamatan = "Depok"
        kabupaten = "Sleman"
        provinsi = "DI Yogyakarta"
        profile_location = alamat

    return StudentData(
        nama_lengkap=nama,
        nis="",
        nisn="",
        tempat_lahir=tempat_lahir,
        tanggal_lahir=tanggal_lahir,
        jenis_kelamin=gender,
        alamat=alamat,
        rt_rw=rt_rw,
        kelurahan=kelurahan,
        kecamatan=kecamatan,
        kabupaten=kabupaten,
        provinsi=provinsi,
        kelas=f"Intake {intake_year}",
        tahun_ajaran="2025/2026",
        github_email=github_email,
        nim=nim,
        fakultas=fakultas,
        program_studi=program_studi,
        profile_bio=profile_bio,
        profile_location=profile_location,
    )


def generate_teacher_data(
    github_email: str, school_code: str = "sma_negeri_1_majenang"
) -> TeacherData:
    """Generate random teacher data in Indonesian format"""
    from location_data import get_locations_for_school

    nama, gender = generate_indonesian_name()
    # Generate NIP (18 digits)

    # Generate NIP (18 digits)
    year_start = random.randint(1990, 2010)
    month_start = random.randint(1, 12)
    nip_base = f"{year_start}{month_start:02d}"
    nip = nip_base + "".join(random.choices(string.digits, k=14))

    # Employee ID
    employee_id = f"UT-{random.randint(100000, 999999)}"

    cities = [
        "Cilacap",
        "Majenang",
        "Purwokerto",
        "Yogyakarta",
        "Semarang",
        "Bandung",
        "Jakarta",
        "Surabaya",
    ]
    tempat = random.choice(cities)

    jalan = random.choice(
        [
            "Jl. Raya Majenang",
            "Jl. Ahmad Yani",
            "Jl. Sudirman",
            "Jl. Diponegoro",
            "Jl. Gatot Subroto",
            "Jl. Pahlawan",
            "Jl. Merdeka",
        ]
    )
    alamat = f"{jalan} No.{random.randint(1, 150)}"
    rt_rw = f"{random.randint(1, 15):03d}/{random.randint(1, 10):03d}"

    # Generate location based on school proximity
    locations = get_locations_for_school(school_code)
    location = random.choice(locations)
    kelurahan = location["kelurahan"]
    kecamatan = location["kecamatan"]
    kabupaten = location["kabupaten"]
    provinsi = location["provinsi"]

    # Fixed profile preference: Guru Senior only
    posisi = "Guru Senior"
    birth_year = random.randint(1978, 1990)
    exp_years = random.randint(12, 24)

    month = random.randint(1, 12)
    day = random.randint(1, 28)
    tanggal = f"{day:02d}-{month:02d}-{birth_year}"

    # Fixed subject cluster preference
    subjects_pool = ["Ilmu Komputer", "Informatika", "Sistem Informasi"]
    bidang_studi = random.choice(subjects_pool)

    tahun_mengajar = f"{exp_years} Tahun"

    # Generate profile bio
    subject_desc = {
        "Ilmu Komputer": "Computer Science",
        "Informatika": "Informatics",
        "Sistem Informasi": "Information Systems",
    }
    subject_en = subject_desc.get(bidang_studi, bidang_studi)
    profile_bio = f"{posisi} specializing in {subject_en}. Teaching advanced courses for {exp_years}+ years."

    # Generate profile location using the selected location data
    profile_location = f"{alamat}, {kelurahan}, {kabupaten}"

    # Generate salary (realistis untuk Guru Senior)
    salary_base = random.randint(5500000, 8000000)  # 5.5 - 8 juta gaji pokok
    salary_allowances = random.randint(1500000, 3000000)  # 1.5 - 3 juta tunjangan
    salary_total = salary_base + salary_allowances

    # Generate salary period (current month/year)
    from datetime import datetime

    now = datetime.now()
    months_id = [
        "Januari",
        "Februari",
        "Maret",
        "April",
        "Mei",
        "Juni",
        "Juli",
        "Agustus",
        "September",
        "Oktober",
        "November",
        "Desember",
    ]
    salary_period = f"Bulan {months_id[now.month - 1]} Tahun {now.year}"

    return TeacherData(
        nama_lengkap=nama,
        nip=nip,
        employee_id=employee_id,
        tempat_lahir=tempat,
        tanggal_lahir=tanggal,
        jenis_kelamin=gender,
        alamat=alamat,
        rt_rw=rt_rw,
        kelurahan=kelurahan,
        kecamatan=kecamatan,
        kabupaten=kabupaten,
        provinsi=provinsi,
        bidang_studi=bidang_studi,
        posisi=posisi,
        tahun_mengajar=tahun_mengajar,
        github_email=github_email,
        profile_bio=profile_bio,
        profile_location=profile_location,
        salary_base=salary_base,
        salary_allowances=salary_allowances,
        salary_total=salary_total,
        salary_period=salary_period,
    )


class GitHubSession:
    def __init__(self, cookies: dict):
        from urllib.parse import unquote

        self.session = requests.Session()
        for key, value in cookies.items():
            self.session.cookies.set(
                key, unquote(value), domain=".github.com", path="/"
            )
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "Dnt": "1",
                "Referer": "https://github.com/",
            }
        )
        self.username = None
        self.email = None
        self.name = None
        self.csrf_token = None

    def _debug_enabled(self) -> bool:
        return (os.getenv("GHS_DEBUG_LOG", "1") or "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _safe_preview(self, text: str, max_len: int = 4000) -> str:
        if not text:
            return ""
        clean = text.replace("\r", "")
        if len(clean) <= max_len:
            return clean
        return clean[:max_len] + f"\n...<truncated {len(clean) - max_len} chars>"

    def _mask_value(self, value: str, keep: int = 4) -> str:
        if value is None:
            return ""
        if len(value) <= keep * 2:
            return "*" * len(value)
        return value[:keep] + "..." + value[-keep:]

    def _write_http_debug_log(
        self, stage: str, payload: dict, response=None, error: str = ""
    ):
        if not self._debug_enabled():
            return

        try:
            logs_dir = os.path.join(BASE_DIR, "logs")
            os.makedirs(logs_dir, exist_ok=True)

            now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            username = (self.username or "unknown").replace("/", "_")
            file_path = os.path.join(logs_dir, f"ghs_{stage}_{username}_{now}.log")

            safe_payload = dict(payload or {})
            if "authenticity_token" in safe_payload:
                safe_payload["authenticity_token"] = self._mask_value(
                    str(safe_payload.get("authenticity_token", ""))
                )

            cookie_names = [c.name for c in self.session.cookies]

            req_info = {}
            res_info = {}
            html_snippet = ""
            if response is not None:
                req = getattr(response, "request", None)
                if req is not None:
                    req_headers = dict(req.headers or {})
                    if "Cookie" in req_headers:
                        req_headers["Cookie"] = "<masked>"
                    req_info = {
                        "method": req.method,
                        "url": req.url,
                        "headers": req_headers,
                        "body_preview": self._safe_preview(str(req.body or ""), 3000),
                    }

                res_info = {
                    "status_code": response.status_code,
                    "url": response.url,
                    "headers": dict(response.headers or {}),
                    "history": [
                        {
                            "status_code": h.status_code,
                            "url": h.url,
                            "location": h.headers.get("Location", ""),
                        }
                        for h in (response.history or [])
                    ],
                }
                html_snippet = self._safe_preview(response.text, 6000)

            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stage": stage,
                "username": self.username,
                "error": error,
                "cookie_names": cookie_names,
                "payload": safe_payload,
                "request": req_info,
                "response": res_info,
                "response_body_preview": html_snippet,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            # Logging must never break main flow.
            pass

    def get_user_info(self) -> dict | None:
        try:
            r = self.session.get(
                "https://github.com/", timeout=TIMEOUT, allow_redirects=True
            )
            if "login" in r.url:
                return None
            patterns = [
                r'data-login="([^"]+)"',
                r'"login":"([^"]+)"',
                r'<meta name="user-login" content="([^"]+)"',
            ]
            for p in patterns:
                m = re.search(p, r.text)
                if m:
                    self.username = m.group(1)
                    break
            if not self.username:
                return None

            # Name
            try:
                rp = self.session.get(
                    f"https://github.com/{self.username}", timeout=TIMEOUT
                )
                nm = re.search(
                    r'<span[^>]*itemprop="name"[^>]*>([^<]+)</span>', rp.text
                )
                if nm:
                    self.name = nm.group(1).strip()
            except:
                pass

            # Email
            try:
                r2 = self.session.get(
                    "https://github.com/settings/emails", timeout=TIMEOUT
                )
                for pat in [
                    r'value="([^"]+@[^"]+)"[^>]*data-primary="true"',
                    r'data-primary="true"[^>]*value="([^"]+@[^"]+)"',
                ]:
                    em = re.search(pat, r2.text)
                    if em and not em.group(1).endswith("@users.noreply.github.com"):
                        self.email = em.group(1).strip()
                        break
                if not self.email:
                    all_e = re.findall(
                        r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", r2.text
                    )
                    valid = [
                        e
                        for e in all_e
                        if not e.endswith("@github.com")
                        and not e.endswith("@users.noreply.github.com")
                        and "noreply" not in e.lower()
                    ]
                    if valid:
                        self.email = valid[0]
            except:
                pass

            # 2FA
            r3 = self.session.get(
                "https://github.com/settings/security", timeout=TIMEOUT
            )
            has_2fa = any(
                p.lower() in r3.text.lower()
                for p in [
                    "Two-factor authentication is <strong>on</strong>",
                    "Two-factor methods",
                    '"twoFactorEnabled":true',
                    "Reconfigure two-factor authentication",
                    "Authenticator app",
                    "SMS number",
                ]
            )

            # Billing
            r4 = self.session.get(
                "https://github.com/settings/billing/payment_information",
                timeout=TIMEOUT,
            )
            has_billing = bool(
                re.search(r'billing_first_name.*value="([^"]+)"', r4.text)
            )

            # Account age
            api_r = requests.get(
                f"https://api.github.com/users/{self.username}", timeout=TIMEOUT
            )
            age_days = 0
            if api_r.status_code == 200:
                ca = api_r.json().get("created_at", "")
                if ca:
                    created = datetime.fromisoformat(ca.replace("Z", "+00:00"))
                    age_days = (datetime.now(timezone.utc) - created).days

            csrf_m = re.search(r'<meta name="csrf-token" content="([^"]+)"', r.text)
            if csrf_m:
                self.csrf_token = csrf_m.group(1)

            return {
                "username": self.username,
                "name": self.name or self.username,
                "email": self.email,
                "has_2fa": has_2fa,
                "has_billing": has_billing,
                "age_days": age_days,
            }
        except:
            return None

    def check_application_status(self) -> dict:
        """
        Check current GitHub Education application status.
        Returns dict with keys:
          - status: 'pending' | 'approved' | 'rejected' | 'none'
          - app_type: 'Student' | 'Faculty' | None
          - submitted_at: str | None
        """
        try:
            r = self.session.get(
                "https://github.com/settings/education/benefits?page=1",
                timeout=TIMEOUT,
                allow_redirects=True,
            )
            if r.status_code == 404:
                r = self.session.get(
                    "https://github.com/settings/education/benefits",
                    timeout=TIMEOUT,
                    allow_redirects=True,
                )

            if r.status_code != 200:
                return {"status": "error"}

            text = r.text.lower()
            status = "none"

            if (
                "you have a current pending application" in text
                or "currently pending review" in text
                or ">pending<" in text
                or "pending application" in text
            ):
                status = "pending"
            elif (
                "awaiting benefits" in text
                or "your academic status has been approved" in text
            ):
                status = "approved"
            elif (
                "not able to verify your academic status" in text
                or "color-bg-danger" in text
                or "rejected" in text
                or "address the following issues" in text
            ):
                status = "rejected"
            elif (
                'data-show-dialog-id="education-benefits-dialog"' in text
                and 'disabled="disabled"' in text
            ):
                status = "pending"
            elif "developer_pack_applications/new" in text:
                status = "none"

            app_type = None
            if "application type:</strong> faculty" in text:
                app_type = "Faculty"
            elif "application type:</strong> student" in text:
                app_type = "Student"

            submitted_match = re.search(
                r"submitted ([\w\s]+ago)", r.text, re.IGNORECASE
            )
            submitted_at = submitted_match.group(1).strip() if submitted_match else None

            return {
                "status": status,
                "app_type": app_type,
                "submitted_at": submitted_at,
            }
        except:
            return {"status": "error"}

    def update_profile_name(
        self,
        full_name: str,
        profile_location: str | None = None,
        timezone_name: str = "Jakarta",
        display_local_time: bool = True,
        profile_bio: str | None = None,
        gender: str | None = None,
    ) -> tuple[bool, str]:
        try:
            r = self.session.get("https://github.com/settings/profile", timeout=TIMEOUT)
            if r.status_code != 200:
                return False, "Failed to open profile page"

            # Find the specific profile form to extract exact token and anti-bot fields
            forms = r.text.split("<form")
            profile_form = ""
            for f in forms:
                if (
                    'name="user[profile_name]"' in f
                    or 'name="user[profile_email]"' in f
                ):
                    profile_form = f
                    break

            if not profile_form:
                profile_form = r.text  # Fallback to entire page if not found

            # Extract authenticity_token
            token_match = re.search(
                r'name="authenticity_token"[^>]*value="([^"]+)"', profile_form
            )
            if not token_match:
                # Try with global fallback
                token_match = re.search(
                    r'name="authenticity_token"[^>]*value="([^"]+)"', r.text
                )

            if not token_match:
                return False, "authenticity_token tidak ditemukan"

            auth_token = token_match.group(1)

            # Profile email
            profile_email = ""
            email_match = re.search(
                r'name="user\[profile_email\]"[^>]*(?:value="([^"]*)"|selected[^>]*>([^<]+))',
                profile_form,
            )
            if email_match:
                profile_email = email_match.group(1) or email_match.group(2) or ""

            # Profile bio
            current_profile_bio = ""
            bio_match = re.search(
                r'name="user\[profile_bio\]"[^>]*>([^<]*)</textarea>', profile_form
            )
            if bio_match:
                current_profile_bio = html.unescape(bio_match.group(1))

            # Profile pronouns
            profile_pronouns = ""
            pronouns_match = re.search(
                r'name="user\[profile_pronouns\]"[^>]*value="([^"]*)"', profile_form
            )
            if pronouns_match:
                profile_pronouns = pronouns_match.group(1)

            gender_norm = (gender or "").strip().lower()
            if gender_norm in {
                "laki-laki",
                "laki laki",
                "pria",
                "male",
                "man",
                "cowok",
            }:
                profile_pronouns_final = "he/him"
            elif gender_norm in {
                "perempuan",
                "wanita",
                "female",
                "woman",
                "cewek",
            }:
                profile_pronouns_final = "she/her"
            else:
                profile_pronouns_final = profile_pronouns

            # Profile blog
            profile_blog = ""
            blog_match = re.search(
                r'name="user\[profile_blog\]"[^>]*value="([^"]*)"', profile_form
            )
            if blog_match:
                profile_blog = blog_match.group(1)

            # Profile company
            profile_company = ""
            company_match = re.search(
                r'name="user\[profile_company\]"[^>]*value="([^"]*)"', profile_form
            )
            if company_match:
                profile_company = company_match.group(1)

            # Profile location
            current_profile_location = ""
            location_match = re.search(
                r'name="user\[profile_location\]"[^>]*value="([^"]*)"', profile_form
            )
            if location_match:
                current_profile_location = html.unescape(location_match.group(1))

            # Timezone
            timezone_match = re.search(
                r'name="user\[profile_local_time_zone_name\]"[^>]*value="([^"]*)"',
                profile_form,
            )
            timezone = (
                timezone_match.group(1)
                if timezone_match
                else "International Date Line West"
            )

            # Display local time
            display_local_time_match = re.search(
                r'name="user\[profile_display_local_time_zone\]"[^>]*value="([^"]*)"',
                profile_form,
            )
            profile_display_local_time_zone = (
                display_local_time_match.group(1) if display_local_time_match else "1"
            )

            # Apply overrides requested by workflow
            profile_location_input = (
                profile_location.strip() if profile_location is not None else None
            )
            if profile_location_input:
                profile_location_final = profile_location_input[:100]
            else:
                profile_location_final = current_profile_location

            profile_bio_input = profile_bio.strip() if profile_bio is not None else None
            if profile_bio_input:
                profile_bio_final = profile_bio_input[:160]
            else:
                profile_bio_final = current_profile_bio

            timezone_final = timezone_name.strip() if timezone_name else timezone
            display_local_time_final = "1" if display_local_time else "0"

            # Required field (anti-bot)
            required_match = re.search(
                r'name="(required_field_\d+)"[^>]*value="([^"]*)"', profile_form
            )
            required_field_name = (
                required_match.group(1) if required_match else "required_field_0"
            )
            required_field_value = required_match.group(2) if required_match else ""

            # Timestamp fields
            import time

            timestamp = str(int(time.time() * 1000))
            timestamp_secret_match = re.search(
                r'name="timestamp_secret"[^>]*value="([^"]+)"', profile_form
            )
            timestamp_secret = (
                timestamp_secret_match.group(1) if timestamp_secret_match else ""
            )

            # Build data with ALL fields (use list of tuples to allow duplicate keys)
            data = [
                ("_method", "put"),
                ("authenticity_token", auth_token),
                ("user[profile_name]", full_name),
                ("user[profile_email]", profile_email),
                ("user[profile_bio]", profile_bio_final),
                ("user[profile_pronouns]", profile_pronouns_final),
                ("user[profile_blog]", profile_blog),
            ]

            # Add 4 social account slots (must be in specific order)
            for i in range(4):
                data.append(("user[profile_social_accounts][][key]", "generic"))
                data.append(("user[profile_social_accounts][][url]", ""))

            # Add remaining fields
            data.extend(
                [
                    ("user[profile_company]", profile_company),
                    ("user[profile_location]", profile_location_final),
                    (
                        "user[profile_display_local_time_zone]",
                        display_local_time_final or profile_display_local_time_zone,
                    ),
                    ("user[profile_local_time_zone_name]", timezone_final),
                    (required_field_name, required_field_value),
                    ("timestamp", timestamp),
                    ("timestamp_secret", timestamp_secret),
                ]
            )
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://github.com/settings/profile",
                "Origin": "https://github.com",
            }
            r2 = self.session.post(
                f"https://github.com/users/{self.username}",
                data=data,
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=False,
            )
            if r2.status_code in [200, 302, 303]:
                return True, f"Profile updated: {full_name}"
            return False, f"HTTP {r2.status_code}"
        except Exception as e:
            return False, str(e)

    def update_billing_info(self, student: StudentData) -> tuple[bool, str]:
        try:
            r = self.session.get(
                "https://github.com/settings/billing/payment_information",
                timeout=TIMEOUT,
            )
            if r.status_code != 200:
                return False, "Failed to open billing page"

            forms = r.text.split("<form")
            bf = ""
            for f in forms:
                if 'name="billing_contact[first_name]"' in f:
                    bf = f
                    break
            if not bf:
                bf = r.text

            tm = re.search(r'name="authenticity_token"[^>]*value="([^"]+)"', bf)
            if not tm:
                tm = re.search(r'name="authenticity_token"[^>]*value="([^"]+)"', r.text)
            if not tm:
                return False, "Token not found"

            # Mirror browser behavior: carry hidden form fields from current billing form.
            # This prevents 422 when GitHub adds/changes required hidden inputs.
            hidden_fields = {}
            for m in re.finditer(
                r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"[^>]*>',
                bf,
                re.IGNORECASE,
            ):
                hidden_fields[m.group(1)] = html.unescape(m.group(2))

            # Keep legacy identity mapping: firstname = first token, lastname = full remaining tokens.
            parts = student.nama_lengkap.split()
            fn = parts[0] if parts else "Budi"
            ln = " ".join(parts[1:]) if len(parts) > 1 else fn

            data = dict(hidden_fields)
            data.update(
                {
                    "submit": "Save billing information",
                    "authenticity_token": tm.group(1),
                    "billing_contact[first_name]": fn,
                    "billing_contact[last_name]": ln,
                    "billing_contact[address1]": student.alamat,
                    "billing_contact[address2]": f"RT {student.rt_rw}, Kel. {student.kelurahan}",
                    "billing_contact[city]": student.kabupaten,
                    "billing_contact[country_code]": "ID",
                    "billing_contact[region]": student.provinsi,
                    "billing_contact[postal_code]": "53257",
                    "vat_code": "",
                    "form_loaded_from": "BILLING_SETTINGS",
                    "target": "user",
                    "contact_type": "billing",
                    "return_to": "/settings/billing/payment_information",
                }
            )

            # Keep fallback for compatibility if hidden field is not present in form.
            data.setdefault("user_id", self.username)

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://github.com/settings/billing/payment_information",
                "Origin": "https://github.com",
            }

            r2 = self.session.post(
                "https://github.com/account/contact",
                data=data,
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=False,
            )

            if r2.status_code in [302, 303]:
                self._write_http_debug_log(
                    stage="billing_success",
                    payload=data,
                    response=r2,
                )
                return True, "Billing updated!"

            if r2.status_code == 422:
                snippets = re.findall(
                    r'<div[^>]*class="[^"]*(?:error|flash-error|FormControl-inlineValidation)[^"]*"[^>]*>(.*?)</div>',
                    r2.text,
                    re.IGNORECASE | re.DOTALL,
                )
                err = "Validation failed"
                for raw in snippets:
                    clean = re.sub(r"<[^>]+>", " ", raw)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    if clean:
                        err = clean
                        break

                detail = (
                    f"first='{fn}', last='{ln}', city='{student.kabupaten}', "
                    f"region='{student.provinsi}', postal='53257'"
                )
                self._write_http_debug_log(
                    stage="billing_422",
                    payload=data,
                    response=r2,
                    error=err,
                )
                return False, f"HTTP 422: {err} | payload: {detail}"

            self._write_http_debug_log(
                stage="billing_http_error",
                payload=data,
                response=r2,
                error=f"HTTP {r2.status_code}",
            )
            return False, f"HTTP {r2.status_code}"
        except Exception as e:
            self._write_http_debug_log(
                stage="billing_exception",
                payload={
                    "name": student.nama_lengkap,
                    "alamat": student.alamat,
                    "kabupaten": student.kabupaten,
                    "provinsi": student.provinsi,
                },
                error=str(e),
            )
            return False, str(e)

    def check_application_status(self) -> dict:
        """
        Check current GitHub Education application status.
        Returns dict with keys:
          - status: 'pending' | 'approved' | 'rejected' | 'none'
          - app_type: 'Student' | 'Faculty' | None
          - submitted_at: str | None
          - rejected_on: str | None
          - reject_reasons: list[str]
          - reject_intro: str | None
        """
        try:

            def _fetch_benefits_html() -> tuple[str, str, str | None]:
                # IMPORTANT: /settings/education returns 404 in current flow.
                # Only use benefits endpoints.
                urls = [
                    "https://github.com/settings/education/benefits?page=1",
                    "https://github.com/settings/education/benefits",
                ]
                last_error = None

                for url in urls:
                    try:
                        r = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
                    except Exception as exc:
                        last_error = f"request error for {url}: {exc}"
                        continue

                    if r.status_code != 200:
                        last_error = f"HTTP {r.status_code} for {url}"
                        continue

                    final_url = str(getattr(r, "url", "") or "")
                    final_url_lower = final_url.lower()
                    if (
                        "/login" in final_url_lower
                        or "session" in final_url_lower
                        and "new" in final_url_lower
                    ):
                        last_error = f"session expired or login required ({final_url})"
                        continue

                    page = r.text or ""
                    if not page.strip():
                        last_error = f"empty body for {url}"
                        continue

                    return page, url, None

                return "", "", last_error

            page, source_url, fetch_error = _fetch_benefits_html()
            if not page:
                return {
                    "status": "error",
                    "app_type": None,
                    "submitted_at": None,
                    "rejected_on": None,
                    "reject_reasons": [],
                    "reject_intro": None,
                    "status_full_text": "",
                    "error": fetch_error or "failed to load benefits page",
                    "source_url": source_url,
                }

            text = page.lower()

            top_summary_status = None
            top_summary_submitted = None
            top_summary_block = re.search(
                r'<details[^>]*class="[^"]*billing-box-accordion[^"]*"[^>]*>\s*'
                r"<summary[^>]*>(.*?)</summary>",
                page,
                re.IGNORECASE | re.DOTALL,
            )
            if top_summary_block:
                summary_html = top_summary_block.group(1)
                top_status_match = re.search(
                    r">\s*(Approved|Rejected|Pending)\s*<",
                    summary_html,
                    re.IGNORECASE,
                )
                if top_status_match:
                    top_summary_status = top_status_match.group(1).strip().lower()

                top_submitted_match = re.search(
                    r"Submitted\s+([^<]+)<",
                    summary_html,
                    re.IGNORECASE,
                )
                if top_submitted_match:
                    top_summary_submitted = top_submitted_match.group(1).strip()

            def _clean_html_block(fragment: str) -> str:
                block = fragment or ""
                block = re.sub(r"<br\\s*/?>", "\n", block, flags=re.IGNORECASE)
                block = re.sub(r"</p>", "\n", block, flags=re.IGNORECASE)
                block = re.sub(r"</li>", "\n", block, flags=re.IGNORECASE)
                block = re.sub(r"<li[^>]*>", "• ", block, flags=re.IGNORECASE)
                block = re.sub(r"<[^>]+>", "", block)
                block = html.unescape(block)
                block = re.sub(r"\n\s+", "\n", block)
                block = re.sub(r"[ \t]+", " ", block)
                block = re.sub(r"\n{3,}", "\n\n", block)
                return block.strip()

            status_cards = re.findall(
                r'<div[^>]*class="[^"]*Box[^"]*mx-4[^"]*mb-4[^"]*mt-2[^"]*"[^>]*>\s*'
                r'<div[^>]*class="[^"]*Box-header[^"]*"[^>]*>(.*?)</div>\s*'
                r'<div[^>]*class="[^"]*Box-body[^"]*"[^>]*>(.*?)</div>',
                page,
                re.IGNORECASE | re.DOTALL,
            )

            status = "none"
            status_confident = False
            status_full_text = ""
            app_type = None
            submitted_at = top_summary_submitted

            if top_summary_status in {"approved", "rejected", "pending"}:
                status = top_summary_status
                status_confident = True

            if status_cards:
                latest_header_html, latest_body_html = status_cards[0]
                latest_header = _clean_html_block(latest_header_html)
                latest_body = _clean_html_block(latest_body_html)
                latest_header_l = latest_header.lower()
                latest_body_l = latest_body.lower()

                status_full_text = (
                    f"{latest_header}\n\n{latest_body}".strip()
                    if latest_body
                    else latest_header
                )

                if status == "none":
                    if "rejected" in latest_header_l:
                        status = "rejected"
                        status_confident = True
                    elif (
                        "approved" in latest_header_l
                        or "awaiting benefits" in latest_header_l
                        or "verified (benefits available)" in latest_header_l
                        or "approved on" in latest_header_l
                    ):
                        status = "approved"
                        status_confident = True
                    elif "pending" in latest_header_l:
                        status = "pending"
                        status_confident = True
                    elif "applied on" in latest_header_l:
                        status = "pending"
                        status_confident = True
                    elif (
                        "currently pending review" in latest_body_l
                        or "current pending application" in latest_body_l
                        or "application has been received" in latest_body_l
                        or "under review" in latest_body_l
                    ):
                        status = "pending"
                        status_confident = True
                    elif (
                        "academic status has been approved" in latest_body_l
                        or "benefits available" in latest_body_l
                    ):
                        status = "approved"
                        status_confident = True
                    elif (
                        "not able to verify your academic status" in latest_body_l
                        or "address the following issues" in latest_body_l
                    ):
                        status = "rejected"
                        status_confident = True

                app_match = re.search(
                    r"Application Type:</strong>\s*(Student|Faculty)",
                    latest_header_html,
                    re.IGNORECASE,
                )
                if app_match:
                    app_type = app_match.group(1).title()

                submitted_match = re.search(
                    r"Submitted\s+([^<]+)<",
                    latest_header_html,
                    re.IGNORECASE,
                )
                if submitted_match:
                    submitted_at = submitted_match.group(1).strip()

            if status == "none":
                if (
                    "you have a current pending application" in text
                    or "currently pending review" in text
                    or "application has been received" in text
                    or "under review" in text
                    or ("application type:" in text and "applied on" in text)
                ):
                    status = "pending"
                    status_confident = True
                elif (
                    "awaiting benefits" in text
                    or "verified (benefits available)" in text
                    or "your academic status has been approved" in text
                ):
                    status = "approved"
                    status_confident = True
                elif (
                    "not able to verify your academic status" in text
                    or "unable to verify your academic" in text
                    or "application has been rejected" in text
                    or "address the following issues" in text
                ):
                    status = "rejected"
                    status_confident = True

            rejected_on = None
            reject_intro = None
            reject_reasons: list[str] = []

            if status == "rejected":
                rejected_on_match = re.search(
                    r"<strong>Rejected</strong>\s*on\s*([^<]+)</span>",
                    page,
                    re.IGNORECASE,
                )
                if rejected_on_match:
                    rejected_on = rejected_on_match.group(1).strip()

                intro_match = re.search(
                    r"<div[^>]*class=\"Box-body\"[^>]*>\s*<strong>(.*?)</strong>",
                    page,
                    re.IGNORECASE | re.DOTALL,
                )
                if intro_match:
                    reject_intro = html.unescape(
                        re.sub(r"<[^>]+>", "", intro_match.group(1))
                    ).strip()

                reasons_block = re.search(
                    r"<div[^>]*class=\"markdown-body[^\"]*\"[^>]*>(.*?)</div>",
                    page,
                    re.IGNORECASE | re.DOTALL,
                )
                if reasons_block:
                    for li in re.findall(
                        r"<li>(.*?)</li>",
                        reasons_block.group(1),
                        re.IGNORECASE | re.DOTALL,
                    ):
                        line = re.sub(r"<[^>]+>", "", li)
                        line = html.unescape(re.sub(r"\s+", " ", line)).strip()
                        if line:
                            reject_reasons.append(line)
            elif status == "none":
                # Fallback: if rejection reasons block exists, this is effectively rejected
                reasons_block = re.search(
                    r"<div[^>]*class=\"markdown-body[^\"]*\"[^>]*>(.*?)</div>",
                    page,
                    re.IGNORECASE | re.DOTALL,
                )
                if reasons_block:
                    status = "rejected"
                    for li in re.findall(
                        r"<li>(.*?)</li>",
                        reasons_block.group(1),
                        re.IGNORECASE | re.DOTALL,
                    ):
                        line = re.sub(r"<[^>]+>", "", li)
                        line = html.unescape(re.sub(r"\s+", " ", line)).strip()
                        if line:
                            reject_reasons.append(line)

            return {
                "status": status,
                "status_confident": status_confident,
                "app_type": app_type,
                "submitted_at": submitted_at,
                "rejected_on": rejected_on,
                "reject_reasons": reject_reasons,
                "reject_intro": reject_intro,
                "status_full_text": status_full_text,
                "source_url": source_url,
            }
        except Exception:
            return {
                "status": "error",
                "app_type": None,
                "submitted_at": None,
                "rejected_on": None,
                "reject_reasons": [],
                "reject_intro": None,
                "status_full_text": "",
                "error": "unexpected parser exception",
            }

    def submit_application(
        self,
        identity: "StudentData | TeacherData",
        id_card_base64: str,
        app_type: str = "student",
        school_profile: Optional[SchoolProfile] = None,
    ) -> tuple:
        try:
            def _confirm_submission_status(max_checks: int = 3) -> str:
                """Poll status shortly to avoid false positive submit success."""
                for idx in range(max_checks):
                    if idx > 0:
                        human_delay(1.5, 3.5)
                    cs = self.check_application_status().get("status", "none")
                    if cs in {"pending", "approved", "rejected"}:
                        return cs
                return "none"

            school = resolve_school_profile(school_profile=school_profile)

            # Simulate human opening the form page
            r = self.session.get(
                "https://github.com/settings/education/developer_pack_applications/new",
                timeout=TIMEOUT,
            )
            if r.status_code != 200:
                return False, "Failed to open application form"

            # Human would take time to read the form (2-5 seconds)
            human_delay(2.0, 5.0)

            if not id_card_base64:
                return False, "photo_proof kosong (ID card base64 kosong)"

            forms = r.text.split("<form")
            application_form = ""
            for f in forms:
                if "developer_pack_applications" in f and "dev_pack_form" in f:
                    application_form = f
                    break
            if not application_form:
                application_form = r.text

            # Find authenticity_token from the form page
            tm = re.search(
                r'name="authenticity_token"[^>]*value="([^"]+)"', application_form
            )
            if not tm:
                tm = re.search(
                    r'name="authenticity_token"[^>]*value="([^"]+)"', r.text
                )
            if not tm:
                return False, "Token not found"

            controlled_keys = {
                "submit",
                "authenticity_token",
                "dev_pack_form[proof_type]",
                "dev_pack_form[photo_proof]",
                "dev_pack_form[application_type]",
                "dev_pack_form[browser_location]",
                "dev_pack_form[camera_required]",
                "dev_pack_form[email_domains]",
                "dev_pack_form[latitude]",
                "dev_pack_form[location_shared]",
                "dev_pack_form[longitude]",
                "dev_pack_form[new_school]",
                "dev_pack_form[override_distance_limit]",
                "dev_pack_form[school_email]",
                "dev_pack_form[school_name]",
                "dev_pack_form[selected_school_id]",
                "dev_pack_form[two_factor_required]",
                "dev_pack_form[user_too_far_from_school]",
                "dev_pack_form[utm_content]",
                "dev_pack_form[utm_source]",
                "dev_pack_form[form_variant]",
            }

            hidden_fields: list[tuple[str, str]] = []
            for m in re.finditer(
                r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"[^>]*>',
                application_form,
                re.IGNORECASE,
            ):
                name = m.group(1)
                if name in controlled_keys:
                    continue
                hidden_fields.append((name, html.unescape(m.group(2))))

            normalized_type = (app_type or "student").strip().lower()
            if normalized_type in {"teacher", "faculty"}:
                proof_type = "1. Dated school ID"
                application_type = "faculty"
                # For teacher: random smartphone device (same as student)
                random_device = get_random_phone_model()
                # Generate filename matching the device's camera pattern
                random_filename = generate_realistic_filename(random_device)
            else:
                proof_type = "3. Dated enrollment letter on school letterhead"
                application_type = "student"
                # For student: random smartphone device
                random_device = get_random_phone_model()
                # Generate filename matching the device's camera pattern
                random_filename = generate_realistic_filename(random_device)

            optimized_b64 = _optimize_proof_image_base64(id_card_base64)

            photo_proof = json.dumps(
                {
                    "image": f"data:image/jpeg;base64,{optimized_b64}",
                    "metadata": {
                        "filename": random_filename,
                        "type": "camera",
                        "mimeType": "image/jpeg",
                        "deviceLabel": random_device,
                    },
                },
                separators=(",", ":"),
            )

            browser_location = json.dumps(
                {
                    "latitude": school.latitude,
                    "longitude": school.longitude,
                },
                separators=(",", ":"),
            )

            # List of tuples to preserve order + allow duplicate keys (submit & form_variant)
            data = list(hidden_fields)
            data.extend(
                [
                    ("submit", "Submit Application"),
                    ("authenticity_token", tm.group(1)),
                    ("dev_pack_form[proof_type]", proof_type),
                    ("dev_pack_form[photo_proof]", photo_proof),
                    ("dev_pack_form[application_type]", application_type),
                    ("dev_pack_form[browser_location]", browser_location),
                    ("dev_pack_form[camera_required]", "true"),
                    ("dev_pack_form[email_domains]", "[]"),
                    ("dev_pack_form[latitude]", school.latitude),
                    ("dev_pack_form[location_shared]", "true"),
                    ("dev_pack_form[longitude]", school.longitude),
                    ("dev_pack_form[new_school]", "false"),
                    ("dev_pack_form[override_distance_limit]", "false"),
                    (
                        "dev_pack_form[school_email]",
                        (getattr(identity, "github_email", "") or self.email or "").strip(),
                    ),
                    ("dev_pack_form[school_name]", school.name),
                    ("dev_pack_form[selected_school_id]", school.github_school_id),
                    ("dev_pack_form[two_factor_required]", "false"),
                    ("dev_pack_form[user_too_far_from_school]", "false"),
                    ("dev_pack_form[utm_content]", ""),
                    ("dev_pack_form[utm_source]", ""),
                    ("dev_pack_form[form_variant]", "upload_proof_form"),
                    ("submit", "Submit Application"),
                ]
            )

            # Simulate human reviewing filled form before clicking submit (1-4 seconds)
            random_think_time()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://github.com/settings/education/developer_pack_applications/new",
                "Origin": "https://github.com",
            }

            # Final micro-delay before actual submission (human clicking)
            human_delay(0.2, 0.8)

            r2 = self.session.post(
                "https://github.com/settings/education/developer_pack_applications",
                data=data,
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=False,
            )
            if r2.status_code in [302, 303]:
                confirmed_status = _confirm_submission_status(max_checks=3)
                if confirmed_status in {"pending", "approved"}:
                    self._write_http_debug_log(
                        stage="submit_success",
                        payload={k: v for k, v in data if k != "dev_pack_form[photo_proof]"},
                        response=r2,
                    )
                    return True, confirmed_status

                redirect_to = (r2.headers.get("Location") or "").lower()
                self._write_http_debug_log(
                    stage="submit_redirect_unconfirmed",
                    payload={k: v for k, v in data if k != "dev_pack_form[photo_proof]"},
                    response=r2,
                    error=f"status={confirmed_status}, location={redirect_to}",
                )
                if "developer_pack_applications/new" in redirect_to:
                    return False, "redirected_back_to_form"
                return False, "submission_not_confirmed"
            elif r2.status_code == 200:
                t = r2.text.lower()
                if "has not been verified" in t and "school email" in t:
                    self._write_http_debug_log(
                        stage="submit_school_email_unverified",
                        payload={k: v for k, v in data if k != "dev_pack_form[photo_proof]"},
                        response=r2,
                    )
                    return False, "school_email_not_verified"

                # If there are form validation errors, those prevent submission
                if "is invalid" in t or "can't be blank" in t or "is not included" in t:
                    err = re.search(
                        r'<div[^>]*class="[^"]*error[^"]*"[^>]*>([^<]+)', r2.text
                    )
                    self._write_http_debug_log(
                        stage="submit_form_error",
                        payload={k: v for k, v in data if k != "dev_pack_form[photo_proof]"},
                        response=r2,
                    )
                    return False, err.group(1).strip() if err else "form_error"

                # Some GitHub variants return 200 on successful submission.
                success_markers = [
                    "currently pending review",
                    "you have a current pending application",
                    "application has been received",
                    "application submitted",
                    "pending application",
                ]
                if any(marker in t for marker in success_markers):
                    self._write_http_debug_log(
                        stage="submit_success_200",
                        payload={k: v for k, v in data if k != "dev_pack_form[photo_proof]"},
                        response=r2,
                    )
                    return True, "pending"

                # Fetch actual status from dashboard to avoid reading history
                cs = _confirm_submission_status(max_checks=4)

                if cs == "approved":
                    return True, "approved"
                elif cs == "pending":
                    return True, "pending"
                elif cs == "rejected":
                    return False, "rejected"

                # Avoid false positive: no success marker and status still none.
                self._write_http_debug_log(
                    stage="submit_unconfirmed_200",
                    payload={k: v for k, v in data if k != "dev_pack_form[photo_proof]"},
                    response=r2,
                    error="no success marker and status remains none",
                )
                return False, "submission_not_confirmed"

            current_status = self.check_application_status()
            cs = current_status.get("status", "none")
            if cs in {"pending", "approved"}:
                return True, cs

            detail = ""
            if r2.text:
                m = re.search(
                    r'<div[^>]*class="[^"]*(?:flash-error|error|flash-full)[^"]*"[^>]*>(.*?)</div>',
                    r2.text,
                    re.IGNORECASE | re.DOTALL,
                )
                if m:
                    detail = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            self._write_http_debug_log(
                stage="submit_failed",
                payload={k: v for k, v in data if k != "dev_pack_form[photo_proof]"},
                response=r2,
            )
            if detail:
                return False, f"HTTP {r2.status_code}: {detail}"
            return False, f"HTTP {r2.status_code}"
        except Exception as e:
            return False, str(e)


def parse_cookies(cookie_string: str) -> dict:
    """Parse cookies from string, handling full headers or single values"""
    cookies = {}

    # Clean up string
    cookie_string = cookie_string.strip()
    if cookie_string.lower().startswith("cookie:"):
        cookie_string = cookie_string[7:].strip()

    # Handle key=value pairs (either split by ; or single)
    if "=" in cookie_string:
        items = cookie_string.split(";")
        for item in items:
            item = item.strip()
            if "=" in item:
                parts = item.split("=", 1)
                key = parts[0].strip()
                val = parts[1].strip()
                # Ignore path, domain, secure etc if they appear (common in raw Set-Cookie)
                if key.lower() not in [
                    "path",
                    "domain",
                    "expires",
                    "samesite",
                    "secure",
                    "httponly",
                ]:
                    cookies[key] = val
    else:
        # Fallback: treat as raw user_session value
        if cookie_string:
            cookies["user_session"] = cookie_string

    return cookies


def create_university_student_proof_base64(
    student: StudentData,
    school_profile: Optional[SchoolProfile] = None,
) -> str:
    """Create university proof using the same layout logic as create_id_card_base64."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        import base64
        import random as rnd

        school = resolve_school_profile(school_profile=school_profile)
        SCHOOL_NAME = school.name
        SCHOOL_ADDRESS = school.address
        SCHOOL_PHONE = school.phone
        PRINCIPAL_NAME = school.principal_name or "Direktorat Akademik"
        PRINCIPAL_NIP = school.principal_nip or "-"
        school_city = school.city or "Yogyakarta"

        width, height = 1200, 900
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        ft = _load_doc_font(26, bold=False)
        fh = _load_doc_font(21, bold=True)
        fb = _load_doc_font(16, bold=False)
        fs = _load_doc_font(14, bold=False)
        fx = _load_doc_font(12, bold=False)

        logo = None
        logo_path = _resolve_logo_path(school.logo_path)
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
            except Exception:
                logo = None

        # ID Card (left) - same geometry/style as student SMA
        ix, iy, iw, ih = 50, 50, 480, 800
        draw.rectangle([ix, iy, ix + iw, iy + ih], outline="black", width=3)
        draw.rectangle([ix, iy, ix + iw, iy + 100], fill=(0, 51, 102))

        cx = ix + iw // 2
        if logo:
            logo_w = 60
            logo_aspect = logo.height / logo.width
            logo_h = int(logo_w * logo_aspect)
            logo_small = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            img.paste(logo_small, (cx - logo_w // 2, iy + 50 - logo_h // 2), logo_small)
        else:
            draw.ellipse(
                [cx - 30, iy + 20, cx + 30, iy + 80],
                fill="white",
                outline="gold",
                width=2,
            )

        ty = iy + 120
        draw.text((cx, ty), "KARTU MAHASISWA", fill="black", font=ft, anchor="mm")
        draw.text((cx, ty + 30), SCHOOL_NAME, fill="black", font=fh, anchor="mm")
        draw.text(
            (cx, ty + 55),
            f"Tahun Akademik {student.tahun_ajaran or '-'}",
            fill="black",
            font=fs,
            anchor="mm",
        )

        dy, dx, lh = ty + 100, ix + 35, 38
        for i, (lbl, val) in enumerate(
            [
                ("Nama", student.nama_lengkap),
                ("NIM", student.nim or "-"),
                ("Fakultas", student.fakultas or "-"),
                ("Prodi", student.program_studi or "-"),
                ("Angkatan", student.kelas or "-"),
                ("TTL", f"{student.tempat_lahir}, {student.tanggal_lahir}"),
            ]
        ):
            y = dy + i * lh
            draw.text((dx, y), lbl, fill="black", font=fb)
            draw.text((dx + 95, y), f": {val}", fill="black", font=fb)

        fy = iy + ih - 80
        draw.text((cx, fy), "Direktorat Akademik", fill="black", font=fs, anchor="mm")
        draw.text((cx, fy + 25), SCHOOL_NAME, fill="black", font=fs, anchor="mm")

        # Letter (right) - same geometry/style as student SMA
        sx = ix + iw + 60
        sy = 50
        sw = width - sx - 50
        draw.rectangle([sx, sy, sx + sw, sy + 800], outline="black", width=2)
        ky = sy + 25
        scx = sx + sw // 2

        draw.text(
            (scx, ky),
            "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET, DAN TEKNOLOGI",
            fill="black",
            font=fx,
            anchor="mm",
        )
        draw.text(
            (scx, ky + 20),
            "DIREKTORAT AKADEMIK UNIVERSITAS",
            fill="black",
            font=fx,
            anchor="mm",
        )

        if logo:
            logo_w = 40
            logo_aspect = logo.height / logo.width
            logo_h = int(logo_w * logo_aspect)
            logo_small = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            img.paste(logo_small, (sx + 40, ky + 10), logo_small)

        draw.text((scx, ky + 45), SCHOOL_NAME, fill="black", font=fh, anchor="mm")
        ay = ky + 70
        draw.text((scx, ay), SCHOOL_ADDRESS, fill="black", font=fx, anchor="mm")
        contact = f"Telp: {SCHOOL_PHONE}"
        if school.email:
            contact = f"{contact} | Email: {school.email}"
        draw.text((scx, ay + 18), contact, fill="black", font=fx, anchor="mm")

        ly = ay + 35
        draw.line([(sx + 25, ly), (sx + sw - 25, ly)], fill="black", width=2)
        draw.line([(sx + 25, ly + 3), (sx + sw - 25, ly + 3)], fill="black", width=1)

        tsy = ly + 40
        draw.text(
            (scx, tsy),
            "SURAT KETERANGAN MAHASISWA AKTIF",
            fill="black",
            font=fh,
            anchor="mm",
        )
        nomor = f"{rnd.randint(100, 999)}/SKMA/{datetime.now().year}"
        draw.text((scx, tsy + 25), f"Nomor: {nomor}", fill="black", font=fx, anchor="mm")

        cy2 = tsy + 55
        cx2 = sx + 25
        draw.text(
            (cx2, cy2),
            f"Yang bertanda tangan di bawah ini, pihak akademik {SCHOOL_NAME},",
            fill="black",
            font=fx,
        )
        draw.text((cx2, cy2 + 15), "dengan ini menerangkan bahwa:", fill="black", font=fx)

        dsy = cy2 + 40
        dlh = 18
        gender_map = {"L": "Laki-laki", "P": "Perempuan"}
        gender_full = gender_map.get((student.jenis_kelamin or "").strip().upper(), student.jenis_kelamin or "-")
        for i, (lbl, val) in enumerate(
            [
                ("Nama", f": {student.nama_lengkap}"),
                ("NIM", f": {student.nim or '-'}"),
                ("TTL", f": {student.tempat_lahir}, {student.tanggal_lahir}"),
                ("Jenis Kelamin", f": {gender_full}"),
                ("Fakultas", f": {student.fakultas or '-'}"),
                ("Program Studi", f": {student.program_studi or '-'}"),
                ("Tahun Akademik", f": {student.tahun_ajaran or '-'}"),
            ]
        ):
            draw.text((cx2, dsy + i * dlh), lbl, fill="black", font=fx)
            draw.text((cx2 + 140, dsy + i * dlh), val, fill="black", font=fx)

        py = dsy + 7 * dlh + 22
        lines = [
            f"Adalah benar merupakan mahasiswa aktif di {SCHOOL_NAME.upper()} pada tahun",
            f"akademik {student.tahun_ajaran or '-'} dan terdaftar pada program studi",
            f"{student.program_studi or '-'} di {student.fakultas or '-'}.",
            "",
            "Yang bersangkutan tercatat aktif dalam sistem akademik kampus dengan",
            "status mahasiswa aktif dan tidak sedang menjalani cuti akademik.",
            "Surat ini diberikan untuk keperluan verifikasi status akademik,",
            "administrasi kampus, pendaftaran program, beasiswa, dan benefit",
            "pendidikan lain yang mensyaratkan bukti aktif sebagai mahasiswa.",
            "",
            "Data identitas pada surat ini disesuaikan dengan data mahasiswa yang",
            "tercatat dalam administrasi akademik universitas dan dapat dilakukan",
            "konfirmasi melalui pihak akademik pada jam kerja resmi kampus.",
            "",
            "Demikian surat keterangan ini dibuat dengan sebenar-benarnya untuk",
            "dipergunakan sebagaimana mestinya.",
        ]
        for i, line in enumerate(lines):
            draw.text((cx2, py + i * 13), line, fill="black", font=fx)

        tdy = py + len(lines) * 13 + 22
        mr = sx + sw - 25
        today_str = datetime.now().strftime("%d %B %Y")
        draw.text((mr - 150, tdy), f"{school_city}, {today_str}", fill="black", font=fx)
        draw.text((mr - 150, tdy + 15), "Direktorat Akademik", fill="black", font=fx)
        principal_name_clean = (PRINCIPAL_NAME or "").strip().lower()
        if principal_name_clean not in {"", "-", "direktorat akademik"}:
            draw.text((mr - 150, tdy + 35), PRINCIPAL_NAME, fill="black", font=fx)
        if PRINCIPAL_NIP and PRINCIPAL_NIP != "-":
            draw.text((mr - 150, tdy + 50), f"NIP/NIK. {PRINCIPAL_NIP}", fill="black", font=fx)

        draw.text(
            (scx, sy + 800 - 30),
            "Dokumen ini dibuat secara elektronis dan sah tanpa tanda tangan basah",
            fill="gray",
            font=fx,
            anchor="mm",
        )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[University Proof Error] {e}")
        return ""


def create_id_card_base64(
    student: StudentData, school_profile: Optional[SchoolProfile] = None
) -> str:
    """Create ID card as base64 JPEG"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        import base64

        school = resolve_school_profile(school_profile=school_profile)
        SCHOOL_NAME = school.name
        SCHOOL_ADDRESS = school.address
        SCHOOL_PHONE = school.phone
        PRINCIPAL_NAME = school.principal_name
        PRINCIPAL_NIP = school.principal_nip
        school_city = school.city or "Majenang"

        width, height = 1200, 900
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        ft = _load_doc_font(26, bold=False)
        fh = _load_doc_font(21, bold=True)
        fb = _load_doc_font(16, bold=False)
        fs = _load_doc_font(14, bold=False)
        fx = _load_doc_font(12, bold=False)

        # Load logo if exists
        logo = None
        logo_path = _resolve_logo_path(school.logo_path)
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
            except:
                pass

        # ID Card (left)
        ix, iy, iw, ih = 50, 50, 480, 800
        draw.rectangle([ix, iy, ix + iw, iy + ih], outline="black", width=3)
        draw.rectangle([ix, iy, ix + iw, iy + 100], fill=(0, 51, 102))

        # Draw logo or placeholder circle
        cx = ix + iw // 2
        if logo:
            # Resize and paste logo
            logo_w = 60
            logo_aspect = logo.height / logo.width
            logo_h = int(logo_w * logo_aspect)
            logo_small = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            img.paste(logo_small, (cx - logo_w // 2, iy + 50 - logo_h // 2), logo_small)
        else:
            draw.ellipse(
                [cx - 30, iy + 20, cx + 30, iy + 80],
                fill="white",
                outline="gold",
                width=2,
            )
        ty = iy + 120
        draw.text((cx, ty), "KARTU PELAJAR", fill="black", font=ft, anchor="mm")
        draw.text((cx, ty + 30), SCHOOL_NAME, fill="black", font=fh, anchor="mm")
        draw.text(
            (cx, ty + 55),
            f"Tahun Ajaran {student.tahun_ajaran}",
            fill="black",
            font=fs,
            anchor="mm",
        )
        dy, dx, lh = ty + 100, ix + 40, 44
        for i, (lbl, val) in enumerate(
            [
                ("NIS", student.nis),
                ("NISN", student.nisn),
                ("Nama", student.nama_lengkap),
                ("Kelas", student.kelas),
                ("TTL", f"{student.tempat_lahir}, {student.tanggal_lahir}"),
            ]
        ):
            y = dy + i * lh
            draw.text((dx, y), lbl, fill="black", font=fb)
            draw.text((dx + 100, y), f": {val}", fill="black", font=fb)
        fy = iy + ih - 80
        draw.text((cx, fy), "Kepala Sekolah", fill="black", font=fs, anchor="mm")
        draw.text((cx, fy + 25), PRINCIPAL_NAME, fill="black", font=fs, anchor="mm")
        draw.text(
            (cx, fy + 45), f"NIP. {PRINCIPAL_NIP}", fill="black", font=fx, anchor="mm"
        )

        # Letter (right)
        sx = ix + iw + 60
        sy = 50
        sw = width - sx - 50
        draw.rectangle([sx, sy, sx + sw, sy + 800], outline="black", width=2)
        ky = sy + 25
        scx = sx + sw // 2
        draw.text(
            (scx, ky),
            "PEMERINTAH PROVINSI JAWA TENGAH",
            fill="black",
            font=fs,
            anchor="mm",
        )
        draw.text(
            (scx, ky + 20),
            "DINAS PENDIDIKAN DAN KEBUDAYAAN",
            fill="black",
            font=fs,
            anchor="mm",
        )

        if logo:
            logo_w = 40
            logo_aspect = logo.height / logo.width
            logo_h = int(logo_w * logo_aspect)
            logo_small = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            img.paste(logo_small, (sx + 40, ky + 10), logo_small)

        draw.text((scx, ky + 45), SCHOOL_NAME, fill="black", font=fh, anchor="mm")
        ay = ky + 70
        draw.text((scx, ay), SCHOOL_ADDRESS, fill="black", font=fx, anchor="mm")
        draw.text(
            (scx, ay + 18), f"Telp: {SCHOOL_PHONE}", fill="black", font=fx, anchor="mm"
        )
        ly = ay + 35
        draw.line([(sx + 25, ly), (sx + sw - 25, ly)], fill="black", width=2)
        draw.line([(sx + 25, ly + 3), (sx + sw - 25, ly + 3)], fill="black", width=1)
        tsy = ly + 40
        draw.text(
            (scx, tsy),
            "SURAT KETERANGAN SISWA AKTIF",
            fill="black",
            font=fh,
            anchor="mm",
        )
        import random as rnd

        nomor = f"{rnd.randint(100, 999)}/SNSA/{datetime.now().year}"
        draw.text(
            (scx, tsy + 25), f"Nomor: {nomor}", fill="black", font=fx, anchor="mm"
        )
        cy2 = tsy + 55
        cx2 = sx + 25
        draw.text(
            (cx2, cy2),
            f"Yang bertanda tangan di bawah ini, Kepala Sekolah {SCHOOL_NAME},",
            fill="black",
            font=fx,
        )
        draw.text(
            (cx2, cy2 + 15), "dengan ini menerangkan bahwa:", fill="black", font=fx
        )
        dsy = cy2 + 40
        dlh = 18
        for i, (lbl, val) in enumerate(
            [
                ("Nama", f": {student.nama_lengkap}"),
                ("NISN", f": {student.nisn}"),
                ("TTL", f": {student.tempat_lahir}, {student.tanggal_lahir}"),
                ("Kelas", f": {student.kelas}"),
                ("Tahun Masuk", f": {datetime.now().year - rnd.randint(0, 2)}"),
            ]
        ):
            draw.text((cx2, dsy + i * dlh), lbl, fill="black", font=fx)
            draw.text((cx2 + 140, dsy + i * dlh), val, fill="black", font=fx)
        py = dsy + 5 * dlh + 25
        lines = [
            f"Adalah benar merupakan siswa aktif di {SCHOOL_NAME.upper()} pada tahun",
            f"ajaran {student.tahun_ajaran} dan memiliki prestasi akademik yang memuaskan.",
            "",
            "Yang bersangkutan tercatat aktif dalam sistem pendidikan kami dan berstatus",
            "siswa aktif. Kami memberi rekomendasi untuk keperluan pendaftaran dan verifikasi",
            "program pendidikan, beasiswa, dan benefit akademik siswa yang memerlukan bukti",
            "status kesiswaan aktif. Kami menjamin bahwa data yang tertera dalam surat ini",
            "sesuai dengan data yang tercatat dalam sistem kami.",
            "",
            "Surat keterangan ini dibuat untuk keperluan pendaftaran dan verifikasi program",
            "pendidikan, beasiswa, dan benefit akademik siswa yang memerlukan bukti status",
            "kesiswaan aktif. Kami menjamin bahwa data yang tertera dalam surat ini dan",
            "fasilitas siswa.",
            "",
            "Demikian surat keterangan ini dibuat dengan sebenar-benarnya atas dasar data yang",
            "tercatat dalam sistem kesiswaan kami dan dapat dipertanggungjawabkan. Apabila",
            "dikemudian hari terdapat kesalahan dalam surat ini, akan kami perbaiki sebagaimana",
            "mestinya.",
        ]
        for i, line in enumerate(lines):
            draw.text((cx2, py + i * 13), line, fill="black", font=fx)
        tdy = py + len(lines) * 13 + 25
        mr = sx + sw - 25
        today_str = datetime.now().strftime("%d %B %Y")
        draw.text((mr - 130, tdy), f"{school_city}, {today_str}", fill="black", font=fx)
        draw.text((mr - 130, tdy + 15), "Kepala Sekolah", fill="black", font=fx)
        draw.text((mr - 130, tdy + 35), PRINCIPAL_NAME, fill="black", font=fx)
        draw.text((mr - 130, tdy + 50), f"NIP. {PRINCIPAL_NIP}", fill="black", font=fx)
        draw.text(
            (scx, sy + 800 - 30),
            "Dokumen ini dibuat secara elektronis dan sah tanpa tanda tangan basah",
            fill="gray",
            font=fx,
            anchor="mm",
        )

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[ID Card Error] {e}")
        return ""


def create_salary_slip_document(
    teacher: TeacherData,
    school_profile: Optional[SchoolProfile] = None,
    width: int = 2480,
    height: int = 3508,
) -> "Image.Image":
    """Create salary slip document A4 format (2480x3508px @ 300dpi)"""
    from PIL import Image, ImageDraw
    from datetime import datetime
    import random as rnd

    school = resolve_school_profile(school_profile=school_profile)
    SCHOOL_NAME = school.name
    SCHOOL_ADDRESS = school.address
    SCHOOL_PHONE = school.phone
    PRINCIPAL_NAME = school.principal_name
    PRINCIPAL_NIP = school.principal_nip

    address_parts = [p.strip() for p in SCHOOL_ADDRESS.split(",") if p.strip()]
    address_line_1 = address_parts[0] if address_parts else SCHOOL_ADDRESS
    address_line_2 = ", ".join(address_parts[1:3]) if len(address_parts) > 1 else ""

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    S = width / 2480  # scale factor

    ft_title = _load_doc_font(int(108 * S), bold=True)
    ft_header = _load_doc_font(int(84 * S), bold=True)
    ft_body = _load_doc_font(int(62 * S), bold=False)
    ft_small = _load_doc_font(int(54 * S), bold=False)
    ft_meta = _load_doc_font(int(50 * S), bold=False)

    mg = int(90 * S)
    cx = width // 2
    bw = max(3, int(6 * S))
    content_w = width - mg * 2 - int(160 * S)

    draw.rectangle(
        [mg, mg, width - mg, height - mg],
        outline="black",
        width=max(3, int(7 * S)),
    )

    # Header - same format as Teaching Certificate
    y = mg + int(130 * S)
    line_h_body = int(80 * S)
    draw.text((cx, y),                  "PEMERINTAH PROVINSI JAWA TENGAH",  fill="black", font=ft_body,   anchor="mm")
    draw.text((cx, y + line_h_body),    "DINAS PENDIDIKAN DAN KEBUDAYAAN",  fill="black", font=ft_body,   anchor="mm")
    draw.text((cx, y + line_h_body*2),  SCHOOL_NAME,                         fill="black", font=ft_header, anchor="mm")

    # Address - wrap if needed (same as Teaching Certificate)
    addr_font = _fit_doc_font(draw, SCHOOL_ADDRESS, max_width=content_w,
                               start_size=int(58 * S), bold=False, min_size=int(40 * S))
    draw.text((cx, y + line_h_body*2 + int(90*S)), SCHOOL_ADDRESS, fill="black", font=addr_font, anchor="mm")
    draw.text((cx, y + line_h_body*2 + int(155*S)), f"Telp: {SCHOOL_PHONE}", fill="black", font=ft_small, anchor="mm")

    sep_y = y + line_h_body*2 + int(220 * S)
    draw.line([(mg + int(80*S), sep_y),     (width - mg - int(80*S), sep_y)],     fill="black", width=bw)
    draw.line([(mg + int(80*S), sep_y + int(12*S)), (width - mg - int(80*S), sep_y + int(12*S))], fill="black", width=max(1, int(2*S)))

    # Logo - bigger and centered in left space
    logo_path = _resolve_logo_path(school.logo_path)
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            # Make logo bigger - use fixed size that's proportional to document
            logo_size = int(280 * S)  # Larger fixed size
            aspect_ratio = logo.width / logo.height
            if aspect_ratio > 1:  # Wider than tall
                logo_w = logo_size
                logo_h = int(logo_size / aspect_ratio)
            else:  # Taller than wide or square
                logo_h = logo_size
                logo_w = int(logo_size * aspect_ratio)
            logo_small = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            
            # Calculate vertical center with the 3 main header lines
            header_top = mg + int(130 * S)
            main_header_height = line_h_body * 2
            header_center_y = header_top + main_header_height // 2
            logo_y = header_center_y - logo_h // 2
            
            # Calculate horizontal center in the left space (between margin and text start)
            left_space_start = mg
            left_space_end = cx - int(600 * S)  # Approximate text start position
            left_space_center = (left_space_start + left_space_end) // 2
            logo_x = left_space_center - logo_w // 2
            
            img.paste(logo_small, (logo_x, logo_y), logo_small)
        except:
            pass

    # Title
    y = sep_y + int(95 * S)
    draw.text((cx, y), "SLIP GAJI GURU", fill="black", font=ft_title, anchor="mm")
    draw.text((cx, y + int(92 * S)), "TEACHER SALARY SLIP", fill="black", font=ft_body, anchor="mm")
    draw.text(
        (cx, y + int(176 * S)),
        f"Nomor: {rnd.randint(100,999)}/SG/{datetime.now().year}",
        fill="black",
        font=ft_meta,
        anchor="mm",
    )

    # Header info - moved to the right for better margin
    y += int(270 * S)
    info_left_x = mg + int(150 * S)
    col_x = info_left_x + int(380 * S)
    val_x = col_x + int(48 * S)
    max_vw = width - val_x - mg - int(120 * S)

    for label, value in [
        ("Nama", teacher.nama_lengkap),
        ("Sekolah", SCHOOL_NAME),
        ("Periode", teacher.salary_period),
    ]:
        vf = _fit_doc_font(
            draw,
            value,
            max_width=max_vw,
            start_size=int(62 * S),
            bold=False,
            min_size=int(42 * S),
        )
        draw.text((info_left_x, y), label, fill="black", font=ft_body)
        draw.text((col_x, y), ":",   fill="black", font=ft_body)
        draw.text((val_x, y), value, fill="black", font=vf)
        y += int(92 * S)

    # Section header - moved to the right for better margin
    y += int(50 * S)
    draw.text((info_left_x, y), "PENDAPATAN GURU", fill="black", font=ft_header)

    # Table setup - with left and right margin (add more space before table)
    y += int(120 * S)
    tl = mg + int(100 * S)
    tr = width - mg - int(100 * S)
    tm = (tl + tr) // 2
    pad = int(36 * S)

    rh_hdr = int(86 * S)
    draw.rectangle([tl, y, tr, y + rh_hdr], outline="black", width=max(2, int(4 * S)))
    draw.line([(tm, y), (tm, y + rh_hdr)], fill="black", width=max(2, int(4 * S)))
    draw.text((tl + (tm - tl) // 2, y + rh_hdr // 2), "PENDAPATAN", fill="black", font=ft_body, anchor="mm")
    draw.text((tm + (tr - tm) // 2, y + rh_hdr // 2), "POTONGAN", fill="black", font=ft_body, anchor="mm")
    y += rh_hdr

    pendapatan_items = [
        ("Gaji Pokok", f"Rp. {teacher.salary_base:,.0f}".replace(",", ".")),
        (
            "Tunjangan Jabatan",
            f"Rp. {int(teacher.salary_allowances * 0.4):,.0f}".replace(",", "."),
        ),
        (
            "Tunjangan Komunikasi",
            f"Rp. {int(teacher.salary_allowances * 0.15):,.0f}".replace(",", "."),
        ),
        (
            "Tunjangan Makan",
            f"Rp. {int(teacher.salary_allowances * 0.2):,.0f}".replace(",", "."),
        ),
        (
            "Tunjangan Transportasi",
            f"Rp. {int(teacher.salary_allowances * 0.25):,.0f}".replace(",", "."),
        ),
        ("Kelebihan Jam", f"Rp. {rnd.randint(100000,300000):,.0f}".replace(",", ".")),
        ("Piket", f"Rp. {rnd.randint(100000,300000):,.0f}".replace(",", ".")),
        ("Tunjangan Pekanan", f"Rp. {rnd.randint(200000,400000):,.0f}".replace(",", ".")),
    ]
    potongan_items = [
        ("Denda Keterlambatan", "Rp. _________"),
        ("Utang", "Rp. _________"),
        ("Pinjaman Sementara", "Rp. _________"),
        ("Biaya TPA", "Rp. _________"),
    ]

    rh = int(90 * S)
    for i, (lbl, val) in enumerate(pendapatan_items):
        yr = y + i * rh
        draw.rectangle([tl, yr, tr, yr + rh], outline="black", width=max(1, int(2 * S)))
        draw.line([(tm, yr), (tm, yr + rh)], fill="black", width=max(1, int(2 * S)))
        # fit label font if needed
        lf = _fit_doc_font(
            draw,
            lbl,
            max_width=tm - tl - pad * 2,
            start_size=int(52 * S),
            bold=False,
            min_size=int(36 * S),
        )
        vf = _fit_doc_font(
            draw,
            val,
            max_width=tm - tl - pad * 2,
            start_size=int(52 * S),
            bold=False,
            min_size=int(36 * S),
        )
        draw.text((tl + pad, yr + rh // 2), lbl, fill="black", font=lf, anchor="lm")
        draw.text((tm - pad, yr + rh // 2), val, fill="black", font=vf, anchor="rm")
        if i < len(potongan_items):
            pl, pv = potongan_items[i]
            plf = _fit_doc_font(
                draw,
                pl,
                max_width=tr - tm - pad * 2,
                start_size=int(52 * S),
                bold=False,
                min_size=int(36 * S),
            )
            draw.text((tm + pad, yr + rh // 2), pl, fill="black", font=plf, anchor="lm")
            draw.text((tr - pad, yr + rh // 2), pv, fill="black", font=ft_small, anchor="rm")

    # Total rows
    y += len(pendapatan_items) * rh
    rh_tot = int(88 * S)
    draw.rectangle(
        [tl, y, tr, y + rh_tot],
        outline="black",
        width=max(2, int(4 * S)),
        fill=(240, 240, 240),
    )
    draw.line([(tm, y), (tm, y + rh_tot)], fill="black", width=max(2, int(4 * S)))
    draw.text((tl + pad, y + rh_tot // 2), "Total Pendapatan", fill="black", font=ft_body, anchor="lm")
    draw.text(
        (tm - pad, y + rh_tot // 2),
        f"Rp. {teacher.salary_total:,.0f}".replace(",", "."),
        fill="black",
        font=ft_body,
        anchor="rm",
    )
    draw.text((tm + pad, y + rh_tot // 2), "Total Potongan", fill="black", font=ft_body, anchor="lm")
    draw.text((tr - pad, y + rh_tot // 2), "Rp. _________", fill="black", font=ft_body, anchor="rm")

    y += rh_tot
    rh_final = int(95 * S)
    draw.rectangle([tl, y, tr, y + rh_final], outline="black", width=bw)
    draw.text((cx, y + rh_final // 2), "TOTAL PENDAPATAN DITERIMA GURU", fill="black", font=ft_header, anchor="mm")
    y += rh_final
    draw.rectangle([tl, y, tr, y + rh_final], outline="black", width=bw)
    draw.text(
        (cx, y + rh_final // 2),
        f"Rp. {teacher.salary_total:,.0f}".replace(",", "."),
        fill="black",
        font=ft_header,
        anchor="mm",
    )

    # Signature (pinned near footer)
    sig_y = height - mg - int(520 * S)
    lx = width * 0.27
    rx = width * 0.73
    draw.text((lx, sig_y), "Penerima", fill="black", font=ft_body, anchor="mm")
    draw.text((rx, sig_y), "Diserahkan Oleh", fill="black", font=ft_body, anchor="mm")
    draw.text((lx, sig_y + int(150 * S)), teacher.nama_lengkap, fill="black", font=ft_body, anchor="mm")
    draw.text((rx, sig_y + int(150 * S)), PRINCIPAL_NAME, fill="black", font=ft_body, anchor="mm")
    draw.text((rx, sig_y + int(230 * S)), f"NIP. {PRINCIPAL_NIP}", fill="black", font=ft_small, anchor="mm")

    draw.text(
        (cx, height - mg - int(75 * S)),
        "Dokumen ini dicetak secara elektronik dan terverifikasi",
        fill="gray",
        font=ft_small,
        anchor="mm",
    )

    return img


def create_id_card_a4(
    teacher: TeacherData,
    school_profile: Optional[SchoolProfile] = None,
    width: int = 2480,
    height: int = 3508,
) -> "Image.Image":
    """Create teacher ID card in A4 format"""
    from PIL import Image, ImageDraw
    from datetime import datetime

    school = resolve_school_profile(school_profile=school_profile)
    SCHOOL_NAME = school.name
    PRINCIPAL_NAME = school.principal_name
    PRINCIPAL_NIP = school.principal_nip

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Scale factor — all pixel values proportional to canvas width
    S = width / 2480

    # Font sizes tuned so all content fits comfortably in A4
    ft_title  = _load_doc_font(int(110 * S), bold=True)
    ft_header = _load_doc_font(int(80 * S),  bold=True)
    ft_body   = _load_doc_font(int(72 * S),  bold=False)
    ft_small  = _load_doc_font(int(60 * S),  bold=False)

    mg = int(120 * S)  # margin
    cx = width // 2
    bw = max(4, int(7 * S))  # border width

    # Outer border
    draw.rectangle([mg, mg, width - mg, height - mg], outline="black", width=bw)

    # Blue header band
    hdr_h = int(340 * S)
    draw.rectangle([mg, mg, width - mg, mg + hdr_h], fill=(0, 51, 102))

    # Logo centred in header band
    logo_path = _resolve_logo_path(school.logo_path)
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_w = int(260 * S)
            logo_h = int(logo_w * logo.height / logo.width)
            logo_small = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            img.paste(logo_small, (cx - logo_w // 2, mg + (hdr_h - logo_h) // 2), logo_small)
        except:
            pass

    # Title block (below header band)
    y = mg + hdr_h + int(60 * S)
    draw.text((cx, y), "KARTU IDENTITAS GURU", fill="black", font=ft_title, anchor="mm")
    y += int(90 * S)
    draw.text((cx, y), "TEACHER IDENTITY CARD", fill="black", font=ft_body, anchor="mm")
    y += int(90 * S)
    school_font = _fit_doc_font(draw, SCHOOL_NAME,
                                 max_width=width - mg * 2 - int(80 * S),
                                 start_size=int(72 * S), bold=True, min_size=int(48 * S))
    draw.text((cx, y), SCHOOL_NAME, fill="black", font=school_font, anchor="mm")
    y += int(90 * S)
    draw.text((cx, y), "Tahun Ajaran 2025/2026", fill="black", font=ft_small, anchor="mm")
    y += int(80 * S)

    # Thin separator line
    draw.line([(mg + int(60*S), y), (width - mg - int(60*S), y)], fill=(180,180,180), width=max(1, int(3*S)))
    y += int(60 * S)

    # Data fields
    label_x  = mg + int(120 * S)
    colon_x  = label_x + int(500 * S)
    value_x  = colon_x + int(50 * S)
    row_h    = int(145 * S)
    max_val_w = width - value_x - mg - int(40 * S)

    fields = [
        ("NIP",          teacher.nip),
        ("Nama",         teacher.nama_lengkap),
        ("TTL",          f"{teacher.tempat_lahir}, {teacher.tanggal_lahir}"),
        ("Bidang Studi", teacher.bidang_studi),
        ("Posisi",       teacher.posisi),
    ]
    for label, value in fields:
        vf = _fit_doc_font(draw, value, max_width=max_val_w,
                           start_size=int(72 * S), bold=False, min_size=int(48 * S))
        draw.text((label_x, y), label, fill="black", font=ft_body)
        draw.text((colon_x, y), ":", fill="black", font=ft_body)
        draw.text((value_x,  y), value, fill="black", font=vf)
        y += row_h

    # Footer — pinned from bottom
    now = datetime.now()
    today = now.strftime("%d %B %Y")
    valid_until = f"31 Desember {now.year}"

    fy = height - mg - int(560 * S)
    draw.line([(mg + int(60*S), fy - int(30*S)), (width - mg - int(60*S), fy - int(30*S))],
              fill=(180,180,180), width=max(1, int(3*S)))
    draw.text((cx, fy),                f"Berlaku hingga: {valid_until}", fill="black", font=ft_small, anchor="mm")
    draw.text((cx, fy + int(70*S)),    f"Dikeluarkan: {today}",         fill="black", font=ft_small, anchor="mm")
    draw.text((cx, fy + int(200*S)),   "Kepala Sekolah",                 fill="black", font=ft_body,  anchor="mm")
    draw.text((cx, fy + int(290*S)),   PRINCIPAL_NAME,                   fill="black", font=ft_body,  anchor="mm")
    draw.text((cx, fy + int(375*S)),   f"NIP. {PRINCIPAL_NIP}",          fill="black", font=ft_small, anchor="mm")
    draw.text(
        (cx, height - mg - int(75 * S)),
        "Dokumen ini dicetak secara elektronik dan terverifikasi",
        fill="gray",
        font=ft_small,
        anchor="mm",
    )

    return img


def create_teaching_certificate_a4(
    teacher: TeacherData,
    school_profile: Optional[SchoolProfile] = None,
    width: int = 2480,
    height: int = 3508,
) -> "Image.Image":
    """Create teaching certificate in A4 format"""
    from PIL import Image, ImageDraw
    from datetime import datetime
    import random as rnd

    school = resolve_school_profile(school_profile=school_profile)
    SCHOOL_NAME = school.name
    SCHOOL_ADDRESS = school.address
    SCHOOL_PHONE = school.phone
    PRINCIPAL_NAME = school.principal_name
    PRINCIPAL_NIP = school.principal_nip
    school_city = school.city or "Majenang"

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    S = width / 2480  # scale factor

    ft_title = _load_doc_font(int(108 * S), bold=True)
    ft_header = _load_doc_font(int(84 * S), bold=True)
    ft_body = _load_doc_font(int(68 * S), bold=False)
    ft_small = _load_doc_font(int(58 * S), bold=False)
    ft_meta = _load_doc_font(int(52 * S), bold=False)

    mg = int(90 * S)
    cx = width // 2
    bw = max(3, int(6 * S))
    content_w = width - mg * 2 - int(160 * S)  # usable text width

    draw.rectangle([mg, mg, width - mg, height - mg], outline="black", width=bw)
    draw.line([(mg + bw, mg + bw), (width - mg - bw, mg + bw)], fill="black", width=bw)

    # Header
    y = mg + int(130 * S)
    line_h_body = int(80 * S)
    draw.text((cx, y),                  "PEMERINTAH PROVINSI JAWA TENGAH",  fill="black", font=ft_body,   anchor="mm")
    draw.text((cx, y + line_h_body),    "DINAS PENDIDIKAN DAN KEBUDAYAAN",  fill="black", font=ft_body,   anchor="mm")
    draw.text((cx, y + line_h_body*2),  SCHOOL_NAME,                         fill="black", font=ft_header, anchor="mm")

    # Address — wrap if needed
    addr_font = _fit_doc_font(draw, SCHOOL_ADDRESS, max_width=content_w,
                               start_size=int(58 * S), bold=False, min_size=int(40 * S))
    draw.text((cx, y + line_h_body*2 + int(90*S)), SCHOOL_ADDRESS, fill="black", font=addr_font, anchor="mm")
    draw.text((cx, y + line_h_body*2 + int(155*S)), f"Telp: {SCHOOL_PHONE}", fill="black", font=ft_small, anchor="mm")

    sep_y = y + line_h_body*2 + int(220 * S)
    draw.line([(mg + int(80*S), sep_y),     (width - mg - int(80*S), sep_y)],     fill="black", width=bw)
    draw.line([(mg + int(80*S), sep_y + int(12*S)), (width - mg - int(80*S), sep_y + int(12*S))], fill="black", width=max(1, int(2*S)))

    # Logo - bigger and centered in left space
    logo_path = _resolve_logo_path(school.logo_path)
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            # Make logo bigger - use fixed size that's proportional to document
            logo_size = int(280 * S)  # Larger fixed size
            aspect_ratio = logo.width / logo.height
            if aspect_ratio > 1:  # Wider than tall
                logo_w = logo_size
                logo_h = int(logo_size / aspect_ratio)
            else:  # Taller than wide or square
                logo_h = logo_size
                logo_w = int(logo_size * aspect_ratio)
            logo_small = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            
            # Calculate vertical center with the 3 main header lines
            header_top = mg + int(130 * S)
            main_header_height = line_h_body * 2
            header_center_y = header_top + main_header_height // 2
            logo_y = header_center_y - logo_h // 2
            
            # Calculate horizontal center in the left space (between margin and text start)
            # Assuming text starts around center, left space is from margin to cx
            left_space_start = mg
            left_space_end = cx - int(600 * S)  # Approximate text start position
            left_space_center = (left_space_start + left_space_end) // 2
            logo_x = left_space_center - logo_w // 2
            
            img.paste(logo_small, (logo_x, logo_y), logo_small)
        except:
            pass

    # Title
    y = sep_y + int(100 * S)
    draw.text((cx, y), "SERTIFIKAT MENGAJAR", fill="black", font=ft_title, anchor="mm")
    draw.text((cx, y + int(90 * S)), "TEACHING CERTIFICATE", fill="black", font=ft_body, anchor="mm")
    y += int(170 * S)
    draw.text((cx, y), f"Nomor: {rnd.randint(100,999)}/SM/{datetime.now().year}", fill="black", font=ft_meta, anchor="mm")

    # Intro text
    y += int(90 * S)
    x_left = mg + int(120 * S)
    line_h_s = int(60 * S)

    draw.text((x_left, y), f"Yang bertanda tangan di bawah ini, Kepala Sekolah {SCHOOL_NAME},", fill="black", font=ft_small)
    y += line_h_s
    draw.text((x_left, y), "dengan ini menyatakan bahwa:", fill="black", font=ft_small)
    y += int(80 * S)

    # Data fields — tighter spacing
    lbl_x   = x_left
    col_x   = lbl_x + int(580 * S)
    val_x   = col_x + int(44 * S)
    max_vw  = width - val_x - mg - int(40 * S)
    row_fld = int(88 * S)

    for label, value in [
        ("Nama",                  teacher.nama_lengkap),
        ("NIP",                   teacher.nip),
        ("Tempat, Tanggal Lahir", f"{teacher.tempat_lahir}, {teacher.tanggal_lahir}"),
        ("Bidang Studi",          teacher.bidang_studi),
        ("Posisi",                teacher.posisi),
        ("Pengalaman Mengajar",   teacher.tahun_mengajar),
    ]:
        vf = _fit_doc_font(draw, value, max_width=max_vw,
                           start_size=int(58 * S), bold=False, min_size=int(40 * S))
        draw.text((lbl_x, y), label, fill="black", font=ft_small)
        draw.text((col_x, y), ":",   fill="black", font=ft_small)
        draw.text((val_x, y), value, fill="black", font=vf)
        y += row_fld

    y += int(50 * S)

    # Body paragraphs — wrapped to content_w
    body_lines = [
        f"Telah berhasil menyelesaikan program sertifikasi dan pelatihan untuk mengajar mata pelajaran {teacher.bidang_studi}",
        f"di {SCHOOL_NAME} dan dengan ini resmi diberikan kewenangan untuk mengajar pada tahun ajaran 2025/2026.",
        "",
        "Area Spesialisasi:",
        f"- {teacher.bidang_studi} Lanjutan",
        f"- Praktikum {teacher.bidang_studi}",
        "",
        "Sertifikat ini dikeluarkan sesuai standar kualifikasi guru yang berlaku dan sah digunakan sebagai bukti kompetensi mengajar.",
    ]
    for raw_line in body_lines:
        if raw_line == "":
            y += int(30 * S)
            continue
        wrapped = _wrap_text_to_width(draw, raw_line, ft_small, max_width=content_w)
        for wl in wrapped:
            draw.text((x_left, y), wl, fill="black", font=ft_small)
            y += line_h_s

    # Signature — pinned from bottom
    now = datetime.now()
    sig_y = height - mg - int(480 * S)
    sig_right = width - mg - int(120 * S)
    draw.text((sig_right, sig_y), f"{school_city}, {now.strftime('%d %B %Y')}", fill="black", font=ft_small, anchor="rm")
    draw.text((sig_right, sig_y + int(65 * S)), "Kepala Sekolah", fill="black", font=ft_small, anchor="rm")
    draw.text((sig_right, sig_y + int(190 * S)), PRINCIPAL_NAME, fill="black", font=ft_small, anchor="rm")
    draw.text((sig_right, sig_y + int(255 * S)), f"NIP. {PRINCIPAL_NIP}", fill="black", font=ft_small, anchor="rm")

    draw.text(
        (cx, height - mg - int(145 * S)),
        "Dokumen ini dicetak secara elektronik dan terverifikasi",
        fill="gray",
        font=ft_small,
        anchor="mm",
    )

    draw.text((cx, height - mg - int(75*S)),
              f"Nomor Sertifikat: TC-{rnd.randint(10000,99999)}-2025",
              fill="gray", font=ft_small, anchor="mm")

    return img


def create_employment_letter_a4(
    teacher: TeacherData,
    school_profile: Optional[SchoolProfile] = None,
    width: int = 2480,
    height: int = 3508,
) -> "Image.Image":
    """Create employment verification letter in A4 format"""
    from PIL import Image, ImageDraw
    from datetime import datetime
    import random as rnd

    school = resolve_school_profile(school_profile=school_profile)
    SCHOOL_NAME = school.name
    SCHOOL_ADDRESS = school.address
    SCHOOL_PHONE = school.phone
    PRINCIPAL_NAME = school.principal_name
    PRINCIPAL_NIP = school.principal_nip

    address_parts = [p.strip() for p in SCHOOL_ADDRESS.split(",") if p.strip()]
    address_line_1 = address_parts[0] if address_parts else SCHOOL_ADDRESS
    address_line_2 = ", ".join(address_parts[1:3]) if len(address_parts) > 1 else ""

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    S = width / 2480  # scale factor

    ft_title = _load_doc_font(int(108 * S), bold=True)
    ft_header = _load_doc_font(int(84 * S), bold=True)
    ft_body = _load_doc_font(int(68 * S), bold=False)
    ft_small = _load_doc_font(int(56 * S), bold=False)
    # Identity fields — same size as ft_body so they don't overflow
    ft_ident = _load_doc_font(int(60 * S), bold=False)

    mg = int(90 * S)
    cx = width // 2
    bw = max(3, int(6 * S))
    content_w = width - mg * 2 - int(160 * S)

    draw.rectangle([mg, mg, width - mg, height - mg], outline="black", width=bw)

    # Header - same format as Teaching Certificate
    y = mg + int(130 * S)
    line_h_body = int(80 * S)
    draw.text((cx, y),                  "PEMERINTAH PROVINSI JAWA TENGAH",  fill="black", font=ft_body,   anchor="mm")
    draw.text((cx, y + line_h_body),    "DINAS PENDIDIKAN DAN KEBUDAYAAN",  fill="black", font=ft_body,   anchor="mm")
    draw.text((cx, y + line_h_body*2),  SCHOOL_NAME,                         fill="black", font=ft_header, anchor="mm")

    # Address - wrap if needed (same as Teaching Certificate)
    addr_font = _fit_doc_font(draw, SCHOOL_ADDRESS, max_width=content_w,
                               start_size=int(58 * S), bold=False, min_size=int(40 * S))
    draw.text((cx, y + line_h_body*2 + int(90*S)), SCHOOL_ADDRESS, fill="black", font=addr_font, anchor="mm")
    draw.text((cx, y + line_h_body*2 + int(155*S)), f"Telp: {SCHOOL_PHONE}", fill="black", font=ft_small, anchor="mm")

    sep_y = y + line_h_body*2 + int(220 * S)
    draw.line([(mg + int(80*S), sep_y),     (width - mg - int(80*S), sep_y)],     fill="black", width=bw)
    draw.line([(mg + int(80*S), sep_y + int(12*S)), (width - mg - int(80*S), sep_y + int(12*S))], fill="black", width=max(1, int(2*S)))

    # Logo - bigger and centered in left space
    logo_path = _resolve_logo_path(school.logo_path)
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            # Make logo bigger - use fixed size that's proportional to document
            logo_size = int(280 * S)  # Larger fixed size
            aspect_ratio = logo.width / logo.height
            if aspect_ratio > 1:  # Wider than tall
                logo_w = logo_size
                logo_h = int(logo_size / aspect_ratio)
            else:  # Taller than wide or square
                logo_h = logo_size
                logo_w = int(logo_size * aspect_ratio)
            logo_small = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            
            # Calculate vertical center with the 3 main header lines
            header_top = mg + int(130 * S)
            main_header_height = line_h_body * 2
            header_center_y = header_top + main_header_height // 2
            logo_y = header_center_y - logo_h // 2
            
            # Calculate horizontal center in the left space (between margin and text start)
            left_space_start = mg
            left_space_end = cx - int(600 * S)  # Approximate text start position
            left_space_center = (left_space_start + left_space_end) // 2
            logo_x = left_space_center - logo_w // 2
            
            img.paste(logo_small, (logo_x, logo_y), logo_small)
        except:
            pass

    # Title
    y = sep_y + int(100 * S)
    draw.text((cx, y),             "SURAT KETERANGAN KERJA", fill="black", font=ft_title, anchor="mm")
    draw.text((cx, y + int(120*S)),"EMPLOYMENT VERIFICATION", fill="black", font=ft_body,  anchor="mm")
    draw.text((cx, y + int(210*S)),
              f"Nomor: {rnd.randint(100,999)}/SKK-2026/{datetime.now().year}",
              fill="black", font=ft_small, anchor="mm")

    # Meta info
    now = datetime.now()
    today = now.strftime("%d %B %Y")
    x_left = mg + int(120 * S)
    line_h_s = int(58 * S)

    y = y + int(300 * S)
    draw.text((x_left, y),                f"Tanggal: {today}",                     fill="black", font=ft_small)
    draw.text((x_left, y + line_h_s),     f"Ref. No.: EV-2026-{teacher.employee_id}", fill="black", font=ft_small)
    draw.text((x_left, y + line_h_s*2),   f"Employee ID: {teacher.employee_id}",   fill="black", font=ft_small)

    y += line_h_s * 2 + int(80 * S)
    draw.text((x_left, y),            "Kepada Yang Berkepentingan:", fill="black", font=ft_body)
    draw.text((x_left, y + int(80*S)),"To Whom It May Concern:",    fill="black", font=ft_small)

    y += int(160 * S)
    draw.text((x_left, y),            "VERIFIKASI KEPEGAWAIAN",  fill="black", font=ft_body)
    draw.text((x_left, y + int(80*S)),"EMPLOYMENT VERIFICATION", fill="black", font=ft_small)
    y += int(150 * S)

    # Separator before identity fields
    draw.line([(x_left, y), (width - mg - int(120*S), y)], fill=(180,180,180), width=max(1,int(2*S)))
    y += int(30 * S)

    # Identity fields — use ft_ident (bold but not oversized)
    exp_years = 10
    try:
        exp_years = int(str(teacher.tahun_mengajar).split()[0])
    except:
        pass
    start_year  = max(1990, datetime.now().year - exp_years)
    start_month = rnd.randint(1, 12)
    start_day   = rnd.randint(1, 28)
    start_date  = f"{start_day:02d}/{start_month:02d}/{start_year}"

    lbl_x  = x_left
    col_x  = lbl_x + int(720 * S)
    val_x  = col_x + int(50 * S)
    max_vw = width - val_x - mg - int(40 * S)
    row_id = int(100 * S)

    ident_fields = [
        ("Nama Lengkap",        teacher.nama_lengkap),
        ("NIP",                  teacher.nip),
        ("Employee ID",          teacher.employee_id),
        ("Posisi",               teacher.posisi),
        ("Bidang",               teacher.bidang_studi),
        ("Status Kepegawaian",   "Guru Tetap / Full-time Faculty"),
        ("Tanggal Mulai Bekerja",start_date),
    ]
    for label, value in ident_fields:
        vf = _fit_doc_font(draw, value, max_width=max_vw,
                           start_size=int(60 * S), bold=False, min_size=int(42 * S))
        vlines = _wrap_text_to_width(draw, value, vf, max_width=max_vw)
        draw.text((lbl_x, y), label, fill="black", font=ft_ident)
        draw.text((col_x, y), ":",   fill="black", font=ft_ident)
        for k, vl in enumerate(vlines):
            draw.text((val_x, y + k * int(64 * S)), vl, fill="black", font=vf)
        y += max(row_id, len(vlines) * int(64 * S) + int(24 * S))

    # Closing note - add more spacing between lines
    y += int(30 * S)
    draw.line([(x_left, y), (width - mg - int(120*S), y)], fill=(180,180,180), width=max(1,int(2*S)))
    y += int(30 * S)
    paragraph_lines = [
        f"Ini untuk menyatakan bahwa {teacher.nama_lengkap} saat ini merupakan",
        "anggota fakultas aktif dengan status kepegawaian yang baik tanpa catatan disipliner.",
        "",
        f"Masa kerja: {teacher.tahun_mengajar} di institusi kami.",
        "",
        "Surat ini dikeluarkan untuk keperluan resmi dan dapat diverifikasi",
        "dengan menghubungi pihak sekolah pada nomor telepon di atas.",
    ]
    for line in paragraph_lines:
        if line == "":
            y += int(20 * S)
            continue
        draw.text((x_left, y), line, fill="black", font=ft_small)
        y += line_h_s

    # Signature - right side but not touching edge
    sig_x = width - mg - int(700 * S)
    sig_y = height - mg - int(520 * S)
    draw.text((sig_x, sig_y),              "Hormat kami,",                 fill="black", font=ft_small)
    draw.text((sig_x, sig_y + int(75*S)),  "Kepala Sekolah",               fill="black", font=ft_body)
    draw.text((sig_x, sig_y + int(210*S)), PRINCIPAL_NAME,                  fill="black", font=ft_body)
    draw.text((sig_x, sig_y + int(285*S)), f"NIP. {PRINCIPAL_NIP}",         fill="black", font=ft_small)

    draw.text((cx, height - mg - int(75*S)),
              "Dokumen ini dicetak secara elektronik dan terverifikasi",
              fill="gray", font=ft_small, anchor="mm")

    return img


def create_teacher_documents_base64(
    teacher: TeacherData, school_profile: Optional[SchoolProfile] = None
) -> str:
    """Create teacher documents collage: 2x2 grid with ID Card, Certificate, Employment Letter, Salary Slip (A4 each @ 300dpi)"""
    try:
        from PIL import Image
        import io
        import base64

        # Create 4 individual A4 documents (2480x3508 @ 300dpi)
        doc_width = 2480
        doc_height = 3508

        id_card = create_id_card_a4(teacher, school_profile, doc_width, doc_height)
        certificate = create_teaching_certificate_a4(
            teacher, school_profile, doc_width, doc_height
        )
        employment = create_employment_letter_a4(
            teacher, school_profile, doc_width, doc_height
        )
        salary_slip = create_salary_slip_document(
            teacher, school_profile, doc_width, doc_height
        )

        # Create 2x2 grid (4960x7016 pixels)
        grid_width = doc_width * 2
        grid_height = doc_height * 2
        grid_img = Image.new("RGB", (grid_width, grid_height), "white")

        # Paste documents in 2x2 layout
        # Top-left: ID Card
        grid_img.paste(id_card, (0, 0))
        # Top-right: Certificate
        grid_img.paste(certificate, (doc_width, 0))
        # Bottom-left: Employment Letter
        grid_img.paste(employment, (0, doc_height))
        # Bottom-right: Salary Slip
        grid_img.paste(salary_slip, (doc_width, doc_height))

        # Save to base64
        buf = io.BytesIO()
        grid_img.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[Teacher Documents Error] {e}")
        import traceback

        traceback.print_exc()
        return ""
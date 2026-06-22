#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════╗
║         appRebuild v2.0  —  by appRebuild            ║
║    APK Decompile & Compile Tool for Termux           ║
║    https://github.com/R3XBASE/appRebuild.git          ║
╚══════════════════════════════════════════════════════╝

License : MIT
Python  : 3.8+
Deps    : apktool, openjdk-17 (via Termux pkg)
"""

import os
import sys
import shutil
import logging
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


# ──────────────────────────────────────────────────────
#  VERSION
# ──────────────────────────────────────────────────────
VERSION = "2.0.0"


# ──────────────────────────────────────────────────────
#  ANSI COLORS  (auto-disable jika bukan TTY)
# ──────────────────────────────────────────────────────
_TTY = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text

def R(t):  return _c("0;31", t)
def G(t):  return _c("0;32", t)
def Y(t):  return _c("1;33", t)
def C(t):  return _c("0;36", t)
def W(t):  return _c("1;37", t)
def DIM(t): return _c("2",    t)
def BOLD(t): return _c("1",   t)
def BG_C(t): return _c("46;30", t)


# ──────────────────────────────────────────────────────
#  PATHS  (semua resolved, tidak ada trailing-slash bug)
# ──────────────────────────────────────────────────────
HOME       = Path.home()
WORK_DIR   = HOME / "appRebuild"
DECOMP_DIR = WORK_DIR / "decompiled"
OUTPUT_DIR = WORK_DIR / "output"
SIGNED_DIR = WORK_DIR / "signed"
LOG_DIR    = WORK_DIR / "logs"
KEYSTORE   = WORK_DIR / "debug.keystore"
SETUP_FLAG = WORK_DIR / ".setup_done"

# Keystore config
KS_ALIAS = "apprebuilddebug"
KS_PASS  = "apprebuild2026"
KS_DNAME = "CN=AppRebuild, OU=Debug, O=Dev, L=Local, ST=Local, C=ID"


# ──────────────────────────────────────────────────────
#  LOGGING  (ke file + stream)
# ──────────────────────────────────────────────────────
def _init_dirs():
    for d in (DECOMP_DIR, OUTPUT_DIR, SIGNED_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)

def get_logger(name: str = "appRebuild") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fh = logging.FileHandler(LOG_DIR / f"appRebuild_{ts}.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    return logger

log = None  # inisialisasi di main() setelah dirs dibuat


# ──────────────────────────────────────────────────────
#  UI HELPERS
# ──────────────────────────────────────────────────────
LINE = "  " + DIM("─" * 46)

def ok(msg):   print(f"  {G('✔')}  {msg}")
def err(msg):  print(f"  {R('✘')}  {R('ERROR:')} {msg}")
def warn(msg): print(f"  {Y('⚠')}  {msg}")
def info(msg): print(f"  {C('➜')}  {msg}")
def step(msg): print(f"\n  {BG_C(f' {msg} ')}")

def line():
    print(LINE)

def press_enter():
    print()
    input(f"  {DIM('[ Tekan Enter untuk lanjut... ]')}")

def confirm(question: str) -> bool:
    ans = input(f"  {Y(question + ' (y/n):')} ").strip().lower()
    return ans == "y"

def filesize(path: Path) -> str:
    """Human-readable file size."""
    try:
        size = path.stat().st_size
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    except OSError:
        return "?"

def expand_path(raw: str) -> Path:
    """Expand ~, env vars, dan resolve path."""
    return Path(os.path.expandvars(os.path.expanduser(raw.strip())))


# ──────────────────────────────────────────────────────
#  BANNER
# ──────────────────────────────────────────────────────
BANNER_ART = r"""
  ╔════════════════════════════════════════════════╗
  ║   ██████╗ ██████╗ ██████╗                     ║
  ║  ██╔══██╗██╔══██╗██╔══██╗                     ║
  ║  ███████║██████╔╝██████╔╝                     ║
  ║  ██╔══██║██╔═══╝ ██╔══██╗                     ║
  ║  ██║  ██║██║     ██║  ██║                     ║
  ║  ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝  Rebuild v{ver:<7} ║
  ║       APK Decompile & Compile Tool            ║
  ╚════════════════════════════════════════════════╝
""".format(ver=VERSION)

def banner():
    os.system("clear")
    print(C(BOLD(BANNER_ART)))

def banner_mini(title: str):
    os.system("clear")
    bar = C(BOLD("  ╔" + "═" * 48 + "╗"))
    mid = C(BOLD(f"  ║  appRebuild v{VERSION}  ·  {title:<28}║"))
    bot = C(BOLD("  ╚" + "═" * 48 + "╝"))
    print(bar); print(mid); print(bot); print()


# ──────────────────────────────────────────────────────
#  SUBPROCESS RUNNER
# ──────────────────────────────────────────────────────
def run_cmd(
    cmd: list,
    log_file: Path = None,
    stream_output: bool = True,
    capture: bool = False,
) -> tuple[int, str]:
    """
    Jalankan command, stream output ke terminal (opsional),
    dan simpan ke log file (opsional).

    Return: (returncode, combined_output)

    FIX v1: Tidak ada double-run seperti versi Bash.
    FIX v2: PIPESTATUS digantikan oleh returncode langsung.
    """
    output_lines: list[str] = []

    try:
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        ) as proc:
            for raw_line in proc.stdout:
                stripped = raw_line.rstrip()
                output_lines.append(stripped)
                if stream_output:
                    print(f"    {DIM(stripped)}")

            proc.wait()
            rc = proc.returncode

    except FileNotFoundError:
        msg = f"Command tidak ditemukan: {cmd[0]}"
        err(msg)
        return (127, msg)
    except Exception as e:
        msg = f"Unexpected error menjalankan {cmd[0]}: {e}"
        err(msg)
        return (1, msg)

    combined = "\n".join(output_lines)

    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.write_text(combined, encoding="utf-8")
        except OSError as e:
            warn(f"Gagal tulis log: {e}")

    return (rc, combined)


# ──────────────────────────────────────────────────────
#  DEPENDENCY CHECK
# ──────────────────────────────────────────────────────

# apktool TIDAK tersedia di repo Termux standar.
# Installer resmi dari rendiix menambahkan custom APT repo,
# setelah itu `pkg install apktool` berjalan normal.
APKTOOL_INSTALLER_URL = (
    "https://raw.githubusercontent.com/rendiix/termux-apktool/main/install.sh"
)

# Package yang bisa langsung dari repo Termux standar
STANDARD_PKGS = {
    "java":      "openjdk-17",
}
OPTIONAL_TOOLS = {
    "apksigner": "android-tools",
    "zipalign":  "android-tools",
    "keytool":   "(bagian dari openjdk-17)",
    "jarsigner": "(bagian dari openjdk-17)",
}


def _tool_version(name: str) -> str:
    """Ambil versi singkat tool."""
    try:
        if name == "java":
            r = subprocess.run(
                ["java", "-version"], capture_output=True, text=True
            )
            line_ = (r.stderr or r.stdout).splitlines()[0]
            parts = line_.split('"')
            return parts[1] if len(parts) >= 2 else line_.split()[-1]
        elif name == "apktool":
            r = subprocess.run(
                ["apktool", "--version"], capture_output=True, text=True
            )
            return r.stdout.strip() or r.stderr.strip()
    except Exception:
        pass
    return "tersedia"


def _install_apktool() -> bool:
    """
    Install apktool via installer resmi rendiix/termux-apktool.
    Installer menambahkan custom APT repo lalu `pkg install apktool`.
    Return True jika berhasil.
    """
    if not shutil.which("curl") and not shutil.which("wget"):
        err("curl / wget tidak tersedia — install dulu: pkg install curl")
        return False

    info("Mengunduh installer apktool (rendiix/termux-apktool)...")
    installer_path = Path("/tmp/apktool_install.sh")

    if shutil.which("curl"):
        rc, _ = run_cmd(
            ["curl", "-fsSL", APKTOOL_INSTALLER_URL, "-o", str(installer_path)],
            stream_output=False,
        )
    else:
        rc, _ = run_cmd(
            ["wget", "-qO", str(installer_path), APKTOOL_INSTALLER_URL],
            stream_output=False,
        )

    if rc != 0 or not installer_path.exists():
        err("Gagal download installer. Periksa koneksi internet.")
        info(f"Download manual: curl -fsSL {APKTOOL_INSTALLER_URL} | bash")
        return False

    info("Menjalankan installer apktool...")
    rc, _ = run_cmd(["bash", str(installer_path)], stream_output=True)
    installer_path.unlink(missing_ok=True)

    if shutil.which("apktool") is not None:
        ok("apktool berhasil diinstall")
        return True
    else:
        err("apktool masih tidak ditemukan setelah installer selesai.")
        warn("Coba jalankan manual:")
        print(f"    curl -fsSL {APKTOOL_INSTALLER_URL} | bash")
        print("    pkg install apktool")
        return False


def check_deps(silent: bool = False) -> bool:
    """
    Periksa dan install dependency yang kurang.
    Return True jika semua required tool tersedia.
    """
    if not silent:
        banner_mini("Dependency Check")
        step("Memeriksa tools yang diperlukan...")
        print()

    missing_standard: list[str] = []
    apktool_missing = shutil.which("apktool") is None

    # Java (dari repo standar)
    for tool, pkg in STANDARD_PKGS.items():
        found = shutil.which(tool) is not None
        if found:
            ver = _tool_version(tool)
            ok(f"{tool:<12}: {ver}")
        else:
            err(f"{tool:<12}: tidak ditemukan")
            missing_standard.append(pkg)

    # apktool (repo non-standar)
    if apktool_missing:
        err(f"{'apktool':<12}: tidak ditemukan")
        warn("apktool tidak tersedia di repo Termux standar.")
        info("Akan diinstall via rendiix/termux-apktool (custom repo).")
    else:
        ver = _tool_version("apktool")
        ok(f"{'apktool':<12}: v{ver}")

    print()

    # Optional
    for tool, note in OPTIONAL_TOOLS.items():
        found = shutil.which(tool) is not None
        if found:
            ok(f"{tool:<12}: tersedia")
        else:
            warn(f"{tool:<12}: tidak ditemukan {DIM(note)}")

    print()

    all_ok = True

    # Install Java dan standard packages
    if missing_standard:
        warn(f"Package kurang: {', '.join(missing_standard)}")
        print()
        if confirm("Install package standar via pkg?"):
            print()
            info("Update repository...")
            run_cmd(["pkg", "update", "-y"], stream_output=False)
            for pkg in missing_standard:
                info(f"Installing: {pkg}")
                run_cmd(["pkg", "install", "-y", pkg], stream_output=False)
                tool_name = next(
                    (t for t, p in STANDARD_PKGS.items() if p == pkg), pkg
                )
                if shutil.which(tool_name) is not None:
                    ok(f"{pkg} berhasil diinstall")
                else:
                    err(f"{pkg} gagal diinstall — coba manual: pkg install {pkg}")
                    all_ok = False
        else:
            all_ok = False

    # Install apktool via custom installer
    if apktool_missing:
        print()
        if confirm("Install apktool via rendiix/termux-apktool?"):
            print()
            if not _install_apktool():
                all_ok = False
        else:
            warn("apktool dibutuhkan untuk decompile dan compile.")
            all_ok = False

    if not all_ok:
        err("Beberapa dependency belum terpenuhi.")
        if not silent:
            press_enter()
        return False

    ok("Semua dependency siap!")
    SETUP_FLAG.touch()

    if not silent:
        press_enter()
    return True


# ──────────────────────────────────────────────────────
#  KEYSTORE
# ──────────────────────────────────────────────────────
def ensure_keystore() -> bool:
    """Buat debug keystore jika belum ada. Return True jika ready."""
    if KEYSTORE.exists():
        return True

    if shutil.which("keytool") is None:
        err("keytool tidak tersedia — tidak bisa generate keystore")
        return False

    info("Membuat debug keystore (sekali saja)...")
    rc, out = run_cmd(
        [
            "keytool", "-genkey", "-v",
            "-keystore", str(KEYSTORE),
            "-alias",    KS_ALIAS,
            "-keyalg",   "RSA",
            "-keysize",  "2048",
            "-validity", "10000",
            "-storepass", KS_PASS,
            "-keypass",   KS_PASS,
            "-dname",     KS_DNAME,
        ],
        stream_output=False,
    )

    if rc == 0 and KEYSTORE.exists():
        ok(f"Keystore dibuat: {KEYSTORE}")
        return True
    else:
        err(f"Gagal buat keystore (rc={rc})")
        if out:
            print(DIM(out[:500]))
        return False


# ──────────────────────────────────────────────────────
#  SIGN APK
# ──────────────────────────────────────────────────────
def do_sign_apk(input_apk: Path) -> Path | None:
    """
    Sign APK dengan apksigner (preferred) atau jarsigner (fallback).
    Return path signed APK jika berhasil, None jika gagal.

    FIX: jarsigner fallback tidak lagi double-copy file.
    """
    if not ensure_keystore():
        return None

    base = input_apk.stem
    signed_apk = SIGNED_DIR / f"{base}_signed.apk"

    step("Signing APK...")

    if shutil.which("apksigner"):
        info("Menggunakan apksigner...")
        rc, out = run_cmd(
            [
                "apksigner", "sign",
                "--ks",          str(KEYSTORE),
                "--ks-key-alias", KS_ALIAS,
                "--ks-pass",     f"pass:{KS_PASS}",
                "--key-pass",    f"pass:{KS_PASS}",
                "--out",         str(signed_apk),
                str(input_apk),
            ],
            stream_output=False,
        )
    elif shutil.which("jarsigner"):
        info("Menggunakan jarsigner (fallback)...")
        # jarsigner sign-in-place: copy dulu ke tujuan
        shutil.copy2(input_apk, signed_apk)
        rc, out = run_cmd(
            [
                "jarsigner",
                "-keystore",  str(KEYSTORE),
                "-storepass", KS_PASS,
                "-keypass",   KS_PASS,
                "-signedjar", str(signed_apk),
                str(input_apk),
                KS_ALIAS,
            ],
            stream_output=False,
        )
    else:
        err("Tidak ada signing tool tersedia (apksigner / jarsigner)")
        return None

    if rc == 0 and signed_apk.exists():
        ok(f"Signed APK  : {signed_apk}")
        ok(f"Ukuran      : {filesize(signed_apk)}")
        return signed_apk
    else:
        err(f"Gagal sign APK (rc={rc})")
        if out:
            print(DIM(out[:600]))
        # Hapus output yang mungkin partial
        if signed_apk.exists():
            signed_apk.unlink(missing_ok=True)
        return None


# ──────────────────────────────────────────────────────
#  ZIPALIGN  (opsional, sebelum signing)
# ──────────────────────────────────────────────────────
def do_zipalign(input_apk: Path) -> Path:
    """
    Jalankan zipalign jika tersedia.
    Return path output (aligned atau original jika tidak tersedia).
    """
    if not shutil.which("zipalign"):
        return input_apk

    aligned = input_apk.with_stem(input_apk.stem + "_aligned")
    info("Menjalankan zipalign...")
    rc, _ = run_cmd(
        ["zipalign", "-v", "-p", "4", str(input_apk), str(aligned)],
        stream_output=False,
    )
    if rc == 0 and aligned.exists():
        ok("zipalign selesai")
        return aligned
    else:
        warn("zipalign gagal, melanjutkan tanpa alignment")
        return input_apk


# ──────────────────────────────────────────────────────
#  APK PATH PROMPT
# ──────────────────────────────────────────────────────
def prompt_apk_path() -> Path | None:
    """Minta user untuk input path APK, validasi, return Path atau None."""
    print(f"  {W('Masukkan path APK:')}")
    print(f"  {DIM('Contoh: /sdcard/Download/MyApp.apk')}")
    raw = input(f"  {C('Path: ')}")

    if not raw.strip():
        err("Path tidak boleh kosong")
        return None

    path = expand_path(raw)

    if not path.exists():
        err(f"File tidak ditemukan: {path}")
        return None

    if not path.is_file():
        err(f"Bukan file: {path}")
        return None

    if path.suffix.lower() != ".apk":
        warn("Ekstensi bukan .apk")
        if not confirm("Lanjutkan quand même?"):
            return None

    return path


# ──────────────────────────────────────────────────────
#  MENU 1 — DECOMPILE
# ──────────────────────────────────────────────────────
def menu_decompile():
    banner_mini("📦 Decompile APK → Smali")

    apk_path = prompt_apk_path()
    if not apk_path:
        press_enter()
        return

    apk_name  = apk_path.stem
    out_dir   = DECOMP_DIR / apk_name
    ts        = datetime.now().strftime("%H%M%S")
    log_file  = LOG_DIR / f"{apk_name}_decompile_{ts}.log"

    line()
    info(f"File   : {apk_path.name}  ({filesize(apk_path)})")
    info(f"Output : {out_dir}")
    line()

    if out_dir.exists():
        warn("Folder output sudah ada!")
        if confirm("Hapus dan decompile ulang?"):
            shutil.rmtree(out_dir)
        else:
            press_enter()
            return

    print()
    step("Menjalankan APKTool...")
    print()

    # FIX: hanya satu kali run (versi Bash menjalankan dua kali!)
    rc, _ = run_cmd(
        ["apktool", "d", str(apk_path), "-o", str(out_dir), "--force"],
        log_file=log_file,
        stream_output=True,
    )

    print()
    smali_dir = out_dir / "smali"

    if rc == 0 and smali_dir.exists():
        smali_count = len(list(out_dir.rglob("*.smali")))
        res_dir     = out_dir / "res"
        res_count   = len(list(res_dir.rglob("*"))) if res_dir.exists() else 0

        line()
        ok(BOLD("Decompile berhasil!"))
        print()
        print(f"  {W('Statistik:')}")
        print(f"    📁 Smali files   : {G(str(smali_count))}")
        print(f"    🖼  Resource files: {G(str(res_count))}")
        print(f"    📂 Output        : {C(str(out_dir))}")
        print(f"    📋 Log           : {DIM(str(log_file))}")
        line()
        print()
        print(f"  {DIM('Struktur output:')}")
        for item in sorted(out_dir.iterdir()):
            print(f"    {C('├─')} {item.name}")
    else:
        line()
        err("Decompile gagal!")
        print(f"    📋 Cek log: {DIM(str(log_file))}")
        line()

    press_enter()


# ──────────────────────────────────────────────────────
#  MENU 2 — COMPILE
# ──────────────────────────────────────────────────────
def menu_compile():
    banner_mini("🔨 Compile Smali → APK")

    folders = sorted(
        p for p in DECOMP_DIR.iterdir()
        if p.is_dir()
    ) if DECOMP_DIR.exists() else []

    smali_dir: Path | None = None

    if folders:
        print(f"  {W('Folder tersedia:')}")
        line()
        for i, folder in enumerate(folders, 1):
            smali_n = len(list(folder.rglob("*.smali")))
            print(f"  {C(f'[{i}]')} {folder.name}  {DIM(f'({smali_n} smali)')}")
        line()
        print(f"  {Y('[M]')} Input path manual")
        print()

        choice = input(f"  {W(f'Pilih [1-{len(folders)}/M]: ')}").strip()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(folders):
                smali_dir = folders[idx]
            else:
                err("Pilihan di luar range")
                press_enter()
                return
        elif choice.lower() == "m":
            raw = input(f"  {C('Path folder: ')}")
            smali_dir = expand_path(raw)
        else:
            err("Pilihan tidak valid")
            press_enter()
            return
    else:
        warn("Belum ada folder decompiled")
        raw = input(f"  {C('Masukkan path folder smali: ')}")
        smali_dir = expand_path(raw)

    # Validasi
    if not smali_dir or not smali_dir.is_dir():
        err(f"Folder tidak ditemukan: {smali_dir}")
        press_enter()
        return

    manifest = smali_dir / "AndroidManifest.xml"
    if not manifest.exists():
        err("Bukan folder APKTool yang valid (tidak ada AndroidManifest.xml)")
        press_enter()
        return

    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_apk = OUTPUT_DIR / f"{smali_dir.name}_{ts}.apk"
    log_file = LOG_DIR / f"{smali_dir.name}_compile_{ts}.log"

    line()
    info(f"Source : {smali_dir}")
    info(f"Output : {out_apk}")
    line()

    print()
    step("Compiling dengan APKTool...")
    print()

    # FIX: hanya satu kali run (versi Bash double-run!)
    rc, _ = run_cmd(
        ["apktool", "b", str(smali_dir), "-o", str(out_apk)],
        log_file=log_file,
        stream_output=True,
    )

    print()

    if rc == 0 and out_apk.exists():
        # Zipalign opsional
        aligned_apk = do_zipalign(out_apk)

        line()
        ok(BOLD("Compile berhasil!"))
        print()
        print(f"  {W('Output:')}")
        print(f"    📦 APK  : {C(str(aligned_apk))}")
        print(f"    📊 Size : {G(filesize(aligned_apk))}")
        print(f"    📋 Log  : {DIM(str(log_file))}")
        line()

        print()
        if confirm("Sign APK sekarang?"):
            print()
            do_sign_apk(aligned_apk)
        else:
            warn("APK belum di-sign — tidak bisa diinstall langsung")
            info("Gunakan menu [3] Sign APK untuk sign nanti")
    else:
        line()
        err("Compile gagal!")
        print(f"    📋 Cek log: {DIM(str(log_file))}")
        line()

    press_enter()


# ──────────────────────────────────────────────────────
#  MENU 3 — SIGN APK
# ──────────────────────────────────────────────────────
def menu_sign():
    banner_mini("✍️  Sign APK")

    unsigned = sorted(OUTPUT_DIR.glob("*.apk")) if OUTPUT_DIR.exists() else []
    apk_path: Path | None = None

    if unsigned:
        print(f"  {W('APK di folder output:')}")
        line()
        for i, apk in enumerate(unsigned, 1):
            print(f"  {C(f'[{i}]')} {apk.name}  {DIM(f'({filesize(apk)})')}")
        line()
        print(f"  {Y('[M]')} Input path manual")
        print()

        choice = input(f"  {W(f'Pilih [1-{len(unsigned)}/M]: ')}").strip()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(unsigned):
                apk_path = unsigned[idx]
            else:
                err("Pilihan di luar range")
                press_enter()
                return
        elif choice.lower() == "m":
            raw = input(f"  {C('Path APK: ')}")
            apk_path = expand_path(raw)
        else:
            err("Pilihan tidak valid")
            press_enter()
            return
    else:
        raw = input(f"  {C('Masukkan path APK: ')}")
        apk_path = expand_path(raw)

    if not apk_path or not apk_path.is_file():
        err(f"File tidak ditemukan: {apk_path}")
        press_enter()
        return

    print()
    do_sign_apk(apk_path)
    press_enter()


# ──────────────────────────────────────────────────────
#  MENU 4 — FILE MANAGER
# ──────────────────────────────────────────────────────
def _list_section(title: str, color_fn, pattern_fn) -> list[Path]:
    """Helper: tampilkan satu seksi file manager."""
    print(f"  {W(title)}")
    items = pattern_fn()
    if items:
        for item in items:
            extra = ""
            if item.is_dir():
                n = len(list(item.rglob("*.smali")))
                extra = DIM(f"({n} smali)")
            else:
                extra = DIM(f"({filesize(item)})")
            print(f"    {color_fn('├─')} {item.name}  {extra}")
    else:
        print(f"    {DIM('(kosong)')}")
    print()
    return items or []

def menu_files():
    while True:
        banner_mini("📂 File Manager")

        decomp_items = _list_section(
            "📁 Decompiled (Smali):", C,
            lambda: sorted(p for p in DECOMP_DIR.iterdir() if p.is_dir())
                    if DECOMP_DIR.exists() else [],
        )
        output_items = _list_section(
            "📦 Output APK:", Y,
            lambda: sorted(OUTPUT_DIR.glob("*.apk"))
                    if OUTPUT_DIR.exists() else [],
        )
        signed_items = _list_section(
            "✅ Signed APK:", G,
            lambda: sorted(SIGNED_DIR.glob("*.apk"))
                    if SIGNED_DIR.exists() else [],
        )

        line()
        print(f"  {W('Opsi:')}")
        print(f"  {C('[1]')} Hapus semua decompiled")
        print(f"  {C('[2]')} Hapus semua output APK")
        print(f"  {C('[3]')} Hapus semua signed APK")
        print(f"  {C('[4]')} Hapus SEMUA data")
        print(f"  {C('[0]')} Kembali")
        print()

        opt = input(f"  {W('Pilih: ')}").strip()

        if opt == "1":
            if confirm("Hapus semua folder decompiled?"):
                for d in decomp_items:
                    shutil.rmtree(d, ignore_errors=True)
                ok("Decompiled dihapus")
        elif opt == "2":
            if confirm("Hapus semua output APK?"):
                for f in output_items:
                    f.unlink(missing_ok=True)
                ok("Output APK dihapus")
        elif opt == "3":
            if confirm("Hapus semua signed APK?"):
                for f in signed_items:
                    f.unlink(missing_ok=True)
                ok("Signed APK dihapus")
        elif opt == "4":
            prompt_hapus = R("Ketik 'HAPUS SEMUA' untuk konfirmasi: ")
            konfirm = input(f"  {prompt_hapus}")
            if konfirm == "HAPUS SEMUA":
                for d in decomp_items:
                    shutil.rmtree(d, ignore_errors=True)
                for f in output_items + signed_items:
                    f.unlink(missing_ok=True)
                ok("Semua data dihapus")
            else:
                warn("Dibatalkan")
        elif opt == "0":
            return
        else:
            warn("Pilihan tidak valid")

        import time; time.sleep(0.8)


# ──────────────────────────────────────────────────────
#  MENU 5 — ABOUT
# ──────────────────────────────────────────────────────
def menu_about():
    banner_mini("ℹ️  About")
    print(f"  {W(f'appRebuild v{VERSION}')}")
    print(f"  APK Decompile & Compile Tool for Termux")
    print()
    line()
    print()
    print(f"  {W('Work Directory:')}")
    print(f"    📂 {WORK_DIR}")
    print()
    print(f"  {W('Tools:')}")

    tools_check = {
        "apktool":   (True,  lambda: f"v{_tool_version('apktool')}"),
        "java":      (True,  lambda: _tool_version('java')),
        "apksigner": (False, lambda: ""),
        "zipalign":  (False, lambda: ""),
        "keytool":   (False, lambda: ""),
        "jarsigner": (False, lambda: ""),
    }

    for tool, (required, ver_fn) in tools_check.items():
        found = shutil.which(tool) is not None
        if found:
            try:
                ver = ver_fn()
                ok(f"{tool} {ver}".strip())
            except Exception:
                ok(tool)
        else:
            if required:
                err(f"{tool} tidak terinstall")
            else:
                warn(f"{tool} tidak tersedia")

    print()
    line()
    print()
    print(f"  {W('Workflow:')}")
    print(f"  {DIM('APK → [Decompile] → Smali+Res → [Edit] → [Compile] → APK → [Sign] → ✅')}")
    print()
    print(f"  {W('Python:')}")
    print(f"    🐍 {sys.version.split()[0]}  ({sys.executable})")
    print()

    # Keystore info
    if KEYSTORE.exists():
        ok(f"Keystore siap: {KEYSTORE}")
    else:
        warn("Keystore belum dibuat (otomatis saat sign)")

    press_enter()


# ──────────────────────────────────────────────────────
#  MAIN MENU
# ──────────────────────────────────────────────────────
def main_menu():
    while True:
        banner()
        print(f"  {W(BOLD('MAIN MENU'))}")
        print()
        print(f"  {C('[1]')}  📦  Decompile APK  →  Smali")
        print(f"  {C('[2]')}  🔨  Compile Smali  →  APK")
        print(f"  {C('[3]')}  ✍️   Sign APK")
        print(f"  {C('[4]')}  📂  File Manager")
        print(f"  {C('[5]')}  🔧  Install / Update Dependencies")
        print(f"  {C('[6]')}  ℹ️   About & Info")
        print()
        print(f"  {R('[0]')}  ❌  Keluar")
        print()
        line()

        try:
            choice = input(f"  {W('Pilih menu: ')}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            print(f"\n  {G('Sampai jumpa! 👋')}\n")
            sys.exit(0)

        dispatch = {
            "1": menu_decompile,
            "2": menu_compile,
            "3": menu_sign,
            "4": menu_files,
            "5": check_deps,
            "6": menu_about,
            "0": None,
        }

        if choice == "0":
            print()
            print(f"  {G('Sampai jumpa! 👋')}")
            print()
            sys.exit(0)
        elif choice in dispatch:
            dispatch[choice]()
        else:
            warn("Pilihan tidak valid")
            import time; time.sleep(0.5)


# ──────────────────────────────────────────────────────
#  CLI MODE  (non-interactive / scripting)
# ──────────────────────────────────────────────────────
def build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="appRebuild",
        description=f"appRebuild v{VERSION} — APK Decompile & Compile Tool for Termux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  appRebuild.py --decompile MyApp.apk
  appRebuild.py --compile ~/appRebuild/decompiled/MyApp
  appRebuild.py --sign ~/appRebuild/output/MyApp.apk
  appRebuild.py --check-deps
        """,
    )
    parser.add_argument("--version", action="version", version=f"appRebuild {VERSION}")
    parser.add_argument("--decompile",  metavar="APK",    help="Decompile APK ke smali")
    parser.add_argument("--compile",    metavar="DIR",    help="Compile folder smali → APK")
    parser.add_argument("--sign",       metavar="APK",    help="Sign APK")
    parser.add_argument("--check-deps", action="store_true", help="Cek & install dependencies")
    parser.add_argument("--no-sign",    action="store_true", help="Skip signing setelah compile")
    parser.add_argument("--output",     metavar="DIR",    help="Override output directory")
    return parser


def run_cli(args: argparse.Namespace):
    """Jalankan dalam non-interactive / scripting mode."""
    if args.output:
        global OUTPUT_DIR
        OUTPUT_DIR = Path(args.output)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.check_deps:
        ok_ = check_deps(silent=False)
        sys.exit(0 if ok_ else 1)

    elif args.decompile:
        apk = expand_path(args.decompile)
        if not apk.is_file():
            err(f"File tidak ditemukan: {apk}")
            sys.exit(1)
        out_dir  = DECOMP_DIR / apk.stem
        ts       = datetime.now().strftime("%H%M%S")
        log_file = LOG_DIR / f"{apk.stem}_decompile_{ts}.log"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        rc, _ = run_cmd(
            ["apktool", "d", str(apk), "-o", str(out_dir), "--force"],
            log_file=log_file,
        )
        if rc == 0 and (out_dir / "smali").exists():
            ok(f"Decompile berhasil → {out_dir}")
            sys.exit(0)
        else:
            err(f"Decompile gagal (rc={rc}) — cek {log_file}")
            sys.exit(1)

    elif args.compile:
        smali = expand_path(args.compile)
        if not smali.is_dir():
            err(f"Folder tidak ditemukan: {smali}")
            sys.exit(1)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_apk = OUTPUT_DIR / f"{smali.name}_{ts}.apk"
        log_file = LOG_DIR / f"{smali.name}_compile_{ts}.log"
        rc, _ = run_cmd(
            ["apktool", "b", str(smali), "-o", str(out_apk)],
            log_file=log_file,
        )
        if rc == 0 and out_apk.exists():
            aligned = do_zipalign(out_apk)
            ok(f"Compile berhasil → {aligned}")
            if not args.no_sign:
                signed = do_sign_apk(aligned)
                if signed:
                    ok(f"Signed → {signed}")
                    sys.exit(0)
                else:
                    sys.exit(1)
            sys.exit(0)
        else:
            err(f"Compile gagal (rc={rc}) — cek {log_file}")
            sys.exit(1)

    elif args.sign:
        apk = expand_path(args.sign)
        if not apk.is_file():
            err(f"File tidak ditemukan: {apk}")
            sys.exit(1)
        signed = do_sign_apk(apk)
        sys.exit(0 if signed else 1)

    else:
        err("Tidak ada operasi yang dipilih. Gunakan --help")
        sys.exit(1)


# ──────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────
def main():
    global log

    # Init direktori & logger
    _init_dirs()
    log = get_logger()

    parser = build_argparser()

    # CLI mode jika ada argumen
    if len(sys.argv) > 1:
        args = parser.parse_args()
        run_cli(args)
        return

    # Interactive TUI mode
    try:
        if not SETUP_FLAG.exists():
            banner()
            print(f"  {W('Selamat datang di appRebuild! 🎉')}")
            print(f"  {DIM('Ini adalah pertama kali kamu menjalankan tool ini.')}")
            print(f"  {DIM('Akan dilakukan pengecekan dependency otomatis.')}")
            press_enter()
            if not check_deps():
                sys.exit(1)

        main_menu()

    except KeyboardInterrupt:
        print()
        print(f"\n  {G('Sampai jumpa! 👋')}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

# appRebuild

**APK Decompile and Compile Tool for Termux**

appRebuild is a command-line tool for Android reverse engineering workflows running
entirely inside Termux on Android. It wraps apktool to decompile APK files into
readable smali and resource files, allows editing, then recompiles and signs the
result — all without requiring a desktop computer.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Interactive Mode](#interactive-mode)
- [CLI Reference](#cli-reference)
- [Directory Layout](#directory-layout)
- [Signing](#signing)
- [Log Files](#log-files)
- [Workflow Overview](#workflow-overview)
- [Troubleshooting](#troubleshooting)
  - [Mirror errors](#mirror-errors----404-broken-packages-or-ssl-symbol-errors)
  - [apt lock error](#apt-lock-error----could-not-get-lock--held-by-process)
  - [apktool not found](#package-apktool-has-no-installation-candidate)
  - [command not found](#apkrebuild-command-not-found)
  - [curl error 23](#curl-23-client-returned-error-on-write)
- [Changelog](#changelog)
- [License](#license)

---

## Requirements

| Requirement | Minimum version | Notes |
|---|---|---|
| Android | 7.0 (API 24) | Termux requires Android 7+ |
| Termux | Any recent F-Droid build | Use F-Droid, not Play Store |
| Python | 3.8 | `pkg install python` |
| Java | OpenJDK 17 | `pkg install openjdk-17` |
| apktool | Any current version | Not in standard repo — see installation note |

> **Note on apktool:** apktool is not available in the standard Termux package
> repository. It must be installed via a separate step using a community
> installer that registers a trusted APT source. The process is described below.

**Optional tools** (improves output quality if present):

| Tool | Package | Purpose |
|---|---|---|
| apksigner | `android-tools` | Preferred signing method (v2/v3 scheme) |
| zipalign | `android-tools` | Aligns APK for optimal install performance |
| jarsigner | bundled with openjdk-17 | Fallback signing if apksigner is absent |

---

## Installation

### Step 1 — Install Termux

Download Termux from [F-Droid](https://f-droid.org/en/packages/com.termux/).
The Play Store version is outdated and receives no package updates — do not use it.

### Step 2 — Switch to a reliable mirror and update

Before installing anything, switch the Termux package mirror to the official
Cloudflare CDN. Third-party mirrors (such as mirrors hosted in China) are
frequently out of sync and will cause 404 errors or broken package installations.

```
echo "deb https://packages.termux.dev/apt/termux-main stable main" > $PREFIX/etc/apt/sources.list
apt update && apt full-upgrade -y
```

If `apt full-upgrade` gets stuck on a lock file error, kill the blocking process
first — see the Troubleshooting section for the full procedure.

After the upgrade completes, install the required packages:

```
pkg install python openjdk-17 android-tools curl -y
```

### Step 3 — Install apktool

apktool is not in the standard Termux repository. The recommended method is to
use the community installer by rendiix, which registers a trusted APT repository
and then installs apktool through `pkg`:

```
curl -fsSL https://raw.githubusercontent.com/rendiix/termux-apktool/main/install.sh | bash
```

After the script completes, verify:

```
apktool --version
```

You should see a version number such as `2.8.x` or newer. If the command is not
found, open a new Termux session and try again.

**Alternative (without curl):**

```
pkg install wget -y
wget -qO /tmp/install.sh https://raw.githubusercontent.com/rendiix/termux-apktool/main/install.sh
bash /tmp/install.sh
```

**What the installer does:** it adds the rendiix package repository to Termux's
APT sources at `$PREFIX/etc/apt/sources.list.d/rendiix.list` and imports the
GPG key. After that, `pkg upgrade apktool` will keep it up to date like any
other package.

### Step 4 — Create the bin directory

Termux does not create `~/bin` by default. Create it before downloading:

```
mkdir -p ~/bin
```

### Step 5 — Download appRebuild

```
curl -fsSL https://raw.githubusercontent.com/R3XBASE/appRebuild/refs/heads/main/appRebuild.py \
  -o ~/bin/appRebuild
chmod +x ~/bin/appRebuild
```

Or clone the full repository:

```
git clone https://github.com/R3XBASE/appRebuild.git
chmod +x appRebuild/appRebuild.py
ln -s "$PWD/appRebuild/appRebuild.py" ~/bin/appRebuild
```

> **If curl exits with error (23):** the destination directory does not exist or
> the disk is full. Confirm `~/bin` was created with `ls ~/bin`, then check free
> space with `df -h $HOME`. Clear the package cache with `apt clean` if space is
> low.

### Step 6 — Add ~/bin to PATH

`~/bin` is not in the Termux default PATH. Add it permanently so the
`appRebuild` command is available in every session:

```
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify the command is found:

```
which appRebuild
```

It should print `/data/data/com.termux/files/home/bin/appRebuild`.

To run without modifying PATH, use the full path instead:

```
python3 ~/bin/appRebuild
```

### Step 7 — First run

```
appRebuild
```

On first launch, appRebuild checks all dependencies and guides you through
installing anything that is missing. If apktool was not yet installed, the tool
will offer to run the rendiix installer automatically.

---

## Quick Start

The most common workflow in three commands:

```
# 1. Decompile
appRebuild --decompile /sdcard/Download/MyApp.apk

# 2. Edit smali / resources
nano ~/appRebuild/decompiled/MyApp/smali/com/example/MainActivity.smali

# 3. Compile and sign
appRebuild --compile ~/appRebuild/decompiled/MyApp
```

The signed APK will be written to `~/appRebuild/signed/`.

---

## Interactive Mode

Launch without arguments to enter the full-screen menu:

```
appRebuild
```

```
  MAIN MENU

  [1]  Decompile APK  ->  Smali
  [2]  Compile Smali  ->  APK
  [3]  Sign APK
  [4]  File Manager
  [5]  Install / Update Dependencies
  [6]  About & Info

  [0]  Exit
```

### Menu 1 — Decompile APK

Prompts for an APK path, then calls `apktool d` to unpack the APK into smali
bytecode and decoded resources. Output is saved to:

```
~/appRebuild/decompiled/<apk-name>/
```

The decompiled folder contains:

```
<apk-name>/
  AndroidManifest.xml    Application manifest (decoded)
  apktool.yml            apktool metadata (do not delete)
  smali/                 Dalvik bytecode as editable .smali files
  res/                   Decoded resource files (layouts, drawables, strings)
  assets/                Raw assets bundled in the APK
  lib/                   Native .so libraries (if any)
  unknown/               Files apktool could not decode
```

### Menu 2 — Compile Smali

Lists all folders in `~/appRebuild/decompiled/` for selection, or accepts a
manual path. Calls `apktool b` to rebuild the APK. If zipalign is available it
runs automatically before signing.

Output APK is written to:

```
~/appRebuild/output/<name>_<timestamp>.apk
```

After a successful compile, you are prompted to sign immediately.

### Menu 3 — Sign APK

Lists unsigned APKs in the output folder or accepts a manual path. Signing uses
apksigner if available, falling back to jarsigner. The signed APK is written to:

```
~/appRebuild/signed/<name>_signed.apk
```

See [Signing](#signing) for details on the debug keystore.

### Menu 4 — File Manager

Displays a summary of all decompiled folders, output APKs, and signed APKs with
file sizes. Offers selective or full deletion with confirmation prompts.

### Menu 5 — Install / Update Dependencies

Re-runs the dependency check and offers to install missing packages via `pkg`.
Run this whenever you update Termux or apktool.

### Menu 6 — About & Info

Displays the current version, work directory path, detected tool versions,
keystore status, and a one-line workflow summary.

---

## CLI Reference

appRebuild can be used non-interactively, making it suitable for shell scripts
and automated workflows.

### Synopsis

```
appRebuild [--decompile APK] [--compile DIR] [--sign APK]
           [--check-deps] [--no-sign] [--output DIR]
           [--version] [--help]
```

### Options

```
--decompile APK     Decompile the given APK file.
                    Output: ~/appRebuild/decompiled/<stem>/

--compile DIR       Compile the given apktool folder into an APK.
                    Signs automatically unless --no-sign is passed.
                    Output: ~/appRebuild/output/<name>_<timestamp>.apk

--sign APK          Sign the given APK with the debug keystore.
                    Output: ~/appRebuild/signed/<name>_signed.apk

--check-deps        Check for required dependencies and offer to install
                    any that are missing. Exits 0 on success, 1 on failure.

--no-sign           Skip automatic signing after --compile.

--output DIR        Override the output directory used by --compile.
                    Directory is created if it does not exist.

--version           Print version and exit.

--help              Print this help and exit.
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Operation failed (see stderr and log file) |
| 127 | Required tool not found in PATH |

### Examples

Decompile an APK:

```
appRebuild --decompile /sdcard/Download/com.example.app.apk
```

Compile without signing (for manual inspection first):

```
appRebuild --compile ~/appRebuild/decompiled/com.example.app --no-sign
```

Compile and write APK to a custom directory:

```
appRebuild --compile ~/appRebuild/decompiled/com.example.app --output /sdcard/build
```

Sign an existing APK:

```
appRebuild --sign ~/appRebuild/output/com.example.app_20260623_143000.apk
```

Full pipeline in a shell script:

```sh
#!/data/data/com.termux/files/usr/bin/bash
set -e

APK="/sdcard/Download/target.apk"
NAME=$(basename "$APK" .apk)

appRebuild --decompile "$APK"

# --- make edits here ---
sed -i 's/debuggable="false"/debuggable="true"/' \
    ~/appRebuild/decompiled/"$NAME"/AndroidManifest.xml

appRebuild --compile ~/appRebuild/decompiled/"$NAME"

echo "Done. Signed APK: ~/appRebuild/signed/${NAME}_signed.apk"
```

---

## Directory Layout

All data is stored under `~/appRebuild/`:

```
~/appRebuild/
  decompiled/          Unpacked APK folders (one folder per APK)
    <apk-name>/
      AndroidManifest.xml
      apktool.yml
      smali/
      res/
      assets/
  output/              Compiled unsigned (or pre-sign) APKs
  signed/              Signed APKs ready for installation
  logs/                Per-operation log files
  debug.keystore       Auto-generated debug signing key
  .setup_done          Flag file created after first dependency check
```

---

## Signing

### Debug keystore

appRebuild generates a debug keystore at `~/appRebuild/debug.keystore` the first
time signing is requested. The keystore is created with the following parameters:

| Parameter | Value |
|---|---|
| Algorithm | RSA 2048-bit |
| Validity | 10 000 days (~27 years) |
| Alias | `apprebuilddebug` |
| Store password | `apprebuild2026` |
| Distinguished name | `CN=AppRebuild, OU=Debug, O=Dev, L=Local, ST=Local, C=ID` |

This keystore is suitable for testing and sideloading. It is **not** suitable for
publishing to app stores or for production distribution.

### Signing tools

appRebuild selects the signing tool in this order:

1. **apksigner** (from `android-tools`) — supports APK Signature Scheme v2 and v3,
   which are required by Android 7.0+ for optimal compatibility.
2. **jarsigner** (from `openjdk-17`) — legacy JAR signing (v1 scheme). Works but
   produces APKs with only v1 signatures.

Install `android-tools` to get apksigner and zipalign:

```
pkg install android-tools -y
```

### Using a custom keystore

appRebuild does not currently expose a UI for custom keystores. To sign with your
own key, sign the output APK directly using apksigner after compiling:

```
apksigner sign \
  --ks /path/to/your.keystore \
  --ks-key-alias your-alias \
  --out ~/appRebuild/signed/MyApp_release.apk \
  ~/appRebuild/output/MyApp_20260623_143000.apk
```

---

## Log Files

Every decompile and compile operation writes a log file to `~/appRebuild/logs/`.

Naming convention:

```
<apk-name>_decompile_<HHMMSS>.log
<apk-name>_compile_<YYYYMMDD_HHMMSS>.log
appRebuild_<YYYYMMDD_HHMMSS>.log     (session log)
```

Logs contain the full stdout and stderr output of apktool and signing tools.
Check these files first when an operation fails.

View the most recent log:

```
ls -t ~/appRebuild/logs/ | head -1 | xargs -I{} cat ~/appRebuild/logs/{}
```

---

## Workflow Overview

```
Input APK
    |
    v
[1] Decompile (apktool d)
    |
    v
~/appRebuild/decompiled/<name>/
    AndroidManifest.xml
    smali/  <-- edit here
    res/    <-- edit here
    |
    v
[2] Compile (apktool b)
    |
    v
~/appRebuild/output/<name>_<timestamp>.apk
    |
    v
[zipalign]  (automatic, if android-tools is installed)
    |
    v
[3] Sign (apksigner or jarsigner)
    |
    v
~/appRebuild/signed/<name>_signed.apk
    |
    v
adb install  /  direct install on device
```

---

## Troubleshooting

### Mirror errors — 404, broken packages, or SSL symbol errors

This is the most common class of errors on fresh or neglected Termux installs.
Symptoms include:

- `404 Not Found` when running `pkg install` or `apt upgrade`
- `CANNOT LINK EXECUTABLE "curl": cannot locate symbol "SSL_set_quic_tls_transport_params"`
- `Unable to fetch some archives`
- Packages that install but immediately crash on first run

All of these are caused by using an outdated or out-of-sync third-party mirror.
The fix is to switch to the official Termux CDN hosted on Cloudflare, which is
always up to date:

```
echo "deb https://packages.termux.dev/apt/termux-main stable main" > $PREFIX/etc/apt/sources.list
apt update && apt full-upgrade -y
```

The `full-upgrade` (not just `upgrade`) is required because it resolves
dependency conflicts that a standard upgrade would leave behind.

After it completes, open a new Termux session before continuing.

If you have the `termux-change-repo` command available, you can also use the
interactive mirror selector:

```
termux-change-repo
```

Select Cloudflare or the official `packages.termux.dev` entry from the list.

### apt lock error — "Could not get lock ... held by process"

This happens when a previous `apt` or `pkg` process was interrupted (by a
force-close or network drop) and did not release its lock files.

Step 1 — identify and kill the blocking process (replace `PID` with the number
shown in the error message):

```
kill -9 PID
```

Step 2 — remove the stale lock files:

```
rm -f $PREFIX/var/lib/apt/lists/lock
rm -f $PREFIX/var/lib/dpkg/lock
rm -f $PREFIX/var/lib/dpkg/lock-frontend
```

Step 3 — repair any half-configured packages:

```
dpkg --configure -a
```

Step 4 — retry:

```
apt update && apt full-upgrade -y
```

### "Package 'apktool' has no installation candidate"

This is the most common error on fresh Termux installs. apktool is not in the
standard Termux repository. Run the rendiix installer to add the correct source:

```
curl -fsSL https://raw.githubusercontent.com/rendiix/termux-apktool/main/install.sh | bash
```

If curl is not installed:

```
pkg install curl -y
curl -fsSL https://raw.githubusercontent.com/rendiix/termux-apktool/main/install.sh | bash
```

After the installer finishes, open a new Termux session and verify:

```
apktool --version
```

If it still shows "command not found", confirm the repository was added:

```
cat $PREFIX/etc/apt/sources.list.d/rendiix.list
```

It should contain a line starting with `deb https://rendiix.github.io`. If the
file is empty or missing, run the installer again.

### "appRebuild: command not found"

`~/bin` is not in the Termux default PATH. Add it permanently:

```
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Then try again:

```
appRebuild
```

To verify the PATH is set correctly in the current session:

```
echo $PATH | tr ':' '\n' | grep bin
```

The output should include a line ending in `/home/bin`. If it does not, run
`source ~/.bashrc` again or open a new Termux session.

As a fallback, the tool can always be invoked directly without PATH:

```
python3 ~/bin/appRebuild
```

### "curl: (23) client returned ERROR on write"

The destination directory does not exist. Create it first:

```
mkdir -p ~/bin
```

Then retry the curl command. If the error persists, check available disk space:

```
df -h $HOME
```

If free space is below 50 MB, clear the package cache before retrying:

```
apt clean
rm -rf ~/.cache
```



The PATH may not include the Termux bin directory in the current session. Start
a fresh Termux session, or run:

```
export PATH="$PREFIX/bin:$PATH"
```

To make this permanent:

```
echo 'export PATH="$PREFIX/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### "java: command not found"

```
pkg install openjdk-17 -y
```

After installation, verify:

```
java -version
```

### Decompile fails with "brut.androlib.AndrolibException"

This usually means the APK uses resources or a manifest format that the installed
version of apktool does not support. Update apktool:

```
pkg upgrade apktool -y
```

If the error persists, try decompiling without resources:

```
apktool d --no-res /path/to/app.apk -o ~/appRebuild/decompiled/app_nores
```

### Compile fails with "could not find class"

The smali code references a class that was modified incorrectly. Review your edits
for mismatched register counts or broken method signatures. The compile log at
`~/appRebuild/logs/` will point to the exact file and line.

### APK installs but crashes immediately

Common causes:
- Smali register count does not match the number of registers declared in the
  `.registers` directive.
- A method was removed but is still referenced elsewhere.
- The `apktool.yml` file was deleted or corrupted — it must remain untouched.

### "INSTALL_PARSE_FAILED_NO_CERTIFICATES"

The APK is not signed. Run menu option 3 or use `--sign`.

### "INSTALL_FAILED_UPDATE_INCOMPATIBLE"

The device has the original APK installed signed with a different key. Uninstall
the original first:

```
adb uninstall com.example.app
```

Or uninstall directly from Android Settings before installing the rebuilt APK.

### Colors do not display correctly

appRebuild auto-disables ANSI color codes when output is redirected to a file or
pipe. If colors are not showing in the Termux terminal, verify your terminal
emulator supports 256-color sequences. Most Termux builds do by default.

### Storage permission errors (cannot read from /sdcard)

Grant Termux storage access:

```
termux-setup-storage
```

Then restart Termux. Files in `/sdcard` will be accessible at
`~/storage/shared/`.

---

## Changelog

### v2.0.0

- Rewritten in Python 3 for reliability and maintainability.
- Added non-interactive CLI mode (`--decompile`, `--compile`, `--sign`,
  `--check-deps`, `--no-sign`, `--output`).
- Fixed critical bug: apktool was being invoked twice per operation in v1
  (once for display, once for logging), wasting time and I/O.
- Fixed `PIPESTATUS` unreliability in Bash; Python subprocess returncode is
  always accurate.
- Fixed jarsigner fallback: v1 passed the wrong file path to the signer.
- Fixed path expansion to handle environment variables in addition to `~`.
- Fixed menu selection bounds: out-of-range indices no longer produce undefined
  behaviour.
- Added zipalign step (automatic, silent if tool absent).
- Added rotating session log files in `~/appRebuild/logs/`.
- ANSI color output now auto-disables when stdout is not a TTY.
- `Ctrl+C` is now caught gracefully at all menu levels.

### v1.0.0

- Initial release as a Bash script.
- Interactive TUI menu for decompile, compile, sign, file management, and
  dependency install.
- Auto-generated debug keystore on first sign.

---

## License

MIT License

Copyright (c) 2026 appRebuild

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

#!/usr/bin/env python3
"""
runtests.py — TAU regression test launcher.

Replaces runtests.sh.  SSH agent must be initialised before running;
use runtests_bootstrap.sh to invoke this from cron.

Requirements: Python 3.9+, rsync, ssh, scp, git on the controlling host.
"""

import sys
import os
import re
import shlex
import shutil
import smtplib
import subprocess
import datetime
import email.message
import email.utils
import pathlib
import time
import argparse
import concurrent.futures

# ── Bootstrap: ensure scripts/ is importable ───────────────────────────────────
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
import configs  # noqa: E402 (import after path manipulation)

# ── Paths ──────────────────────────────────────────────────────────────────────
LOCAL_HOME    = pathlib.Path.home()
LOCAL_TESTTAU = LOCAL_HOME / "testtau"
RESULTS_DIR   = LOCAL_TESTTAU / "results"

# ── Tunable settings ───────────────────────────────────────────────────────────

# TAU git branch to check out before testing.
TAU_BRANCH = "master"
#TAU_BRANCH = "openmp-suspend"
#TAU_BRANCH = "L0_decode"
#TAU_BRANCH= "combine-wrappers"
# TAU_BRANCH = "OMPT_ROCM"
#TAU_BRANCH = "tune-start-stop"

# Web / mail host.
WEBHOST   = "yu"
WEBPATH   = "~/public_html/tau_regression"
EMAIL_TO   = "wjspear@gmail.com"
EMAIL_FROM = "onboarding@resend.dev"
SMTP_HOST  = "smtp.resend.com"
SMTP_PORT  = 465
SMTP_KEY_FILE = pathlib.Path.home() / ".resend_api_key"

# Active platforms — config names as they appear in configs.configurations.
# Comment / uncomment individual lines to enable or disable platforms.
ACTIVE_PLATFORMS = [
    "yu",
    "pegasus",
    "pegasus_intel",
    "instinct",
    "gilgamesh_nvhpc",
    "gary",
    "hopper1",
    # "delphi",
    # "delphi_intel",
    # "delphi_pgi",
    # "instinct_rocm",
    # "omnia_rocm",
    # "sever",
    # "saturn",
    # "miniyu",
]

# SSH keys loaded via keychain (used when running under cron/non-login shells).
# Add key filenames here (basename only, relative to ~/.ssh/).
KEYCHAIN_KEYS = ["id_rsa", "git_key_rsa"]

# ── SSH agent bootstrap ────────────────────────────────────────────────────────

def ensure_ssh_agent() -> None:
    """
    Make sure an SSH agent with loaded keys is available.

    * Interactive session: SSH_AUTH_SOCK is already set and the socket exists
      → nothing to do.
    * Cron / non-login shell: invoke keychain in --noask --eval mode and parse
      the exported variables directly into os.environ.
    """
    sock = os.environ.get("SSH_AUTH_SOCK", "")
    if sock and pathlib.Path(sock).exists():
        # Agent already live — nothing to do.
        return

    r = subprocess.run(
        ["keychain", "-q", "--noask", "--agents", "ssh",
         "--eval"] + KEYCHAIN_KEYS,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print("WARNING: keychain failed — SSH operations may ask for passwords.",
              file=sys.stderr)
        return

    # keychain --eval emits lines like:
    #   SSH_AUTH_SOCK=/tmp/ssh-XXX/agent.1234; export SSH_AUTH_SOCK;
    #   SSH_AGENT_PID=1234; export SSH_AGENT_PID;
    for line in r.stdout.splitlines():
        m = re.match(r'(\w+)=([^;]+);', line)
        if m:
            os.environ[m.group(1)] = m.group(2)


# ── Formatting helpers ────────────────────────────────────────────────────────

def fmt_duration(seconds: float) -> str:
    """Format a duration as 'Xh Ym Zs', omitting leading zero fields."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m or h:
        parts.append(f"{m}m")
    parts.append(f"{sec}s")
    return " ".join(parts)


# ── Error tracking ─────────────────────────────────────────────────────────────
_errors: list[str] = []


def log_error(msg: str) -> None:
    _errors.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr, flush=True)


# ── Source update ──────────────────────────────────────────────────────────────

def update_source() -> bool:
    """git pull tau2 (checking out TAU_BRANCH) and pdtoolkit.

    Returns False if a fatal error (bad branch) prevents a safe run.
    """
    tau2   = LOCAL_TESTTAU / "tau2"
    pdtkit = LOCAL_TESTTAU / "pdtoolkit"

    if not tau2.is_dir():
        log_error(
            f"FATAL: tau2 not found at {tau2}. "
            "Aborting — no tests were run."
        )
        return False

    for path, name, do_checkout in [
        (tau2,   "tau2",       True),
        (pdtkit, "pdtoolkit",  False),
    ]:
        if not path.is_dir():
            log_error(f"{name} not found at {path}")
            continue
        print(f"  Updating {name} …", flush=True)
        if do_checkout:
            r = subprocess.run(["git", "-C", str(path), "fetch"])
            if r.returncode != 0:
                log_error(
                    f"FATAL: git fetch failed for {name}. "
                    f"Cannot verify branch '{TAU_BRANCH}' is current. "
                    f"Aborting — no tests were run."
                )
                return False
            r = subprocess.run(["git", "-C", str(path), "checkout", TAU_BRANCH])
            if r.returncode != 0:
                log_error(
                    f"FATAL: git checkout '{TAU_BRANCH}' failed for {name}. "
                    f"Branch does not exist locally or on the remote. "
                    f"Aborting — no tests were run."
                )
                return False
        r = subprocess.run(["git", "-C", str(path), "pull"])
        if r.returncode != 0:
            log_error(
                f"FATAL: git pull failed for {name}. "
                f"Source may be stale — aborting to avoid running outdated tests."
            )
            return False
    return True


# ── NPB provisioning ──────────────────────────────────────────────────────────

# NPB 3.4.4 standard suite — expands to NPB3.4/ with NPB3.4-MPI/ inside.
NPB_URL = "https://www.nas.nasa.gov/assets/npb/NPB3.4.4.tar.gz"
NPB_DIR = "NPB3.4-MPI"


def _patch_npb_makedef(npb_dir: pathlib.Path) -> None:
    """
    Idempotently patch config/make.def with three changes needed for TAU
    regression testing:

    1. MPIFC → tau_f90.sh  (Fortran MPI compiler wrapper)
    2. MPICC → tau_cc.sh   (C MPI compiler wrapper)
    3. FFLAGS split into DEFAULT_FFLAGS + EXTRA_FFLAGS so that the test
       infrastructure can inject flags via the EXTRA_FFLAGS env-var
       (e.g. EXTRA_FFLAGS=-noswitcherror for non-standard Fortran platforms).

    If make.def does not exist, it is first created by copying make.def.template.
    The template itself is never modified.
    """
    config_dir = npb_dir / "config"
    make_def   = config_dir / "make.def"

    if not make_def.exists():
        template = config_dir / "make.def.template"
        if not template.exists():
            log_error(f"NPB: cannot find {make_def} or {template} — skipping patch")
            return
        import shutil as _shutil
        _shutil.copy(template, make_def)

    text    = make_def.read_text()
    changed = False

    if "tau_f90.sh" not in text:
        text = re.sub(r"^(MPIFC\s*=\s*).*$", r"\1tau_f90.sh", text, flags=re.MULTILINE)
        changed = True

    if "tau_cc.sh" not in text:
        text = re.sub(r"^(MPICC\s*=\s*).*$", r"\1tau_cc.sh", text, flags=re.MULTILINE)
        changed = True

    # Replace a plain "FFLAGS = <val>" line with the DEFAULT_FFLAGS/?=/EXTRA_FFLAGS
    # pattern so that callers can pass EXTRA_FFLAGS=-noswitcherror (or similar).
    # Also inject -std=legacy, required for gfortran 10+ to accept NPB's older
    # Fortran style.  Guard: skip if already fully patched.
    if "EXTRA_FFLAGS" not in text:
        def _fflags_replacer(m: re.Match) -> str:
            base = m.group(1).strip()
            if "-std=legacy" not in base:
                base = base + " -std=legacy"
            return f"DEFAULT_FFLAGS ?= {base}\nFFLAGS = ${{DEFAULT_FFLAGS}} ${{EXTRA_FFLAGS}}"
        new_text = re.sub(
            r"^FFLAGS\s*=\s*(.+)$", _fflags_replacer, text, flags=re.MULTILINE
        )
        if new_text != text:
            text    = new_text
            changed = True
    elif "-std=legacy" not in text:
        # Already has EXTRA_FFLAGS but missing -std=legacy (older patch applied).
        new_text = re.sub(
            r"^(DEFAULT_FFLAGS\s*\?=\s*.+)$",
            lambda m: m.group(1) + " -std=legacy",
            text, flags=re.MULTILINE
        )
        if new_text != text:
            text    = new_text
            changed = True

    if changed:
        make_def.write_text(text)
        print(f"  Patched {make_def} with TAU compiler wrappers and EXTRA_FFLAGS support",
              flush=True)


def ensure_npb() -> bool:
    """
    Ensure NPB3.4-MPI is present at tau2/examples/NPB3.4-MPI inside the local
    testtau tree (the only location used by the test suite).

    If the directory is already there, just re-apply the make.def patch
    (idempotent).  Otherwise, download NPB_URL, extract NPB3.4-MPI/ from the
    archive, and patch make.def.

    Returns True on success, False on failure (non-fatal — the NPB test will
    simply fail to build on the remote).
    """
    import tarfile
    import urllib.request
    import tempfile
    import shutil as _shutil

    dest = LOCAL_TESTTAU / "tau2" / "examples" / NPB_DIR

    if (dest / "Makefile").exists():
        _patch_npb_makedef(dest)
        return True

    print(f"  NPB not found — downloading {NPB_URL}", flush=True)

    tmp_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = pathlib.Path(tmp.name)
        urllib.request.urlretrieve(NPB_URL, tmp_path)

        with tarfile.open(tmp_path) as tar:
            # Identify the top-level archive directory that contains NPB_DIR.
            archive_root: str | None = None
            for m in tar.getmembers():
                parts = pathlib.PurePosixPath(m.name).parts
                if len(parts) >= 2 and parts[1] == NPB_DIR:
                    archive_root = parts[0]
                    break
            if archive_root is None:
                log_error(
                    f"NPB: could not find {NPB_DIR}/ inside the archive — "
                    "archive layout may have changed"
                )
                return False

            with tempfile.TemporaryDirectory() as extract_dir:
                tar.extractall(path=extract_dir)
                src = pathlib.Path(extract_dir) / archive_root / NPB_DIR
                _shutil.copytree(str(src), str(dest))

        _patch_npb_makedef(dest)
        print(f"  NPB provisioned at {dest}", flush=True)
        return True

    except Exception as exc:
        log_error(f"NPB provisioning failed: {exc}")
        return False
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


# ── Local-to-remote copy ───────────────────────────────────────────────────────

def local_copy(active_cfgs: list) -> None:
    """
    rsync LOCAL_TESTTAU to each unique (url, remoteHome) pair in the active
    platform list.  The tree lands at <remoteHome>/TAU_REGRESSION/testtau/ on
    each remote host — matching the original runtests.sh localcopy() layout.
    """
    seen: set[tuple[str, str]] = set()
    src  = str(LOCAL_TESTTAU)

    for cfg in active_cfgs:
        if not cfg.url:
            continue
        key = (cfg.url, cfg.remoteHome)
        if key in seen:
            continue
        seen.add(key)
        dest = f"{cfg.url}:{cfg.remoteHome}/TAU_REGRESSION"
        print(f"  rsync → {dest}", flush=True)
        r = subprocess.run(["rsync", "-k", "--delete", "-az", "-q", src, dest])
        if r.returncode != 0:
            log_error(f"rsync to {cfg.url} failed (rc={r.returncode})")


# ── Per-platform remote SSH command ────────────────────────────────────────────

def _build_remote_cmd(platform: str, cfg) -> str:
    """
    Build the shell command string executed remotely via:
        ssh <url> bash -l -c '<cmd>'

    Generates the ssh command to copy the test script to its working directory and then run it.
    """
    runroot = cfg.runroot
    dest    = f"{runroot}/TAU_REGRESSION/testtau-{platform}"

    steps = [
        # Try module-load Python; tolerate failure (spack / system Python also work)
        "{ module load python 2>/dev/null && unset PYTHONHOME; } || true",
        f"export PYTHONPATH={dest}/scripts",
        "ulimit -c unlimited",
        f"mkdir -p {dest}",
        # Sync scripts / tau2 from the remote home staging area
        "cd $HOME/TAU_REGRESSION",
        (
            f"rsync --delete -az -q "
            f"testtau/scripts testtau/tau2 {dest}"
        ),
        # Smart PDT: only rsync if changed, otherwise mark as skip-rebuild
        (
            f"if [[ ! -d {dest}/pdtoolkit ]]"
            f" || [[ ! -f {dest}/pdtoolkit/include/pdbAll.h ]]"
            f" || ! diff -q -r testtau/pdtoolkit/CVS/ {dest}/pdtoolkit/CVS/ &>/dev/null"
            f"; then"
            f"  rsync --delete -az -q testtau/pdtoolkit {dest};"
            f"  rm -rf {dest}/pdtoolkit/no-build;"
            f" else"
            f"  touch {dest}/pdtoolkit/no-build;"
            f" fi"
        ),
        # Switch into runroot so tau_regression.py receives the right run_prefix
        f"cd {runroot}",
        f"time python3 {dest}/scripts/tau_regression.py {platform} {runroot}",
    ]
    return "; ".join(steps)


def _run_platform(platform: str, cfg, html_path: pathlib.Path) -> int:
    """SSH into cfg.url and run tau_regression.py, capturing all output to html_path."""
    inner = _build_remote_cmd(platform, cfg)
    cmd   = ["ssh", cfg.url, "bash -l -c " + shlex.quote(inner)]
    print(f"  Launching {platform} → {cfg.url}", flush=True)
    with html_path.open("w", errors="replace") as fh:
        result = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    return result.returncode


def launch_tests(active_cfgs: list, date_dir: pathlib.Path, serial: bool = False) -> None:
    """Launch all platforms in parallel; collect exit codes when done."""
    n = 1 if serial else (len(active_cfgs) or 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        futures = {
            pool.submit(
                _run_platform,
                cfg.name,
                cfg,
                date_dir / f"{cfg.name}.html",
            ): cfg.name
            for cfg in active_cfgs
        }
        for fut, name in futures.items():
            try:
                rc = fut.result()
            except Exception as exc:
                log_error(f"{name}: unexpected exception: {exc}")
            else:
                if rc != 0:
                    log_error(f"{name} exited with code {rc}")
    print("All platform tests complete.", flush=True)


# ── Results checking and publishing ────────────────────────────────────────────

def check_and_publish(date_dir: pathlib.Path, lprint, timing_lines: list | None = None, *, send_email: bool = True) -> None:
    """Run checkresults.py, scp results to webhost, send email summary."""

    # Run checkresults.py from the dated results directory
    r = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "checkresults.py"), TAU_BRANCH],
        cwd=str(date_dir),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or "found an error!" in r.stdout:
        log_error("checkresults.py reported errors")

    # Scan HTML files for in-band failure markers
    for html_file in sorted(date_dir.glob("*.html")):
        try:
            text = html_file.read_text(errors="replace")
        except OSError:
            continue
        if "Failure: Encountered" in text:
            log_error(f"Failure marker found in {html_file.name}")
            break

    passed  = not _errors
    subject = "TAU Regression OK" if passed else "TAU Regression Encountered Errors"
    status  = "PASSED" if passed else "FAILED"
    lprint(f"Result: {status}")

    # Copy dated results directory and index to web host
    subprocess.run(["scp", "-r", str(date_dir),            f"{WEBHOST}:{WEBPATH}"], check=False)
    subprocess.run(["scp", str(RESULTS_DIR / "index.html"),f"{WEBHOST}:{WEBPATH}"], check=False)

    # Build email body, write to /tmp/today, scp, then send via mailx on webhost
    body_lines = ["-- Testing Arch Suite --"]
    if timing_lines:
        body_lines.extend(timing_lines)
    body_lines.append(f"  Arch suite {status}")
    body_lines.append("  See http://yu.nic.uoregon.edu/~wspear/tau_regression/ for more details")
    body_lines.append("")
    if _errors:
        body_lines.append("Failures:")
        body_lines.extend(f"  {e}" for e in _errors)
    else:
        body_lines.append("No failures detected.")
    body = "\n".join(body_lines) + "\n"

    today = pathlib.Path("/tmp/today")
    today.write_text(body)

    subprocess.run(["scp", str(today), f"{WEBHOST}:{WEBPATH}/today"], check=False)

    # Send mail via Resend SMTP (API key in ~/.resend_api_key, mode 600).
    msg = email.message.EmailMessage()
    msg["Subject"]    = subject
    msg["From"]       = EMAIL_FROM
    msg["To"]         = EMAIL_TO
    msg["Message-ID"] = email.utils.make_msgid(domain="resend.dev")
    msg["Date"]       = email.utils.formatdate()
    msg.set_content(body)
    if send_email:
        try:
            api_key = SMTP_KEY_FILE.read_text().strip()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
                smtp.login("resend", api_key)
                smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_bytes())
            lprint(f"Email sent to {EMAIL_TO}")
        except Exception as exc:
            log_error(f"Failed to send email: {exc}")
    else:
        lprint("Email skipped (--no-email)")


# ── Argument parsing ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TAU regression test launcher.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Platform config names come from configs.configurations.\n"
            "Example:\n"
            "  runtests.py --tau-branch my-feature --configs yu pegasus"
        ),
    )
    parser.add_argument(
        "--tau-branch",
        metavar="BRANCH",
        default=None,
        help=f"TAU git branch to test (default: {TAU_BRANCH!r} as set in script)",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        metavar="NAME",
        help="One or more platform config names to run "
             "(default: ACTIVE_PLATFORMS list in script)",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Skip sending the results email (useful for manual/ad-hoc runs)",
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Skip the git fetch/pull source update step",
    )
    parser.add_argument(
        "--serial",
        action="store_true",
        help="Run platform tests one at a time instead of in parallel",
    )
    args = parser.parse_args()
    if args.configs:
        unknown = [n for n in args.configs if n not in configs.configurations]
        if unknown:
            available = sorted(configs.configurations.keys())
            parser.error(
                f"Unknown config(s): {', '.join(unknown)}\n"
                f"Available configs: {', '.join(available)}"
            )
    return args


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()

    global TAU_BRANCH
    if args.tau_branch:
        TAU_BRANCH = args.tau_branch

    now      = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d_%H-%M")
    date_dir = RESULTS_DIR / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    (RESULTS_DIR / "recent.filename").write_text(date_str + "\n")

    log_path = pathlib.Path(f"/tmp/nightly-arch-test.{date_str}.log")
    print(f"Log:     {log_path}")
    print(f"Results: {date_dir}")

    # Resolve active configs (validate names at startup)
    platform_names = args.configs if args.configs else ACTIVE_PLATFORMS
    active_cfgs = []
    for name in platform_names:
        if name not in configs.configurations:
            log_error(f"Unknown platform '{name}' in ACTIVE_PLATFORMS")
        else:
            active_cfgs.append(configs.configurations[name])

    ensure_ssh_agent()

    with log_path.open("w") as _log:

        def lprint(msg: str) -> None:
            ts   = datetime.datetime.now().strftime("%H:%M:%S")
            line = f"[{ts}] {msg}"
            print(line, flush=True)
            _log.write(line + "\n")
            _log.flush()

        lprint(f"Started at {now}")
        lprint(f"TAU_BRANCH = {TAU_BRANCH}")
        lprint(f"Platforms  = {[c.name for c in active_cfgs]}")

        t0 = time.monotonic()
        if args.no_update:
            lprint("=== update_source (skipped via --no-update) ===")
            source_ok = True
        else:
            lprint("=== update_source ===")
            source_ok = update_source()
            lprint(f"  done in {time.monotonic()-t0:.0f}s")

        if not source_ok:
            lprint("FATAL: source update failed — skipping tests, sending error email.")
            check_and_publish(date_dir, lprint, send_email=not args.no_email)
        else:
            t0 = time.monotonic()
            lprint("=== ensure_npb ===")
            ensure_npb()
            lprint(f"  done in {time.monotonic()-t0:.0f}s")

            t0 = time.monotonic()
            lprint("=== local_copy ===")
            local_copy(active_cfgs)
            upload_elapsed = time.monotonic() - t0
            lprint(f"  done in {upload_elapsed:.0f}s")

            t0 = time.monotonic()
            lprint("=== launch_tests ===")
            launch_tests(active_cfgs, date_dir, serial=args.serial)
            tests_elapsed = time.monotonic() - t0
            lprint(f"  done in {tests_elapsed:.0f}s")

            lprint("=== check_and_publish ===")
            check_and_publish(
                date_dir,
                lprint,
                timing_lines=[
                    f"  Update/Upload completed in {fmt_duration(upload_elapsed)}",
                    f"  Tests completed in {fmt_duration(tests_elapsed)}",
                ],
                send_email=not args.no_email,
            )

        lprint(f"Ended at {datetime.datetime.now()}")
        lprint(f"Total errors: {len(_errors)}")

    # Archive to cold storage once uploaded (matches original bash mv behaviour).
    cold = LOCAL_HOME / "ColdStorage" / "regression_stuff"
    cold.mkdir(parents=True, exist_ok=True)
    shutil.move(str(date_dir), str(cold))

    return len(_errors)


if __name__ == "__main__":
    sys.exit(main())

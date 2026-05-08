# local_settings.py — site-specific overrides for runtests.py
#
# HOW TO USE:
#   cp scripts/local_settings.example.py scripts/local_settings.py
#   Edit local_settings.py with your own values.
#
# local_settings.py is listed in .gitignore and will never be committed.
# Anything defined here overrides the corresponding default in runtests.py.

import pathlib
import configs as _configs  # needed for per-platform remoteHome overrides

# ── TAU branch ────────────────────────────────────────────────────────────────
TAU_BRANCH = "master"
# TAU_BRANCH = "my-feature-branch"

# ── Web publishing ────────────────────────────────────────────────────────────
# Set WEBHOST to an SSH alias / hostname to publish results via scp.
# Leave empty ("") to keep results locally in results/ with a warning.
WEBHOST = ""              # e.g. "yu"
WEBPATH = ""              # e.g. "~/public_html/tau_regression"
WEBURL  = ""              # e.g. "http://yu.nic.uoregon.edu/~youruser/tau_regression/"

# ── Email notification ────────────────────────────────────────────────────────
# Leave EMAIL_TO or EMAIL_FROM empty to disable email entirely (a warning will
# be printed instead of sending).
EMAIL_TO      = ""        # e.g. "you@example.com"
EMAIL_FROM    = ""        # e.g. "tau-regression@yourdomain.com"
SMTP_HOST     = ""        # e.g. "smtp.resend.com"
SMTP_PORT     = 465
SMTP_KEY_FILE = pathlib.Path.home() / ".resend_api_key"

# ── Active platforms ──────────────────────────────────────────────────────────
# Must be keys from configs.configurations (defined in configs.py).
ACTIVE_PLATFORMS = [
    # "yu",
    # "pegasus",
    # "pegasus_intel",
    # "instinct",
    # "gilgamesh_nvhpc",
    # "gary",
    # "hopper1",
]

# ── SSH keychain ──────────────────────────────────────────────────────────────
# Key filenames relative to ~/.ssh/ — loaded by keychain for cron runs.
KEYCHAIN_KEYS = [
    # "id_rsa",
    # "git_key_rsa",
]

# ── Cold storage archive ──────────────────────────────────────────────────────
# After publishing, move the dated results directory here.
# Set to None (or omit) to leave results in place under results/.
COLD_STORAGE = None
# COLD_STORAGE = pathlib.Path.home() / "ColdStorage" / "regression_stuff"

# ── Per-platform remoteHome overrides ────────────────────────────────────────
# Each platform config has a remoteHome attribute that determines where on the
# remote host the TAU_REGRESSION staging tree lives.  Override them here.
#
# To set the same home directory for every platform:
# for _cfg in _configs.configurations.values():
#     _cfg.remoteHome = "/home/youruser"
#
# Or per platform:
# _configs.configurations["yu"].remoteHome         = "/home/youruser"
# _configs.configurations["pegasus"].remoteHome    = "/home/users/youruser"
# _configs.configurations["instinct"].remoteHome   = "/home/users/youruser"

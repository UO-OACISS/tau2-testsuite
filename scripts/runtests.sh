#!/bin/bash
# runtests_bootstrap.sh — cron launcher for runtests.py
#
# Only needed when running from cron where PATH may be minimal.
# When already logged in interactively (SSH_AUTH_SOCK is set), you can run
# runtests.py directly — it detects the live agent and skips keychain.
#
# Example crontab entry:
#   0 2 * * * /home/wspear/testtau/scripts/runtests_bootstrap.sh >> /tmp/runtests-cron.log 2>&1

export USER=wspear
export PATH=/home/wspear/bin:$PATH

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

exec python3 "$SCRIPT_DIR/runtests.py" "$@"

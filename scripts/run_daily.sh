#!/usr/bin/env bash
# Story 1.6 — entry point invoked by the scheduler (launchd/cron) at 17:00.
# Activates the venv, loads .env, runs the pipeline, and records the exit status.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p _bmad-output/logs

# Make Homebrew tools (ffmpeg, node, npx) visible to launchd's minimal PATH.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

if [ -f .env ]; then set -a; . ./.env; set +a; fi

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

"$PY" daily_reporter.py "$@"
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
  echo "[$(date '+%Y-%m-%dT%H:%M:%S')] run_daily.sh: pipeline exited $STATUS" \
    >> _bmad-output/logs/scheduler.log
fi
exit "$STATUS"

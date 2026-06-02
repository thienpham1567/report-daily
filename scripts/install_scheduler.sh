#!/usr/bin/env bash
# Story 1.6 — install the launchd agent that runs the pipeline daily at 17:00.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.vietnix.dailyreporter"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents"
sed "s|__ROOT__|$ROOT|g" "$ROOT/scripts/$LABEL.plist" > "$DEST"

launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"

echo "Installed and loaded: $DEST"
echo "Current timezone: $(date '+%Z %z')  (need ICT/+0700 for 17:00 Vietnam time)"
echo "Trigger a test run now with:  launchctl start $LABEL"
echo "Cron alternative (if you prefer):"
echo "  0 17 * * *  $ROOT/scripts/run_daily.sh >> $ROOT/_bmad-output/logs/cron.log 2>&1"

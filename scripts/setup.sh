#!/usr/bin/env bash
# Story 1.1 — Environment setup and tooling.
# Idempotent: safe to re-run. Sets up FFmpeg, Python venv, ML deps, and HyperFrames.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> [1/6] Checking core toolchain"
command -v git   >/dev/null || { echo "ERROR: git not found"; exit 1; }
command -v node  >/dev/null || { echo "ERROR: Node.js not found (need 22+)"; exit 1; }
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
[ "$NODE_MAJOR" -ge 22 ] || { echo "ERROR: Node 22+ required (have $(node -v))"; exit 1; }
echo "    git $(git --version | awk '{print $3}'), node $(node -v)"

echo "==> [2/6] FFmpeg (AC 1.1.5)"
if ! command -v ffmpeg >/dev/null; then
  if command -v brew >/dev/null; then brew install ffmpeg; else
    echo "ERROR: install ffmpeg manually (brew not found)"; exit 1; fi
fi
ffmpeg -version | head -1

echo "==> [3/6] Python 3.10+ venv"
PYBIN=""
for c in python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null; then
    V="$("$c" -c 'import sys;print(sys.version_info[:2]>=(3,10))')"
    [ "$V" = "True" ] && { PYBIN="$c"; break; }
  fi
done
if [ -z "$PYBIN" ]; then
  echo "    No Python 3.10+ found; installing via brew..."
  brew install python@3.12
  PYBIN="$(brew --prefix)/bin/python3.12"
fi
[ -d .venv ] || "$PYBIN" -m venv .venv
echo "    venv python: $(.venv/bin/python --version)"

echo "==> [4/6] Python dependencies (PyTorch MPS/CPU + OmniVoice — AC 1.1.2/1.1.3)"
.venv/bin/python -m pip install --upgrade pip >/dev/null
# Apple Silicon / CPU wheels. For NVIDIA, replace with:
#   pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
.venv/bin/python -m pip install -r requirements.txt

echo "==> [5/6] HeyGen HyperFrames CLI (AC 1.1.4)"
npx --yes hyperframes@0.6.65 --version
[ -d video ] || npx --yes hyperframes@0.6.65 init video
echo "    HyperFrames doctor:"
( cd video && npx --yes hyperframes@0.6.65 doctor || true )

echo "==> [6/6] Reference voice check (Story 1.3)"
if [ ! -f ref/reference.wav ]; then
  echo "    WARNING: ref/reference.wav not found."
  echo "    Provide a short clean WAV of the target voice + transcript in ref/reference.txt"
  echo "    (or run scripts/make_reference.sh to generate a placeholder)."
fi

echo ""
echo "Setup complete. Next:"
echo "  cp .env.example .env   # then edit credentials / reference voice"
echo "  .venv/bin/python daily_reporter.py --dry-run"

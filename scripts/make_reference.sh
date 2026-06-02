#!/usr/bin/env bash
# Generate a PLACEHOLDER Vietnamese reference voice clip for OmniVoice cloning.
# Replace ref/reference.wav with a real recording of the target voice for
# production-quality cloning.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p ref

REF_TEXT="Xin chào, đây là giọng đọc tham chiếu dùng để nhân bản giọng nói cho báo cáo công việc hằng ngày."

say -v Linh -o ref/_tmp.aiff "$REF_TEXT"
ffmpeg -y -i ref/_tmp.aiff -ar 24000 -ac 1 ref/reference.wav
rm -f ref/_tmp.aiff
printf '%s' "$REF_TEXT" > ref/reference.txt

echo "Wrote ref/reference.wav (24kHz mono) + ref/reference.txt"
echo "NOTE: this is a synthetic placeholder. Swap in a real voice clip for true cloning."

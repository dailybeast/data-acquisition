#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/../../data-acquisition"
LOG="$DIR/backfill.log"

cd "$DIR"

export PYTHONUNBUFFERED=1
export GCS_BUCKET="data-acquisition-storage"
export PUBLICATIONS='[
  {"slug": "howl",    "base_url": "https://michaelwolffnyc.substack.com", "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/howl",    "full_history": true},
  {"slug": "punchup", "base_url": "https://thepunchup.substack.com",      "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/punchup", "full_history": true}
]'

"$VENV/bin/python" main.py >> "$LOG" 2>&1

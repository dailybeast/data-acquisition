#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/../../data-acquisition"
LOG="$DIR/run.log"

cd "$DIR"

export PYTHONUNBUFFERED=1
export GOOGLE_CLOUD_PROJECT="data-platform-455517"
export GCS_BUCKET="data-acquisition-storage"
export PUBLICATIONS='[
  {"slug": "royalist", "base_url": "https://theroyalist.substack.com", "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/royalist"},
  {"slug": "swamp",    "base_url": "https://theswamp.substack.com",    "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/swamp"},
  {"slug": "joannacoles", "base_url": "https://joannacoles.substack.com", "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/joannacoles"},
  {"slug": "howl",    "base_url": "https://michaelwolffnyc.substack.com", "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/howl"},
  {"slug": "punchup",    "base_url": "https://thepunchup.substack.com", "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/punchup"}
]'

echo "=== $(date '+%Y-%m-%d %H:%M:%S') START ===" >> "$LOG"
"$VENV/bin/python" main.py >> "$LOG" 2>&1
echo "=== $(date '+%Y-%m-%d %H:%M:%S') END ===" >> "$LOG"

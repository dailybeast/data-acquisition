#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/../../data-acquisition"
LOG="$DIR/run.log"

cd "$DIR"

export PYTHONUNBUFFERED=1
export GCS_BUCKET="data-acquisition-storage"
export PUBLICATIONS='[
  {"slug": "royalist", "base_url": "https://theroyalist.substack.com", "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/royalist"},
  {"slug": "swamp",    "base_url": "https://theswamp.substack.com",    "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/swamp"},
  {"slug": "joannacoles", "base_url": "https://joannacoles.substack.com", "sid": "s%3AQTV7o-Hza6UkFCzlHN1uLgIVmjIEF0U4.grHasQC3BTbr%2BltpAGODhFqS7Kl7iXeabvc%2FOdGrGr8", "gcs_prefix": "substack/joannacoles"}
]'

"$VENV/bin/python" main.py >> "$LOG" 2>&1

#!/bin/bash
set -euo pipefail

PROJECT="data-platform-455517"
REGION="us-central1"
IMAGE="gcr.io/$PROJECT/substack-raw-storage"
JOB="substack-raw-storage"

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Building image ==="
docker build --platform linux/amd64 -t "$IMAGE" "$DIR"

echo "=== Pushing image ==="
docker push "$IMAGE"

echo "=== Deploying Cloud Run Job ==="
if gcloud run jobs describe "$JOB" --region "$REGION" --project "$PROJECT" &>/dev/null; then
  gcloud run jobs update "$JOB" \
    --image "$IMAGE" \
    --region "$REGION" \
    --project "$PROJECT"
else
  gcloud run jobs create "$JOB" \
    --image "$IMAGE" \
    --region "$REGION" \
    --project "$PROJECT" \
    --set-env-vars "GCS_BUCKET=data-acquisition-storage" \
    --set-secrets "PUBLICATIONS=substack-publications:latest,BRIGHT_DATA_PROXY=bright-data-proxy:latest" \
    --memory 512Mi \
    --task-timeout 3600 \
    --max-retries 0
fi

echo "=== Done ==="
echo "Run manually: gcloud run jobs execute $JOB --region $REGION --project $PROJECT"

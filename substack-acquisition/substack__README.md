# Substack Acquisition

Fetches post stats and subscriber data from the Substack dashboard API for all publications under our purview and loads them into shared BigQuery tables.

## Publications

| Slug | URL |
|------|-----|
| `royalist` | https://theroyalist.substack.com |
| `swamp` | https://theswamp.substack.com |
| `joannacoles` | https://joannacoles.substack.com |
| `howl` | https://michaelwolffnyc.substack.com |
| `punchup` | https://thepunchup.substack.com |

To add a new publication, add one entry to the `substack-publications` secret in Secret Manager — no code changes required.

## Data Collected (per run, last 15 posts per publication)

- Post overview — stats snapshot including views, opens, open rate, CTR, signups, estimated revenue
- Traffic — referrer sources, device breakdown
- Growth — new subscribers and unsubscribes attributed to each post
- Comments — comment body, comment ID, parent comment ID (for threading)
- Subscriber snapshot — current paid subscriber list

## Architecture

```
Cloud Scheduler (daily cron)
      |
      v
Cloud Run Job  (substack-raw-storage, us-central1)
      |  Iterates over all publications in PUBLICATIONS secret
      |  Fetches from Substack dashboard API via Bright Data proxy
      |  (proxy routes around Cloudflare's block on GCP datacenter IPs)
      v
Google Cloud Storage  (data-acquisition-storage)
  substack/{publication}/{timestamp}/
      ├── overview.json
      ├── traffic.json
      ├── growth.json
      ├── comments.json
      └── subscriber_snapshot.json
      |
      | GCS notification → Pub/Sub (substack-gcs-notifications)
      v
Cloud Function  (substack-gcs-to-bigquery, us-central1)
      |  Derives publication and endpoint from GCS path
      v
BigQuery — raw_landing dataset (data-platform-455517)
  substack___post_overview
  substack___post_traffic
  substack___post_growth
  substack___post_comments
  substack___subscribers_snapshot
```

All tables include a `publication` field to identify the source publication.

## Project Structure

```
substack-acquisition/
  raw-storage/          # Cloud Run Job — fetches from API and writes to GCS
    main.py             # Entry point — iterates publications, orchestrates fetches
    fetch_post_stats.py # Substack API client, retry logic, GCS upload
    Dockerfile          # Container image for the Cloud Run Job
    deploy.sh           # Build, push, and deploy the Cloud Run Job
    run.sh              # Local execution (testing only — not used in production)
    backfill.sh         # One-shot backfill for new publications (full_history=true)
    run.log             # Output log (not committed)
    .env                # Local env vars (not committed)
  gcs-to-bigquery/      # Cloud Function — GCS → BigQuery loader
    main.py
    requirements.txt
```

## Environment Variables

| Variable | Description | Source |
|----------|-------------|--------|
| `GCS_BUCKET` | GCS bucket name | Cloud Run Job env var |
| `PUBLICATIONS` | JSON array of publication configs (see below) | Secret Manager: `substack-publications` |
| `BRIGHT_DATA_PROXY` | Bright Data proxy URL for routing Substack API requests | Secret Manager: `bright-data-proxy` |

### PUBLICATIONS format

```json
[
  {
    "slug": "royalist",
    "base_url": "https://theroyalist.substack.com",
    "sid": "<substack.sid cookie value>",
    "gcs_prefix": "substack/royalist"
  }
]
```

`sid` is the `substack.sid` session cookie from a logged-in browser session with dashboard access. Refresh it from DevTools → Application → Cookies → `substack.com` when it expires. Update the `substack-publications` secret in Secret Manager when rotating.

## Deployment

The Cloud Run Job is deployed from `raw-storage/` using `deploy.sh`:

```bash
bash substack-acquisition/raw-storage/deploy.sh
```

This builds the Docker image, pushes it to GCR (`gcr.io/data-platform-455517/substack-raw-storage`), and creates or updates the Cloud Run Job in `us-central1`. Secrets (`PUBLICATIONS`, `BRIGHT_DATA_PROXY`) are pulled from Secret Manager at runtime — no local env required for production.

To trigger a manual run:

```bash
gcloud run jobs execute substack-raw-storage --region us-central1 --project data-platform-455517
```

## Backfill

When adding a new publication, run `backfill.sh` to load its full post history before the daily cron takes over. It works identically to `run.sh` but sets `"full_history": true` in the publication config, which causes `main.py` to fetch all posts instead of just the most recent 15.

Edit `backfill.sh` to include only the new publication(s), then run it once manually:

```bash
bash substack-acquisition/raw-storage/backfill.sh
```

After the backfill completes, add the publication to the `substack-publications` secret in Secret Manager for ongoing daily pulls.

## BigQuery

- **Project:** `data-platform-455517`
- **Dataset:** `raw_landing`
- Tables use `WRITE_APPEND` — each run adds a new snapshot row per post identified by `snapshot_date` (UTC timestamp).
- Filter by publication: `WHERE publication = 'royalist'`
- Deduplicate in queries with: `QUALIFY ROW_NUMBER() OVER (PARTITION BY post_id, publication ORDER BY snapshot_date DESC) = 1`

## Known Issues

- `engaged`, `likes`, `restacks` and other computed engagement metrics occasionally return null when Substack's stats computation pipeline hasn't completed. `stats_updated_at` being null is the signal. The next snapshot will have the values once Substack's pipeline catches up.
- Comment replies: the API appears to return all comments flat in the `items` array with `parent_comment_id` null for top-level comments and populated for replies. Verify against a post with known replies.

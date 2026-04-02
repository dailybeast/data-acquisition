# Substack Acquisition

Fetches post stats and subscriber data from the Substack dashboard API for all publications under our purview and loads them into shared BigQuery tables.

## Publications

| Slug | URL |
|------|-----|
| `royalist` | https://theroyalist.substack.com |
| `swamp` | https://theswamp.substack.com |
| `joannacoles` | https://joannacoles.substack.com |

To add a new publication, add one entry to the `PUBLICATIONS` env var in `raw-storage/run.sh` — no code changes required.

## Data Collected (per run, last 50 posts per publication)

- Post overview — stats snapshot including views, opens, open rate, CTR, signups, estimated revenue
- Traffic — referrer sources, device breakdown
- Growth — new subscribers and unsubscribes attributed to each post
- Comments — comment body, comment ID, parent comment ID (for threading)
- Subscriber snapshot — current paid subscriber list

## Architecture

```
macOS cron (10am ET daily)
      |
      v
raw-storage/run.sh
      |  Iterates over all publications in PUBLICATIONS env var
      |  Fetches from Substack dashboard API
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

> **Note:** The acquisition script runs locally due to Cloudflare IP restrictions on Substack's API that block cloud datacenter IPs. The laptop must be awake at 10am ET for the job to run. Ensure **System Settings → Battery → prevent automatic sleeping** is enabled.

All tables include a `publication` field to identify the source publication.

## Project Structure

```
substack-acquisition/
  raw-storage/          # Local cron job — fetches from API and writes to GCS
    main.py             # Entry point — iterates publications, orchestrates fetches
    fetch_post_stats.py # Substack API client, retry logic, GCS upload
    run.sh              # Cron entrypoint — sets env vars and runs main.py
    run.log             # Output log (not committed)
    .env                # Local env vars (not committed)
  gcs-to-bigquery/      # Cloud Function — GCS → BigQuery loader
    main.py
    requirements.txt
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GCS_BUCKET` | GCS bucket name |
| `PUBLICATIONS` | JSON array of publication configs (see below) |

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

`sid` is the `substack.sid` session cookie from a logged-in browser session with dashboard access. Refresh it from DevTools → Application → Cookies → `substack.com` when it expires.

## BigQuery

- **Project:** `data-platform-455517`
- **Dataset:** `raw_landing`
- Tables use `WRITE_APPEND` — each run adds a new snapshot row per post identified by `snapshot_date` (UTC timestamp).
- Filter by publication: `WHERE publication = 'royalist'`
- Deduplicate in queries with: `QUALIFY ROW_NUMBER() OVER (PARTITION BY post_id, publication ORDER BY snapshot_date DESC) = 1`

## Known Issues

- `engaged`, `likes`, `restacks` and other computed engagement metrics occasionally return null when Substack's stats computation pipeline hasn't completed. `stats_updated_at` being null is the signal. The next snapshot will have the values once Substack's pipeline catches up.
- Comment replies: the API appears to return all comments flat in the `items` array with `parent_comment_id` null for top-level comments and populated for replies. Verify against a post with known replies.

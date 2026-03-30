# data-acquisition

Data acquisition pipelines for ingesting third-party platform data into BigQuery.

## Overview

This repo contains scripts and Cloud Functions for pulling data from external platforms, staging it in GCS, and loading it into BigQuery for analysis.

## Pipelines

### Substack — The Royalist

Fetches post stats and subscriber data from the Substack dashboard API for [The Royalist](https://theroyalist.substack.com) and loads it into BigQuery.

**Data collected (per run, last 10 posts):**
- Post overview — stats snapshot including views, opens, open rate, CTR, signups, estimated revenue
- Traffic — referrer sources, device breakdown
- Growth — new subscribers and unsubscribes attributed to each post
- Comments — comment thread data
- Subscriber snapshot — current paid subscriber list

**Architecture:**

```
Cloud Scheduler
      |
      v
Cloud Run Job (raw-storage/)
      |  Fetches from Substack API
      v
Google Cloud Storage
  substack/theroyalist/{timestamp}/
      ├── overview.json
      ├── traffic.json
      ├── growth.json
      ├── comments.json
      └── subscriber_snapshot.json
      |
      | GCS notification → Pub/Sub topic
      v
Cloud Function (gcs-to-bigquery/)
      |
      v
BigQuery — raw_landing dataset
  substack_royalist___post_overview
  substack_royalist___post_traffic
  substack_royalist___post_growth
  substack_royalist___post_comments
  substack_royalist___subscribers_snapshot
```

## Project Structure

```
substack-acquisition/
  raw-storage/          # Acquisition script (runs as Cloud Run Job)
    main.py             # Entry point — orchestrates fetches and uploads
    fetch_post_stats.py # Substack API client and GCS upload logic
    .env                # Local env vars (not committed)
  gcs-to-bigquery/      # Cloud Function — GCS → BigQuery loader
    main.py
    requirements.txt
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SUBSTACK_SID` | Substack session cookie (`substack.sid`) |
| `GCS_BUCKET` | GCS bucket name |
| `GCS_PREFIX` | Path prefix within the bucket (e.g. `substack/theroyalist`) |

## BigQuery

- **Project:** `data-platform-455517`
- **Dataset:** `raw_landing`
- Tables use `WRITE_APPEND` — each run adds a new snapshot row per post identified by `snapshot_date` (UTC timestamp).
- Deduplicate in queries with: `QUALIFY ROW_NUMBER() OVER (PARTITION BY post_id ORDER BY snapshot_date DESC) = 1`

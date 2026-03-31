# Data Acquisition

This repository contains all data acquisition jobs for The Daily Beast's data platform. Its scope is strictly bounded: **get data from a source and write it to raw storage, unchanged.**

---

## Scope & Responsibility

This layer has one job. It does not transform, enrich, or aggregate data. It does not serve dashboards. It does not call downstream systems. It writes raw payloads to a landing zone and stops.

Everything downstream — transformation, delivery, alerting — is handled in separate layers and separate repositories. This separation is intentional. The acquisition layer should be able to change without touching transformation logic, and transformation should be able to run without ever calling a source API.

---

## Architecture

```
Source API / Scraper / Managed Connector
           │
           ▼
   [ Acquisition Job ]         ← this repo
           │
           ▼
   raw_landing.{source}___*    ← BigQuery, data-platform-455517
           │
           ▼
   [ Transformation Layer ]    ← separate repo (dbt)
           │
           ▼
   [ Delivery / Consumers ]    ← dashboards, agents, reports
```

---

## Repository Structure

```
/
├── sources/
│   ├── substack/
│   │   ├── README.md          # acquisition pattern, auth, jobs, known issues
│   │   └── royalist/
│   ├── zephr/
│   │   ├── README.md
│   │   └── ...
│   ├── braintree/
│   │   ├── README.md
│   │   └── ...
│   └── ...
├── shared/
│   └── gcs_writer.py          # shared BigQuery/GCS write utilities
├── .github/
│   └── workflows/             # Cloud Run job deploy configs
└── README.md
```

Each source lives in its own directory. A source directory contains everything needed to run that acquisition job independently: the fetch logic, any auth config references, and a deployment manifest.

---

## Guiding Principles

**1. Acquisition is not transformation.**
Jobs in this repo write raw API responses to the landing zone. No field renaming, no type casting, no filtering. If the source sends it, we store it.

**2. One source, one job.**
Each source has its own acquisition job. Jobs do not share fetch logic across sources. This keeps failure blast radius small and makes each job independently deployable and debuggable.

**3. The right acquisition mechanism lives at the source level.**
Sources vary in how data is available — managed connectors (Fivetran), direct API calls, scrapers. There is no single correct acquisition pattern. What is consistent is the output: a raw landing table in BigQuery.

**4. Write raw, write append.**
Landing tables are append-only. Each run writes a new snapshot with a `snapshot_date` timestamp. Deduplication and state management are handled downstream in the transformation layer.

**5. Jobs are stateless.**
Acquisition jobs do not track their own state, manage offsets, or read from previously written data. If incremental logic is needed it is handled via scheduling and the `snapshot_date` column in the output.

---

## Output Convention

All jobs write to the `raw_landing` dataset in the `data-platform-455517` GCP project.

Table naming follows the pattern:

```
raw_landing.{source}___{object}
```

Examples:
```
raw_landing.substack_royalist___post_overview
raw_landing.substack_royalist___subscribers_snapshot
raw_landing.zephr___users
```

Every landing table must include a `snapshot_date` column (TIMESTAMP, UTC) populated at write time by the acquisition job.

---

## Adding a New Source

1. Create a directory under `sources/{source_name}/`.
2. Implement a fetch function that returns the raw API response with no modifications.
3. Use the shared write utility to append to the appropriate `raw_landing` table.
4. Add a `snapshot_date` timestamp to every row at write time.
5. Open a PR — include the target table name and expected schema in the description.
6. Once merged, coordinate with the transformation team to build the corresponding staging model in dbt.

---

## What Does Not Belong Here

- SQL transforms or field renaming
- Business logic or metric calculations
- Writes to any table outside of `raw_landing`
- Reading from `raw_landing` or any downstream table
- Alerting or notification logic
- Anything a Tableau dashboard or agent should read from

If you find yourself doing any of the above inside an acquisition job, it belongs in a different layer.

---

## Ownership

Data Engineering — The Daily Beast  
Questions: [alex.heston@thedailybeast.com](mailto:alex.heston@thedailybeast.com)
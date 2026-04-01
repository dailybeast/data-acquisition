import json
import base64
from google.cloud import bigquery


BQ_PROJECT = "data-platform-455517"
BQ_DATASET = "raw_landing"

ENDPOINT_TO_TABLE_SUFFIX = {
    "overview": "post_overview",
    "traffic": "post_traffic",
    "growth": "post_growth",
    "comments": "post_comments",
    "subscriber_snapshot": "subscribers_snapshot",
}

def gcs_to_bq(event, context):
    message = base64.b64decode(event['data']).decode("utf-8")
    data = json.loads(message)

    bucket_name = data["bucket"]
    file_name = data["name"]

    # file_name: substack/{publication}/{timestamp}/{endpoint}.json
    parts = file_name.split("/")
    publication = parts[1]
    endpoint = parts[-1].replace(".json", "")

    suffix = ENDPOINT_TO_TABLE_SUFFIX.get(endpoint)
    if not suffix:
        print(f"no table mapping for endpoint '{endpoint}' — skipping")
        return

    table_id = f"substack___{suffix}"

    gcs_uri = f"gs://{bucket_name}/{file_name}"
    full_table = f"{BQ_PROJECT}.{BQ_DATASET}.{table_id}"

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )


    load_job = client.load_table_from_uri(gcs_uri, full_table, job_config=job_config)
    load_job.result()
    print(f"Loaded {gcs_uri} into {full_table}")

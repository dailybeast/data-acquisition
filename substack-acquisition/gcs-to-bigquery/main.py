import json
import base64
from google.cloud import bigquery


BQ_PROJECT = "data-platform-455517"
BQ_DATASET = "raw_landing"

TABLE_MAP = {
    "subscriber_snapshot": "substack_royalist___subscribers_snapshot",
    "engagement": "substack_royalist___post_engagement",
    "overview": "substack_royalist___post_overview",
    "traffic": "substack_royalist___post_traffic",
    "growth": "substack_royalist___post_growth",
    "comments": "substack_royalist___post_comments"
}

def gcs_to_bq(event, context):
    message = base64.b64decode(event['data']).decode("utf-8")
    data = json.loads(message)

    bucket_name = data["bucket"]
    file_name = data["name"]
    endpoint = file_name.split("/")[-1].replace(".json", "")
    table_id = TABLE_MAP.get(endpoint)

    if not table_id:
        print(f"check your table names, cant find a matching endpoint for {endpoint}")
        return

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

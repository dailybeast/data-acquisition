import os, time, datetime, json
import requests
from google.cloud import storage


SUBSTACK_BASE_URL = "https://theroyalist.substack.com"
SUBSTACK_SID = os.environ["SUBSTACK_SID"]
GCS_BUCKET = os.environ["GCS_BUCKET"]
GCS_PREFIX = os.environ["GCS_PREFIX"]
SNAPSHOT_DATE = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

session = requests.Session()
session.cookies.set("substack.sid", SUBSTACK_SID, domain="substack.com")
session.headers.update({
    "accept": "*/*",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
})

def fetch_all_post_ids():
    posts = []
    offset = 0
    limit = 25

    while True:
        resp = session.get(
            f"{SUBSTACK_BASE_URL}/api/v1/post_management/published",
            params={"offset": offset, "limit": limit, "order_by": "post_date", "order_direction": "desc"}
        )
        resp.raise_for_status()
        page = resp.json()["posts"]

        posts.extend(page)
        
        if len(page) < limit:
            break
        
        offset += limit
        time.sleep(0.3)
    return posts

def fetch_post_details(post_id):
    details = {}
    endpoints = {
        "overview": f"/api/v1/post_management/detail/{post_id}?offset=0&limit=1",
        "traffic":    f"/api/v1/post_management/detail/{post_id}/traffic",
        "growth":     f"/api/v1/post_management/detail/{post_id}/growth",
        "comments":   f"/api/v1/post_management/detail/{post_id}/discussion?tabId=comments",
    }

    for name, path in endpoints.items():
        resp = session.get(f"{SUBSTACK_BASE_URL}{path}")
        resp.raise_for_status()
        details[name] = resp.json()
        time.sleep(2)

    return details

def fetch_all_subscribers():
    subscribers = []
    offset = 0
    limit = 100
    fields = [
        "user_id", "subscription_created_at", "subscription_id", 
        "subscription_interval", "unsubscribed_at", "is_free_trial", 
        "is_gift", "is_subscribed", "is_comp", "first_payment_at",
        "activity_rating", "subscription_expires_at"
    ]

    while True:
        resp = session.post(
            f"{SUBSTACK_BASE_URL}/api/v1/subscriber-stats",
            json={
                "filters": {"subscription_type": "paid", "order_by_desc_nulls_last": "subscription_created_at"}, "limit": limit, "offset": offset, "fields": fields
        }
        )
        resp.raise_for_status()
        page = resp.json()["subscribers"]
        subscribers.extend(page)
        print(f"Fetched {len(subscribers)} subscribers so far...")

        if len(page) < limit:
            break

        offset += limit
        time.sleep(0.3)

    return subscribers
        

def upload_to_gcs(data, endpoint_name):
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob_path = f"{GCS_PREFIX}/{SNAPSHOT_DATE}/{endpoint_name}.json"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        "\n".join(json.dumps(record) for record in data),
        content_type="application/json"
    )
    print(f"Uploaded {len(data)} records to gs://{GCS_BUCKET}/{blob_path}")



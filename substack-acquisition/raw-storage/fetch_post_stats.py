import os, time, datetime, json
import requests
from google.cloud import storage


SNAPSHOT_DATE = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
GCS_BUCKET = os.environ["GCS_BUCKET"]


def _request_with_backoff(fn, max_retries=4):
    """Call fn() and retry on 429/5xx with exponential backoff."""
    for attempt in range(max_retries):
        resp = fn()
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 2 ** (attempt + 2)))
            print(f"Rate limited — waiting {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
        elif resp.status_code >= 500:
            wait = 2 ** (attempt + 1)
            print(f"Server error {resp.status_code} — waiting {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
        else:
            resp.raise_for_status()
            return resp
    raise Exception(f"Request failed after {max_retries} attempts — last status {resp.status_code}")


def make_session(sid):
    session = requests.Session()
    session.cookies.set("substack.sid", sid, domain="substack.com")
    session.headers.update({
        "accept": "*/*",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    })
    return session


def fetch_all_post_ids(session, base_url):
    posts = []
    offset = 0
    limit = 25

    while True:
        resp = _request_with_backoff(lambda: session.get(
            f"{base_url}/api/v1/post_management/published",
            params={"offset": offset, "limit": limit, "order_by": "post_date", "order_direction": "desc"}
        ))
        page = resp.json()["posts"]

        posts.extend(page)

        if len(page) < limit:
            break

        offset += limit
        time.sleep(0.3)
    return posts


def fetch_post_details(session, base_url, post_id):
    details = {}
    endpoints = {
        "overview": f"/api/v1/post_management/detail/{post_id}?offset=0&limit=1",
        "traffic":  f"/api/v1/post_management/detail/{post_id}/traffic",
        "growth":   f"/api/v1/post_management/detail/{post_id}/growth",
        "comments": f"/api/v1/post_management/detail/{post_id}/discussion?tabId=comments",
    }

    for name, path in endpoints.items():
        resp = _request_with_backoff(lambda p=path: session.get(f"{base_url}{p}"))
        details[name] = resp.json()
        time.sleep(2)

    return details


def fetch_all_subscribers(session, base_url):
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
        resp = _request_with_backoff(lambda: session.post(
            f"{base_url}/api/v1/subscriber-stats",
            json={
                "filters": {"subscription_type": "paid", "order_by_desc_nulls_last": "subscription_created_at"},
                "limit": limit,
                "offset": offset,
                "fields": fields
            }
        ))
        page = resp.json()["subscribers"]
        subscribers.extend(page)
        print(f"Fetched {len(subscribers)} subscribers so far...")

        if len(page) < limit:
            break

        offset += limit
        time.sleep(0.3)

    return subscribers


def upload_to_gcs(data, endpoint_name, gcs_prefix):
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob_path = f"{gcs_prefix}/{SNAPSHOT_DATE}/{endpoint_name}.json"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        "\n".join(json.dumps(record) for record in data),
        content_type="application/json"
    )
    print(f"Uploaded {len(data)} records to gs://{GCS_BUCKET}/{blob_path}")

import json
import os
import time

from fetch_post_stats import make_session, fetch_all_post_ids, fetch_post_details, fetch_all_subscribers, upload_to_gcs, SNAPSHOT_DATE


def strip_emoji_keys(obj):
    if isinstance(obj, dict):
        return {k: strip_emoji_keys(v) for k, v in obj.items() if k.isascii() and k != "reactions"}
    if isinstance(obj, list):
        return [strip_emoji_keys(i) for i in obj]
    return obj


def run_publication(pub):
    slug = pub["slug"]
    session = make_session(pub["sid"])
    base_url = pub["base_url"]
    gcs_prefix = pub["gcs_prefix"]

    posts = fetch_all_post_ids(session, base_url)[:10]
    print(f"[{slug}] Found {len(posts)} posts")

    overview_results = []
    traffic_results = []
    growth_results = []
    comments_results = []

    for post in posts:
        post_id = post["id"]
        print(f"[{slug}] Fetching details for post {post_id}...")
        details = fetch_post_details(session, base_url, post_id)

        overview = strip_emoji_keys(details["overview"])
        for p in overview.get("posts", []):
            links = p.get("stats", {}).get("links", [])
            p["stats"]["links"] = [{"text": l[0], "clicks": l[1]} for l in links if isinstance(l, list)]
        overview_results.append({"snapshot_date": SNAPSHOT_DATE, "publication": slug, "post_id": post_id, "data": overview})
        traffic_results.append({"snapshot_date": SNAPSHOT_DATE, "publication": slug, "post_id": post_id, "data": details["traffic"]})
        growth_results.append({"snapshot_date": SNAPSHOT_DATE, "publication": slug, "post_id": post_id, "data": details["growth"]})

        for item in details["comments"].get("items", []):
            comment = item.get("comment", {})
            parent_comments = item.get("parentComments", [])
            parent_comment_id = parent_comments[-1].get("id") if parent_comments else None
            comments_results.append({
                "snapshot_date": SNAPSHOT_DATE,
                "publication": slug,
                "post_id": post_id,
                "comment_id": comment.get("id"),
                "parent_comment_id": parent_comment_id,
                "body": comment.get("body"),
            })
        time.sleep(1)

    subscriber_snapshot = fetch_all_subscribers(session, base_url)
    upload_to_gcs([{"snapshot_date": SNAPSHOT_DATE, "publication": slug, "sub": s} for s in subscriber_snapshot], "subscriber_snapshot", gcs_prefix)
    upload_to_gcs(overview_results, "overview", gcs_prefix)
    upload_to_gcs(traffic_results, "traffic", gcs_prefix)
    upload_to_gcs(growth_results, "growth", gcs_prefix)
    upload_to_gcs(comments_results, "comments", gcs_prefix)


def main():
    publications = json.loads(os.environ["PUBLICATIONS"])
    for i, pub in enumerate(publications):
        if i > 0:
            time.sleep(10)
        print(f"--- Starting acquisition for {pub['slug']} ---")
        run_publication(pub)


if __name__ == "__main__":
    main()

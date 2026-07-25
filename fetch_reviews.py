"""
Phase 1: Ingestion
Pulls reviews from Apple's official Customer Reviews RSS/JSON feed.
Also includes search/lookup helpers using Apple's official iTunes Search API.
No API key required. No cost. This works right now.
"""

import requests
import pandas as pd
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def search_apps(term: str, country: str = "us", limit: int = 6) -> list[dict]:
    """Search for apps by name via Apple's official iTunes Search API."""
    url = "https://itunes.apple.com/search"
    params = {"term": term, "country": country, "entity": "software", "limit": limit}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json().get("results", [])


def lookup_app(app_id: str, country: str = "us"):
    """Look up a single app by numeric App Store ID via Apple's official iTunes Lookup API."""
    url = "https://itunes.apple.com/lookup"
    params = {"id": app_id, "country": country}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0] if results else None


def resolve_app(query: str, country: str = "us") -> list[dict]:
    """Accepts a numeric App Store ID or a name/search term. Returns candidate list."""
    query = query.strip()
    if query.isdigit():
        app = lookup_app(query, country=country)
        return [app] if app else []
    return search_apps(query, country=country)


def fetch_app_reviews(app_id: str, country: str = "us", max_pages: int = 10, debug: bool = False):
    """Fetch reviews for an app from Apple's official Customer Reviews feed."""
    all_reviews = []
    log = []

    for page in range(1, max_pages + 1):
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
        resp = requests.get(url, headers=HEADERS, timeout=10)

        if resp.status_code != 200:
            log.append(f"Page {page}: HTTP {resp.status_code} - {resp.text[:200]}")
            break

        try:
            body = resp.json()
        except ValueError:
            log.append(f"Page {page}: response was not valid JSON. Raw start: {resp.text[:200]}")
            break

        feed = body.get("feed", {})
        entries = feed.get("entry", [])

        if isinstance(entries, dict):
            entries = [entries]

        if not entries:
            log.append(f"Page {page}: feed had no 'entry' field at all. Top-level keys: {list(feed.keys())}")
            break

        page_review_count = 0
        for entry in entries:
            if "im:rating" not in entry:
                continue
            all_reviews.append({
                "author": entry.get("author", {}).get("name", {}).get("label", "unknown"),
                "rating": int(entry["im:rating"]["label"]),
                "title": entry.get("title", {}).get("label", ""),
                "review": entry.get("content", {}).get("label", ""),
                "version": entry.get("im:version", {}).get("label", ""),
                "date": entry.get("updated", {}).get("label", ""),
            })
            page_review_count += 1

        log.append(f"Page {page}: {len(entries)} entries in feed, {page_review_count} were reviews")

        if page_review_count == 0 and len(entries) <= 1:
            log.append(f"Page {page}: no actual reviews found, stopping.")
            break

        time.sleep(0.5)

    df = pd.DataFrame(all_reviews)
    if not df.empty:
        df = df.drop_duplicates(subset=["author", "review", "date"])

    if debug:
        return df, log
    return df

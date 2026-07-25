"""
Run this ONCE locally (with your OPENAI_API_KEY set) to generate real,
cached example results for a few well-known apps. This is what powers
the free "Examples" page that visitors can browse without spending
your API credit.

Usage:
    python generate_examples.py

Edit EXAMPLE_APPS below to pick whichever apps you want to feature.
Each run costs well under $0.10 per app.
"""

import json
import os
from fetch_reviews import fetch_app_reviews
from analyze_reviews import classify_batch, build_rice_table

EXAMPLE_APPS = [
    {"name": "Duolingo", "app_id": "570060128"},
    {"name": "Spotify", "app_id": "324684580"},
    {"name": "Notion", "app_id": "1232780281"},
]

OUT_DIR = "data/examples"


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_")


def generate_one(app_name: str, app_id: str, max_pages: int = 5):
    print(f"\n--- {app_name} ---")
    reviews_df = fetch_app_reviews(app_id, max_pages=max_pages)
    print(f"Fetched {len(reviews_df)} reviews")

    classified = classify_batch(reviews_df["review"].tolist())
    rice_table = build_rice_table(classified, reviews_df)

    # Grab a couple of real sample quotes per theme for display credibility
    samples_by_theme = {}
    for theme in rice_table["theme"]:
        matches = classified[classified["theme"] == theme]
        samples_by_theme[theme] = matches["summary"].head(3).tolist()

    output = {
        "app_name": app_name,
        "app_id": app_id,
        "review_count": len(reviews_df),
        "avg_rating": round(reviews_df["rating"].mean(), 2),
        "rice_table": rice_table.to_dict(orient="records"),
        "samples_by_theme": samples_by_theme,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = f"{OUT_DIR}/{slugify(app_name)}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY in your .env before running this.")

    for app in EXAMPLE_APPS:
        generate_one(app["name"], app["app_id"])

    print("\nDone. Commit the files in data/examples/ to your repo so the "
          "Examples page works for every visitor without needing a key.")

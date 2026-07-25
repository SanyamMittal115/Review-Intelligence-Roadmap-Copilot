"""
Phase 2: GenAI theme extraction
Phase 3: RICE scoring

Batches reviews into groups (to control cost + stay under rate limits),
asks the model to classify + summarize each, then aggregates into a
RICE-scored, prioritized roadmap.

Requires OPENAI_API_KEY in your .env file and billing set up on
platform.openai.com before this will actually run.
"""

import os
import json
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4.1-nano"  # cheapest capable model - fine for classification/extraction

_client = None

def get_client() -> OpenAI:
    """Create the OpenAI client only when it's actually needed, not on import."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "No OPENAI_API_KEY found. Add it to your .env file "
                "(copy .env.example to .env and paste your key in)."
            )
        _client = OpenAI(api_key=api_key)
    return _client

THEME_PROMPT = """You are a product analyst. For each review below, classify it into
exactly one theme from this list: ["Bug/Crash", "Feature Request", "Pricing",
"UX/Usability", "Performance", "Praise", "Other"].

Also give a one-sentence summary and a sentiment score from -1 (very negative)
to 1 (very positive).

Return ONLY a JSON array, one object per review, in this exact format:
[{{"index": 0, "theme": "...", "summary": "...", "sentiment": 0.0}}, ...]

Reviews:
{reviews_block}
"""

ROADMAP_PROMPT = """You are a product manager writing a roadmap justification.

Start your response with exactly one sentence in this form, filled in with
the real numbers: "This theme scores a RICE priority of {rice_score:.1f}
({priority_tier} priority), driven by a reach of {reach:.1f}/10, impact of
{impact:.1f}/10, confidence of {confidence:.1f}/10, and effort of {effort:.1f}/10."

Then write 2-3 more sentences explaining WHY, grounded in the actual review
data below. Be specific.

Theme: {theme}
Number of reviews: {count}
Average rating for these reviews: {avg_rating:.1f}
Average sentiment: {avg_sentiment:.2f}
Sample complaints/requests: {samples}
"""


def _priority_tier(rice_score: float) -> str:
    if rice_score >= 75:
        return "Critical"
    if rice_score >= 40:
        return "High"
    if rice_score >= 15:
        return "Medium"
    return "Low"


def classify_batch(reviews: list[str], batch_size: int = 25) -> pd.DataFrame:
    """Send reviews to the model in batches, get back theme/summary/sentiment."""
    results = []

    for start in range(0, len(reviews), batch_size):
        batch = reviews[start:start + batch_size]
        reviews_block = "\n".join(f"{i}: {r[:300]}" for i, r in enumerate(batch))
        prompt = THEME_PROMPT.format(reviews_block=reviews_block)

        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            print(f"Batch starting at {start}: failed to parse JSON, skipping batch")
            continue

        for item in parsed:
            item["global_index"] = start + item["index"]
            results.append(item)

        print(f"Batch {start}-{start+len(batch)}: classified {len(parsed)} reviews")

    return pd.DataFrame(results)


def build_rice_table(df: pd.DataFrame, reviews_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate classified reviews into a RICE-scored theme table."""
    merged = df.merge(
        reviews_df, left_on="global_index", right_index=True, suffixes=("", "_orig")
    )

    grouped = merged.groupby("theme").agg(
        review_count=("theme", "count"),
        avg_rating=("rating", "mean"),
        avg_sentiment=("sentiment", "mean"),
    ).reset_index()

    # Auto-suggested starting points - you (the PM) can override these in the app
    grouped["reach"] = (grouped["review_count"] / grouped["review_count"].max() * 10).round(1)
    grouped["impact"] = ((1 - grouped["avg_sentiment"]) / 2 * 10).round(1)  # more negative = higher impact to fix
    grouped["confidence"] = 8.0  # default; real reviews = decent confidence
    grouped["effort"] = 5.0      # default; user should adjust per theme

    grouped["rice_score"] = (
        grouped["reach"] * grouped["impact"] * grouped["confidence"] / grouped["effort"]
    ).round(1)

    grouped = grouped.sort_values("rice_score", ascending=False).reset_index(drop=True)
    return grouped


def generate_justification(theme_row: dict, samples: list[str]) -> str:
    """Generate a stakeholder-ready paragraph for one roadmap item.
    theme_row must include: theme, review_count, avg_rating, avg_sentiment,
    rice_score, reach, impact, confidence, effort (the CURRENT, possibly
    user-adjusted values, not necessarily the original computed ones).
    """
    prompt = ROADMAP_PROMPT.format(
        theme=theme_row["theme"],
        count=int(theme_row["review_count"]),
        avg_rating=theme_row["avg_rating"],
        avg_sentiment=theme_row["avg_sentiment"],
        rice_score=theme_row["rice_score"],
        priority_tier=_priority_tier(theme_row["rice_score"]),
        reach=theme_row["reach"],
        impact=theme_row["impact"],
        confidence=theme_row["confidence"],
        effort=theme_row["effort"],
        samples="; ".join(samples[:3]),
    )
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

# Review Intelligence & Roadmap Copilot

Pulls real App Store reviews from Apple's official Customer Reviews feed,
uses GenAI to classify and summarize them into themes, then generates a
RICE-prioritized, stakeholder-ready product roadmap.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your real OpenAI key.
3. Run:
   ```
   streamlit run Home.py
   ```

## Structure

```
Home.py
pages/
  1_Examples.py
  2_Fetch_Reviews.py
  3_Analyze_and_Score.py
  4_Roadmap.py
fetch_reviews.py
analyze_reviews.py
generate_examples.py
data/examples/*.json
```

## Cost

Classification runs in batches of 25 reviews using gpt-4.1-nano.
A full run on ~250 reviews costs well under $0.10.

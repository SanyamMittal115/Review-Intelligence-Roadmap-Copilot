import streamlit as st
import json
import glob
import pandas as pd

st.set_page_config(page_title="Examples", page_icon="📚", layout="wide")
st.title("📚 Example Roadmaps")
st.caption("Real output from this pipeline, pre-generated for three well-known apps. "
           "Free to browse — no API key needed.")

example_files = sorted(glob.glob("data/examples/*.json"))

if not example_files:
    st.warning("No example files found yet. Run `python generate_examples.py` "
               "locally to generate them.")
    st.stop()

examples = {}
for path in example_files:
    with open(path) as f:
        data = json.load(f)
        examples[data["app_name"]] = data

app_choice = st.selectbox("Choose an app", list(examples.keys()))
data = examples[app_choice]

if data.get("_placeholder"):
    st.info("ℹ️ This is illustrative sample data, not a live API result — "
             "the creator will swap this for real generated output.")

col1, col2 = st.columns(2)
col1.metric("Reviews analyzed", data["review_count"])
col2.metric("Average rating", data["avg_rating"])

st.subheader("RICE-prioritized roadmap")
rice_df = pd.DataFrame(data["rice_table"]).sort_values("rice_score", ascending=False)
st.dataframe(
    rice_df[["theme", "review_count", "avg_rating", "avg_sentiment", "rice_score"]],
    use_container_width=True,
)
st.bar_chart(rice_df.set_index("theme")["rice_score"])

st.subheader("Sample themes from real reviews")
for theme, samples in data["samples_by_theme"].items():
    with st.expander(theme):
        for s in samples:
            st.markdown(f"- {s}")

st.divider()
st.caption(
    "Want to run this on a different app? Head to **Fetch Reviews** to pull "
    "any app's reviews for free. Running new GenAI analysis requires a password "
    "since it uses a paid API — that step is reserved to prevent abuse."
)

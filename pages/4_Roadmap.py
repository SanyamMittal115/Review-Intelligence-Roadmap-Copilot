import streamlit as st
import pandas as pd
import os
from analyze_reviews import generate_justification

st.set_page_config(page_title="Roadmap", page_icon="📊", layout="wide")
st.title("3. Prioritized roadmap")
st.caption("Adjust RICE weights live and generate stakeholder-ready justifications.")

if st.session_state.get("rice_table") is None:
    st.warning("No analysis yet. Go to **Analyze & Score** first.")
    st.stop()

has_key = bool(os.getenv("OPENAI_API_KEY"))
rice_df = st.session_state.rice_table.copy()
run_id = st.session_state.get("analysis_run_id", "default")

if "justifications" not in st.session_state:
    st.session_state.justifications = {}  # theme_key -> {"text": ..., "score": ...}

def priority_tier(score):
    if score >= 75:
        return "Critical"
    if score >= 40:
        return "High"
    if score >= 15:
        return "Medium"
    return "Low"

with st.expander("What do these sliders mean?"):
    st.markdown("""
    **RICE** = (Reach × Impact × Confidence) ÷ Effort. Higher = higher priority.
    Move the sliders, watch the score and priority tier update instantly (free, no API call).
    When you click **Generate stakeholder justification**, the AI writes text based on
    whatever the sliders say at that moment. If you move the sliders afterward, you'll
    see a warning that the text below is now out of date for the new score.
    """)

edited_rows = []

for i, row in rice_df.iterrows():
    theme_key = row["theme"].replace(" ", "_").replace("/", "_")
    with st.expander(f"{row['theme']} — {int(row['review_count'])} reviews — RICE: {row['rice_score']}"):
        c1, c2, c3, c4 = st.columns(4)
        reach = c1.slider("Reach", 0.0, 10.0, float(row["reach"]), key=f"reach_{run_id}_{theme_key}")
        impact = c2.slider("Impact", 0.0, 10.0, float(row["impact"]), key=f"impact_{run_id}_{theme_key}")
        confidence = c3.slider("Confidence", 0.0, 10.0, float(row["confidence"]), key=f"conf_{run_id}_{theme_key}")
        effort = c4.slider("Effort", 0.5, 10.0, float(row["effort"]), key=f"effort_{run_id}_{theme_key}")

        new_score = round(reach * impact * confidence / effort, 1)
        tier = priority_tier(new_score)

        m1, m2 = st.columns(2)
        m1.metric("Live RICE score", new_score)
        m2.metric("Live priority tier", tier)

        current_row = {
            "theme": row["theme"], "review_count": row["review_count"],
            "avg_rating": row["avg_rating"], "avg_sentiment": row["avg_sentiment"],
            "reach": reach, "impact": impact, "confidence": confidence,
            "effort": effort, "rice_score": new_score,
        }

        gen_key = f"{run_id}_{theme_key}"
        saved = st.session_state.justifications.get(gen_key)

        if saved and abs(saved["score"] - new_score) > 0.05:
            st.warning(
                f"⚠️ Sliders changed — this text was generated when the score was "
                f"{saved['score']} ({priority_tier(saved['score'])}). It's now {new_score} "
                f"({tier}). Click Generate again to update it."
            )

        if st.button("Generate stakeholder justification", key=f"justify_{gen_key}", disabled=not has_key):
            samples = st.session_state.classified[
                st.session_state.classified["theme"] == row["theme"]
            ]["summary"].tolist()
            with st.spinner("Writing justification..."):
                text = generate_justification(current_row, samples)
            st.session_state.justifications[gen_key] = {"text": text, "score": new_score}
            st.rerun()

        if saved:
            st.write(saved["text"])

        edited_rows.append(current_row)

updated_df = pd.DataFrame(edited_rows).sort_values("rice_score", ascending=False)

st.subheader("Ranked roadmap")
st.dataframe(updated_df[["theme", "review_count", "avg_rating", "rice_score"]], use_container_width=True)

st.download_button(
    "Download roadmap as CSV",
    updated_df.to_csv(index=False),
    file_name=f"{st.session_state.get('app_name', 'app')}_roadmap.csv",
)

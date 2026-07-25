import streamlit as st
import os
from analyze_reviews import classify_batch, build_rice_table

st.set_page_config(page_title="Analyze & Score", page_icon="🧠", layout="wide")
st.title("2. Run GenAI analysis + RICE scoring")
st.caption("Uses the OpenAI API — costs a few cents per run.")

if st.session_state.get("reviews_df") is None:
    st.warning("No reviews loaded yet. Go to **Fetch Reviews** first.")
    st.stop()

has_key = bool(os.getenv("OPENAI_API_KEY"))
if not has_key:
    st.warning("No OPENAI_API_KEY found in .env. Add it there before running analysis.")

# --- Optional password gate ---
# If you deploy this publicly, set ANALYZE_PASSWORD in your .env / Streamlit secrets
# so random visitors can't spend down your API credit. Leave it unset locally
# and this gate is skipped entirely.
required_password = os.getenv("ANALYZE_PASSWORD")
if not required_password:
    st.error("ANALYZE_PASSWORD is not set in your .env file. Add it before using this page.")
    st.stop()
entered = st.text_input("This step costs real money — enter the access password to run it", type="password")
unlocked = entered == required_password
if entered and not unlocked:
    st.error("Incorrect password.")

st.write(f"Reviews loaded: **{len(st.session_state.reviews_df)}**")
st.caption("Estimated cost for this batch: well under $0.10 using gpt-4.1-nano")

if st.button("Analyze reviews", type="primary", disabled=not (has_key and unlocked)):
    with st.spinner("Classifying reviews and calculating RICE scores..."):
        classified = classify_batch(st.session_state.reviews_df["review"].tolist())
        rice_table = build_rice_table(classified, st.session_state.reviews_df)
    st.session_state.classified = classified
    st.session_state.rice_table = rice_table
    import uuid
    st.session_state.analysis_run_id = str(uuid.uuid4())[:8]
    st.success("Analysis complete")

if st.session_state.get("rice_table") is not None:
    st.subheader("Theme summary")
    st.dataframe(st.session_state.rice_table, use_container_width=True)
    st.info("👉 Head to **Roadmap** to adjust priorities and generate justifications")

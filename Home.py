import streamlit as st

st.set_page_config(page_title="Review Roadmap Copilot", page_icon="📱", layout="wide")

st.title("📱 Review Intelligence & Roadmap Copilot")
st.caption("Turn real App Store reviews into a GenAI-prioritized product roadmap")

st.markdown("""
### How this works
This tool pulls real user reviews from Apple's official App Store feed,
uses GenAI to classify them into themes, and builds a RICE-prioritized
roadmap — the same workflow a PM runs manually every sprint.

**Use the pages in the sidebar:**
1. **Examples** — browse pre-generated real roadmaps for 3 apps, free, no key needed — start here
2. **Fetch Reviews** — search for any app by name or ID, pull its reviews for free
3. **Analyze & Score** — GenAI theme classification + RICE scoring (password-protected — this step costs money)
4. **Roadmap** — interactive prioritized roadmap with adjustable RICE weights, exportable

---
*Built with Python, Streamlit, the Apple Customer Reviews API, and the OpenAI API.*
""")

for key in ["reviews_df", "rice_table", "classified"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state.reviews_df is not None:
    st.success(f"✅ {len(st.session_state.reviews_df)} reviews loaded — head to Analyze & Score")
else:
    st.info("👈 Start on the **Examples** or **Fetch Reviews** page")

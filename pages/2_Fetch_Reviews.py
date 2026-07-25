import streamlit as st
from fetch_reviews import fetch_app_reviews, resolve_app

st.set_page_config(page_title="Fetch Reviews", page_icon="📥", layout="wide")
st.title("2. Pull reviews")
st.caption("Free — pulls from Apple's official Customer Reviews feed. No key needed.")

for key in ["reviews_df", "fetch_log", "resolved_candidates", "selected_app"]:
    if key not in st.session_state:
        st.session_state[key] = None

st.subheader("Find an app")
query = st.text_input('Type an app name (e.g. "Locket") or paste its numeric App Store ID')

if st.button("Search"):
    if not query.strip():
        st.warning("Type something first.")
    else:
        with st.spinner("Searching Apple's App Store..."):
            candidates = resolve_app(query)
        st.session_state.resolved_candidates = candidates
        st.session_state.selected_app = None
        if not candidates:
            st.error("No apps found. Try a different name or double check the ID.")

if st.session_state.resolved_candidates:
    options = {
        f"{c['trackName']} — {c.get('artistName', 'unknown developer')} (ID: {c['trackId']})": c
        for c in st.session_state.resolved_candidates
    }
    choice_label = st.radio("Select the app you meant:", list(options.keys()))
    selected = options[choice_label]

    col1, col2 = st.columns([1, 4])
    if selected.get("artworkUrl60"):
        col1.image(selected["artworkUrl60"])
    col2.write(f"**{selected['trackName']}**")
    col2.caption(f"by {selected.get('artistName', 'unknown')} · App ID {selected['trackId']}")

    st.session_state.selected_app = selected

st.divider()

if st.session_state.selected_app:
    app = st.session_state.selected_app
    st.subheader(f"Pull reviews for {app['trackName']}")
    max_pages = st.slider("Pages of reviews to pull (~50/page)", 1, 10, 5)

    if st.button("Fetch reviews from Apple", type="primary"):
        with st.spinner("Pulling reviews..."):
            df, log = fetch_app_reviews(str(app["trackId"]), max_pages=max_pages, debug=True)
        st.session_state.reviews_df = df
        st.session_state.app_name = app["trackName"]
        st.session_state.fetch_log = log
        if len(df) > 0:
            st.success(f"Pulled {len(df)} reviews for {app['trackName']}")
        else:
            st.error(f"Pulled 0 reviews for {app['trackName']} — expand the debug log below to see why")
else:
    st.info("Search for an app above and select it to continue.")

if st.session_state.fetch_log:
    with st.expander("Debug log", expanded=(st.session_state.reviews_df is None or len(st.session_state.reviews_df) == 0)):
        for line in st.session_state.fetch_log:
            st.text(line)

if st.session_state.reviews_df is not None and len(st.session_state.reviews_df) > 0:
    st.dataframe(st.session_state.reviews_df, use_container_width=True)
    st.download_button(
        "Download raw reviews as CSV",
        st.session_state.reviews_df.to_csv(index=False),
        file_name=f"{st.session_state.get('app_name', 'app')}_reviews.csv",
    )
    st.info("👉 Head to **Analyze & Score** next")

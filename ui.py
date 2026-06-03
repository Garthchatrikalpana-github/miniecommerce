import streamlit as st
from analyzer import analyze_logs

st.set_page_config(page_title="AI Log Analyzer", layout="wide")

st.title("🚀 AI Log Analyzer (Demo)")

uploaded_file = st.file_uploader("Upload Log File")

if uploaded_file:

    log_text = uploaded_file.read().decode()

    if st.button("Analyze"):

        error, code, result = analyze_logs(log_text)

        st.subheader("🔴 Error Detected")
        st.code(error)

        st.subheader("📂 Relevant Code")
        for c in code:
            st.code(c["content"][:500])

        st.subheader("🧠 RCA")
        st.markdown(result)
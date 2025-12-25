import os, time, requests
import streamlit as st

API_BASE = os.getenv("PUBLIC_API_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Subtitle AI MVP", layout="wide")
st.title("Subtitle AI MVP — EN Transcription + FA Subtitles")
st.caption("Upload an episode → get English & Persian SRT + QA report + TM updates.")

with st.sidebar:
    st.subheader("API")
    st.code(API_BASE)
    st.write("If you run on a VPS, set PUBLIC_API_URL in .env to your server address.")

tab1, tab2 = st.tabs(["Upload & Run", "Track Jobs"])

with tab1:
    st.subheader("Upload")
    f = st.file_uploader("Audio/Video file", type=None)
    if f and st.button("Start"):
        r = requests.post(f"{API_BASE}/jobs", files={"file": (f.name, f.getvalue())}, timeout=600)
        if r.status_code != 200:
            st.error(r.text)
        else:
            job = r.json()
            st.success(f"Job created: {job['job_id']}")
            st.session_state["job_id"] = job["job_id"]

    st.markdown("---")
    jid = st.text_input("Job ID", value=st.session_state.get("job_id",""))
    auto = st.checkbox("Auto-refresh", value=True)
    if jid:
        ph = st.empty()
        while auto:
            s = requests.get(f"{API_BASE}/jobs/{jid}", timeout=30).json()
            ph.json(s)
            if s.get("status") == "DONE":
                st.success("DONE ✅ Download below.")
                break
            time.sleep(5)

        c1,c2,c3,c4 = st.columns(4)
        def download(kind, label):
            url = f"{API_BASE}/jobs/{jid}/download/{kind}"
            rr = requests.get(url, timeout=60)
            if rr.status_code == 200:
                st.download_button(label, rr.content, file_name=f"{jid}_{kind}")
            else:
                st.caption(f"{label}: not ready")
        with c1: download("en_srt","English SRT")
        with c2: download("fa_srt","Persian SRT")
        with c3: download("qa_report","QA report")
        with c4: download("librarian","Librarian report")

with tab2:
    st.subheader("Track multiple jobs")
    ids = st.text_area("One job_id per line")
    if st.button("Check"):
        out = []
        for jid in [x.strip() for x in ids.splitlines() if x.strip()]:
            try:
                out.append(requests.get(f"{API_BASE}/jobs/{jid}", timeout=30).json())
            except Exception as e:
                out.append({"job_id": jid, "status": "error", "error": str(e)})
        st.json(out)

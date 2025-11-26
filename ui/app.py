# ui/app.py
import streamlit as st
import os, sys, time
from pathlib import Path

# Project root (works on Kaggle or locally)
ROOT = "/kaggle/working/capstone_project" if os.path.exists("/kaggle/working") else r'C:\Users\HEALTHY MACHINES\OneDrive\Desktop\capstone_project_package'
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "src"))

card_image_path = os.path.join(ROOT, "A_pair_of_digital_graphics_features_Faiq_Ahamed’s_.png")

st.set_page_config(page_title="AI Research Team - Demo", layout="wide")
col1, col2 = st.columns([1,3])
with col1:
    try:
        st.image(card_image_path, width=220)
    except Exception:
        st.write("⚠️ Project image not available")
with col2:
    st.title("AI Research Team — Multi-Agent Research Automation")
    st.markdown("**Author:** Faiq Ahamed  •  **Track:** Freestyle")

st.sidebar.header("Settings & Mode")
st.sidebar.write("Toggle between mock mode (no external calls) and real mode (uses Gemini / Google APIs).")

USE_MOCK_UI = st.sidebar.checkbox("Use Mock Mode (recommended)", value=True)

if not USE_MOCK_UI:
    st.sidebar.markdown("🔐 **Real API mode ON — enter credentials below**")
    api_key_input = st.sidebar.text_input("GOOGLE_API_KEY (optional - for some adapters)", value="", type="password")
    if api_key_input:
        os.environ["GOOGLE_API_KEY"] = api_key_input.strip()

    st.sidebar.markdown("Optional: Upload Service Account JSON (preferred for Gemini tool)")
    sa_file = st.sidebar.file_uploader("Upload service-account.json", type=["json"])
    if sa_file is not None:
        sa_path = Path(ROOT) / "service_account_uploaded.json"
        with open(sa_path, "wb") as f:
            f.write(sa_file.getbuffer())
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(sa_path)
        st.sidebar.success("Service account uploaded and configured.")
    else:
        sa_path_text = st.sidebar.text_input("Or enter path to GOOGLE_APPLICATION_CREDENTIALS (optional)", value="")
        if sa_path_text.strip():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path_text.strip()

    st.sidebar.markdown("---")
    st.sidebar.write("Credential status:")
    st.sidebar.write("GOOGLE_API_KEY:", "SET" if os.environ.get("GOOGLE_API_KEY") else "NOT SET")
    st.sidebar.write("GOOGLE_APPLICATION_CREDENTIALS:", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "NOT SET"))
else:
    st.sidebar.info("Mock mode ON — no external API calls will be made.")

# Import modules AFTER potential credentials are set in the same process
from orchestrator import Orchestrator
from agents import ResearchAgent, SummarizerAgent, CriticAgent, WriterAgent
from tool_adapter import Tool, simple_search
from a2a_simulator import A2ABus
from memory import Session, MemoryStore
from observability import log_event, trace_span, emit_metric

st.subheader("Run Research Pipeline")
query = st.text_input("Enter research query:", "Recent breakthroughs in quantum computing and impact on AI (2024–2025)", key="query_input")
run_button = st.button("Run Research")
clear_button = st.button("Clear Outputs")

search_tool = Tool("web_search", simple_search)
research = ResearchAgent("ResearchAgent", tools={"search": search_tool}, use_mock=USE_MOCK_UI)
summarizer = SummarizerAgent("SummarizerAgent", use_mock=USE_MOCK_UI)
critic = CriticAgent("CriticAgent", use_mock=USE_MOCK_UI)
writer = WriterAgent("WriterAgent", use_mock=USE_MOCK_UI)
bus = A2ABus()
orch = Orchestrator(
    agents=[research, summarizer, critic, writer],
    bus=bus,
    memory_path=os.path.join(ROOT, "data", "processed", "memory_store.json"),
    use_mock=USE_MOCK_UI
)

import shutil

# --- Memory store (robust initialization) ---
memory_path = os.path.join(ROOT, "data", "processed", "memory_store.json")

try:
    # Attempt normal load
    memory = MemoryStore(memory_path)

except Exception as e:
    # Recovery path when JSON is corrupted
    st.warning("⚠️ Memory store corrupted — creating backup and resetting. Error: " + str(e))

    # Backup original file if exists
    if os.path.exists(memory_path):
        shutil.copyfile(memory_path, memory_path + ".corrupt.bak")
        st.info(f"Backup created: {memory_path}.corrupt.bak")

    # Write a clean empty JSON array
    try:
        os.makedirs(os.path.dirname(memory_path), exist_ok=True)
        with open(memory_path, "w", encoding="utf-8") as f:
            f.write("[]")
    except Exception as write_err:
        st.error(f"Failed to create clean memory file: {write_err}")
        raise

    # Reload clean store
    memory = MemoryStore(memory_path)
    st.success("Memory store reset successfully.")


progress_bar = st.progress(0)
status_text = st.empty()
findings_expander = st.expander("Research Findings", expanded=True)
summary_expander = st.expander("Summarizer Output", expanded=True)
critique_expander = st.expander("Critic Output", expanded=True)
draft_expander = st.expander("Final Draft", expanded=True)

if run_button:
    # read the input right at run time
    current_query = st.session_state.get("query_value", query) if "query_value" in st.session_state else query
    # also update session_state so future runs use explicit value
    st.session_state["query_value"] = current_query

    if not USE_MOCK_UI and not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")):
        st.error("Real mode selected but no credentials are set. Please enter GOOGLE_API_KEY or upload/set GOOGLE_APPLICATION_CREDENTIALS in the sidebar.")
    else:
        status_text.info("Starting pipeline…")
        session = Session(f"ui-session-{int(time.time())}")
        session.add_turn("user", query)
        steps = ["research", "summarize", "critique", "write", "finalize"]
        results = orch.run_pipeline(session_id=session.session_id, user_query=current_query)
        for i, step in enumerate(steps):
            status_text.info(f"Running step: {step}")
            time.sleep(0.5)
            progress_bar.progress(int(((i+1)/len(steps))*100))
            if step == "finalize":
                results = orch.run_pipeline(session_id=session.session_id, user_query=query)
        progress_bar.progress(100)
        status_text.success("Pipeline complete ✔️")

        with findings_expander:
            st.text_area("Findings", results.get("findings", ""), height=150)
        with summary_expander:
            st.text_area("Summary", results.get("summary", ""), height=150)
        with critique_expander:
            st.text_area("Critique", results.get("critique", ""), height=150)
        with draft_expander:
            st.text_area("Final Draft", results.get("final_draft", ""), height=300)
            st.download_button("Download Draft as TXT", data=results.get("final_draft", ""), file_name="final_draft.txt")



if clear_button:
    st.experimental_rerun()

if st.sidebar.checkbox("Show Logs / Traces"):
    st.subheader("Logs / Traces")
    log_file = os.path.join(ROOT, "data", "processed", "agent_logs.jsonl")
    if os.path.exists(log_file):
        logs = open(log_file).read().strip().split("\n")[-20:]
        st.write(logs)
    else:
        st.write("No logs available.")
if st.sidebar.checkbox("Show Memory Store"):
    st.subheader("Memory Store")
    st.json(memory.store)

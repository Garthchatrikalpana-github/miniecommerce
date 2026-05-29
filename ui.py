import streamlit as st
import re
import json
import textwrap
from datetime import datetime
import pandas as pd
from google import genai
from google.genai import types

print("✅ Dependencies loaded successfully")

# ─── STREAMLIT UI CONFIGURATION ──────────────────────────────────────────────
st.set_page_config(page_title="AI Production Log Analyzer", page_icon="🔍", layout="wide")

st.title("🔍 AI Production Log Analyzer")
st.markdown("Drop your application log file below to extract errors, discover the probable root cause, and get troubleshooting steps.")

# ─── YOUR PIPELINE INITIALIZATION ───────────────────────────────────────────
# Ensure your ANTHROPIC_API_KEY, client, MODEL, IMPORTANT_LEVELS, NOISE_PATTERNS,
# and functions like is_noise(), build_log_text(), chunk_text(), analyze_chunk(), 
# and merge_results() are copied here from your notebook.
# ─── Configuration ──────────────────────────────────────────────────────────
GEMINI_API_KEY = "AQ.Ab8RN6Ibyl242AE2IwZjwqIPjyrMC5rM0B2or4X8Ao478ojAkg"   # <-- Replace with your Google AI Studio key
MODEL          = "gemini-2.5-flash"

# Initialize the official Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)
print("✅ Gemini client initialised")


MAX_TOKENS        = 2048
CHUNK_SIZE        = 4000   # characters per chunk sent to LLM

def group_multiline_logs(raw: str) -> list[dict]:
    """
    Groups stack traces that follow an ERROR/WARNING/CRITICAL line
    into a single log event dict.
    """
    # Regex to detect the start of a structured log line
    LOG_HEADER = re.compile(
        r'^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d+)'
        r'\s+(\w+)\s+([\w\.]+)\s+-\s+(.+)$'
    )

    events = []
    current = None

    for line in raw.splitlines():
        line = line.rstrip()
        if not line:
            continue

        m = LOG_HEADER.match(line)
        if m:
            if current:
                events.append(current)
            current = {
                "timestamp" : m.group(1),
                "level"     : m.group(2),
                "service"   : m.group(3),
                "message"   : m.group(4),
                "traceback" : ""
            }
        else:
            # Continuation / stack-trace line
            if current:
                current["traceback"] += line + "\n"

    if current:
        events.append(current)

    print(f"📦 Grouped into {len(events)} log events")
    return events

NOISE_PATTERNS = [
    re.compile(r'watchfiles', re.IGNORECASE),
    re.compile(r'multipart\.multipart', re.IGNORECASE),
    re.compile(r'GET /health', re.IGNORECASE),        # heartbeat
    re.compile(r'uvicorn\.access', re.IGNORECASE),
]

def is_noise(event: dict) -> bool:
    text = event["service"] + " " + event["message"]
    return any(p.search(text) for p in NOISE_PATTERNS)

def build_log_text(events: list[dict]) -> str:
    """Serialise structured events back to a readable string for the LLM."""
    lines = []
    for e in events:
        lines.append(
            f"[{e['timestamp']}] [{e['level']}] [{e['service']}] {e['message']}"
        )
        if e["traceback"].strip():
            lines.append(e["traceback"].rstrip())
        lines.append("")  # blank separator
    return "\n".join(lines)


def chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split text into chunks of ≤ `size` characters."""
    return [text[i:i + size] for i in range(0, len(text), size)]


SYSTEM_PROMPT = """\
You are an expert AI Production Support Engineer specialising in application log analysis.
Analyse the provided application logs and return a structured JSON report with exactly these keys:

{
  "error_summary": "One-sentence summary of all errors found.",
  "incidents": [
    {
      "id": 1,
      "error_type": "short error category",
      "severity": "LOW | MEDIUM | HIGH | CRITICAL",
      "impacted_component": "service or module name",
      "probable_root_cause": "detailed root cause explanation",
      "troubleshooting_steps": ["step1", "step2", "step3"],
      "recommended_fix": "concrete code or config fix"
    }
  ],
  "overall_health": "GREEN | YELLOW | RED",
  "incident_summary": "2-3 sentence executive summary suitable for an on-call engineer."
}

Return ONLY valid JSON — no markdown fences, no extra text.
"""


# def analyze_chunk(chunk: str, chunk_num: int, total: int) -> dict:
#     """Send one log chunk to Claude and return parsed JSON."""
#     print(f"  ⏳ Analysing chunk {chunk_num}/{total} …")
#     response = client.messages.create(
#         model      = MODEL,
#         max_tokens = MAX_TOKENS,
#         system     = SYSTEM_PROMPT,
#         messages   = [{"role": "user", "content": f"Application logs:\n\n{chunk}"}]
#     )
#     raw = response.content[0].text.strip()
#     # Strip accidental markdown fences if present
#     raw = re.sub(r'^```[\w]*\n?', '', raw)
#     raw = re.sub(r'\n?```$', '', raw)
#     return json.loads(raw)
def analyze_chunk(chunk: str, chunk_num: int, total: int) -> dict:
    """Send one log chunk to Gemini and return parsed JSON."""
    print(f"  ⏳ Analysing chunk {chunk_num}/{total} …")
    
    response = client.models.generate_content(
        model=MODEL,
        contents=f"Application logs:\n\n{chunk}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json"  # Forces JSON output natively
        ),
    )
    
    # Parse and return the JSON directly
    return json.loads(response.text)


def merge_results(results: list[dict]) -> dict:
    """Merge results from multiple chunks into a single report."""
    all_incidents = []
    summaries     = []
    health_order  = {"RED": 3, "YELLOW": 2, "GREEN": 1}
    worst_health  = "GREEN"

    for r in results:
        all_incidents.extend(r.get("incidents", []))
        summaries.append(r.get("incident_summary", ""))
        h = r.get("overall_health", "GREEN")
        if health_order.get(h, 0) > health_order.get(worst_health, 0):
            worst_health = h

    # Re-number incidents
    for idx, inc in enumerate(all_incidents, 1):
        inc["id"] = idx

    return {
        "error_summary"    : results[0].get("error_summary", "") if results else "",
        "incidents"        : all_incidents,
        "overall_health"   : worst_health,
        "incident_summary" : " ".join(summaries)
    }


# Your updated log parser function stays exactly the same
def group_multiline_logs(raw: str) -> list[dict]:
    LOG_HEADER = re.compile(
        r'^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})'
        r'\s*\|\s*(\w+)\s*\|\s*([\w\.-]+)\s*\|\s*(.*)$'
    )
    events = []
    current = None
    for line in raw.splitlines():
        line = line.rstrip()
        if not line: continue
        m = LOG_HEADER.match(line)
        if m:
            if current: events.append(current)
            current = {
                "timestamp" : m.group(1),
                "level"     : m.group(2).strip(),
                "service"   : m.group(3).strip(),
                "message"   : m.group(4).strip(),
                "traceback" : ""
            }
        else:
            if current: current["traceback"] += line + "\n"
    if current: events.append(current)
    return events

IMPORTANT_LEVELS = {"ERROR", "WARNING", "CRITICAL"}

# ─── STREAMLIT INTERACTIVE UI COMPONENTS ──────────────────────────────────────

# 1. Drag and Drop File Uploader
# 1. Drag and Drop File Uploader
uploaded_file = st.file_uploader("Upload your application log file (.log, .txt)", type=["log", "txt"])

if uploaded_file is not None:
    # Read the file contents as text
    CUSTOM_LOGS = uploaded_file.read().decode("utf-8")
    
    if CUSTOM_LOGS.strip():
        # Step-by-step progress logging in the UI 
        with st.status("🚀 Processing logs and running AI analysis...", expanded=True) as status_box:
            
            st.write("📦 Parsing log structure...")
            grouped = group_multiline_logs(CUSTOM_LOGS)
            
            st.write("🧹 Filtering out system noise...")
            cleaned = [e for e in grouped if not is_noise(e)]
            
            st.write("🚨 Extracting high-priority incidents...")
            important = [e for e in cleaned if e["level"] in IMPORTANT_LEVELS]
            
            st.write(f"📊 Found {len(grouped)} total lines | {len(cleaned)} after noise removal | {len(important)} actionable issues.")
            
            if important:
                st.write("🤖 Sending critical log fragments to Claude for diagnostic analysis...")
                log_text2 = build_log_text(important)
                chunks2   = chunk_text(log_text2)
                
                # Run the actual API calls
                results2  = [analyze_chunk(c, i + 1, len(chunks2)) for i, c in enumerate(chunks2)]
                report2   = merge_results(results2)
                
                status_box.update(label="✅ Analysis complete!", state="complete", expanded=False)
                
                # ─── RENDERING THE BEAUTIFUL REPORT ───────────────────────────────────
                st.success("### 📊 AI Log Analysis Report")
                
                # 🛠️ FIX: If the report returned is a plain string, render it directly!
                if isinstance(report2, str):
                    st.markdown(report2)
                
                # If it's a parsed dictionary/json structure, read it safely using .get()
                elif isinstance(report2, dict):
                    # Display Health Status visually
                    health = report2.get("overall_health", "GREEN").upper()
                    health_colors = {"RED": "red", "YELLOW": "orange", "GREEN": "green"}
                    health_icons = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}
                    
                    st.markdown(f"#### System Health Status: :{health_colors.get(health, 'green')}[{health_icons.get(health, '🟢')} {health}]")
                    
                    # Display Summaries inside callout cards
                    if report2.get("error_summary"):
                        st.info(f"**📋 Error Summary:**\n{report2.get('error_summary')}")
                    if report2.get("incident_summary"):
                        st.warning(f"**📝 Executive Overview:**\n{report2.get('incident_summary')}")
                    
                    # Iterate and display individual incidents elegantly
                    st.markdown("### 🚨 Detected Incidents")
                    incidents_list = report2.get("incidents", [])
                    
                    for idx, inc in enumerate(incidents_list):
                        sev = inc.get("severity", "LOW").upper()
                        sev_colors = {"CRITICAL": "red", "HIGH": "orange", "MEDIUM": "blue", "LOW": "green"}
                        error_type = inc.get("error_type", "Unknown Runtime Exception")
                        inc_id = inc.get("id", idx + 1)
                        
                        # Create an expandable tile for each error found
                        with st.expander(f"🔹 Incident #{inc_id} | Severity: :{sev_colors.get(sev, 'blue')}[{sev}] | {error_type}"):
                            st.markdown(f"**🏗️ Impacted Component:** `{inc.get('impacted_component', 'N/A')}`")
                            st.markdown(f"**🔍 Probable Root Cause:**\n{inc.get('probable_root_cause', 'No details provided.')}")
                            
                            # Render Troubleshooting Steps as a checkbox list
                            st.markdown("**🛠️ Recommended Troubleshooting Steps:**")
                            for step_idx, step in enumerate(inc.get("troubleshooting_steps", [])):
                                # Added a unique string integer key suffix to prevent element ID overlapping crashes
                                st.checkbox(step, key=f"step_{inc_id}_{step_idx}")
                                
                            # Code snippet block formatting for recommended fixes
                            if inc.get("recommended_fix"):
                                st.markdown("**✅ Recommended Fix:**")
                                st.code(inc.get("recommended_fix"), language="python")
                else:
                    # Fallback string representation in case it is an unexpected format type
                    st.code(str(report2))
                            
            else:
                status_box.update(label="✅ Finished processing.", state="complete", expanded=True)
                st.balloons()
                st.success("### 🎉 No critical incidents detected! Your logs look completely healthy.")
    else:
        st.error("⚠️ The uploaded file is completely empty. Please try another file.")
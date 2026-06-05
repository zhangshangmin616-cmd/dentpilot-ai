import html
import os

import streamlit as st
import streamlit.components.v1 as components


SUBJECTS = [
    "Dentistry",
    "Endodontics",
    "Periodontology",
    "Oral Surgery",
    "Oral Pathology",
    "Dental Anatomy",
    "Pharmacology",
    "General Pathology",
]

EXAMINER_STYLES = [
    "Strict Professor",
    "Friendly Tutor",
    "OSCE Examiner",
    "Fast Oral Pathology Professor",
]


def get_secret(name, default=None):
    env_value = os.getenv(name)
    if env_value:
        return env_value

    try:
        value = st.secrets.get(name, default)
    except Exception:
        return default
    return value if value is not None else default


def render_realtime_oral_exam_page():
    st.markdown(
        """
        <section class="hero">
            <div class="eyebrow">实时口试模拟</div>
            <h1 class="hero-title">🎙️ Realtime Oral Exam</h1>
            <p class="hero-subtitle">Speak with an AI dental professor in real time.</p>
            <p class="hero-copy">通过 ElevenLabs Conversational AI Widget 进行实时英文口试训练。适合练习牙科英文表达、追问反应和口试节奏。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.warning("Realtime voice may consume ElevenLabs credits. Use it carefully.")

    default_context = st.session_state.get("last_course_text", "")
    course_context = st.text_area(
        "Paste your lecture/topic here",
        value=default_context,
        height=180,
        placeholder="Example: Dental caries is a biofilm-mediated disease caused by acid production...",
    )

    col_subject, col_style = st.columns(2)
    with col_subject:
        subject = st.selectbox("Subject", SUBJECTS)
    with col_style:
        examiner_style = st.selectbox("Examiner style", EXAMINER_STYLES)

    starter_instruction = (
        f"My topic is: {course_context.strip() or '[your lecture/topic]'}. "
        "Please examine me on this topic."
    )
    st.markdown("### 开场提示")
    st.info(starter_instruction)

    agent_id = get_secret("ELEVENLABS_AGENT_ID")
    if not agent_id:
        st.markdown("### Setup Required")
        st.error(
            "ELEVENLABS_AGENT_ID is missing. Create an ElevenLabs Conversational AI agent "
            "and add the agent id to your .env or Streamlit secrets."
        )
        st.caption("这个页面不需要 ElevenLabs API Key，只需要 Conversational AI Agent ID。")
        return

    safe_agent_id = html.escape(str(agent_id), quote=True)

    widget_html = f"""
    <div style="min-height: 620px; width: 100%;">
      <elevenlabs-convai agent-id="{safe_agent_id}"></elevenlabs-convai>
    </div>
    <script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>
    """

    st.markdown("### Realtime Exam Room")
    st.caption("点击 widget 内的通话按钮开始。开始时可以先读上面的开场提示。")
    try:
        components.html(widget_html, height=700, scrolling=True)
    except Exception as exc:
        st.warning(f"Realtime oral exam widget failed to render: {exc}")

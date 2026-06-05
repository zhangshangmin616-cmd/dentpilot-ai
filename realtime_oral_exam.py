import html
import json
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
            <h1 class="hero-title">🎙️ Realtime Oral Exam Simulator</h1>
            <p class="hero-subtitle">This is not a general AI call. It is a simulated dental oral examination.</p>
            <p class="hero-copy">AI 考官会根据你的课程主题、科目和考官风格，直接开始英文口试提问。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="feature-card" style="margin-bottom: 1rem;">
            <div class="feature-title">开始方式</div>
            <div class="feature-copy">
                Paste your lecture topic, choose examiner style, then start the call.
                The AI examiner will ask Question 1 directly.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    default_context = st.session_state.get("last_course_text", "")
    course_context = st.text_area(
        "考试主题 / 课程内容",
        value=default_context,
        height=170,
        placeholder="例如：Dental caries, reversible pulpitis, periodontal pocket, endodontic diagnosis...",
    )

    col_subject, col_style = st.columns(2)
    with col_subject:
        subject = st.selectbox("科目", SUBJECTS)
    with col_style:
        examiner_style = st.selectbox("考官风格", EXAMINER_STYLES)

    dynamic_variables = {
        "course_context": course_context.strip(),
        "subject": subject,
        "examiner_style": examiner_style,
    }

    with st.expander("Debug: dynamic variables being sent"):
        st.json(dynamic_variables)

    agent_id = get_secret("ELEVENLABS_AGENT_ID")
    if not agent_id:
        st.markdown("### 需要配置")
        st.error(
            "缺少 ELEVENLABS_AGENT_ID。请先在 ElevenLabs 创建 Conversational AI Agent，"
            "然后把 Agent ID 添加到 .env 或 Streamlit Secrets。"
        )
        st.caption("这个页面不会显示任何 API key；前端只读取 Agent ID。")
        return

    if st.button("Start Realtime Oral Exam", type="primary", use_container_width=True):
        st.session_state["realtime_oral_exam_started"] = True
        st.session_state["realtime_oral_exam_vars"] = dynamic_variables

    if not st.session_state.get("realtime_oral_exam_started"):
        st.info("填写主题并点击 Start Realtime Oral Exam 后，实时口试房间会出现在这里。")
        return

    variables_to_send = st.session_state.get("realtime_oral_exam_vars", dynamic_variables)
    safe_agent_id = html.escape(str(agent_id), quote=True)
    safe_dynamic_variables = html.escape(
        json.dumps(variables_to_send, ensure_ascii=False),
        quote=True,
    )

    widget_html = f"""
    <div style="min-height: 620px; width: 100%;">
      <elevenlabs-convai
        agent-id="{safe_agent_id}"
        dynamic-variables='{safe_dynamic_variables}'>
      </elevenlabs-convai>
    </div>
    <script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>
    """

    st.markdown("### 口试房间")
    st.success("Click Start a call. The examiner will begin the oral exam directly.")
    try:
        components.html(widget_html, height=700, scrolling=True)
    except Exception as exc:
        st.warning(f"Realtime oral exam widget failed to render: {exc}")

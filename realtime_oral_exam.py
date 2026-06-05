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
            <div class="eyebrow">实时口试训练</div>
            <h1 class="hero-title">Realtime Oral Exam</h1>
            <p class="hero-subtitle">让 AI 牙科教授像真实口试一样主动提问、追问、打分和中文反馈。</p>
            <p class="hero-copy">适合中国留学生练习英文牙科口试、OSCE 问答、病例表达和考官追问反应。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    default_context = st.session_state.get("last_course_text", "")
    course_context = st.text_area(
        "考试主题 / 课程内容",
        value=default_context,
        height=160,
        placeholder="例如：Dental caries, reversible pulpitis, periodontal pocket, endodontic diagnosis...",
    )

    col_subject, col_style = st.columns(2)
    with col_subject:
        subject = st.selectbox("科目", SUBJECTS)
    with col_style:
        examiner_style = st.selectbox("考官风格", EXAMINER_STYLES)

    topic = course_context.strip() or "[your topic]"
    starter_instruction = (
        f"My topic is: {topic}. "
        f"Subject: {subject}. Examiner style: {examiner_style}. "
        "Please start the oral exam now. Ask me the first question, wait for my answer, "
        "then grade me and ask a follow-up question."
    )

    st.markdown("### 开始考试")
    st.info(starter_instruction)
    st.caption("点击下方通话按钮后，先读这句话。然后考官会开始问你，不是普通闲聊。")

    agent_id = get_secret("ELEVENLABS_AGENT_ID")
    if not agent_id:
        st.markdown("### 需要配置")
        st.error(
            "缺少 ELEVENLABS_AGENT_ID。请先在 ElevenLabs 创建 Conversational AI Agent，"
            "然后把 Agent ID 添加到 .env 或 Streamlit Secrets。"
        )
        st.caption("这个页面只需要 Agent ID，不需要在前端暴露 ElevenLabs API Key。")
        return

    safe_agent_id = html.escape(str(agent_id), quote=True)
    widget_html = f"""
    <div style="min-height: 620px; width: 100%;">
      <elevenlabs-convai agent-id="{safe_agent_id}"></elevenlabs-convai>
    </div>
    <script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>
    """

    st.markdown("### 口试房间")
    try:
        components.html(widget_html, height=700, scrolling=True)
    except Exception as exc:
        st.warning(f"Realtime oral exam widget failed to render: {exc}")

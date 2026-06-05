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


def build_override_prompt(course_context: str, subject: str, examiner_style: str) -> str:
    return f"""
You are DentPilot AI, a realistic English oral examination professor for Chinese students in English-taught dental and medical programs.

Use the selected subject, examiner style, and course context.

Selected subject: {subject}
Examiner style: {examiner_style}
Course context: {course_context or "The student has not provided course context yet. Ask them for a topic before starting."}

Exam behavior:
- Ask one question at a time.
- Wait for the student's spoken answer.
- Do not reveal the model answer before the student answers.
- Use English for oral exam questions.
- After each answer, give:
  1. Score for this answer
  2. Strengths
  3. Missing points
  4. Corrected answer
  5. 中文反馈
  6. One follow-up question
- Make the exam progressively harder.
- After about 5 questions, give a final exam report:
  - Total score / 100
  - Pass level: Fail, Borderline, Pass, Good, Excellent
  - Strong areas
  - Weak areas
  - Three-day revision plan
  - Recommended next topics

Rubric:
- Content Accuracy: 30 points
- Completeness: 20 points
- Clinical Reasoning: 20 points
- English Expression: 10 points
- Examiner Interaction: 10 points
- Pronunciation and Fluency: 10 points

Safety:
- This is for study and exam preparation only.
- Do not provide real patient diagnosis.
- Do not claim to replace a licensed clinician or professor.
""".strip()


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

    dynamic_variables = {
        "course_context": course_context,
        "subject": subject,
        "examiner_style": examiner_style,
    }
    override_prompt = build_override_prompt(course_context, subject, examiner_style)

    safe_agent_id = html.escape(str(agent_id), quote=True)
    safe_dynamic_variables = html.escape(
        json.dumps(dynamic_variables, ensure_ascii=False),
        quote=True,
    )
    safe_override_prompt = html.escape(override_prompt, quote=True)

    widget_html = f"""
    <div style="min-height: 620px; width: 100%;">
      <elevenlabs-convai
        agent-id="{safe_agent_id}"
        dynamic-variables='{safe_dynamic_variables}'
        override-prompt="{safe_override_prompt}"
      ></elevenlabs-convai>
    </div>
    <script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>
    """

    st.markdown("### Realtime Exam Room")
    st.caption("点击 widget 内的通话按钮开始。开始时可以先读上面的开场提示。")
    try:
        components.html(widget_html, height=700, scrolling=True)
    except Exception as exc:
        st.warning(f"Realtime oral exam widget failed to render: {exc}")

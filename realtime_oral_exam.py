import os
from html import escape

import streamlit as st


DEFAULT_ORAL_APP_URL = "https://dentpilot-oral-app.vercel.app"


def get_oral_app_url() -> str:
    try:
        secret_value = st.secrets["ORAL_APP_URL"]
    except Exception:
        secret_value = None

    if secret_value:
        return str(secret_value).strip()

    env_value = os.getenv("ORAL_APP_URL")
    if env_value:
        return env_value.strip()

    return DEFAULT_ORAL_APP_URL


def render_realtime_oral_exam_page():
    oral_app_url = get_oral_app_url()
    escaped_oral_app_url = escape(oral_app_url, quote=True)
    is_local_url = oral_app_url.startswith("http://localhost") or oral_app_url.startswith(
        "http://127.0.0.1"
    )

    st.markdown(
        """
        <section class="oral-app-hero">
            <h1 class="oral-app-title">🎙️ 实时口试 App</h1>
            <p class="oral-app-subtitle">
                进入新版口试房间，输入课程主题和讲义内容后，AI 教授会根据你的内容直接开始英文口试。
            </p>
            <div class="oral-app-hero-card">
                <p>
                    这是新版实时口试界面，不再是通用 AI 电话窗口。
                    你可以输入口试主题和课程内容，点击开始口试，AI 教授会根据你的内容提问、追问并给出反馈。
                </p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    feature_cards = [
        ("教授头像与真实口试房间界面", "更像真实考场，而不是通用电话窗口。"),
        ("必须输入主题后才能开始", "避免泛泛开场，让每次口试都围绕你的主题。"),
        ("AI 教授围绕课程内容提问", "根据课程主题和讲义内容展开提问与追问。"),
        ("实时英文口试与追问", "用英文口头回答，训练真实 oral exam 的表达节奏。"),
        ("适合中国英授口腔/医学生", "中文入口降低操作负担，英文保留在考试训练中。"),
    ]

    st.markdown('<div class="oral-app-feature-grid">', unsafe_allow_html=True)
    for title, copy in feature_cards:
        st.markdown(
            f"""
            <div class="oral-app-feature-card">
                <div class="oral-app-feature-title">{title}</div>
                <div class="oral-app-feature-copy">{copy}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.link_button(
        "🎙️ 进入新版实时口试 App",
        oral_app_url,
        use_container_width=True,
    )

    if is_local_url:
        st.info(
            "本地测试时，请先在另一个 PowerShell 窗口运行：\n\n"
            "cd Desktop\\dentpilot-oral-app\n\n"
            "npm.cmd run dev"
        )
    else:
        st.markdown("当前实时口试 App 地址：")
        st.markdown(f"[{oral_app_url}]({escaped_oral_app_url})")

    st.markdown(
        """
        <style>
        .oral-app-hero {
            margin: 0.5rem 0 1.5rem;
        }
        .oral-app-title {
            margin-bottom: 0.55rem;
            font-size: 2.2rem;
            font-weight: 850;
        }
        .oral-app-subtitle {
            max-width: 760px;
            color: rgba(15, 23, 42, 0.72);
            font-size: 1.08rem;
            line-height: 1.75;
        }
        .oral-app-hero-card {
            margin-top: 1.2rem;
            padding: 1.25rem 1.35rem;
            border: 1px solid rgba(14, 165, 233, 0.22);
            border-radius: 0.9rem;
            background: linear-gradient(135deg, rgba(240, 249, 255, 0.96), rgba(236, 253, 245, 0.92));
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.07);
        }
        .oral-app-hero-card p {
            margin: 0;
            color: #0f172a;
            font-size: 1rem;
            line-height: 1.8;
        }
        .oral-app-feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 0.9rem;
            margin: 1.1rem 0 1.2rem;
        }
        .oral-app-feature-card {
            min-height: 7.4rem;
            padding: 1rem;
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 0.75rem;
            background: rgba(255, 255, 255, 0.86);
        }
        .oral-app-feature-title {
            margin-bottom: 0.45rem;
            color: #0f172a;
            font-weight: 800;
        }
        .oral-app-feature-copy {
            color: rgba(15, 23, 42, 0.68);
            font-size: 0.94rem;
            line-height: 1.65;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

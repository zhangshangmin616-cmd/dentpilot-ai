import csv
import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont

from ai_engine import generate_study_pack
from clinical_case import (
    ClinicalCaseConfigError,
    ClinicalCaseJSONError,
    generate_clinical_case,
    grade_clinical_case,
)
from oral_exam import (
    OralExamConfigError,
    OralExamJSONError,
    generate_oral_question,
    grade_oral_answer,
)
from realtime_oral_exam import render_realtime_oral_exam_page
from weakness_analysis import (
    WeaknessAnalysisConfigError,
    WeaknessAnalysisJSONError,
    analyze_weaknesses,
)


load_dotenv(Path(__file__).resolve().parent / ".env", override=False)



def extract_pdf_text(uploaded_file) -> tuple[str, int]:
    pdf = PdfReader(uploaded_file)
    pages = []
    for page in pdf.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text.strip())
    return "\n\n".join(pages), len(pdf.pages)


def get_pdf_font_name() -> str:
    font_candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/arialuni.ttf"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            font_name = "DentPilotCJK"
            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return font_name
    font_name = "STSong-Light"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    return font_name


def as_paragraph_text(value) -> str:
    text_value = str(value or "")
    return (
        text_value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def build_study_pack_pdf(pack: dict, subject: str) -> bytes:
    buffer = io.BytesIO()
    font_name = get_pdf_font_name()
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "DentPilotBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10,
        leading=15,
        spaceAfter=8,
    )
    title = ParagraphStyle(
        "DentPilotTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=22,
        leading=28,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    section = ParagraphStyle(
        "DentPilotSection",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1e40af"),
        spaceBefore=14,
        spaceAfter=8,
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="DentPilot AI 复习包",
    )

    story = [
        Paragraph("DentPilot AI 复习包", title),
        Paragraph(f"专业方向：{as_paragraph_text(subject)}", body),
        Spacer(1, 8),
        Paragraph("中文讲解", section),
        Paragraph(as_paragraph_text(pack.get("chinese_explanation", "")), body),
        Paragraph("术语表", section),
    ]

    glossary = pack.get("glossary", [])
    if glossary:
        glossary_rows = [[
            Paragraph("英文", body),
            Paragraph("中文", body),
            Paragraph("定义", body),
            Paragraph("分类", body),
        ]]
        for term in glossary:
            glossary_rows.append([
                Paragraph(as_paragraph_text(term.get("english", "")), body),
                Paragraph(as_paragraph_text(term.get("chinese", "")), body),
                Paragraph(as_paragraph_text(term.get("definition", "")), body),
                Paragraph(as_paragraph_text(term.get("category", "")), body),
            ])
        glossary_table = Table(glossary_rows, colWidths=[1.25 * inch, 1.15 * inch, 3.0 * inch, 1.2 * inch])
        glossary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(glossary_table)
    else:
        story.append(Paragraph("没有匹配到术语。", body))

    story.append(Paragraph("Quiz 自测", section))
    quiz = pack.get("quiz", [])
    if quiz:
        for index, q in enumerate(quiz, start=1):
            options = q.get("options", [])
            option_text = "<br/>".join(as_paragraph_text(option) for option in options)
            quiz_text = (
                f"<b>Q{index}. {as_paragraph_text(q.get('question', ''))}</b><br/>"
                f"{option_text}<br/>"
                f"<b>答案：</b> {as_paragraph_text(q.get('answer', ''))}<br/>"
                f"<b>解析：</b> {as_paragraph_text(q.get('explanation_zh', ''))}"
            )
            story.append(Paragraph(quiz_text, body))
    else:
        story.append(Paragraph("没有生成自测题。", body))

    story.extend([
        Paragraph("考前总结", section),
        Paragraph(as_paragraph_text(pack.get("exam_summary", "")), body),
        Paragraph("Anki 卡片", section),
    ])

    flashcards = pack.get("flashcards", [])
    if flashcards:
        flashcard_rows = [[Paragraph("正面", body), Paragraph("背面", body), Paragraph("类型", body)]]
        for card in flashcards:
            flashcard_rows.append([
                Paragraph(as_paragraph_text(card.get("front", "")), body),
                Paragraph(as_paragraph_text(card.get("back", "")), body),
                Paragraph(as_paragraph_text(card.get("type", "")), body),
            ])
        flashcard_table = Table(flashcard_rows, colWidths=[2.2 * inch, 3.6 * inch, 0.8 * inch])
        flashcard_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ccfbf1")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(flashcard_table)
    else:
        story.append(Paragraph("没有生成 Anki 卡片。", body))

    doc.build(story)
    return buffer.getvalue()

st.set_page_config(
    page_title="DentPilot AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
        :root {
            --brand: #2563eb;
            --brand-2: #14b8a6;
            --brand-dark: #1e40af;
            --ink: #0f172a;
            --muted: #64748b;
            --panel: #ffffff;
            --line: #dbeafe;
            --soft: #eff6ff;
            --mint: #f0fdfa;
        }

        .stApp {
            background:
                radial-gradient(circle at 8% 0%, rgba(20, 184, 166, 0.20), transparent 28rem),
                radial-gradient(circle at 90% 12%, rgba(37, 99, 235, 0.18), transparent 32rem),
                linear-gradient(180deg, #f8fbff 0%, #eef6ff 44%, #f8fafc 100%);
            color: var(--ink);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 62%, #0b1220 100%);
        }

        [data-testid="stSidebar"] * {
            color: #e5edf7;
        }

        [data-testid="stSidebar"] .stSelectbox label {
            color: #cbd5e1;
        }

        [data-testid="stSidebar"] hr {
            border-color: rgba(226, 232, 240, 0.18);
        }

        [data-testid="collapsedControl"] {
            top: 0.85rem;
            left: 0.85rem;
            z-index: 999999;
        }

        button[data-testid="stExpandSidebarButton"],
        [data-testid="collapsedControl"] button,
        [data-testid="stSidebarCollapseButton"] button {
            min-width: 3rem;
            min-height: 3rem;
            border: 2px solid rgba(255, 255, 255, 0.92) !important;
            border-radius: 999px !important;
            background: #2563eb !important;
            color: #ffffff !important;
            box-shadow: 0 16px 36px rgba(15, 23, 42, 0.28), 0 0 0 4px rgba(37, 99, 235, 0.18) !important;
        }

        button[data-testid="stExpandSidebarButton"]:hover,
        [data-testid="collapsedControl"] button:hover,
        [data-testid="stSidebarCollapseButton"] button:hover {
            background: #1d4ed8 !important;
            transform: translateY(-1px);
        }

        button[data-testid="stExpandSidebarButton"] span,
        button[data-testid="stExpandSidebarButton"] svg,
        [data-testid="collapsedControl"] button span,
        [data-testid="collapsedControl"] button svg {
            color: #ffffff !important;
            fill: #ffffff !important;
        }

        button[data-testid="stExpandSidebarButton"]::after,
        [data-testid="collapsedControl"] button::after {
            content: "菜单";
            position: absolute;
            left: 3.25rem;
            top: 50%;
            transform: translateY(-50%);
            padding: 0.25rem 0.5rem;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.88);
            color: #ffffff;
            font-size: 0.78rem;
            font-weight: 800;
            white-space: nowrap;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
        }

        .main .block-container {
            padding-top: 1.75rem;
            max-width: 1200px;
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        .hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(37, 99, 235, 0.16);
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.96) 0%, rgba(240, 247, 255, 0.92) 56%, rgba(240, 253, 250, 0.94) 100%);
            border-radius: 20px;
            padding: 2.25rem;
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.08);
            margin-bottom: 1.25rem;
        }

        .eyebrow {
            color: var(--brand-dark);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }

        .hero-title {
            color: var(--ink);
            font-size: clamp(2.35rem, 4vw, 4.6rem);
            font-weight: 850;
            line-height: 0.98;
            margin: 0;
        }

        .hero-subtitle {
            color: var(--muted);
            font-size: 1.15rem;
            line-height: 1.65;
            max-width: 720px;
            margin-top: 1rem;
            margin-bottom: 0;
        }

        .hero-copy {
            color: #334155;
            font-size: 0.98rem;
            line-height: 1.7;
            max-width: 760px;
            margin-top: 0.75rem;
        }

        .hero-metrics {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
            margin-top: 1.4rem;
        }

        .metric-pill {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 12px;
            padding: 0.8rem 0.9rem;
        }

        .metric-value {
            color: var(--brand-dark);
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }

        .feature-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
            margin: 1rem 0 1.1rem;
        }

        .feature-card {
            background: var(--panel);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 12px;
            padding: 1rem;
            min-height: 132px;
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
        }

        .feature-icon {
            color: var(--brand);
            font-size: 1.35rem;
            line-height: 1;
        }

        .feature-title {
            color: var(--ink);
            font-weight: 800;
            margin-top: 0.55rem;
            margin-bottom: 0.3rem;
        }

        .feature-copy {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .input-panel {
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 16px;
            padding: 1.25rem;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.07);
        }

        .section-label {
            color: var(--brand-dark);
            font-weight: 800;
            font-size: 0.86rem;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .section-copy {
            color: var(--muted);
            margin-bottom: 1rem;
        }

        div[data-testid="stButton"] > button {
            border-radius: 10px;
            border: 0;
            min-height: 3rem;
            font-weight: 800;
            box-shadow: 0 12px 24px rgba(37, 99, 235, 0.22);
        }

        div[data-testid="stDownloadButton"] > button {
            border-radius: 10px;
            font-weight: 700;
        }

        .result-wrap {
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 16px;
            padding: 1rem;
            margin-top: 1.4rem;
        }

        .example-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.6fr) minmax(220px, 0.8fr);
            gap: 1rem;
            align-items: stretch;
            margin-bottom: 0.8rem;
        }

        .example-card,
        .workflow-card {
            background: #ffffff;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 12px;
            padding: 1rem;
        }

        .example-title {
            color: var(--ink);
            font-weight: 800;
            margin-bottom: 0.45rem;
        }

        .example-copy {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.55;
        }

        .footer {
            color: #64748b;
            border-top: 1px solid rgba(148, 163, 184, 0.25);
            margin-top: 2rem;
            padding: 1.2rem 0 0.25rem;
            text-align: center;
            font-size: 0.9rem;
        }

        @media (max-width: 900px) {
            .hero-metrics,
            .feature-grid,
            .example-grid {
                grid-template-columns: 1fr;
            }

            .hero {
                padding: 1.35rem;
            }

            [data-testid="collapsedControl"] {
                top: 0.75rem;
                left: 0.75rem;
            }

            button[data-testid="stExpandSidebarButton"],
            [data-testid="collapsedControl"] button {
                min-width: 3.4rem;
                min-height: 3.4rem;
            }

            button[data-testid="stExpandSidebarButton"]::after,
            [data-testid="collapsedControl"] button::after {
                left: 3.65rem;
                font-size: 0.82rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


sample = (
    "Dental caries is a biofilm-mediated, sugar-driven, multifactorial disease that results "
    "in the demineralization of dental hard tissues. The balance between demineralization "
    "and remineralization is influenced by oral hygiene, diet, fluoride exposure, saliva, "
    "and bacterial activity. Pulpitis is inflammation of the dental pulp and may be reversible "
    "or irreversible depending on the duration and severity of symptoms."
)


def render_oral_grade_result(result: dict):
    st.markdown("### 评分结果")
    score_col, level_col = st.columns([1, 1])
    score_col.metric("总分", f"{result.get('score', 0)}/100")
    level_col.metric("等级", result.get("level", ""))

    rubric_rows = [
        {"评分项": "Content Accuracy", "得分": result.get("content_accuracy", 0), "满分": 30},
        {"评分项": "Completeness", "得分": result.get("completeness", 0), "满分": 20},
        {"评分项": "Clinical Reasoning", "得分": result.get("clinical_reasoning", 0), "满分": 20},
        {"评分项": "English Expression", "得分": result.get("english_expression", 0), "满分": 10},
        {"评分项": "Examiner Interaction", "得分": result.get("examiner_interaction", 0), "满分": 10},
        {"评分项": "Pronunciation & Fluency", "得分": result.get("pronunciation_fluency", 0), "满分": 10},
    ]
    st.dataframe(pd.DataFrame(rubric_rows), use_container_width=True, hide_index=True)

    col_1, col_2 = st.columns(2)
    with col_1:
        st.subheader("优点")
        strengths = result.get("strengths") or []
        if strengths:
            for item in strengths:
                st.markdown(f"- {item}")
        else:
            st.write("暂无。")
    with col_2:
        st.subheader("缺失要点")
        missing_points = result.get("missing_points") or []
        if missing_points:
            for item in missing_points:
                st.markdown(f"- {item}")
        else:
            st.write("暂无。")

    st.subheader("Corrected Answer")
    st.write(result.get("corrected_answer", ""))

    st.subheader("中文反馈")
    st.write(result.get("chinese_feedback", ""))

    st.subheader("Follow-up Question")
    st.info(result.get("follow_up_question", ""))


def render_oral_exam_mode(default_text: str):
    st.session_state.setdefault("oral_exam_history", [])
    st.session_state.setdefault("oral_exam_rounds", [])

    st.markdown(
        """
        <section class="hero">
            <div class="eyebrow">AI 笔试训练</div>
            <h1 class="hero-title">DentPilot AI Written Exam</h1>
            <p class="hero-subtitle">英文笔试训练：生成问题、输入英文答案、结构化评分和中文反馈。</p>
            <p class="hero-copy">这个模式已经改为纯文本笔试训练；实时语音练习请使用 sidebar 里的 Realtime Oral Exam。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="input-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">笔试材料</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">粘贴英文课程内容，或复用刚才 Study Pack 中输入过的文本，生成英文笔试题。</div>',
        unsafe_allow_html=True,
    )

    oral_default_text = st.session_state.get("last_course_text", default_text)
    oral_course_text = st.text_area(
        "Course Text",
        value=oral_default_text,
        height=220,
        placeholder="Paste your English dental or medical course text here...",
    )

    control_col_1, control_col_2 = st.columns(2)
    with control_col_1:
        oral_subject = st.selectbox(
            "Subject",
            ["Dentistry", "Anatomy", "Pathology", "Pharmacology", "Endodontics", "Periodontology", "Oral Surgery"],
        )
    with control_col_2:
        oral_difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)

    if st.button("Generate Written Question", type="primary", use_container_width=True):
        if not oral_course_text.strip():
            st.error("请先粘贴英文课程内容。")
        else:
            try:
                with st.spinner("正在生成笔试题..."):
                    st.session_state["oral_question_data"] = generate_oral_question(
                        oral_course_text,
                        oral_subject,
                        oral_difficulty,
                    )
                    st.session_state["oral_exam_result"] = None
                    st.session_state["oral_student_answer"] = ""
                    st.session_state["oral_exam_rounds"] = []
                    st.session_state["last_course_text"] = oral_course_text
                st.success("笔试题已生成。")
            except OralExamConfigError as exc:
                st.error(str(exc))
            except OralExamJSONError as exc:
                st.error("DeepSeek 返回了无效 JSON。下面是原始输出，方便调试：")
                st.code(exc.raw_output)
            except Exception as exc:
                st.error(f"生成笔试题失败：{exc}")

    question_data = st.session_state.get("oral_question_data")
    if question_data:
        st.markdown("### Written Exam Question")
        question_text = question_data.get("question", "")
        st.info(question_text)

        with st.expander("查看 expected points / must-mention terms / model answer"):
            st.markdown("**Expected Points**")
            for item in question_data.get("expected_points", []):
                st.markdown(f"- {item}")
            st.markdown("**Must Mention Terms**")
            for item in question_data.get("must_mention_terms", []):
                st.markdown(f"- {item}")
            st.markdown("**Model Answer**")
            st.write(question_data.get("model_answer", ""))

        st.session_state.setdefault("oral_student_answer", "")
        student_answer = st.text_area(
            "Your English Answer",
            height=180,
            placeholder="Type your written exam answer in English...",
            key="oral_student_answer",
        )

        if st.button("Submit & Grade", type="primary", use_container_width=True):
            if not student_answer.strip():
                st.error("请先输入你的英文回答。")
            else:
                try:
                    with st.spinner("正在批改你的笔试回答..."):
                        result = grade_oral_answer(question_data, student_answer, oral_subject)
                    st.session_state["oral_exam_result"] = result
                    attempt = {
                        "subject": oral_subject,
                        "difficulty": question_data.get("difficulty", oral_difficulty),
                        "topic": question_data.get("topic", ""),
                        "question": question_data.get("question", ""),
                        "expected_points": question_data.get("expected_points", []),
                        "answer": student_answer,
                        "result": result,
                        "grading_result": result,
                    }
                    st.session_state["oral_exam_history"].insert(0, attempt)
                    st.session_state["oral_exam_history"] = st.session_state["oral_exam_history"][:10]
                    st.session_state["oral_exam_rounds"].append(attempt)
                except OralExamConfigError as exc:
                    st.error(str(exc))
                except OralExamJSONError as exc:
                    st.error("DeepSeek 返回了无效 JSON。下面是原始输出，方便调试：")
                    st.code(exc.raw_output)
                except Exception as exc:
                    st.error(f"批改失败：{exc}")

    if st.session_state.get("oral_exam_result"):
        render_oral_grade_result(st.session_state["oral_exam_result"])
        follow_up = st.session_state["oral_exam_result"].get("follow_up_question", "")
        if follow_up and st.button("Continue With Follow-up Question", use_container_width=True):
            st.session_state["oral_question_data"] = {
                "question": follow_up,
                "expected_points": [],
                "must_mention_terms": [],
                "difficulty": oral_difficulty,
                "topic": st.session_state.get("oral_question_data", {}).get("topic", oral_subject),
                "model_answer": "",
            }
            st.session_state["oral_exam_result"] = None
            st.session_state["oral_student_answer"] = ""
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    rounds = st.session_state.get("oral_exam_rounds", [])
    if rounds:
        st.markdown("### Current Written Exam Session")
        st.caption(f"{len(rounds)} round(s) completed in this written exam session.")
        for index, attempt in enumerate(rounds, start=1):
            result = attempt.get("grading_result") or attempt.get("result", {})
            with st.expander(f"Round {index}: {result.get('score', 0)}/100 ({result.get('level', '')})"):
                st.markdown(f"**Question:** {attempt.get('question', '')}")
                st.markdown(f"**Answer:** {attempt.get('answer', '')}")
                st.markdown(f"**Feedback:** {result.get('chinese_feedback', '')}")

    st.markdown("### 最近笔试记录")
    history = st.session_state.get("oral_exam_history", [])
    if not history:
        st.info("还没有笔试记录。生成问题并提交回答后，会在这里保存最近记录。")
    else:
        for index, attempt in enumerate(history[:5], start=1):
            result = attempt.get("result", {})
            label = f"{index}. {attempt.get('topic') or attempt.get('subject')} - {result.get('score', 0)}/100 ({result.get('level', '')})"
            with st.expander(label):
                st.markdown(f"**Question:** {attempt.get('question', '')}")
                st.markdown(f"**Your Answer:** {attempt.get('answer', '')}")
                st.markdown(f"**Chinese Feedback:** {result.get('chinese_feedback', '')}")

    st.markdown(
        """
        <div class="footer">
            DentPilot AI Written Exam 是纯文本笔试训练模式，用于帮助学生准备英文医学/牙科考试。实时语音请使用 Realtime Oral Exam。
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_clinical_case_grade(result: dict):
    st.markdown("### 病例评分")
    score_col, level_col = st.columns(2)
    score_col.metric("总分", f"{result.get('score', 0)}/100")
    level_col.metric("等级", result.get("level", ""))

    rubric_rows = [
        {"评分项": "Diagnosis", "得分": result.get("diagnosis_score", 0), "满分": 20},
        {"评分项": "Evidence", "得分": result.get("evidence_score", 0), "满分": 20},
        {"评分项": "Differential diagnosis", "得分": result.get("differential_score", 0), "满分": 15},
        {"评分项": "Additional tests", "得分": result.get("tests_score", 0), "满分": 15},
        {"评分项": "Treatment plan", "得分": result.get("treatment_score", 0), "满分": 15},
        {"评分项": "Patient communication", "得分": result.get("patient_communication_score", 0), "满分": 10},
        {"评分项": "Safety and red flags", "得分": result.get("safety_score", 0), "满分": 5},
    ]
    st.dataframe(pd.DataFrame(rubric_rows), use_container_width=True, hide_index=True)

    col_1, col_2 = st.columns(2)
    with col_1:
        st.subheader("做得好的地方")
        strengths = result.get("strengths") or []
        if strengths:
            for item in strengths:
                st.markdown(f"- {item}")
        else:
            st.write("暂无。")
    with col_2:
        st.subheader("需要补充")
        missing_points = result.get("missing_points") or []
        if missing_points:
            for item in missing_points:
                st.markdown(f"- {item}")
        else:
            st.write("暂无。")

    st.subheader("Model Answer")
    st.write(result.get("model_answer", ""))

    st.subheader("中文反馈")
    st.write(result.get("chinese_feedback", ""))

    st.subheader("下一步练习建议")
    st.info(result.get("next_practice_suggestion", ""))


def render_clinical_case_mode(default_text: str):
    st.session_state.setdefault("clinical_case_history", [])

    st.markdown(
        """
        <section class="hero">
            <div class="eyebrow">AI 临床病例训练</div>
            <h1 class="hero-title">Clinical Case Training</h1>
            <p class="hero-subtitle">根据课程内容生成牙科/医学临床病例，训练诊断、证据、鉴别诊断、检查、治疗计划和患者沟通。</p>
            <p class="hero-copy">完成口试或病例训练后，系统会自动分析你的薄弱知识点，并生成个性化复习计划。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="input-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">病例材料</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-copy">粘贴英文课程内容，系统会生成一个虚构但贴近课程重点的临床病例。</div>',
        unsafe_allow_html=True,
    )

    case_default_text = st.session_state.get("last_course_text", default_text)
    case_course_text = st.text_area(
        "Course Text",
        value=case_default_text,
        height=220,
        placeholder="Paste your English dental or medical course text here...",
        key="clinical_case_course_text",
    )

    control_col_1, control_col_2 = st.columns(2)
    with control_col_1:
        case_subject = st.selectbox(
            "Subject",
            ["Dentistry", "Anatomy", "Pathology", "Pharmacology", "Endodontics", "Periodontology", "Oral Surgery"],
            key="clinical_case_subject",
        )
    with control_col_2:
        case_difficulty = st.selectbox(
            "Difficulty",
            ["easy", "medium", "hard"],
            index=1,
            key="clinical_case_difficulty",
        )

    if st.button("Generate Clinical Case", type="primary", use_container_width=True):
        if not case_course_text.strip():
            st.error("请先粘贴英文课程内容。")
        else:
            try:
                with st.spinner("正在生成临床病例..."):
                    st.session_state["clinical_case_data"] = generate_clinical_case(
                        case_course_text,
                        case_subject,
                        case_difficulty,
                    )
                    st.session_state["clinical_case_result"] = None
                    st.session_state["last_course_text"] = case_course_text
                st.success("临床病例已生成。")
            except ClinicalCaseConfigError as exc:
                st.error(str(exc))
            except ClinicalCaseJSONError as exc:
                st.error("DeepSeek 返回了无效 JSON。下面是原始输出，方便调试：")
                st.code(exc.raw_output)
            except Exception as exc:
                st.error(f"生成临床病例失败：{exc}")

    case_data = st.session_state.get("clinical_case_data")
    if case_data:
        st.markdown("### Clinical Case")
        st.subheader(case_data.get("case_title", "Clinical Case"))

        case_col_1, case_col_2 = st.columns(2)
        with case_col_1:
            st.markdown("**Patient Info**")
            st.write(case_data.get("patient_info", ""))
            st.markdown("**Chief Complaint**")
            st.write(case_data.get("chief_complaint", ""))
            st.markdown("**History**")
            st.write(case_data.get("history", ""))
        with case_col_2:
            st.markdown("**Clinical Findings**")
            st.write(case_data.get("clinical_findings", ""))
            st.markdown("**Radiographic Findings**")
            st.write(case_data.get("radiographic_findings", ""))

        st.markdown("### Questions")
        for index, question in enumerate(case_data.get("questions", []), start=1):
            st.markdown(f"{index}. {question}")

        with st.expander("查看 expected diagnosis / expected points / red flags"):
            st.markdown("**Expected Diagnosis**")
            st.write(case_data.get("expected_diagnosis", ""))
            st.markdown("**Expected Points**")
            for item in case_data.get("expected_points", []):
                st.markdown(f"- {item}")
            st.markdown("**Red Flags**")
            for item in case_data.get("red_flags", []):
                st.markdown(f"- {item}")

        student_answer = st.text_area(
            "Your Clinical Reasoning Answer",
            height=220,
            placeholder=(
                "Answer in English. You can organize it as: diagnosis, evidence, "
                "differentials, tests, treatment plan, patient explanation."
            ),
            key="clinical_case_answer",
        )

        if st.button("Submit Case Answer", type="primary", use_container_width=True):
            if not student_answer.strip():
                st.error("请先输入你的英文病例分析。")
            else:
                try:
                    with st.spinner("正在批改病例分析..."):
                        result = grade_clinical_case(case_data, student_answer, case_subject)
                    st.session_state["clinical_case_result"] = result
                    attempt = {
                        "subject": case_subject,
                        "difficulty": case_difficulty,
                        "case_title": case_data.get("case_title", ""),
                        "answer": student_answer,
                        "result": result,
                    }
                    st.session_state["clinical_case_history"].insert(0, attempt)
                    st.session_state["clinical_case_history"] = st.session_state["clinical_case_history"][:10]
                except ClinicalCaseConfigError as exc:
                    st.error(str(exc))
                except ClinicalCaseJSONError as exc:
                    st.error("DeepSeek 返回了无效 JSON。下面是原始输出，方便调试：")
                    st.code(exc.raw_output)
                except Exception as exc:
                    st.error(f"批改失败：{exc}")

    if st.session_state.get("clinical_case_result"):
        render_clinical_case_grade(st.session_state["clinical_case_result"])

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 最近病例训练记录")
    history = st.session_state.get("clinical_case_history", [])
    if not history:
        st.info("还没有病例训练记录。生成病例并提交回答后，会在这里保存最近记录。")
    else:
        for index, attempt in enumerate(history[:5], start=1):
            result = attempt.get("result", {})
            label = f"{index}. {attempt.get('case_title') or attempt.get('subject')} - {result.get('score', 0)}/100 ({result.get('level', '')})"
            with st.expander(label):
                st.markdown(f"**Subject:** {attempt.get('subject', '')}")
                st.markdown(f"**Your Answer:** {attempt.get('answer', '')}")
                st.markdown(f"**Chinese Feedback:** {result.get('chinese_feedback', '')}")

    st.markdown(
        """
        <div class="footer">
            Clinical Case Training 是 DentPilot AI 的文本病例训练模式，用于练习临床思维，不替代真实医疗建议。
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_weakness_analysis_mode():
    oral_history = st.session_state.get("oral_exam_history", [])
    clinical_history = st.session_state.get("clinical_case_history", [])

    st.markdown(
        """
        <section class="hero">
            <div class="eyebrow">AI 弱点分析</div>
            <h1 class="hero-title">Weakness Analysis</h1>
            <p class="hero-subtitle">根据口试和临床病例训练记录，找出强项、弱点、可能原因，并生成 3 天复习计划。</p>
            <p class="hero-copy">完成口试或病例训练后，系统会自动分析你的薄弱知识点，并生成个性化复习计划。</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="input-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">练习记录</div>', unsafe_allow_html=True)

    metric_col_1, metric_col_2 = st.columns(2)
    metric_col_1.metric("Written Exam Attempts", len(oral_history))
    metric_col_2.metric("Clinical Case Attempts", len(clinical_history))

    if not oral_history and not clinical_history:
        st.info("Please complete at least one oral exam or clinical case first.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if st.button("Analyze My Weaknesses", type="primary", use_container_width=True):
        try:
            with st.spinner("正在分析你的练习弱点..."):
                st.session_state["weakness_analysis_result"] = analyze_weaknesses(
                    oral_history,
                    clinical_history,
                )
            st.success("弱点分析已生成。")
        except WeaknessAnalysisConfigError as exc:
            st.error(str(exc))
        except WeaknessAnalysisJSONError as exc:
            st.error("DeepSeek 返回了无效 JSON。下面是原始输出，方便调试：")
            st.code(exc.raw_output)
        except Exception as exc:
            st.error(f"弱点分析失败：{exc}")

    result = st.session_state.get("weakness_analysis_result")
    if result:
        st.markdown("### Overall Summary")
        st.write(result.get("overall_summary", ""))

        col_1, col_2 = st.columns(2)
        with col_1:
            st.subheader("Strong Areas")
            for item in result.get("strong_areas", []):
                st.markdown(f"- {item}")
        with col_2:
            st.subheader("Weak Areas")
            for item in result.get("weak_areas", []):
                st.markdown(f"- {item}")

        st.subheader("Likely Reasons")
        for item in result.get("likely_reasons", []):
            st.markdown(f"- {item}")

        st.subheader("Topic Breakdown")
        topic_breakdown = result.get("topic_breakdown", [])
        if topic_breakdown:
            st.dataframe(pd.DataFrame(topic_breakdown), use_container_width=True, hide_index=True)
        else:
            st.info("暂无 topic breakdown。")

        st.subheader("Three-Day Study Plan")
        for day_plan in result.get("three_day_plan", []):
            with st.expander(f"Day {day_plan.get('day')}: {day_plan.get('focus', '')}", expanded=True):
                for task in day_plan.get("tasks", []):
                    st.markdown(f"- {task}")

        with st.expander("Next Practice Suggestions"):
            st.markdown("**Next Oral Questions**")
            for item in result.get("next_oral_questions", []):
                st.markdown(f"- {item}")
            st.markdown("**Next Case Topics**")
            for item in result.get("next_case_topics", []):
                st.markdown(f"- {item}")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="footer">
            Weakness Analysis 会根据当前会话练习记录生成学习建议；刷新或重新开启会话后，临时记录可能会清空。
        </div>
        """,
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown("## 🦷 DentPilot AI")
    st.caption("面向中国留学生的英授牙科学习助手")
    st.markdown("---")

    mode = st.radio(
        "学习模式",
        ["Study Pack", "AI Written Exam", "Clinical Case", "Weakness Analysis", "Realtime Oral Exam"],
        format_func={
            "Study Pack": "Study Pack / 复习包",
            "AI Written Exam": "AI Written Exam / 笔试训练",
            "Clinical Case": "Clinical Case / 临床病例",
            "Weakness Analysis": "Weakness Analysis / 弱点分析",
            "Realtime Oral Exam": "🎙️ Realtime Oral Exam / 实时口试",
        }.get,
    )

    mode_descriptions = {
        "Study Pack": "上传英文课件或 PDF，生成中文讲解、术语、Quiz、Anki 和 PDF 复习包。",
        "AI Written Exam": "用英文答题，练习考点覆盖、表达结构和书面考试思路。",
        "Clinical Case": "通过临床病例训练诊断、证据、检查、治疗计划和患者沟通。",
        "Weakness Analysis": "根据练习记录分析薄弱点，并生成 3 天复习计划。",
        "Realtime Oral Exam": "和 AI 牙科教授实时口试，练习英文回答、追问和考官反馈。",
    }

    st.markdown("### 当前模式")
    st.write(mode_descriptions.get(mode, "DentPilot AI 学习训练模式。"))

    if mode != "Realtime Oral Exam":
        st.markdown("---")
        if os.getenv("DEEPSEEK_API_KEY"):
            st.caption("AI 服务已连接")
        else:
            st.caption("AI 服务未配置 · 将使用本地备用模式")


if mode == "AI Written Exam":
    render_oral_exam_mode(sample)
    st.stop()

if mode == "Clinical Case":
    render_clinical_case_mode(sample)
    st.stop()

if mode == "Weakness Analysis":
    render_weakness_analysis_mode()
    st.stop()

if mode == "Realtime Oral Exam":
    render_realtime_oral_exam_page()
    st.stop()


st.markdown(
    """
    <section class="hero">
        <div class="eyebrow">英授牙科课程学习助手</div>
        <h1 class="hero-title">DentPilot AI</h1>
        <p class="hero-subtitle">AI Study Assistant for English-Taught Dental Students</p>
        <p class="hero-copy">为中国留学生设计：把英文 lecture、PDF、PPT 和教材段落整理成可复习的中文讲解、牙科术语、自测题、Anki 卡片和 PDF 复习包。</p>
        <div class="hero-metrics">
            <div class="metric-pill">
                <div class="metric-value">中文</div>
                <div class="metric-label">先理解，再背诵</div>
            </div>
            <div class="metric-pill">
                <div class="metric-value">自测</div>
                <div class="metric-label">检查概念是否掌握</div>
            </div>
            <div class="metric-pill">
                <div class="metric-value">Anki</div>
                <div class="metric-label">导出 CSV 复习卡片</div>
            </div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">✦</div>
            <div class="feature-title">中文讲解</div>
            <div class="feature-copy">把密集的英文牙科内容转成适合中国学生理解的中文复习笔记。</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">⌁</div>
            <div class="feature-title">牙科术语表</div>
            <div class="feature-copy">匹配课程关键词，建立中英文术语和定义之间的联系。</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">?</div>
            <div class="feature-title">Quiz 自测</div>
            <div class="feature-copy">检查定义、机制链、临床意义和高频考点是否真正掌握。</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">↓</div>
            <div class="feature-title">复习资料导出</div>
            <div class="feature-copy">导出 Anki CSV 和 PDF 复习包，方便考前整理和间隔复习。</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="input-panel">', unsafe_allow_html=True)
st.markdown('<div class="section-label">生成复习包</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-copy">上传 PDF，或粘贴英文牙科 lecture、教材段落、PPT 文本。</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="example-grid">
        <div class="example-card">
            <div class="example-title">示例输入</div>
            <div class="example-copy">{sample}</div>
        </div>
        <div class="workflow-card">
            <div class="example-title">生成内容</div>
            <div class="example-copy">1. 中文讲解<br>2. 术语表<br>3. Quiz 自测<br>4. Anki CSV<br>5. PDF 复习包</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_pdf = st.file_uploader(
    "上传 PDF 课程资料",
    type=["pdf"],
    help="支持英文 lecture PDF、教材节选或课件讲义。可选中文本 PDF 的提取效果最好。",
)

pdf_text = ""
if uploaded_pdf is not None:
    try:
        with st.spinner("Extracting text from PDF..."):
            pdf_text, page_count = extract_pdf_text(uploaded_pdf)
        if pdf_text.strip():
            st.success(f"已从 PDF 的 {page_count} 页中提取文本。生成前你仍然可以编辑。")
        else:
            st.warning("没有从这个 PDF 中提取到可选中文本。如果这是扫描版 PDF，需要先做 OCR。")
    except Exception as exc:
        st.error(f"无法提取这个 PDF 的文本：{exc}")

text = st.text_area(
    "英文牙科 / 医学课程内容",
    value=pdf_text or sample,
    height=220,
    placeholder="在这里粘贴英文牙科 lecture、PPT 或教材内容...",
)
st.session_state["last_course_text"] = text

subject = st.selectbox(
    "科目",
    [
        "Dentistry",
        "Endodontics",
        "Periodontology",
        "Oral Surgery",
        "Oral Pathology",
        "Dental Anatomy",
        "Pharmacology",
        "General Pathology",
    ],
    key="study_pack_subject",
)
if not subject:
    subject = "Dentistry"

col_a, col_b = st.columns([1.25, 3.75], vertical_alignment="center")
with col_a:
    generate = st.button("生成复习包", type="primary", use_container_width=True)
with col_b:
    st.caption("建议先用一小段 lecture/PPT 文本测试，结果会更清晰。")

st.markdown("</div>", unsafe_allow_html=True)


if generate:
    if not text.strip():
        st.error("请先粘贴英文课程内容或上传 PDF。")
        st.stop()

    pack = generate_study_pack(text, subject)

    st.markdown('<div class="result-wrap">', unsafe_allow_html=True)
    st.markdown("### 复习包")
    status_message = pack.get("status_message")
    if pack.get("mode") == "fallback":
        st.warning(status_message or "当前使用本地备用模式。")
    elif status_message:
        st.success(status_message)

    pdf_bytes = build_study_pack_pdf(pack, subject)
    st.download_button(
        "导出 PDF 复习包",
        pdf_bytes,
        "dentpilot_study_pack.pdf",
        "application/pdf",
        use_container_width=True,
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["中文讲解", "术语表", "Quiz 自测", "Anki 卡片", "考前总结"]
    )

    with tab1:
        st.subheader("中文讲解")
        st.write(pack["chinese_explanation"])
        st.subheader("核心概念")
        for item in pack["key_concepts"]:
            st.markdown(f"- {item}")

    with tab2:
        st.subheader("中英医学术语表")
        if pack["glossary"]:
            df_terms = pd.DataFrame(pack["glossary"])
            st.dataframe(df_terms, use_container_width=True)
            csv_terms = df_terms.to_csv(index=False).encode("utf-8-sig")
            st.download_button("下载术语表 CSV", csv_terms, "glossary.csv", "text/csv")
        else:
            st.info("没有匹配到内置术语。你可以在 glossary.py 里继续添加。")

    with tab3:
        st.subheader("自测题")
        for i, q in enumerate(pack["quiz"], start=1):
            st.markdown(f"**Q{i}. {q['question']}**")
            for option in q["options"]:
                st.write(f"- {option}")
            with st.expander("查看答案与中文解析"):
                st.write(f"答案：{q['answer']}")
                st.write(q["explanation_zh"])

    with tab4:
        st.subheader("Anki 卡片")
        df_cards = pd.DataFrame(pack["flashcards"])
        st.dataframe(df_cards, use_container_width=True)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Front", "Back", "Tags"])
        for card in pack["flashcards"]:
            writer.writerow([card["front"], card["back"], f"medstudy::{subject}::{card['type']}"])
        st.download_button(
            "下载 Anki CSV",
            output.getvalue().encode("utf-8-sig"),
            "medstudy_anki_cards.csv",
            "text/csv",
        )

    with tab5:
        st.subheader("考前总结")
        st.write(pack["exam_summary"])
        st.info("真实商业版可以在这里加入：PDF 导出、课程文件夹、错题本、会员限制。")
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("点击“生成复习包”开始。")


st.markdown(
    """
    <div class="footer">
        DentPilot AI 帮助英授牙科留学生把英文课程资料整理成中文讲解、术语复习、Quiz 自测、Anki 卡片和 PDF 复习包。
    </div>
    """,
    unsafe_allow_html=True,
)

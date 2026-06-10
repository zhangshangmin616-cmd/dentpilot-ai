import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any

from dotenv import load_dotenv
from openai import OpenAI

from glossary import STARTER_GLOSSARY


load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", clean_text(text))
    return [p.strip() for p in parts if p.strip()]


def find_terms(text: str) -> List[Dict[str, str]]:
    """
    本地术语库匹配：
    接入 AI 后，它不是主要生成器，只是用来给 AI 一个标准术语参考。
    """
    lower = text.lower()
    hits = []
    for term, data in STARTER_GLOSSARY.items():
        if term in lower:
            hits.append({
                "english": term,
                "chinese": data.get("zh", ""),
                "definition": data.get("definition", ""),
                "chinese_explanation": data.get("explanation_zh", ""),
                "category": data.get("category", ""),
            })
    return hits


def subject_focus_note(subject: str) -> str:
    subject_key = (subject or "").strip().lower()
    if subject_key == "orthodontics":
        return (
            "Orthodontics focus: malocclusion, occlusion, cephalometrics, orthodontic diagnosis, "
            "appliances, tooth movement, biomechanics, retention, and relapse prevention."
        )
    if subject_key == "preventive dentistry":
        return (
            "Preventive Dentistry focus: caries prevention, fluoride, plaque control, oral hygiene, "
            "diet counseling, sealants, epidemiology, risk assessment, and prevention programs."
        )
    if subject_key == "microbiology":
        return (
            "Microbiology focus: bacterial structure and classification, Gram-positive and Gram-negative bacteria, "
            "acid-fast bacteria, spores and capsules, bacterial genetics, growth and culture, sterilization and "
            "disinfection, antibiotics and resistance, viruses, fungi, parasites, host-microbe interaction, "
            "immunity and infection, oral microbiology, dental plaque biofilm, caries-related microorganisms, "
            "periodontal pathogens, opportunistic infections, and laboratory diagnosis. Ask about definition, "
            "classification, structure, pathogenesis, virulence factors, transmission, diagnosis, prevention, "
            "sterilization/disinfection, antimicrobial treatment, and oral clinical relevance. Do not force "
            "Microbiology topics into dental procedure templates."
        )
    return "Use the selected subject and course text as the main scope."


def local_fallback_study_pack(text: str, subject: str, error_message: str = "") -> Dict[str, Any]:
    """
    如果 DeepSeek API Key 没配置、余额不足、网络失败，就返回本地备用版本。
    这样网页不会直接崩掉。
    """
    text = clean_text(text)
    terms = find_terms(text)

    if not terms:
        terms = []

    is_balance_error = "insufficient balance" in error_message.lower() or "402" in error_message
    if is_balance_error:
        status_message = "AI 服务暂时不可用，当前已自动切换到本地备用模式。请稍后再试或联系管理员处理。"
    elif error_message:
        status_message = "AI 服务暂时不可用，当前已自动切换到本地备用模式。"
    else:
        status_message = "当前使用本地备用模式。"

    chinese_explanation = (
        "当前系统使用了本地备用生成模式。\n\n"
        "本地模式只能根据 glossary.py 里的术语做简单匹配，中文讲解、题目和考前总结不会像 AI 版本那么完整。\n\n"
    )

    if terms:
        chinese_explanation += "识别到的重点术语如下：\n"
        for t in terms[:8]:
            chinese_explanation += f"- {t['english']}：{t['chinese']}。{t['chinese_explanation']}\n"
    else:
        chinese_explanation += "暂未匹配到内置术语。请检查输入文本，或稍后重新生成。"

    quiz = []
    for t in terms[:6]:
        quiz.append({
            "question": f"What is the Chinese meaning of '{t['english']}'?",
            "options": [t["chinese"], "牙槽骨", "牙龈退缩", "根尖周脓肿"],
            "answer": t["chinese"],
            "explanation_zh": f"{t['english']} 常译为“{t['chinese']}”。{t['chinese_explanation']}",
        })

    if not quiz:
        quiz.append({
            "question": "What is the first step when studying a dense English medical paragraph?",
            "options": ["Extract key terms", "Ignore definitions", "Only translate word by word", "Skip the paragraph"],
            "answer": "Extract key terms",
            "explanation_zh": "医学英文材料应先提取术语、定义、机制和临床意义，再进行复习。",
        })

    flashcards = []
    for t in terms[:10]:
        flashcards.append({
            "front": f"What is {t['english']}?",
            "back": f"{t['definition']}\n中文：{t['chinese']}。{t['chinese_explanation']}",
            "type": "term",
        })

    return {
        "mode": "fallback",
        "status_message": status_message,
        "subject": subject,
        "chinese_explanation": chinese_explanation,
        "key_concepts": [
            "识别英文医学材料中的核心术语。",
            "理解疾病、机制、解剖结构和治疗原则之间的关系。",
            "把内容整理成 Quiz 和 Anki 卡片进行复习。",
        ],
        "exam_summary": (
            "考前重点：掌握核心术语的英文定义、中文含义、机制链、临床意义和常见考法。"
            "当前为本地备用模式，建议稍后重新生成。"
        ),
        "glossary": terms,
        "quiz": quiz,
        "flashcards": flashcards,
    }


def build_prompt(text: str, subject: str, matched_terms: List[Dict[str, str]]) -> str:
    """
    构建给 DeepSeek 的提示词。
    要求它必须返回 JSON，方便 Streamlit 页面读取。
    """
    schema_example = {
        "subject": subject,
        "chinese_explanation": "分段中文讲解，要求完整、适合中国英授医学生理解。",
        "key_concepts": [
            "核心概念1",
            "核心概念2",
            "核心概念3"
        ],
        "exam_summary": "考前总结，包含必背点、机制链、易混点和答题模板。",
        "glossary": [
            {
                "english": "medical term",
                "chinese": "中文术语",
                "definition": "English definition",
                "chinese_explanation": "中文解释",
                "category": "Dentistry / Medicine / Anatomy / Pathology"
            }
        ],
        "quiz": [
            {
                "question": "English multiple choice question",
                "options": ["A. option", "B. option", "C. option", "D. option"],
                "answer": "A. option",
                "explanation_zh": "中文解析，解释为什么选这个答案，以及其他选项为什么不对。"
            }
        ],
        "flashcards": [
            {
                "front": "Question side of Anki card",
                "back": "Answer side with Chinese explanation",
                "type": "term | concept | exam"
            }
        ]
    }

    matched_terms_text = json.dumps(matched_terms[:20], ensure_ascii=False, indent=2)

    prompt = f"""
你是 DentPilot AI，一个给中国英授医学/口腔学生使用的双语学习助手。

你的任务：
把用户提供的英文医学/口腔课程内容，转换成适合复习的中文学习包。

用户专业方向：
{subject}

本地术语库已匹配到的参考术语：
Subject focus:
{subject_focus_note(subject)}

{matched_terms_text}

用户输入的英文课程内容：
{text}

请严格遵守以下要求：

1. 必须输出合法 JSON，不要输出 Markdown，不要使用 ```json 代码块。
2. chinese_explanation 要完整，不要只翻译一句话。
3. chinese_explanation 需要包括：
   - 这段内容在讲什么
   - 重要术语解释
   - 机制链或因果关系
   - 临床意义
   - 考试可能怎么考
4. key_concepts 至少 5 条。
5. glossary 至少 8 条；如果原文术语少，可以从原文相关内容中提取概念性术语。
6. quiz 至少 8 道题，尽量用英文出题。
7. quiz 每道题必须包含：
   - question
   - options
   - answer
   - explanation_zh
8. explanation_zh 要解释为什么答案正确，不要只写答案。
9. flashcards 至少 12 张，适合导入 Anki。
10. exam_summary 要像考前速记资料，包括：
    - 必背术语
    - 机制链
    - 易混点
    - 简答题答题模板
    - 考前 5 分钟速记
11. 不要编造真实患者诊断，不要替代医生判断。这里只做学习辅助。

请按照下面这个 JSON schema 返回：

{json.dumps(schema_example, ensure_ascii=False, indent=2)}
"""
    return prompt


def safe_json_loads(content: str) -> Dict[str, Any]:
    """
    尽量稳地解析模型返回。
    """
    content = content.strip()

    if content.startswith("```"):
        content = re.sub(r"^```json", "", content, flags=re.IGNORECASE).strip()
        content = re.sub(r"^```", "", content).strip()
        content = re.sub(r"```$", "", content).strip()

    return json.loads(content)


def normalize_document_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text_into_sections(text: str) -> List[Dict[str, Any]]:
    """Public helper used by Study Pack: split by detected questions/headings or chunk long text."""
    return detect_exam_sections(text)


def build_sections_from_markers(
    normalized: str,
    markers: List[re.Match],
    detected_by: str,
) -> List[Dict[str, Any]]:
    sections = []
    for fallback_index, marker in enumerate(markers, start=1):
        number = int(marker.group("number"))
        body_start = marker.end()
        body_end = markers[fallback_index].start() if fallback_index < len(markers) else len(normalized)
        body = normalized[body_start:body_end].strip()
        first_line = body.split("\n", 1)[0].strip()
        title = re.sub(r"\s+", " ", first_line)[:120] or f"Question {number}"
        sections.append({
            "number": number,
            "title": title,
            "text": body,
            "detected_by": detected_by,
            "fallback_index": fallback_index,
        })
    return sections


def longest_sequential_marker_run(markers: List[re.Match]) -> List[re.Match]:
    if len(markers) < 2:
        return []

    best_run: List[re.Match] = []
    current_run: List[re.Match] = []
    previous_number: int | None = None

    for marker in markers:
        number = int(marker.group("number"))
        if previous_number is not None and number == previous_number:
            continue
        if previous_number is None or number == previous_number + 1:
            current_run.append(marker)
        elif number == 1:
            current_run = [marker]
        else:
            if len(current_run) > len(best_run):
                best_run = current_run
            current_run = [marker]
        previous_number = number

    if len(current_run) > len(best_run):
        best_run = current_run

    return best_run if len(best_run) >= 2 else []


def detect_exam_sections(text: str, expected_count: int | None = None) -> List[Dict[str, Any]]:
    """
    检测考试题/章节。优先识别 1. / 1) / Question 1 这类编号。
    PDF/DOCX 提取后题号可能不在行首，所以这里同时支持内联连续编号。
    """
    normalized = normalize_document_text(text)
    if not normalized:
        return []

    detection_patterns = [
        (
            "line_numbered_question",
            re.compile(r"(?m)^\s*(?P<number>\d{1,3})[\.\)]\s+(?=\S)"),
        ),
        (
            "inline_numbered_question",
            re.compile(r"(?<![\w.])(?P<number>\d{1,3})[\.\)]\s+(?=\S)"),
        ),
        (
            "line_plain_number_question",
            re.compile(r"(?m)^\s*(?P<number>\d{1,3})\s+(?=\S)"),
        ),
        (
            "named_heading",
            re.compile(
                r"(?im)^\s*(?:Question|Q|Topic|Chapter|Section)\s+(?P<number>\d{1,3})[:\.\)]?\s+(?=\S)"
            ),
        ),
        (
            "inline_named_heading",
            re.compile(
                r"(?i)(?<!\w)(?:Question|Q|Topic|Chapter|Section)\s+(?P<number>\d{1,3})[:\.\)]?\s+(?=\S)"
            ),
        ),
    ]

    best_sections: List[Dict[str, Any]] = []
    for detected_by, pattern in detection_patterns:
        markers = list(pattern.finditer(normalized))
        marker_run = longest_sequential_marker_run(markers)
        if not marker_run:
            continue
        sections = build_sections_from_markers(normalized, marker_run, detected_by)
        if expected_count and len(sections) == expected_count:
            return sections
        if len(sections) > len(best_sections):
            best_sections = sections

    if best_sections:
        return best_sections

    old_numbered_pattern = re.compile(
        r"(?ms)^\s*(?P<number>\d{1,3})[\.\)]\s+(.+?)(?=^\s*\d{1,3}[\.\)]\s+|\Z)"
    )
    numbered_matches = list(old_numbered_pattern.finditer(normalized))
    if len(numbered_matches) >= 2:
        sections = []
        for fallback_index, match in enumerate(numbered_matches, start=1):
            number = int(match.group("number"))
            body = match.group(2).strip()
            first_line = body.split("\n", 1)[0].strip()
            title = re.sub(r"\s+", " ", first_line)[:120] or f"Question {number}"
            sections.append({
                "number": number,
                "title": title,
                "text": body,
                "detected_by": "numbered_question",
                "fallback_index": fallback_index,
            })
        return sections

    heading_pattern = re.compile(
        r"(?ms)^\s*(?:Question|Q|Topic|Chapter|Section)\s+(?P<number>\d{1,3})[:\.\)]?\s+(.+?)(?=^\s*(?:Question|Q|Topic|Chapter|Section)\s+\d{1,3}[:\.\)]?\s+|\Z)",
        re.IGNORECASE,
    )
    heading_matches = list(heading_pattern.finditer(normalized))
    if len(heading_matches) >= 2:
        sections = []
        for fallback_index, match in enumerate(heading_matches, start=1):
            number = int(match.group("number"))
            body = match.group(2).strip()
            first_line = body.split("\n", 1)[0].strip()
            sections.append({
                "number": number,
                "title": re.sub(r"\s+", " ", first_line)[:120] or f"Question {number}",
                "text": body,
                "detected_by": "heading",
                "fallback_index": fallback_index,
            })
        return sections

    # 没有明确题号时，按长度切块，并保留 overlap，至少保证后半部分不会消失。
    chunk_size = 8500
    overlap = 500
    chunks: List[str] = []
    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > chunk_size:
            chunks.append(current.strip())
            tail = current[-overlap:] if overlap and len(current) > overlap else current
            current = f"{tail}\n\n{paragraph}".strip()
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current.strip())

    if not chunks:
        for start in range(0, len(normalized), max(1, chunk_size - overlap)):
            chunk = normalized[start:start + chunk_size].strip()
            if chunk:
                chunks.append(chunk)

    return [
        {
            "number": index,
            "title": f"Section {index}",
            "text": chunk,
            "detected_by": "length_chunk",
            "fallback_index": index,
        }
        for index, chunk in enumerate(chunks, start=1)
    ]


def depth_settings(depth: str) -> Dict[str, Any]:
    settings = {
        "快速总结": {
            "mode_name": "精简版",
            "detail": "concise preview, but still one module per detected section",
            "max_section_chars": 6000,
            "max_tokens": 1800,
        },
        "标准复习包": {
            "mode_name": "标准版",
            "detail": "balanced exam-focused notes for every section",
            "max_section_chars": 8500,
            "max_tokens": 2600,
        },
        "考前冲刺包": {
            "mode_name": "考前冲刺版",
            "detail": "high-yield points, common mistakes, oral exam framing",
            "max_section_chars": 8000,
            "max_tokens": 2400,
        },
        "详细逐题版": {
            "mode_name": "详细版",
            "detail": "cover as much material as possible for each question or section",
            "max_section_chars": 10000,
            "max_tokens": 3600,
        },
    }
    return settings.get(depth, settings["标准复习包"])


def ensure_list(value, fallback: List[str] | None = None) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return fallback or []
    return [value]


def build_section_fallback_module(section: Dict[str, Any], subject: str, error_message: str = "") -> Dict[str, Any]:
    section_text = clean_text(section.get("text", ""))
    terms = find_terms(section_text)
    title = section.get("title") or f"Section {section.get('number', '')}"
    if terms:
        must_know = [
            f"Define {term['english']} and explain its Chinese meaning: {term['chinese']}."
            for term in terms[:4]
        ]
    else:
        must_know = [
            f"能够用英文解释本题主题：{title}",
            "说明核心定义、机制、临床意义和考试常见问法。",
            "用结构化短答案回答，而不是只背零散词汇。",
        ]

    quiz = [
        {
            "question_type": "mcq",
            "question": f"Which point is most important when answering an oral exam question about {title}?",
            "options": ["A. Definition and mechanism", "B. Ignore clinical relevance", "C. Only translate words", "D. Skip examples"],
            "answer": "A. Definition and mechanism",
            "explanation_zh": "口试回答应优先覆盖定义、机制和临床意义。",
        },
        {
            "question_type": "mcq",
            "question": f"What should you avoid when discussing {title}?",
            "options": ["A. Structured answer", "B. Common mistakes", "C. Vague one-sentence answer", "D. Key terms"],
            "answer": "C. Vague one-sentence answer",
            "explanation_zh": "本地备用模式仍提醒你避免空泛回答。",
        },
        {
            "question_type": "oral",
            "question": f"Explain {title} as if you are answering a dental oral exam.",
            "options": [],
            "answer": "Use definition, mechanism, clinical relevance, and one example.",
            "explanation_zh": "这是一道口试题，重点是英文组织能力。",
        },
        {
            "question_type": "short_answer",
            "question": f"Write a short exam answer template for {title}.",
            "options": [],
            "answer": "Definition -> key mechanism -> clinical relevance -> common mistake.",
            "explanation_zh": "短答题需要有清晰结构。",
        },
    ]

    cards = [
        {"front": f"Term card: {title}", "back": "写出核心英文术语和中文含义。", "type": "term"},
        {"front": f"Concept card: {title}", "back": "解释定义、机制和临床意义。", "type": "concept"},
        {"front": f"Exam answer card: {title}", "back": "用 4 句英文组织口试答案。", "type": "exam"},
    ]

    return {
        "section_number": section.get("number"),
        "title": title,
        "source_excerpt": section_text[:600],
        "chinese_core_explanation": "当前使用本地备用模式。本模块根据识别到的题目/章节保留覆盖，不会只处理文件开头。",
        "must_know": must_know,
        "glossary": terms[:10],
        "common_mistakes": [
            "只说中文意思，不会用英文定义。",
            "缺少机制链或临床意义。",
            "回答太短，无法覆盖评分点。",
        ],
        "oral_exam_questions": [
            f"Define and explain the clinical relevance of {title}.",
            f"What common mistake should be avoided when answering {title}?",
        ],
        "short_answer_template": "Definition -> mechanism/pathway -> clinical relevance -> exam trap/common mistake.",
        "follow_up_questions": [
            "Can you give one clinical example?",
            "How would you explain this to a patient?",
        ],
        "quiz": quiz,
        "flashcards": cards,
        "generation_note": error_message,
    }


def build_section_prompt(
    section: Dict[str, Any],
    subject: str,
    depth: str,
    matched_terms: List[Dict[str, str]],
) -> str:
    settings = depth_settings(depth)
    raw_section_text = str(section.get("text", ""))
    max_chars = int(settings["max_section_chars"])
    if len(raw_section_text) > max_chars:
        head_chars = max_chars - 1800
        tail_chars = 1500
        section_text = (
            raw_section_text[:head_chars]
            + "\n\n[Middle omitted only because this section is very long; preserve all detected sections.]\n\n"
            + raw_section_text[-tail_chars:]
        )
    else:
        section_text = raw_section_text
    schema_example = {
        "title": section.get("title", ""),
        "chinese_core_explanation": "中文核心讲解，覆盖定义、机制、临床意义、考试问法。",
        "must_know": ["Must-know point 1", "Must-know point 2"],
        "glossary": [
            {
                "english": "term",
                "chinese": "中文",
                "definition": "English definition",
                "chinese_explanation": "中文解释",
                "category": "Dentistry"
            }
        ],
        "common_mistakes": ["mistake 1", "mistake 2"],
        "oral_exam_questions": ["English oral exam question 1"],
        "short_answer_template": "A concise English answer template.",
        "follow_up_questions": ["follow-up question 1"],
        "quiz": [
            {
                "question_type": "mcq",
                "question": "English MCQ",
                "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
                "answer": "A. ...",
                "explanation_zh": "中文解析"
            },
            {
                "question_type": "oral",
                "question": "English oral exam question",
                "options": [],
                "answer": "Expected answer outline",
                "explanation_zh": "中文评分提示"
            },
            {
                "question_type": "short_answer",
                "question": "English short answer question",
                "options": [],
                "answer": "Short answer template",
                "explanation_zh": "中文解析"
            }
        ],
        "flashcards": [
            {"front": "Term card", "back": "Answer", "type": "term"},
            {"front": "Concept card", "back": "Answer", "type": "concept"},
            {"front": "Exam answer card", "back": "Answer", "type": "exam"}
        ]
    }

    return f"""
You are DentPilot AI, an exam-focused bilingual dental/medical study assistant.
You must output valid JSON only. Do not output markdown.

CRITICAL COVERAGE RULE:
You must not skip sections. If there are 28 questions, produce 28 study modules. Do not over-compress. Preserve exam coverage.

Current generation depth:
{depth} / {settings["mode_name"]}: {settings["detail"]}

Subject:
{subject}

Subject focus:
{subject_focus_note(subject)}

Detected section/question:
Question {section.get("number")}: {section.get("title")}

Reference glossary hits:
{json.dumps(matched_terms[:12], ensure_ascii=False, indent=2)}

Section text:
{section_text}

Generate one complete study module for this section only.
Requirements:
1. 中文核心讲解：解释本题考点、机制链、临床意义、考试问法。
2. 必背英文术语：提取本题相关高频术语。
3. Must-know points: at least 5 in English when possible.
4. Common mistakes: at least 3, especially mistakes Chinese English-taught dental/medical students make.
5. Likely oral exam questions: at least 3.
6. Short answer template: concise English answer structure.
7. Follow-up questions: at least 2.
8. Quiz: at least 2 MCQ, 1 oral exam question, 1 short answer question.
9. Anki cards: at least 3 cards: term card, concept card, exam answer card.
10. Keep content professional, exam-focused, and tied to this exact section.

Return this JSON schema:
{json.dumps(schema_example, ensure_ascii=False, indent=2)}
"""


def normalize_section_module(module: Dict[str, Any], section: Dict[str, Any], subject: str) -> Dict[str, Any]:
    if not isinstance(module, dict):
        module = {}
    title = str(module.get("title") or section.get("title") or f"Question {section.get('number')}")
    normalized = {
        "section_number": section.get("number"),
        "title": title,
        "source_excerpt": clean_text(section.get("text", ""))[:600],
        "chinese_core_explanation": str(module.get("chinese_core_explanation", "")),
        "must_know": [str(item) for item in ensure_list(module.get("must_know"))],
        "glossary": module.get("glossary") if isinstance(module.get("glossary"), list) else [],
        "common_mistakes": [str(item) for item in ensure_list(module.get("common_mistakes"))],
        "oral_exam_questions": [str(item) for item in ensure_list(module.get("oral_exam_questions"))],
        "short_answer_template": str(module.get("short_answer_template", "")),
        "follow_up_questions": [str(item) for item in ensure_list(module.get("follow_up_questions"))],
        "quiz": module.get("quiz") if isinstance(module.get("quiz"), list) else [],
        "flashcards": module.get("flashcards") if isinstance(module.get("flashcards"), list) else [],
    }
    if not normalized["chinese_core_explanation"]:
        normalized["chinese_core_explanation"] = "AI 已返回本模块，但缺少中文核心讲解。"
    if len(normalized["quiz"]) < 4 or len(normalized["flashcards"]) < 3:
        fallback = build_section_fallback_module(section, subject)
        normalized["quiz"] = normalized["quiz"] or fallback["quiz"]
        normalized["flashcards"] = normalized["flashcards"] or fallback["flashcards"]
    return normalized


def generate_section_module(
    client: OpenAI,
    model_name: str,
    section: Dict[str, Any],
    subject: str,
    depth: str,
) -> Dict[str, Any]:
    matched_terms = find_terms(section.get("text", ""))
    settings = depth_settings(depth)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a bilingual dental and medical exam study assistant. "
                    "You must output valid JSON only. Do not output markdown. "
                    "You preserve every detected exam section."
                ),
            },
            {
                "role": "user",
                "content": build_section_prompt(section, subject, depth, matched_terms),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.25,
        max_tokens=settings["max_tokens"],
    )
    content = response.choices[0].message.content or "{}"
    return normalize_section_module(safe_json_loads(content), section, subject)


def aggregate_modules(
    modules: List[Dict[str, Any]],
    sections: List[Dict[str, Any]],
    subject: str,
    depth: str,
    mode: str = "ai",
    status_message: str = "",
    expected_section_count: int | None = None,
) -> Dict[str, Any]:
    glossary = []
    quiz = []
    flashcards = []
    key_concepts = []
    for module in modules:
        glossary.extend(module.get("glossary", []))
        quiz.extend(module.get("quiz", []))
        flashcards.extend(module.get("flashcards", []))
        key_concepts.extend(module.get("must_know", [])[:3])

    detected_count = len(sections)
    generated_count = len(modules)
    missing_sections = [
        section.get("number")
        for section in sections
        if section.get("number") not in {module.get("section_number") for module in modules}
    ]
    coverage_percent = round((generated_count / detected_count) * 100, 1) if detected_count else 0
    coverage_report = {
        "detected_sections": detected_count,
        "generated_sections": generated_count,
        "coverage_percent": coverage_percent,
        "missing_sections": missing_sections,
        "has_missing": bool(missing_sections) or generated_count < detected_count,
        "detection_method": sections[0].get("detected_by", "") if sections else "",
        "expected_sections": expected_section_count or 0,
        "expected_mismatch": bool(expected_section_count and detected_count != expected_section_count),
        "detected_titles": [
            {
                "number": section.get("number"),
                "title": section.get("title", ""),
                "method": section.get("detected_by", ""),
            }
            for section in sections
        ],
    }

    chinese_explanation = "\n\n".join(
        f"Question {module.get('section_number')}: {module.get('title')}\n{module.get('chinese_core_explanation')}"
        for module in modules
    )
    exam_summary = (
        f"检测到 {detected_count} 个考试题/章节，已生成 {generated_count} 个复习模块，覆盖率 {coverage_percent}%。\n\n"
        "考前使用方法：先按“逐题讲解”理解每个模块，再用“口试题库”和“Quiz”检查自己是否能用英文回答。"
        "重点关注 Must-know points、Common mistakes 和 Short answer template。"
    )

    if not status_message:
        status_message = f"已按{depth_settings(depth)['mode_name']}生成逐题复习包。"

    return {
        "mode": mode,
        "status_message": status_message,
        "subject": subject,
        "generation_depth": depth,
        "study_modules": modules,
        "coverage_report": coverage_report,
        "chinese_explanation": chinese_explanation,
        "key_concepts": key_concepts,
        "exam_summary": exam_summary,
        "glossary": glossary,
        "quiz": quiz,
        "flashcards": flashcards,
    }


def normalize_study_pack(data: Dict[str, Any], subject: str, fallback_terms: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    确保返回给 app.py 的字段一定存在。
    """
    if not isinstance(data, dict):
        data = {}

    data.setdefault("subject", subject)
    data.setdefault("mode", "ai")
    data.setdefault("status_message", "AI 已成功生成复习包。")
    data.setdefault("chinese_explanation", "AI 已返回结果，但缺少中文讲解字段。")
    data.setdefault("key_concepts", [])
    data.setdefault("exam_summary", "AI 已返回结果，但缺少考前总结字段。")
    data.setdefault("glossary", fallback_terms)
    data.setdefault("quiz", [])
    data.setdefault("flashcards", [])

    if not isinstance(data["key_concepts"], list):
        data["key_concepts"] = [str(data["key_concepts"])]

    if not isinstance(data["glossary"], list):
        data["glossary"] = fallback_terms

    if not isinstance(data["quiz"], list):
        data["quiz"] = []

    if not isinstance(data["flashcards"], list):
        data["flashcards"] = []

    # 防止某些题目缺字段导致前端报错
    normalized_quiz = []
    for q in data["quiz"]:
        if not isinstance(q, dict):
            continue
        normalized_quiz.append({
            "question": str(q.get("question", "Untitled question")),
            "options": q.get("options", []),
            "answer": str(q.get("answer", "")),
            "explanation_zh": str(q.get("explanation_zh", "")),
        })
    data["quiz"] = normalized_quiz

    normalized_cards = []
    for c in data["flashcards"]:
        if not isinstance(c, dict):
            continue
        normalized_cards.append({
            "front": str(c.get("front", "")),
            "back": str(c.get("back", "")),
            "type": str(c.get("type", "concept")),
        })
    data["flashcards"] = normalized_cards

    return data


def generate_study_pack(
    text: str,
    subject: str,
    depth: str = "标准复习包",
    expected_section_count: int | None = None,
) -> Dict[str, Any]:
    """
    Streamlit 的 app.py 会调用这个函数。
    这里改成：先检测题号/章节，再逐题生成模块，避免长文后半部分被压缩丢失。
    """
    raw_text = normalize_document_text(text)

    if not raw_text:
        return local_fallback_study_pack(raw_text, subject, "没有输入文本。")

    sections = detect_exam_sections(raw_text, expected_section_count)
    if not sections:
        sections = detect_exam_sections(clean_text(raw_text), expected_section_count)

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if not api_key:
        modules = [
            build_section_fallback_module(section, subject, "AI 服务未配置。")
            for section in sections
        ]
        return aggregate_modules(
            modules,
            sections,
            subject,
            depth,
            mode="fallback",
            status_message="AI 服务未配置，当前已按章节生成本地备用复习包。",
            expected_section_count=expected_section_count,
        )

    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        modules = []
        skipped_errors = []
        for section in sections:
            try:
                modules.append(generate_section_module(client, model_name, section, subject, depth))
            except Exception as section_error:
                skipped_errors.append(f"Question {section.get('number')}: {section_error}")
                modules.append(build_section_fallback_module(section, subject, str(section_error)))

        mode = "ai" if not skipped_errors else "partial"
        if skipped_errors:
            status_message = "部分模块使用了本地备用模式，但系统仍保留了每个检测到的章节。"
        else:
            status_message = f"AI 已生成 {len(modules)} 个逐题复习模块。"
        return aggregate_modules(
            modules,
            sections,
            subject,
            depth,
            mode=mode,
            status_message=status_message,
            expected_section_count=expected_section_count,
        )

    except Exception as e:
        modules = [
            build_section_fallback_module(section, subject, str(e))
            for section in sections
        ]
        return aggregate_modules(
            modules,
            sections,
            subject,
            depth,
            mode="fallback",
            status_message="AI 服务暂时不可用，当前已按章节生成本地备用复习包。",
            expected_section_count=expected_section_count,
        )

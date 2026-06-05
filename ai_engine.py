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


def generate_study_pack(text: str, subject: str) -> Dict[str, Any]:
    """
    Streamlit 的 app.py 会调用这个函数。
    这里改成：优先调用 DeepSeek，失败则使用本地备用版本。
    """
    text = clean_text(text)

    if not text:
        return local_fallback_study_pack(text, subject, "没有输入文本。")

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if not api_key:
        return local_fallback_study_pack(
            text,
            subject,
            "AI 服务未配置。"
        )

    matched_terms = find_terms(text)

    # 为了控制成本，先限制输入长度。后面可以再做长文分段处理。
    max_chars = 15000
    text_for_ai = text[:max_chars]

    if len(text) > max_chars:
        text_for_ai += "\n\n[注意：原文过长，当前版本只处理前 15000 个字符。]"

    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a bilingual medical education assistant. "
                        "You must output valid json only. "
                        "Do not output markdown."
                    )
                },
                {
                    "role": "user",
                    "content": build_prompt(text_for_ai, subject, matched_terms)
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=6000,
        )

        content = response.choices[0].message.content or "{}"
        data = safe_json_loads(content)
        return normalize_study_pack(data, subject, matched_terms)

    except Exception as e:
        return local_fallback_study_pack(
            text,
            subject,
            str(e)
        )

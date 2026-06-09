import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


class OralExamError(Exception):
    """Base exception for the text-based oral exam simulator."""


class OralExamConfigError(OralExamError):
    """Raised when the DeepSeek API key is not configured."""


class OralExamJSONError(OralExamError):
    """Raised when the model response cannot be parsed as JSON."""

    def __init__(self, raw_output: str):
        super().__init__("DeepSeek returned invalid JSON.")
        self.raw_output = raw_output


def _get_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise OralExamConfigError("缺少 DEEPSEEK_API_KEY。请先在 .env 或云端 Secrets 中配置。")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def _get_model_name() -> str:
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"


def _safe_json_loads(content: str) -> Dict[str, Any]:
    raw_output = (content or "").strip()
    cleaned = raw_output

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"^```", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise OralExamJSONError(raw_output)
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise OralExamJSONError(raw_output)

    if not isinstance(parsed, dict):
        raise OralExamJSONError(raw_output)
    return parsed


def _as_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = minimum
    return max(minimum, min(maximum, number))


def _level_from_score(score: int) -> str:
    if score < 50:
        return "Fail"
    if score < 60:
        return "Borderline"
    if score < 75:
        return "Pass"
    if score < 90:
        return "Good"
    return "Excellent"


def _subject_focus_note(subject: str) -> str:
    subject_key = (subject or "").strip().lower()
    if subject_key == "orthodontics":
        return (
            "For Orthodontics, focus on malocclusion, occlusion, cephalometrics, "
            "orthodontic diagnosis, appliances, tooth movement, biomechanics, retention, and relapse prevention."
        )
    if subject_key == "preventive dentistry":
        return (
            "For Preventive Dentistry, focus on caries prevention, fluoride, plaque control, "
            "oral hygiene instruction, diet counseling, sealants, epidemiology, risk assessment, and prevention programs."
        )
    return ""


def _normalize_question(data: Dict[str, Any], subject: str, difficulty: str) -> Dict[str, Any]:
    allowed_difficulties = {"easy", "medium", "hard"}
    normalized_difficulty = str(data.get("difficulty", difficulty)).lower().strip()
    if normalized_difficulty not in allowed_difficulties:
        normalized_difficulty = difficulty

    return {
        "question": str(data.get("question", "")).strip(),
        "expected_points": _as_string_list(data.get("expected_points")),
        "must_mention_terms": _as_string_list(data.get("must_mention_terms")),
        "difficulty": normalized_difficulty,
        "topic": str(data.get("topic", subject)).strip(),
        "model_answer": str(data.get("model_answer", "")).strip(),
    }


def _normalize_grade(data: Dict[str, Any]) -> Dict[str, Any]:
    content_accuracy = _bounded_int(data.get("content_accuracy"), 0, 30)
    completeness = _bounded_int(data.get("completeness"), 0, 20)
    clinical_reasoning = _bounded_int(data.get("clinical_reasoning"), 0, 20)
    english_expression = _bounded_int(data.get("english_expression"), 0, 10)
    examiner_interaction = _bounded_int(data.get("examiner_interaction"), 0, 10)
    pronunciation_fluency = _bounded_int(data.get("pronunciation_fluency"), 0, 10)

    score = _bounded_int(
        data.get(
            "score",
            content_accuracy
            + completeness
            + clinical_reasoning
            + english_expression
            + examiner_interaction
            + pronunciation_fluency,
        ),
        0,
        100,
    )
    level = str(data.get("level") or _level_from_score(score)).strip()
    if level not in {"Fail", "Borderline", "Pass", "Good", "Excellent"}:
        level = _level_from_score(score)

    return {
        "score": score,
        "level": level,
        "content_accuracy": content_accuracy,
        "completeness": completeness,
        "clinical_reasoning": clinical_reasoning,
        "english_expression": english_expression,
        "examiner_interaction": examiner_interaction,
        "pronunciation_fluency": pronunciation_fluency,
        "strengths": _as_string_list(data.get("strengths")),
        "missing_points": _as_string_list(data.get("missing_points")),
        "corrected_answer": str(data.get("corrected_answer", "")).strip(),
        "chinese_feedback": str(data.get("chinese_feedback", "")).strip(),
        "follow_up_question": str(data.get("follow_up_question", "")).strip(),
    }


def generate_oral_question(course_text: str, subject: str, difficulty: str) -> Dict[str, Any]:
    course_text = (course_text or "").strip()
    if not course_text:
        raise ValueError("Course text is empty.")

    difficulty = difficulty if difficulty in {"easy", "medium", "hard"} else "medium"
    text_for_ai = course_text[:12000]
    if len(course_text) > 12000:
        text_for_ai += "\n\n[The original text was longer than 12000 characters and has been truncated.]"

    prompt = f"""
You are an experienced examiner for English-taught dental and medical students.
Create one text-based oral exam question from the course text.

Subject: {subject}
Subject focus:
{_subject_focus_note(subject) or "Use the selected subject and course text as the main scope."}

Difficulty: {difficulty}

Course text:
{text_for_ai}

Return valid JSON only. Do not use markdown. The JSON must match this schema:
{{
  "question": "A clear oral exam question in English",
  "expected_points": ["Key point 1", "Key point 2"],
  "must_mention_terms": ["term 1", "term 2"],
  "difficulty": "easy | medium | hard",
  "topic": "Short topic name",
  "model_answer": "A concise but complete model oral answer in English"
}}
"""

    response = _get_client().chat.completions.create(
        model=_get_model_name(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a dental and medical oral examiner. "
                    "You must return valid JSON only, with no markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.25,
        max_tokens=1800,
    )

    raw = response.choices[0].message.content or "{}"
    return _normalize_question(_safe_json_loads(raw), subject, difficulty)


def grade_oral_answer(question_data: Dict[str, Any], student_answer: str, subject: str) -> Dict[str, Any]:
    student_answer = (student_answer or "").strip()
    if not student_answer:
        raise ValueError("Student answer is empty.")

    prompt = f"""
You are grading a text-based oral exam answer for an English-taught dental or medical program.

Subject: {subject}

Question data:
{json.dumps(question_data, ensure_ascii=False, indent=2)}

Student answer:
{student_answer}

Use this rubric:
- Content Accuracy: 30 points
- Completeness: 20 points
- Clinical Reasoning: 20 points
- English Expression: 10 points
- Examiner Interaction: 10 points
- Pronunciation & Fluency: 10 points

For Phase 1, pronunciation_fluency must be estimated from the typed answer's clarity, coherence, and fluency.
Be fair but strict. Give practical feedback for a Chinese student preparing for an English oral exam.

Return valid JSON only. Do not use markdown. The JSON must match this schema:
{{
  "score": 0,
  "level": "Fail | Borderline | Pass | Good | Excellent",
  "content_accuracy": 0,
  "completeness": 0,
  "clinical_reasoning": 0,
  "english_expression": 0,
  "examiner_interaction": 0,
  "pronunciation_fluency": 0,
  "strengths": ["Strength 1", "Strength 2"],
  "missing_points": ["Missing point 1", "Missing point 2"],
  "corrected_answer": "A corrected oral-style answer in English",
  "chinese_feedback": "中文反馈，说明优点、扣分原因和下一步复习建议",
  "follow_up_question": "A follow-up oral exam question in English"
}}
"""

    response = _get_client().chat.completions.create(
        model=_get_model_name(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict but supportive dental and medical oral examiner. "
                    "You must return valid JSON only, with no markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=2500,
    )

    raw = response.choices[0].message.content or "{}"
    return _normalize_grade(_safe_json_loads(raw))

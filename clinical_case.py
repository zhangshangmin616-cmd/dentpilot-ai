import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


class ClinicalCaseError(Exception):
    """Base exception for the clinical case training mode."""


class ClinicalCaseConfigError(ClinicalCaseError):
    """Raised when the DeepSeek API key is not configured."""


class ClinicalCaseJSONError(ClinicalCaseError):
    """Raised when the model response cannot be parsed as JSON."""

    def __init__(self, raw_output: str):
        super().__init__("DeepSeek returned invalid JSON.")
        self.raw_output = raw_output


def _get_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ClinicalCaseConfigError("缺少 DEEPSEEK_API_KEY。请先在 .env 或云端 Secrets 中配置。")
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
            raise ClinicalCaseJSONError(raw_output)
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise ClinicalCaseJSONError(raw_output)

    if not isinstance(parsed, dict):
        raise ClinicalCaseJSONError(raw_output)
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


def _normalize_case(data: Dict[str, Any]) -> Dict[str, Any]:
    default_questions = [
        "What is the most likely diagnosis?",
        "What evidence supports your diagnosis?",
        "What differential diagnoses should be considered?",
        "What additional tests would you perform?",
        "What is your treatment plan?",
        "How would you explain this to the patient?",
    ]

    questions = _as_string_list(data.get("questions")) or default_questions

    return {
        "case_title": str(data.get("case_title", "")).strip(),
        "patient_info": str(data.get("patient_info", "")).strip(),
        "chief_complaint": str(data.get("chief_complaint", "")).strip(),
        "history": str(data.get("history", "")).strip(),
        "clinical_findings": str(data.get("clinical_findings", "")).strip(),
        "radiographic_findings": str(data.get("radiographic_findings", "")).strip(),
        "questions": questions,
        "expected_diagnosis": str(data.get("expected_diagnosis", "")).strip(),
        "expected_points": _as_string_list(data.get("expected_points")),
        "red_flags": _as_string_list(data.get("red_flags")),
    }


def _normalize_grade(data: Dict[str, Any]) -> Dict[str, Any]:
    diagnosis_score = _bounded_int(data.get("diagnosis_score"), 0, 20)
    evidence_score = _bounded_int(data.get("evidence_score"), 0, 20)
    differential_score = _bounded_int(data.get("differential_score"), 0, 15)
    tests_score = _bounded_int(data.get("tests_score"), 0, 15)
    treatment_score = _bounded_int(data.get("treatment_score"), 0, 15)
    patient_communication_score = _bounded_int(data.get("patient_communication_score"), 0, 10)
    safety_score = _bounded_int(data.get("safety_score"), 0, 5)

    score = _bounded_int(
        data.get(
            "score",
            diagnosis_score
            + evidence_score
            + differential_score
            + tests_score
            + treatment_score
            + patient_communication_score
            + safety_score,
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
        "diagnosis_score": diagnosis_score,
        "evidence_score": evidence_score,
        "differential_score": differential_score,
        "tests_score": tests_score,
        "treatment_score": treatment_score,
        "patient_communication_score": patient_communication_score,
        "safety_score": safety_score,
        "strengths": _as_string_list(data.get("strengths")),
        "missing_points": _as_string_list(data.get("missing_points")),
        "model_answer": str(data.get("model_answer", "")).strip(),
        "chinese_feedback": str(data.get("chinese_feedback", "")).strip(),
        "next_practice_suggestion": str(data.get("next_practice_suggestion", "")).strip(),
    }


def _subject_focus_note(subject: str) -> str:
    subject_key = (subject or "").strip().lower()
    if subject_key == "orthodontics":
        return (
            "For Orthodontics, focus on malocclusion, occlusion, cephalometrics, "
            "orthodontic diagnosis, appliances, tooth movement, retention, and relapse prevention."
        )
    if subject_key == "preventive dentistry":
        return (
            "For Preventive Dentistry, focus on caries prevention, fluoride, plaque control, "
            "oral hygiene instruction, diet counseling, sealants, epidemiology, prevention programs, and patient education."
        )
    return ""


def generate_clinical_case(course_text: str, subject: str, difficulty: str) -> Dict[str, Any]:
    course_text = (course_text or "").strip()
    if not course_text:
        raise ValueError("Course text is empty.")

    difficulty = difficulty if difficulty in {"easy", "medium", "hard"} else "medium"
    text_for_ai = course_text[:12000]
    if len(course_text) > 12000:
        text_for_ai += "\n\n[The original text was longer than 12000 characters and has been truncated.]"

    prompt = f"""
You are creating a beginner-friendly clinical case for English-taught dental and medical students.
Create one realistic but fictional clinical case based on the course text.
Do not include voice, audio, or speech tasks.

Subject: {subject}
Subject focus:
{_subject_focus_note(subject) or "Use the selected subject and course text as the main clinical scope."}

Difficulty: {difficulty}

Course text:
{text_for_ai}

Return valid JSON only. Do not use markdown. The JSON must match this schema:
{{
  "case_title": "Short case title",
  "patient_info": "Age, sex, and relevant background",
  "chief_complaint": "Main complaint in the patient's words",
  "history": "Relevant history",
  "clinical_findings": "Key clinical signs and examination findings",
  "radiographic_findings": "Key imaging findings or 'Not available' if not relevant",
  "questions": [
    "What is the most likely diagnosis?",
    "What evidence supports your diagnosis?",
    "What differential diagnoses should be considered?",
    "What additional tests would you perform?",
    "What is your treatment plan?",
    "How would you explain this to the patient?"
  ],
  "expected_diagnosis": "Expected diagnosis",
  "expected_points": ["Expected point 1", "Expected point 2"],
  "red_flags": ["Safety issue or red flag 1", "Safety issue or red flag 2"]
}}
"""

    response = _get_client().chat.completions.create(
        model=_get_model_name(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a dental and medical clinical tutor. "
                    "You must return valid JSON only, with no markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.35,
        max_tokens=2400,
    )

    raw = response.choices[0].message.content or "{}"
    return _normalize_case(_safe_json_loads(raw))


def grade_clinical_case(case_data: Dict[str, Any], student_answer: str, subject: str) -> Dict[str, Any]:
    student_answer = (student_answer or "").strip()
    if not student_answer:
        raise ValueError("Student answer is empty.")

    prompt = f"""
You are grading a beginner-friendly clinical case answer for an English-taught dental or medical program.

Subject: {subject}

Case data:
{json.dumps(case_data, ensure_ascii=False, indent=2)}

Student answer:
{student_answer}

Use this rubric:
- Diagnosis: 20 points
- Evidence: 20 points
- Differential diagnosis: 15 points
- Additional tests: 15 points
- Treatment plan: 15 points
- Patient communication: 10 points
- Safety and red flags: 5 points

Be fair, practical, and strict. Give feedback in Chinese for a Chinese student, but keep the model answer in English.

Return valid JSON only. Do not use markdown. The JSON must match this schema:
{{
  "score": 0,
  "level": "Fail | Borderline | Pass | Good | Excellent",
  "diagnosis_score": 0,
  "evidence_score": 0,
  "differential_score": 0,
  "tests_score": 0,
  "treatment_score": 0,
  "patient_communication_score": 0,
  "safety_score": 0,
  "strengths": [],
  "missing_points": [],
  "model_answer": "",
  "chinese_feedback": "",
  "next_practice_suggestion": ""
}}
"""

    response = _get_client().chat.completions.create(
        model=_get_model_name(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict but supportive clinical tutor. "
                    "You must return valid JSON only, with no markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=2600,
    )

    raw = response.choices[0].message.content or "{}"
    return _normalize_grade(_safe_json_loads(raw))

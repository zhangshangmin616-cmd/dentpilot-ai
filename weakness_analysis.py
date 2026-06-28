import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path(__file__).resolve().parent / ".env", override=True, encoding="utf-8-sig")


class WeaknessAnalysisError(Exception):
    """Base exception for weakness analysis."""


class WeaknessAnalysisConfigError(WeaknessAnalysisError):
    """Raised when the DeepSeek API key is not configured."""


class WeaknessAnalysisJSONError(WeaknessAnalysisError):
    """Raised when the model response cannot be parsed as JSON."""

    def __init__(self, raw_output: str):
        super().__init__("DeepSeek returned invalid JSON.")
        self.raw_output = raw_output


def _get_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise WeaknessAnalysisConfigError("缺少 DEEPSEEK_API_KEY。请先在 .env 或云端 Secrets 中配置。")
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
            raise WeaknessAnalysisJSONError(raw_output)
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise WeaknessAnalysisJSONError(raw_output)

    if not isinstance(parsed, dict):
        raise WeaknessAnalysisJSONError(raw_output)
    return parsed


def _as_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def _normalize_topic_breakdown(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []

    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        performance = str(item.get("performance", "medium")).strip().lower()
        if performance not in {"weak", "medium", "strong"}:
            performance = "medium"
        rows.append({
            "topic": str(item.get("topic", "")).strip(),
            "performance": performance,
            "reason": str(item.get("reason", "")).strip(),
            "recommended_action": str(item.get("recommended_action", "")).strip(),
        })
    return rows


def _normalize_three_day_plan(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []

    rows = []
    for index, item in enumerate(value[:3], start=1):
        if not isinstance(item, dict):
            continue
        try:
            day = int(item.get("day", index))
        except (TypeError, ValueError):
            day = index
        rows.append({
            "day": day,
            "focus": str(item.get("focus", "")).strip(),
            "tasks": _as_string_list(item.get("tasks")),
        })
    return rows


def _normalize_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "overall_summary": str(data.get("overall_summary", "")).strip(),
        "strong_areas": _as_string_list(data.get("strong_areas")),
        "weak_areas": _as_string_list(data.get("weak_areas")),
        "likely_reasons": _as_string_list(data.get("likely_reasons")),
        "topic_breakdown": _normalize_topic_breakdown(data.get("topic_breakdown")),
        "three_day_plan": _normalize_three_day_plan(data.get("three_day_plan")),
        "next_oral_questions": _as_string_list(data.get("next_oral_questions")),
        "next_case_topics": _as_string_list(data.get("next_case_topics")),
    }


def analyze_weaknesses(oral_exam_history, clinical_case_history) -> Dict[str, Any]:
    oral_exam_history = oral_exam_history or []
    clinical_case_history = clinical_case_history or []

    if not oral_exam_history and not clinical_case_history:
        raise ValueError("No oral exam or clinical case history available.")

    payload = {
        "oral_exam_history": oral_exam_history[-10:],
        "clinical_case_history": clinical_case_history[-10:],
    }

    prompt = f"""
You are DentPilot AI's learning coach for Chinese students in English-taught dental and medical programs.
Analyze the student's oral exam attempts and clinical case attempts.

History data:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Return valid JSON only. Do not use markdown.
Write feedback in clear Chinese where helpful, but keep suggested oral questions and case topics in English.
Focus on actionable weaknesses, likely reasons, topic patterns, and a realistic three-day study plan.

The JSON must match this schema:
{{
  "overall_summary": "...",
  "strong_areas": ["...", "..."],
  "weak_areas": ["...", "..."],
  "likely_reasons": ["...", "..."],
  "topic_breakdown": [
    {{
      "topic": "...",
      "performance": "weak | medium | strong",
      "reason": "...",
      "recommended_action": "..."
    }}
  ],
  "three_day_plan": [
    {{
      "day": 1,
      "focus": "...",
      "tasks": ["...", "..."]
    }},
    {{
      "day": 2,
      "focus": "...",
      "tasks": ["...", "..."]
    }},
    {{
      "day": 3,
      "focus": "...",
      "tasks": ["...", "..."]
    }}
  ],
  "next_oral_questions": ["...", "..."],
  "next_case_topics": ["...", "..."]
}}
"""

    response = _get_client().chat.completions.create(
        model=_get_model_name(),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise learning analytics coach. "
                    "You must return valid JSON only, with no markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.25,
        max_tokens=2600,
    )

    raw = response.choices[0].message.content or "{}"
    return _normalize_analysis(_safe_json_loads(raw))

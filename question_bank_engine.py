from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import hashlib
import json
import re


BANK_PATH = Path(__file__).resolve().parent / "data" / "school_question_bank.json"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "how", "in", "into", "is", "it", "its", "of", "on", "or", "the",
    "this", "that", "to", "what", "when", "where", "which", "why", "with", "you",
    "your", "describe", "explain", "discuss", "list", "give", "main", "important",
}

FOCUS_KEYWORDS: dict[str, set[str]] = {
    "definition_scope": {"definition", "define", "meaning", "scope", "concept"},
    "classification": {"classification", "classify", "types", "category", "groups"},
    "structure_function": {"structure", "function", "component", "relationship"},
    "equipment_and_tools": {"instrument", "equipment", "tools", "handpiece", "maintenance"},
    "organization_workflow": {"organization", "workflow", "office", "ergonomics", "position", "four-handed"},
    "indications_contraindications": {"indication", "contraindication", "contraindications", "suitable"},
    "clinical_steps": {"steps", "stage", "stages", "procedure", "sequence"},
    "technique_methodology": {"technique", "method", "protocol", "methodology"},
    "complications_prevention": {"complication", "complications", "prevention", "risk", "adverse"},
    "material_properties": {"material", "properties", "composition", "fluoride", "release", "setting"},
    "anatomy_landmarks": {"anatomy", "nerve", "artery", "vein", "foramen", "canal", "landmark"},
    "diagnosis_methods": {"diagnosis", "diagnostic", "differential", "signs", "symptoms", "test"},
    "treatment_principles": {"treatment", "management", "therapy", "principles", "plan"},
    "comparison": {"compare", "comparison", "difference", "advantages", "limitations"},
    "patient_communication": {"patient", "communication", "explain", "education", "advice"},
    "case_reasoning": {"case", "scenario", "patient", "clinical", "reasoning"},
    "mechanism_pathogenesis": {"mechanism", "pathogenesis", "etiology", "bacteria", "inflammation"},
    "hygiene_infection_control": {"hygiene", "infection", "asepsis", "antisepsis", "disinfection", "sterilization"},
}

SUBJECT_FOCUS_HINTS: dict[str, dict[str, Any]] = {
    "orthodontics": {
        "keywords": {
            "orthodontic", "orthodontics", "malocclusion", "occlusion", "cephalometric",
            "cephalometrics", "diagnosis", "appliance", "bracket", "aligner", "tooth movement",
            "retention", "retainer", "anchorage", "growth", "class i", "class ii", "class iii",
            "口腔正畸", "正畸", "错颌", "咬合", "头影测量", "矫治器", "牙移动", "保持",
        },
        "focus": ["diagnosis_methods", "structure_function", "treatment_principles", "technique_methodology"],
        "must_know": [
            "Classify the malocclusion or occlusal problem",
            "Explain orthodontic diagnosis, including clinical examination and cephalometric assessment when relevant",
            "Describe the appliance or biomechanical principle used for tooth movement",
            "Mention retention and relapse prevention",
        ],
        "tags": ["orthodontics", "malocclusion", "occlusion", "cephalometrics", "appliances", "tooth movement", "retention"],
    },
    "preventive dentistry": {
        "keywords": {
            "preventive dentistry", "prevention", "caries prevention", "fluoride", "plaque control",
            "oral hygiene", "diet counseling", "sealant", "sealants", "epidemiology",
            "prevention program", "risk assessment", "dmft", "dmfs", "community dentistry",
            "口腔预防", "预防", "龋病预防", "氟化物", "菌斑控制", "口腔卫生", "饮食指导",
            "窝沟封闭", "流行病学", "预防项目",
        },
        "focus": ["complications_prevention", "patient_communication", "hygiene_infection_control", "diagnosis_methods"],
        "must_know": [
            "Assess caries or oral disease risk before choosing prevention",
            "Explain fluoride, plaque control, oral hygiene instruction, and diet counseling",
            "Describe sealants or other preventive interventions when indicated",
            "Connect prevention to epidemiology, community programs, or patient education",
        ],
        "tags": ["preventive dentistry", "caries prevention", "fluoride", "plaque control", "sealants", "epidemiology"],
    },
    "microbiology": {
        "keywords": {
            "microbiology", "microbe", "microorganism", "bacteria", "bacterial", "gram positive",
            "gram negative", "acid fast", "spore", "spores", "capsule", "capsules", "genetics",
            "culture", "growth", "sterilization", "sterilisation", "disinfection", "antibiotic",
            "antimicrobial", "resistance", "virus", "viral", "fungi", "yeast", "mold", "mould",
            "protozoa", "parasite", "parasites", "host microbe", "immunity", "infection",
            "oral microbiology", "biofilm", "dental plaque", "cariogenic", "streptococcus mutans",
            "periodontal pathogen", "opportunistic infection", "laboratory diagnosis",
            "微生物", "细菌", "革兰阳性", "革兰阴性", "抗酸", "芽孢", "荚膜", "培养", "灭菌",
            "消毒", "抗生素", "耐药", "病毒", "真菌", "寄生虫", "免疫", "感染", "口腔微生物",
            "菌斑", "生物膜", "龋病相关微生物", "牙周致病菌", "机会感染", "实验室诊断",
        },
        "focus": [
            "definition_scope",
            "classification",
            "structure_function",
            "mechanism_pathogenesis",
            "hygiene_infection_control",
            "diagnosis_methods",
            "treatment_principles",
            "patient_communication",
        ],
        "must_know": [
            "Define or classify the microorganism or microbiological process",
            "Describe structure, virulence factors, transmission, and pathogenesis when relevant",
            "Explain laboratory diagnosis, culture, sterilization, disinfection, or antimicrobial resistance when relevant",
            "Connect the topic to oral microbiology, dental plaque biofilm, caries, periodontal pathogens, or opportunistic infection",
        ],
        "tags": [
            "microbiology",
            "bacteria",
            "viruses",
            "fungi",
            "sterilization",
            "disinfection",
            "antibiotic resistance",
            "oral microbiology",
            "biofilm",
            "laboratory diagnosis",
        ],
    },
}


def normalize_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def tokenize(text: Any) -> set[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9-]*|[0-9]+|[\u4e00-\u9fff]+", normalize_text(text))
    return {token for token in raw if len(token) > 1 and token not in STOPWORDS}


def _ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r";|\n|\|", value)
        return [part.strip() for part in parts if part.strip()]
    return [str(value).strip()] if str(value).strip() else []


def _ensure_dict(value: Any) -> dict[str, float]:
    if isinstance(value, dict):
        out: dict[str, float] = {}
        for key, score in value.items():
            try:
                out[str(key)] = float(score)
            except Exception:
                out[str(key)] = 0.0
        return out
    if isinstance(value, str):
        rubric: dict[str, float] = {}
        for part in re.split(r";|\n|\|", value):
            if not part.strip():
                continue
            if ":" in part:
                key, score = part.split(":", 1)
            elif "-" in part:
                key, score = part.rsplit("-", 1)
            else:
                continue
            try:
                rubric[key.strip()] = float(score.strip().replace("%", ""))
            except Exception:
                rubric[key.strip()] = 0.0
        return rubric
    return {}


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")).strip(),
        "enabled": bool(item.get("enabled", True)),
        "subject": str(item.get("subject", "")).strip(),
        "topic": str(item.get("topic", "")).strip(),
        "aliases": _ensure_list(item.get("aliases")),
        "category": str(item.get("category", "")).strip(),
        "difficulty": str(item.get("difficulty", "")).strip(),
        "source_original_questions": _ensure_list(item.get("source_original_questions")),
        "merged_question": str(item.get("merged_question", "")).strip(),
        "answer_template": _ensure_list(item.get("answer_template")),
        "must_know": _ensure_list(item.get("must_know")),
        "common_mistakes": _ensure_list(item.get("common_mistakes")),
        "scoring_rubric": _ensure_dict(item.get("scoring_rubric")),
        "follow_up_questions": _ensure_list(item.get("follow_up_questions")),
        "tags": _ensure_list(item.get("tags")),
    }


def load_school_question_bank() -> list[dict[str, Any]]:
    if not BANK_PATH.exists():
        return []
    try:
        raw = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [
        _normalize_item(item)
        for item in raw
        if isinstance(item, dict) and item.get("enabled", True) is not False
    ]


def get_question_bank_status() -> dict[str, Any]:
    relative_path = "data/school_question_bank.json"
    if not BANK_PATH.exists():
        return {
            "exists": False,
            "count": 0,
            "path": relative_path,
            "message": "学校题库文件不存在。请创建 data/school_question_bank.json。",
        }

    try:
        raw = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "count": 0,
            "path": relative_path,
            "message": f"学校题库 JSON 无法解析：{exc}",
        }

    if not isinstance(raw, list):
        return {
            "exists": True,
            "count": 0,
            "path": relative_path,
            "message": "学校题库 JSON 必须是数组格式。",
        }

    enabled_count = sum(
        1 for item in raw if isinstance(item, dict) and item.get("enabled", True) is not False
    )
    disabled_count = sum(
        1 for item in raw if isinstance(item, dict) and item.get("enabled", True) is False
    )
    if enabled_count == 0:
        return {
            "exists": True,
            "count": 0,
            "path": relative_path,
            "message": f"题库文件已存在，但当前没有启用题目。已忽略 {disabled_count} 条 disabled 模板或草稿。",
        }

    return {
        "exists": True,
        "count": enabled_count,
        "path": relative_path,
        "message": f"学校题库可用，已启用 {enabled_count} 条题目。",
    }


def _item_search_text(item: dict[str, Any]) -> str:
    return " ".join(
        [
            item.get("topic", ""),
            item.get("subject", ""),
            item.get("category", ""),
            item.get("merged_question", ""),
            " ".join(item.get("aliases", [])),
            " ".join(item.get("tags", [])),
            " ".join(item.get("must_know", [])),
            " ".join(item.get("follow_up_questions", [])),
        ]
    )


def find_relevant_school_questions(
    topic: str,
    subject: str,
    course_context: str,
    limit: int = 5,
) -> dict[str, Any]:
    bank = load_school_question_bank()
    if not bank:
        return {
            "best_match": None,
            "matches": [],
            "match_reason": "school question bank file missing or empty",
            "match_score": 0,
        }

    topic_norm = normalize_text(topic)
    subject_norm = normalize_text(subject)
    query_tokens = tokenize(topic) | tokenize(course_context)
    subject_hint = SUBJECT_FOCUS_HINTS.get(subject_norm, {})
    subject_keywords = {normalize_text(keyword) for keyword in subject_hint.get("keywords", set())}
    scored: list[dict[str, Any]] = []

    for item in bank:
        score = 0
        reasons: list[str] = []
        item_topic_norm = normalize_text(item.get("topic"))
        aliases = {normalize_text(alias) for alias in item.get("aliases", [])}
        tags = {normalize_text(tag) for tag in item.get("tags", [])}
        item_tokens = tokenize(_item_search_text(item))

        if topic_norm and item_topic_norm == topic_norm:
            score += 40
            reasons.append("exact topic match")
        elif topic_norm and (topic_norm in item_topic_norm or item_topic_norm in topic_norm):
            score += 24
            reasons.append("partial topic match")

        if topic_norm and topic_norm in aliases:
            score += 28
            reasons.append("exact alias match")

        alias_overlap = aliases.intersection(query_tokens)
        if alias_overlap:
            score += min(18, 6 * len(alias_overlap))
            reasons.append("alias keyword match")

        if subject_norm and subject_norm == normalize_text(item.get("subject")):
            score += 10
            reasons.append("subject match")

        subject_overlap = subject_keywords.intersection(item_tokens | query_tokens)
        if subject_overlap:
            score += min(18, 4 * len(subject_overlap))
            reasons.append("subject focus match")

        tag_overlap = tags.intersection(query_tokens)
        if tag_overlap:
            score += min(12, 4 * len(tag_overlap))
            reasons.append("tag match")

        overlap = query_tokens.intersection(item_tokens)
        if overlap:
            score += min(24, 3 * len(overlap))
            reasons.append("token overlap")

        if score > 0:
            scored.append(
                {
                    "item": item,
                    "score": score,
                    "reason": ", ".join(reasons) or "weak token overlap",
                }
            )

    scored.sort(key=lambda row: row["score"], reverse=True)
    matches = scored[: max(1, int(limit))]
    best = matches[0] if matches else None
    return {
        "best_match": best["item"] if best else None,
        "matches": matches,
        "match_reason": best["reason"] if best else "no school question matched",
        "match_score": best["score"] if best else 0,
    }


def infer_question_focus(item: dict[str, Any]) -> list[str]:
    text = normalize_text(_item_search_text(item))
    category = normalize_text(item.get("category"))
    topic_text = normalize_text(item.get("topic"))
    subject_text = normalize_text(item.get("subject"))
    focus_scores: Counter[str] = Counter()

    for focus, keywords in FOCUS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                focus_scores[focus] += 1

    category_focus = {
        "drug": ["mechanism_pathogenesis", "indications_contraindications", "patient_communication"],
        "disease": ["definition_scope", "mechanism_pathogenesis", "diagnosis_methods", "treatment_principles"],
        "anatomy": ["anatomy_landmarks", "structure_function", "clinical_steps"],
        "procedure": ["clinical_steps", "indications_contraindications", "complications_prevention"],
        "dental_material": ["material_properties", "comparison", "technique_methodology"],
        "radiology": ["diagnosis_methods", "anatomy_landmarks"],
    }
    for focus in category_focus.get(category, []):
        focus_scores[focus] += 2

    subject_hint = SUBJECT_FOCUS_HINTS.get(subject_text, {})
    for focus in subject_hint.get("focus", []):
        focus_scores[focus] += 3

    if any(word in topic_text for word in ["instrument", "equipment", "handpiece"]):
        focus_scores["equipment_and_tools"] += 4
        focus_scores["hygiene_infection_control"] += 2
    if any(word in topic_text for word in ["organization", "office", "ergonomic"]):
        focus_scores["organization_workflow"] += 4
    if any(word in topic_text for word in ["infection", "steril", "asepsis", "disinfection"]):
        focus_scores["hygiene_infection_control"] += 4
    if any(word in topic_text for word in ["prosthetic", "impression", "material"]):
        focus_scores["material_properties"] += 3

    if not focus_scores:
        return ["case_reasoning"]
    return [focus for focus, _ in focus_scores.most_common(3)]


def _variant_index(*parts: Any, modulo: int = 5) -> int:
    seed = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % max(1, modulo)


def _choose_question_type(question_type: str, focus: list[str], mode: str, difficulty: str, seed: str) -> str:
    if question_type and question_type != "自动混合":
        return question_type
    pool = ["Short Answer 简答题", "MCQ 单选题", "True / False 判断题"]
    if mode == "考前模拟" or difficulty in {"hard", "exam mode"}:
        pool.extend(["Case-based 病例题", "Matching 匹配题"])
    if any(f in focus for f in ["case_reasoning", "diagnosis_methods", "treatment_principles"]):
        pool.append("Case-based 病例题")
    if "comparison" in focus:
        pool.append("Matching 匹配题")
    return pool[_variant_index(seed, focus, mode, difficulty, modulo=len(pool))]


def _first(items: list[str], fallback: str) -> str:
    return items[0] if items else fallback


def _build_options(topic: str, expected_points: list[str], common_mistakes: list[str]) -> tuple[list[str], str]:
    correct = _first(expected_points, f"Correct concept about {topic}")
    distractors = common_mistakes[:3] + [
        f"{topic} is unrelated to clinical decision making",
        f"Only memorization is needed; mechanism is not important",
        f"Treatment can be chosen without diagnosis",
    ]
    options = [correct] + [item for item in distractors if normalize_text(item) != normalize_text(correct)]
    options = options[:4]
    while len(options) < 4:
        options.append(f"Incorrect option {len(options)}")
    labelled = [f"{chr(65 + idx)}. {text}" for idx, text in enumerate(options)]
    return labelled, "A"


def _short_model_answer(topic: str, expected_points: list[str], common_mistakes: list[str]) -> str:
    points = "; ".join(expected_points[:5]) if expected_points else f"define {topic} and give clinical relevance"
    mistakes = "; ".join(common_mistakes[:2]) if common_mistakes else "avoid vague, non-specific answers"
    return f"A strong answer should cover: {points}. Avoid: {mistakes}."


def _fallback_item(topic: str, subject: str, course_context: str) -> dict[str, Any]:
    topic_norm = normalize_text(topic)
    subject_norm = normalize_text(subject)
    context_terms = list(tokenize(course_context))[:6]
    must_know = [f"Define {topic or subject}", "Give the key clinical significance"]
    category = "general"
    extra_tags: list[str] = []
    if any(word in topic_norm for word in ["amoxicillin", "ibuprofen", "lidocaine", "paracetamol", "acetaminophen", "metronidazole"]):
        category = "drug"
        must_know = [
            f"State the drug class of {topic}",
            "Explain the mechanism of action",
            "Give a dental indication",
            "Mention contraindications, allergy risk, adverse effects, or prescribing precautions",
        ]
        extra_tags = ["drug", "mechanism", "precaution", "patient communication"]
    elif any(word in topic_norm for word in ["caries", "pulpitis", "periodontitis", "gingivitis"]):
        category = "disease"
        must_know = [
            f"Define {topic}",
            "Explain etiology and pathogenesis",
            "Describe key clinical features or diagnosis",
            "Mention treatment or prevention principles",
        ]
        extra_tags = ["disease", "pathogenesis", "diagnosis", "treatment"]
    elif any(word in topic_norm for word in ["root canal", "extraction", "scaling", "treatment"]):
        category = "procedure"
        must_know = [
            f"State the indication for {topic}",
            "Describe the main clinical steps",
            "Explain disinfection, instruments, or materials if relevant",
            "Mention complications and prevention",
        ]
        extra_tags = ["procedure", "clinical steps", "complications"]
    elif any(word in topic_norm for word in ["nerve", "sinus", "enamel", "dentin", "pulp", "anatomy"]):
        category = "anatomy"
        must_know = [
            f"Describe the location and structure of {topic}",
            "Explain function or innervation",
            "Connect anatomy to clinical relevance",
        ]
        extra_tags = ["anatomy", "landmark", "clinical relevance"]
    elif any(word in topic_norm for word in ["composite", "glass ionomer", "amalgam", "impression", "cement", "material"]):
        category = "dental_material"
        must_know = [
            f"Describe the composition or properties of {topic}",
            "State clinical indications",
            "Mention advantages, limitations, and handling points",
        ]
        extra_tags = ["material", "properties", "indications", "comparison"]
    elif any(word in topic_norm for word in ["instrument", "equipment", "handpiece"]):
        must_know = [
            f"Classify the instruments or equipment related to {topic}",
            "Explain function and selection",
            "Mention sterilization, disinfection, or maintenance",
        ]
        extra_tags = ["instrument", "equipment", "sterilization"]
    elif subject_norm == "microbiology" or any(
        word in topic_norm
        for word in [
            "microbiology", "bacteria", "gram", "acid-fast", "spore", "capsule",
            "culture", "sterilization", "disinfection", "antibiotic resistance",
            "virus", "fungi", "parasite", "biofilm", "plaque", "pathogen",
            "laboratory diagnosis",
        ]
    ):
        category = "general"
        must_know = [
            f"Define or classify {topic or subject}",
            "Describe structure, virulence factors, transmission, or pathogenesis when relevant",
            "Explain laboratory diagnosis, culture, sterilization/disinfection, or antimicrobial resistance when relevant",
            "Connect the topic to oral microbiology, plaque biofilm, caries microorganisms, periodontal pathogens, or opportunistic infection",
        ]
        extra_tags = [
            "microbiology",
            "classification",
            "structure",
            "pathogenesis",
            "diagnosis",
            "sterilization",
            "antimicrobial resistance",
            "oral microbiology",
        ]
    elif subject_norm in SUBJECT_FOCUS_HINTS:
        hint = SUBJECT_FOCUS_HINTS[subject_norm]
        must_know = list(hint["must_know"])
        extra_tags = list(hint["tags"])
        if subject_norm == "orthodontics":
            category = "procedure"
        elif subject_norm == "preventive dentistry":
            category = "general"
        elif subject_norm == "microbiology":
            category = "general"
    if context_terms:
        must_know.append("Use course terms: " + ", ".join(context_terms[:4]))
    return {
        "id": "fallback",
        "topic": topic or subject or "this topic",
        "subject": subject or "Dentistry",
        "category": category,
        "merged_question": "",
        "must_know": must_know,
        "common_mistakes": ["Giving a vague answer", "Not connecting the concept to clinical use"],
        "scoring_rubric": {"definition": 30, "key_points": 40, "clinical_relevance": 30},
        "follow_up_questions": [],
        "tags": extra_tags,
        "answer_template": [],
        "source_original_questions": [],
    }


def generate_written_question_from_bank(params: dict[str, Any]) -> dict[str, Any]:
    mode = str(params.get("mode", "日常练习")).strip()
    question_type = str(params.get("question_type", "自动混合")).strip()
    topic = str(params.get("topic") or params.get("exam_topic") or "").strip()
    subject = str(params.get("subject", "Dentistry")).strip()
    difficulty = str(params.get("difficulty", "medium")).strip()
    course_context = str(params.get("course_context", "")).strip()
    best_match = params.get("best_match") or params.get("bank_item")
    seed = str(params.get("question_seed", "0"))

    source = "school_question_bank" if isinstance(best_match, dict) and best_match else "fallback"
    item = _normalize_item(best_match) if source == "school_question_bank" else _fallback_item(topic, subject, course_context)
    matched_topic = item.get("topic") or topic or subject
    focus = infer_question_focus(item)
    resolved_type = _choose_question_type(question_type, focus, mode, difficulty, seed + matched_topic)
    expected_points = item.get("must_know") or _fallback_item(matched_topic, subject, course_context)["must_know"]
    common_mistakes = item.get("common_mistakes") or ["Giving a generic answer", "Missing clinical significance"]
    rubric = item.get("scoring_rubric") or {"content_accuracy": 50, "coverage": 30, "exam_structure": 20}
    model_answer = _short_model_answer(matched_topic, expected_points, common_mistakes)

    focus_line = ", ".join(focus)
    if resolved_type == "MCQ 单选题":
        options, correct_answer = _build_options(matched_topic, expected_points, common_mistakes)
        question = f"Which option best reflects the key exam point about {matched_topic}?"
    elif resolved_type == "True / False 判断题":
        correct_answer = "True"
        options = ["True", "False"]
        question = f"True or False: {expected_points[0] if expected_points else matched_topic}. Briefly justify your answer."
    elif resolved_type == "Matching 匹配题":
        correct_answer = model_answer
        options = []
        left = expected_points[:3] or [matched_topic]
        right = common_mistakes[:3] or ["clinical relevance", "definition", "common error"]
        question = f"Match the key ideas about {matched_topic} with their correct clinical meaning: {'; '.join(left)}. Use concise English."
        if right:
            question += f" Avoid these traps: {'; '.join(right[:2])}."
    elif resolved_type == "Case-based 病例题":
        correct_answer = model_answer
        options = []
        question = (
            f"A dental patient presents with a problem related to {matched_topic}. "
            f"Using the focus of {focus_line}, explain your diagnosis or management reasoning and mention two must-know points."
        )
    else:
        correct_answer = model_answer
        options = []
        if "equipment_and_tools" in focus:
            question = f"Classify the main instruments or equipment related to {matched_topic}, and explain one clinical selection or sterilization point."
        elif "material_properties" in focus:
            question = f"Explain the key properties and indications of {matched_topic}, and mention one limitation or common handling mistake."
        elif "anatomy_landmarks" in focus:
            question = f"Describe the anatomy of {matched_topic} and explain why it matters clinically."
        elif "clinical_steps" in focus:
            question = f"Describe the main clinical steps for {matched_topic} and explain one error that could affect the outcome."
        elif "mechanism_pathogenesis" in focus:
            question = f"Explain the mechanism or pathogenesis of {matched_topic} and connect it to one clinical consequence."
        else:
            question = f"Give a concise exam answer on {matched_topic}, covering definition, key points, and clinical relevance."

    if mode == "考前模拟":
        question = question.replace("concise", "exam-standard concise")
    elif mode == "错题强化":
        weak_points = params.get("recent_wrong_points") or params.get("user_weaknesses") or []
        if weak_points:
            question += f" Pay special attention to your previous weak point: {str(weak_points[0])[:120]}."

    return {
        "question_type": resolved_type,
        "question": question[:900],
        "options": options,
        "correct_answer": correct_answer,
        "expected_points": expected_points,
        "model_answer": model_answer,
        "scoring_rubric": rubric,
        "common_mistakes": common_mistakes,
        "source": source,
        "question_source": source,
        "matched_topic": matched_topic,
        "topic": matched_topic,
        "focus": focus,
        "question_focus": focus,
        "bank_id": item.get("id"),
        "follow_up_questions": item.get("follow_up_questions", []),
    }


if __name__ == "__main__":
    for sample_topic in [
        "Dental caries",
        "Amoxicillin",
        "Dental instruments",
        "Root canal treatment",
        "Glass ionomer cement",
    ]:
        match = find_relevant_school_questions(sample_topic, "Dentistry", sample_topic)
        generated = generate_written_question_from_bank(
            {
                "mode": "日常练习",
                "question_type": "自动混合",
                "topic": sample_topic,
                "subject": "Dentistry",
                "difficulty": "medium",
                "course_context": sample_topic,
                "best_match": match["best_match"],
                "question_seed": "local-test",
            }
        )
        print("\n==", sample_topic)
        print("match:", match["match_reason"], match["match_score"])
        print("focus:", generated["focus"])
        print("question:", generated["question"])

import html
import json
import os
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components


def get_secret(name, default=None):
    env_value = os.getenv(name)
    if env_value:
        return env_value

    try:
        value = st.secrets.get(name, default)
    except Exception:
        return default
    return value if value is not None else default


def generate_examiner_audio(text: str) -> bytes | None:
    api_key = get_secret("ELEVENLABS_API_KEY")
    voice_id = get_secret("ELEVENLABS_VOICE_ID")
    model_id = get_secret("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")

    if not api_key or not voice_id:
        return None

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": text,
            "model_id": model_id,
        },
        timeout=45,
    )
    if not response.ok:
        raise RuntimeError(f"ElevenLabs TTS failed with status {response.status_code}.")
    return response.content


def transcribe_student_audio(audio_file) -> str:
    api_key = get_secret("ELEVENLABS_API_KEY")
    model_id = get_secret("ELEVENLABS_STT_MODEL", "scribe_v2")

    if not api_key:
        return ""

    audio_bytes = _read_audio_bytes(audio_file)
    if not audio_bytes:
        return ""

    filename = getattr(audio_file, "name", "student_answer.wav") or "student_answer.wav"
    content_type = getattr(audio_file, "type", None) or "audio/wav"

    response = requests.post(
        "https://api.elevenlabs.io/v1/speech-to-text",
        headers={"xi-api-key": api_key},
        data={"model_id": model_id},
        files={"file": (filename, audio_bytes, content_type)},
        timeout=90,
    )
    if not response.ok:
        raise RuntimeError(f"ElevenLabs STT failed with status {response.status_code}.")

    payload = response.json()
    return str(payload.get("text") or payload.get("transcript") or "").strip()


def browser_tts_button(text: str, button_label="🔊 Free Browser Voice"):
    safe_text = json.dumps(text or "")
    safe_label = html.escape(button_label)
    components.html(
        f"""
        <button id="dentpilot-browser-tts" style="
            border: 0;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            background: #0f172a;
            color: white;
            font-weight: 700;
            cursor: pointer;
        ">{safe_label}</button>
        <script>
        const button = document.getElementById("dentpilot-browser-tts");
        const text = {safe_text};
        button.addEventListener("click", () => {{
            if (!("speechSynthesis" in window)) {{
                alert("Browser speech synthesis is not available in this browser.");
                return;
            }}
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "en-US";
            utterance.rate = 0.92;
            window.speechSynthesis.speak(utterance);
        }});
        </script>
        """,
        height=58,
    )


def _read_audio_bytes(audio_file: Any) -> bytes:
    if audio_file is None:
        return b""
    if hasattr(audio_file, "getvalue"):
        return audio_file.getvalue()
    if hasattr(audio_file, "read"):
        try:
            audio_file.seek(0)
        except Exception:
            pass
        return audio_file.read()
    return b""

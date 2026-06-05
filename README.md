# DentPilot AI

DentPilot AI is a Streamlit study-assistance app for Chinese students in English-taught dental and medical programs.

Current features:
- Study Pack generation with Chinese explanations, glossary, quiz, Anki CSV, and PDF export
- Text-based AI Oral Exam
- AI Clinical Case Training
- Weakness Analysis
- Optional voice tools
- Realtime Oral Exam with ElevenLabs Conversational AI Widget

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

## Environment Variables

For DeepSeek study pack, oral exam, clinical case, and weakness analysis:

```env
DEEPSEEK_API_KEY=your_deepseek_key
DEEPSEEK_MODEL=deepseek-chat
```

For optional old round-based voice tools:

```env
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
ELEVENLABS_TTS_MODEL=eleven_multilingual_v2
ELEVENLABS_STT_MODEL=scribe_v2
```

## Realtime Oral Exam Setup

1. Create an ElevenLabs Conversational AI Agent.
2. Copy the Agent ID.
3. Add to local `.env`:

```env
ELEVENLABS_AGENT_ID=agent_xxxxxxxxxxxxx
```

4. On Streamlit Cloud, add the same value in Secrets:

```toml
ELEVENLABS_AGENT_ID = "agent_xxxxxxxxxxxxx"
```

The Realtime Oral Exam page uses the ElevenLabs Conversational AI Widget. It does not require `ELEVENLABS_API_KEY` in the Streamlit app.

## Recommended ElevenLabs Agent System Prompt

Use the prompt in `ELEVENLABS_AGENT_PROMPT.md` when creating your ElevenLabs Conversational AI Agent.

The Streamlit page embeds only the ElevenLabs Agent ID. All exam behavior should be configured inside the ElevenLabs Agent system prompt.

## Safety Boundary

DentPilot AI is for study and exam preparation only. It is not a real patient diagnosis tool and does not replace a licensed clinician, teacher, or professor.

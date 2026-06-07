# DentPilot AI

DentPilot AI is a Streamlit study-assistance app for Chinese students in English-taught dental and medical programs.

Current features:
- Study Pack generation with Chinese explanations, glossary, quiz, Anki CSV, and PDF export
- Text-based AI Oral Exam
- AI Clinical Case Training
- Weakness Analysis
- Optional voice tools
- Realtime Oral Exam launcher for the separate Next.js oral exam app

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

For Supabase login:

```env
NEXT_PUBLIC_SUPABASE_URL=https://nakkcdzpxdggirujgmtk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_publishable_key
```

On Streamlit Cloud, add these in Secrets:

```toml
NEXT_PUBLIC_SUPABASE_URL = "https://nakkcdzpxdggirujgmtk.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY = "your_supabase_publishable_key"
```

Use the Supabase Publishable key only. Do not add the service_role key to Streamlit.

The main Streamlit app keeps users logged in with browser `localStorage` containing only the Supabase `access_token`, `refresh_token`, expiry time, and basic user id/email. It never stores passwords or service role keys. Logout clears both Streamlit session state and the saved browser auth item.

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

## Realtime Oral Exam Deployment

The realtime oral exam is now a separate Next.js app. The Streamlit page opens it in a new tab instead of embedding the old ElevenLabs widget, which keeps microphone permissions more stable.

Local:

```env
ORAL_APP_URL=http://localhost:3000
```

Production:

```env
ORAL_APP_URL=https://dentpilot-oral-app.vercel.app
```

On Streamlit Cloud, add `ORAL_APP_URL` in Secrets:

```toml
ORAL_APP_URL = "https://dentpilot-oral-app.vercel.app"
```

The ElevenLabs Agent ID is configured inside the Next.js app with `NEXT_PUBLIC_ELEVENLABS_AGENT_ID`; Streamlit no longer needs `ELEVENLABS_AGENT_ID` for the realtime oral exam launcher.

## Safety Boundary

DentPilot AI is for study and exam preparation only. It is not a real patient diagnosis tool and does not replace a licensed clinician, teacher, or professor.

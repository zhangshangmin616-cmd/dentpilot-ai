# DentPilot Oral App

A standalone Next.js realtime oral exam interface for DentPilot AI.

This app is separate from the existing Streamlit project. It uses a custom UI with the `@elevenlabs/react` SDK, not the ElevenLabs widget.

## Install

```bash
npm install
```

## Configure `.env.local`

Create a `.env.local` file:

```env
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=agent_7301ktcm03w0es9ssrb4thyhwb3k
```

For this MVP, the app uses public agent mode. Do not put `ELEVENLABS_API_KEY` in the frontend.

## Run

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

## What It Does

DentPilot AI  
Realtime Oral Exam Simulator

Stop rereading notes. Train like a real oral exam.

The AI professor will ask questions, listen to your answer, challenge your reasoning, and give feedback in the selected exam language.

Supported languages:
- UI: Chinese, English, Russian
- Oral exam professor: English or Russian

## Notes

- No login
- No database
- No payment
- No backend
- No ElevenLabs widget embed
- No generic support call UI
- No ElevenLabs API key exposed in the browser

The ElevenLabs agent should already have the oral examiner system prompt configured in the ElevenLabs dashboard. Use the root `ELEVENLABS_AGENT_PROMPT.md` so the agent reads `exam_language` and starts the oral exam in English or Russian.

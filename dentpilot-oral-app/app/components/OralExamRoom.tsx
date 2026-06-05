"use client";

import {
  ConversationProvider,
  useConversation
} from "@elevenlabs/react";
import { useEffect, useMemo, useState } from "react";
import ExaminerCard from "./ExaminerCard";
import RubricPanel from "./RubricPanel";
import TranscriptPanel, { TranscriptMessage } from "./TranscriptPanel";

const subjects = [
  "Dentistry",
  "Endodontics",
  "Periodontology",
  "Oral Surgery",
  "Oral Pathology",
  "Dental Anatomy",
  "Pharmacology",
  "General Pathology"
];

const examinerStyles = [
  "Strict Professor",
  "Friendly Tutor",
  "OSCE Examiner",
  "Fast Oral Pathology Professor"
];

const difficulties = ["Easy", "Medium", "Hard"];

const agentId = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID || "";

function formatTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function coerceMessage(message: unknown): TranscriptMessage {
  const payload = message as Record<string, unknown>;
  const rawRole = String(payload.source || payload.role || payload.type || "system").toLowerCase();
  const text = String(payload.message || payload.text || payload.transcript || payload.content || JSON.stringify(message));
  const role = rawRole.includes("user") ? "user" : rawRole.includes("agent") || rawRole.includes("ai") ? "agent" : "system";

  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text
  };
}

function extractScore(messages: TranscriptMessage[]) {
  const latestAgent = [...messages].reverse().find((message) => message.role === "agent");
  const text = latestAgent?.text || "";
  const scoreMatch = text.match(/(?:score|total score)\D{0,12}(\d{1,3})(?:\s*\/\s*100)?/i);
  const missingMatch = text.match(/missing points?:?\s*([\s\S]{0,220})/i);

  return {
    lastScore: scoreMatch ? `${scoreMatch[1]}/100` : undefined,
    missingPoints: missingMatch ? missingMatch[1].trim() : undefined
  };
}

function OralExamRoomInner() {
  const [courseContext, setCourseContext] = useState("");
  const [subject, setSubject] = useState("Dentistry");
  const [examinerStyle, setExaminerStyle] = useState("Strict Professor");
  const [difficulty, setDifficulty] = useState("Medium");
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [error, setError] = useState("");
  const [seconds, setSeconds] = useState(0);
  const [micMuted, setMicMuted] = useState(false);
  const [sessionStarted, setSessionStarted] = useState(false);
  const [contextUpdateAvailable, setContextUpdateAvailable] = useState(true);

  const conversation = useConversation({
    micMuted,
    onConnect: () => {
      setError("");
      setSessionStarted(true);
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-system-connected`,
          role: "system",
          text: "Session connected. The examiner should begin the oral exam directly."
        }
      ]);
    },
    onDisconnect: () => {
      setSessionStarted(false);
    },
    onError: (event: unknown) => {
      setError(event instanceof Error ? event.message : String(event));
    },
    onMessage: (message: unknown) => {
      setMessages((current) => [...current, coerceMessage(message)]);
    }
  });

  const status = String((conversation as { status?: string }).status || "disconnected");
  const mode = String((conversation as { mode?: string }).mode || "idle");
  const isSpeaking = Boolean((conversation as { isSpeaking?: boolean }).isSpeaking || mode === "speaking");
  const isListening = status === "connected" && !isSpeaking;
  const questionNumber = Math.max(1, messages.filter((message) => message.role === "agent" && /\?/.test(message.text)).length);
  const { lastScore, missingPoints } = useMemo(() => extractScore(messages), [messages]);

  useEffect(() => {
    if (status !== "connected") {
      return;
    }

    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [status]);

  async function startExam() {
    setError("");

    if (!agentId) {
      setError("NEXT_PUBLIC_ELEVENLABS_AGENT_ID is missing. Add it to .env.local.");
      return;
    }

    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });

      const dynamicVariables = {
        course_context: courseContext.trim() || "The student did not provide course context. Ask for a topic first.",
        subject,
        examiner_style: examinerStyle,
        difficulty
      };

      setMessages([
        {
          id: `${Date.now()}-system-start`,
          role: "system",
          text: `Exam setup sent: ${subject}, ${examinerStyle}, ${difficulty}.`
        }
      ]);
      setSeconds(0);

      await conversation.startSession({
        agentId,
        dynamicVariables
      } as never);

      if (typeof (conversation as { sendContextualUpdate?: (text: string) => void }).sendContextualUpdate === "function") {
        (conversation as { sendContextualUpdate: (text: string) => void }).sendContextualUpdate(
          `Start a dental oral exam now. Course context: ${dynamicVariables.course_context}. Subject: ${subject}. Examiner style: ${examinerStyle}. Difficulty: ${difficulty}. Ask Question 1 directly.`
        );
        setContextUpdateAvailable(true);
      } else {
        setContextUpdateAvailable(false);
      }
    } catch (event) {
      setError(event instanceof Error ? event.message : String(event));
    }
  }

  async function endExam() {
    try {
      await conversation.endSession();
      setSessionStarted(false);
    } catch (event) {
      setError(event instanceof Error ? event.message : String(event));
    }
  }

  return (
    <main className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-950/45 px-5 py-4 backdrop-blur-xl">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-200/80">DentPilot AI</p>
          <h1 className="text-xl font-black text-white sm:text-2xl">Realtime Oral Exam</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className={`rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] ${status === "connected" ? "bg-emerald-300 text-emerald-950" : status === "connecting" ? "bg-amber-300 text-amber-950" : "bg-white/10 text-slate-300"}`}>
            {status}
          </span>
          <span className="rounded-full bg-white/10 px-4 py-2 font-mono text-sm text-cyan-100">{formatTime(seconds)}</span>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[20rem_minmax(0,1fr)_22rem]">
        <ExaminerCard
          canEnd={status === "connected" || sessionStarted}
          examinerStyle={examinerStyle}
          isMuted={micMuted}
          isSpeaking={isSpeaking}
          mode={isListening ? "listening" : mode}
          onEndExam={endExam}
          onToggleMute={() => setMicMuted((value) => !value)}
          status={status}
        />

        <section className="panel min-h-[28rem] p-5 sm:p-7">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-200/80">DentPilot AI</p>
            <h2 className="mt-3 text-4xl font-black leading-tight text-white sm:text-5xl">
              AI Oral Exam Simulator
            </h2>
            <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-300">
              Stop rereading notes. Train like a real oral exam.
            </p>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
              The AI professor will ask you questions, listen to your English answer,
              challenge your reasoning, and give feedback.
            </p>
          </div>

          <div className="mt-8 grid gap-4">
            <label>
              <span className="label">Course context</span>
              <textarea
                className="field min-h-32 resize-y"
                disabled={status === "connected"}
                onChange={(event) => setCourseContext(event.target.value)}
                placeholder="Paste lecture notes or type a topic, e.g. reversible pulpitis, dental caries, periodontal pockets..."
                value={courseContext}
              />
            </label>

            <div className="grid gap-4 md:grid-cols-3">
              <label>
                <span className="label">Subject</span>
                <select className="field" disabled={status === "connected"} onChange={(event) => setSubject(event.target.value)} value={subject}>
                  {subjects.map((item) => (
                    <option key={item} className="text-slate-950" value={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label>
                <span className="label">Examiner style</span>
                <select className="field" disabled={status === "connected"} onChange={(event) => setExaminerStyle(event.target.value)} value={examinerStyle}>
                  {examinerStyles.map((item) => (
                    <option key={item} className="text-slate-950" value={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label>
                <span className="label">Difficulty</span>
                <select className="field" disabled={status === "connected"} onChange={(event) => setDifficulty(event.target.value)} value={difficulty}>
                  {difficulties.map((item) => (
                    <option key={item} className="text-slate-950" value={item}>{item}</option>
                  ))}
                </select>
              </label>
            </div>

            {status === "connected" ? (
              <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-5">
                <h3 className="text-xl font-bold text-cyan-100">
                  {isSpeaking ? "Professor is speaking..." : "Listening to your answer..."}
                </h3>
                <p className="mt-2 text-slate-300">Answer in English.</p>
              </div>
            ) : (
              <button className="primary-button text-base" onClick={startExam} type="button">
                Start Oral Exam
              </button>
            )}

            {!contextUpdateAvailable && (
              <div className="rounded-xl border border-amber-300/30 bg-amber-300/10 p-4 text-sm text-amber-100">
                Say: Start my oral exam on this topic.
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-rose-300/30 bg-rose-300/10 p-4 text-sm text-rose-100">
                {error}
              </div>
            )}
          </div>
        </section>

        <RubricPanel lastScore={lastScore} missingPoints={missingPoints} questionNumber={questionNumber} />
      </div>

      <div className="mt-4">
        <TranscriptPanel messages={messages} />
      </div>
    </main>
  );
}

export default function OralExamRoom() {
  return (
    <ConversationProvider>
      <OralExamRoomInner />
    </ConversationProvider>
  );
}

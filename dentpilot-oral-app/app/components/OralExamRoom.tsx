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
type UiLanguage = "zh" | "en" | "ru";
type ExamLanguage = "English" | "Russian";

const uiLanguages: Array<{ value: UiLanguage; label: string }> = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
  { value: "ru", label: "Русский" }
];

const examLanguages: Array<{ value: ExamLanguage; label: string }> = [
  { value: "English", label: "English" },
  { value: "Russian", label: "Русский" }
];

const copy = {
  en: {
    title: "Realtime Oral Exam",
    heroTitle: "AI Oral Exam Simulator",
    heroLead: "Stop rereading notes. Train like a real oral exam.",
    heroBody: "The AI professor will ask questions, listen to your answer, challenge your reasoning, and give feedback in the selected exam language.",
    uiLanguage: "UI language",
    examLanguage: "Exam language",
    courseContext: "Course context",
    coursePlaceholder: "Paste lecture notes or type a topic, e.g. reversible pulpitis, dental caries, periodontal pockets...",
    subject: "Subject",
    examinerStyle: "Examiner style",
    difficulty: "Difficulty",
    professorSpeaking: "Professor is speaking...",
    listening: "Listening to your answer...",
    answerInstruction: "Answer in the selected exam language.",
    start: "Start Oral Exam",
    fallbackSay: "Say: Start my oral exam on this topic.",
    setupSent: "Exam setup sent",
    connected: "Session connected. The examiner should begin the oral exam directly."
  },
  zh: {
    title: "实时口试",
    heroTitle: "AI 口试模拟器",
    heroLead: "不要只反复看笔记，像真实口试一样训练。",
    heroBody: "AI 教授会根据你的课程内容提问、听你的回答、追问推理，并用你选择的口试语言给出反馈。",
    uiLanguage: "界面语言",
    examLanguage: "口试语言",
    courseContext: "课程内容",
    coursePlaceholder: "粘贴讲义内容或输入主题，例如 reversible pulpitis、dental caries、periodontal pockets...",
    subject: "科目",
    examinerStyle: "考官风格",
    difficulty: "难度",
    professorSpeaking: "教授正在提问...",
    listening: "正在听你的回答...",
    answerInstruction: "请用所选口试语言回答。",
    start: "开始口试",
    fallbackSay: "请说：Start my oral exam on this topic.",
    setupSent: "口试设置已发送",
    connected: "会话已连接。教授会直接开始第 1 个问题。"
  },
  ru: {
    title: "Устный экзамен",
    heroTitle: "AI-симулятор устного экзамена",
    heroLead: "Не просто перечитывайте конспекты. Тренируйтесь как на реальном устном экзамене.",
    heroBody: "AI-преподаватель будет задавать вопросы, слушать ответ, проверять клиническое мышление и давать обратную связь на выбранном языке экзамена.",
    uiLanguage: "Язык интерфейса",
    examLanguage: "Язык экзамена",
    courseContext: "Материал курса",
    coursePlaceholder: "Вставьте конспект или тему, например reversible pulpitis, dental caries, periodontal pockets...",
    subject: "Предмет",
    examinerStyle: "Стиль экзаменатора",
    difficulty: "Сложность",
    professorSpeaking: "Преподаватель говорит...",
    listening: "Слушаю ваш ответ...",
    answerInstruction: "Отвечайте на выбранном языке экзамена.",
    start: "Начать устный экзамен",
    fallbackSay: "Скажите: Start my oral exam on this topic.",
    setupSent: "Настройки экзамена отправлены",
    connected: "Сессия подключена. Экзаменатор должен сразу начать первый вопрос."
  }
} as const;

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
  const scoreMatch = text.match(/(?:score|total score|оценка|балл)\D{0,16}(\d{1,3})(?:\s*\/\s*100)?/i);
  const missingMatch = text.match(/(?:missing points?|недостающие пункты|пропущенные пункты):?\s*([\s\S]{0,220})/i);

  return {
    lastScore: scoreMatch ? `${scoreMatch[1]}/100` : undefined,
    missingPoints: missingMatch ? missingMatch[1].trim() : undefined
  };
}

function OralExamRoomInner() {
  const [uiLanguage, setUiLanguage] = useState<UiLanguage>("zh");
  const [examLanguage, setExamLanguage] = useState<ExamLanguage>("English");
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
  const labels = copy[uiLanguage];

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
          text: labels.connected
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
        difficulty,
        exam_language: examLanguage,
        ui_language: uiLanguage,
        exam_language_instruction:
          examLanguage === "Russian"
            ? "Use Russian for spoken questions, follow-up questions, scoring feedback, strengths, missing points, corrected answer, and final report."
            : "Use English for spoken questions, follow-up questions, scoring feedback, strengths, missing points, corrected answer, and final report."
      };

      setMessages([
        {
          id: `${Date.now()}-system-start`,
          role: "system",
          text: `${labels.setupSent}: ${subject}, ${examinerStyle}, ${difficulty}, ${examLanguage}.`
        }
      ]);
      setSeconds(0);

      await conversation.startSession({
        agentId,
        dynamicVariables
      } as never);

      if (typeof (conversation as { sendContextualUpdate?: (text: string) => void }).sendContextualUpdate === "function") {
        (conversation as { sendContextualUpdate: (text: string) => void }).sendContextualUpdate(
          `Start a dental oral exam now. Exam language: ${examLanguage}. ${dynamicVariables.exam_language_instruction} Course context: ${dynamicVariables.course_context}. Subject: ${subject}. Examiner style: ${examinerStyle}. Difficulty: ${difficulty}. Ask Question 1 directly in ${examLanguage}.`
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
          <h1 className="text-xl font-black text-white sm:text-2xl">{labels.title}</h1>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <span>{labels.uiLanguage}</span>
            <select className="field h-9 min-w-28 py-1 text-sm" onChange={(event) => setUiLanguage(event.target.value as UiLanguage)} value={uiLanguage}>
              {uiLanguages.map((item) => (
                <option key={item.value} className="text-slate-950" value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
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
          labels={{
            aiProfessor: uiLanguage === "ru" ? "AI-преподаватель" : uiLanguage === "zh" ? "AI 教授" : "AI Professor",
            dentalExaminer: uiLanguage === "ru" ? "Стоматологический экзаменатор" : uiLanguage === "zh" ? "牙科考官" : "Dental Examiner",
            examinerStyle: labels.examinerStyle,
            state: uiLanguage === "ru" ? "Состояние" : uiLanguage === "zh" ? "状态" : "State",
            speaking: uiLanguage === "ru" ? "Говорит" : uiLanguage === "zh" ? "正在说话" : "Speaking",
            listening: uiLanguage === "ru" ? "Слушает" : uiLanguage === "zh" ? "正在听" : "Listening",
            ready: uiLanguage === "ru" ? "Готов" : uiLanguage === "zh" ? "准备就绪" : "Ready",
            connection: uiLanguage === "ru" ? "Подключение" : uiLanguage === "zh" ? "连接" : "Connection",
            mute: uiLanguage === "ru" ? "Выключить микрофон" : uiLanguage === "zh" ? "麦克风静音" : "Mute microphone",
            unmute: uiLanguage === "ru" ? "Включить микрофон" : uiLanguage === "zh" ? "取消静音" : "Unmute microphone",
            endExam: uiLanguage === "ru" ? "Завершить экзамен" : uiLanguage === "zh" ? "结束口试" : "End Exam"
          }}
          mode={isListening ? "listening" : mode}
          onEndExam={endExam}
          onToggleMute={() => setMicMuted((value) => !value)}
          status={status}
        />

        <section className="panel min-h-[28rem] p-5 sm:p-7">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-200/80">DentPilot AI</p>
            <h2 className="mt-3 text-4xl font-black leading-tight text-white sm:text-5xl">
              {labels.heroTitle}
            </h2>
            <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-300">
              {labels.heroLead}
            </p>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
              {labels.heroBody}
            </p>
          </div>

          <div className="mt-8 grid gap-4">
            <label>
              <span className="label">{labels.courseContext}</span>
              <textarea
                className="field min-h-32 resize-y"
                disabled={status === "connected"}
                onChange={(event) => setCourseContext(event.target.value)}
                placeholder={labels.coursePlaceholder}
                value={courseContext}
              />
            </label>

            <div className="grid gap-4 md:grid-cols-4">
              <label>
                <span className="label">{labels.examLanguage}</span>
                <select className="field" disabled={status === "connected"} onChange={(event) => setExamLanguage(event.target.value as ExamLanguage)} value={examLanguage}>
                  {examLanguages.map((item) => (
                    <option key={item.value} className="text-slate-950" value={item.value}>{item.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span className="label">{labels.subject}</span>
                <select className="field" disabled={status === "connected"} onChange={(event) => setSubject(event.target.value)} value={subject}>
                  {subjects.map((item) => (
                    <option key={item} className="text-slate-950" value={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label>
                <span className="label">{labels.examinerStyle}</span>
                <select className="field" disabled={status === "connected"} onChange={(event) => setExaminerStyle(event.target.value)} value={examinerStyle}>
                  {examinerStyles.map((item) => (
                    <option key={item} className="text-slate-950" value={item}>{item}</option>
                  ))}
                </select>
              </label>
              <label>
                <span className="label">{labels.difficulty}</span>
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
                  {isSpeaking ? labels.professorSpeaking : labels.listening}
                </h3>
                <p className="mt-2 text-slate-300">{labels.answerInstruction}</p>
              </div>
            ) : (
              <button className="primary-button text-base" onClick={startExam} type="button">
                {labels.start}
              </button>
            )}

            {!contextUpdateAvailable && (
              <div className="rounded-xl border border-amber-300/30 bg-amber-300/10 p-4 text-sm text-amber-100">
                {labels.fallbackSay}
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-rose-300/30 bg-rose-300/10 p-4 text-sm text-rose-100">
                {error}
              </div>
            )}
          </div>
        </section>

        <RubricPanel
          labels={{
            rubric: uiLanguage === "ru" ? "Рубрика" : uiLanguage === "zh" ? "评分标准" : "Rubric",
            title: uiLanguage === "ru" ? "Оценка устного экзамена" : uiLanguage === "zh" ? "口试评分" : "Oral Exam Score",
            currentQuestion: uiLanguage === "ru" ? "Текущий вопрос" : uiLanguage === "zh" ? "当前问题" : "Current Question",
            lastScore: uiLanguage === "ru" ? "Последний балл" : uiLanguage === "zh" ? "上次得分" : "Last Score",
            pending: uiLanguage === "ru" ? "Ожидается" : uiLanguage === "zh" ? "等待评分" : "Pending",
            missingPoints: uiLanguage === "ru" ? "Недостающие пункты" : uiLanguage === "zh" ? "遗漏要点" : "Missing Points",
            missingPlaceholder:
              uiLanguage === "ru"
                ? "Обратная связь появится после оценки ответа."
                : uiLanguage === "zh"
                  ? "考官评分后会显示反馈。"
                  : "Feedback will appear after the examiner grades your answer.",
            finalPlaceholder:
              uiLanguage === "ru"
                ? "Итоговый отчет: общий балл, уровень, сильные и слабые стороны, план повторения и следующие темы."
                : uiLanguage === "zh"
                  ? "最终报告：总分、通过等级、强项、弱项、复习计划和下一步主题。"
                  : "Final report placeholder: total score, pass level, strong areas, weak areas, revision plan, and next topics."
          }}
          lastScore={lastScore}
          missingPoints={missingPoints}
          questionNumber={questionNumber}
        />
      </div>

      <div className="mt-4">
        <TranscriptPanel
          labels={{
            transcript: uiLanguage === "ru" ? "Транскрипт" : uiLanguage === "zh" ? "转录" : "Transcript",
            conversation: uiLanguage === "ru" ? "Разговор" : uiLanguage === "zh" ? "对话" : "Conversation",
            messages: uiLanguage === "ru" ? "сообщений" : uiLanguage === "zh" ? "条消息" : "messages",
            empty:
              uiLanguage === "ru"
                ? "Живая расшифровка появится здесь, когда будет доступна."
                : uiLanguage === "zh"
                  ? "实时语音转录会在可用时显示在这里。"
                  : "The live voice transcript will appear here when available.",
            professor: uiLanguage === "ru" ? "Преподаватель" : uiLanguage === "zh" ? "教授" : "Professor",
            student: uiLanguage === "ru" ? "Студент" : uiLanguage === "zh" ? "学生" : "Student",
            system: uiLanguage === "ru" ? "Система" : uiLanguage === "zh" ? "系统" : "System"
          }}
          messages={messages}
        />
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

const rubric = [
  ["Content Accuracy", 30],
  ["Completeness", 20],
  ["Clinical Reasoning", 20],
  ["English Expression", 10],
  ["Examiner Interaction", 10],
  ["Pronunciation and Fluency", 10]
] as const;

type RubricPanelProps = {
  questionNumber: number;
  lastScore?: string;
  missingPoints?: string;
};

export default function RubricPanel({ questionNumber, lastScore, missingPoints }: RubricPanelProps) {
  return (
    <aside className="panel flex min-h-[28rem] flex-col p-5">
      <div>
        <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/75">Rubric</p>
        <h2 className="mt-1 text-xl font-bold text-white">Oral Exam Score</h2>
      </div>

      <div className="mt-5 grid gap-3">
        {rubric.map(([label, score]) => (
          <div key={label} className="flex items-center justify-between rounded-xl bg-white/[0.06] px-3 py-2">
            <span className="text-sm text-slate-200">{label}</span>
            <span className="font-bold text-cyan-200">{score}</span>
          </div>
        ))}
      </div>

      <div className="mt-5 grid gap-3">
        <div className="rounded-xl border border-white/10 bg-slate-950/35 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Current Question</p>
          <p className="mt-1 text-3xl font-black text-white">Q{Math.max(questionNumber, 1)}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-slate-950/35 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Last Score</p>
          <p className="mt-1 text-2xl font-bold text-cyan-200">{lastScore || "Pending"}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-slate-950/35 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Missing Points</p>
          <p className="mt-2 text-sm leading-6 text-slate-300">{missingPoints || "Feedback will appear after the examiner grades your answer."}</p>
        </div>
      </div>

      <div className="mt-auto rounded-xl bg-cyan-300/10 p-4 text-sm text-cyan-100">
        Final report placeholder: total score, pass level, strong areas, weak areas, revision plan, and next topics.
      </div>
    </aside>
  );
}

export type TranscriptMessage = {
  id: string;
  role: "agent" | "user" | "system";
  text: string;
};

type TranscriptPanelProps = {
  messages: TranscriptMessage[];
  labels: {
    transcript: string;
    conversation: string;
    messages: string;
    empty: string;
    professor: string;
    student: string;
    system: string;
  };
};

export default function TranscriptPanel({ messages, labels }: TranscriptPanelProps) {
  return (
    <section className="panel p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/75">{labels.transcript}</p>
          <h2 className="text-lg font-bold text-white">{labels.conversation}</h2>
        </div>
        <span className="rounded-full bg-white/[0.08] px-3 py-1 text-xs text-slate-300">
          {messages.length} {labels.messages}
        </span>
      </div>

      {messages.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/15 bg-white/[0.04] p-5 text-sm text-slate-300">
          {labels.empty}
        </div>
      ) : (
        <div className="max-h-72 space-y-3 overflow-y-auto pr-2">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`max-w-3xl rounded-2xl px-4 py-3 text-sm leading-6 ${
                message.role === "agent"
                  ? "bg-cyan-300/12 text-cyan-50"
                  : message.role === "user"
                    ? "ml-auto bg-white/[0.1] text-white"
                    : "bg-slate-950/40 text-slate-300"
              }`}
            >
              <p className="mb-1 text-[0.68rem] font-bold uppercase tracking-[0.18em] text-slate-400">
                {message.role === "agent" ? labels.professor : message.role === "user" ? labels.student : labels.system}
              </p>
              {message.text}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

import VoiceWave from "./VoiceWave";

type ExaminerCardProps = {
  examinerStyle: string;
  status: string;
  mode: string;
  isMuted: boolean;
  isSpeaking: boolean;
  onToggleMute: () => void;
  onEndExam: () => void;
  canEnd: boolean;
};

export default function ExaminerCard({
  examinerStyle,
  status,
  mode,
  isMuted,
  isSpeaking,
  onToggleMute,
  onEndExam,
  canEnd
}: ExaminerCardProps) {
  const stateLabel = isSpeaking ? "Speaking" : mode === "listening" ? "Listening" : "Ready";

  return (
    <aside className="panel flex min-h-[28rem] flex-col p-5">
      <div className="flex items-center gap-4">
        <div className="grid h-16 w-16 place-items-center rounded-2xl bg-cyan-300 text-3xl text-slate-950 shadow-lg shadow-cyan-500/20">
          Dr
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/75">AI Professor</p>
          <h2 className="text-xl font-bold text-white">Dental Examiner</h2>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-white/10 bg-slate-950/35 p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Examiner Style</p>
        <p className="mt-1 text-lg font-semibold text-cyan-100">{examinerStyle}</p>
      </div>

      <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/35 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">State</p>
            <p className="mt-1 text-lg font-semibold text-white">{stateLabel}</p>
          </div>
          <VoiceWave active={isSpeaking || mode === "listening"} />
        </div>
        <p className="mt-3 text-sm text-slate-300">Connection: {status}</p>
      </div>

      <div className="mt-auto grid gap-3 pt-6">
        <button className="secondary-button" onClick={onToggleMute} type="button">
          {isMuted ? "Unmute microphone" : "Mute microphone"}
        </button>
        <button className="secondary-button border-rose-300/30 text-rose-100" disabled={!canEnd} onClick={onEndExam} type="button">
          End Exam
        </button>
      </div>
    </aside>
  );
}

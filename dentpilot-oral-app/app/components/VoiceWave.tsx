type VoiceWaveProps = {
  active: boolean;
};

export default function VoiceWave({ active }: VoiceWaveProps) {
  return (
    <div className="flex h-8 items-center gap-1" aria-label={active ? "Voice active" : "Voice idle"}>
      {[0, 1, 2, 3, 4].map((bar) => (
        <span
          key={bar}
          className={`w-1.5 rounded-full bg-cyan-300 ${active ? "animate-pulse" : "opacity-35"}`}
          style={{
            height: active ? `${12 + ((bar + 1) % 3) * 8}px` : "10px",
            animationDelay: `${bar * 90}ms`
          }}
        />
      ))}
    </div>
  );
}

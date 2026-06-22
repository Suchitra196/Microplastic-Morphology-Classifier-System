interface ETIGaugeProps {
  score: number;   // 0–100
  color: string;
  size?: number;
}

export default function ETIGauge({ score, color, size = 80 }: ETIGaugeProps) {
  const r = (size / 2) * 0.78;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  // show ~270° arc (gap at bottom)
  const arcLen = circumference * 0.75;
  const offset = circumference - arcLen * Math.min(score / 100, 1);

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(135deg)" }}>
        {/* Track */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke="#1e1e1e"
          strokeWidth={6}
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeLinecap="round"
        />
        {/* Progress */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke={color}
          strokeWidth={6}
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.8s ease", filter: `drop-shadow(0 0 4px ${color})` }}
        />
      </svg>
      <span
        className="absolute font-bold"
        style={{ fontSize: size * 0.28, color }}
      >
        {Math.round(score)}
      </span>
    </div>
  );
}

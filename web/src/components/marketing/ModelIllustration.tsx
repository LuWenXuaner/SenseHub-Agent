const NODE_COLORS = ["#4a9eff", "#22c55e", "#ff6900"] as const;

type Props = { type: "plant" | "star" | "scale" | "ear" };

export function ModelIllustration({ type }: Props) {
  return (
    <svg viewBox="0 0 200 140" className="h-full w-full" aria-hidden>
      <rect width="200" height="140" fill="#f3f3f3" />
      {type === "plant" && <PlantArt />}
      {type === "star" && <StarArt />}
      {type === "scale" && <ScaleArt />}
      {type === "ear" && <EarArt />}
    </svg>
  );
}

function Dot({ cx, cy, color }: { cx: number; cy: number; color: string }) {
  return (
    <>
      <circle cx={cx} cy={cy} r={5} fill={color} />
      <circle cx={cx} cy={cy} r={8} fill="none" stroke={color} strokeOpacity={0.35} />
    </>
  );
}

function PlantArt() {
  return (
    <g stroke="#1a1a1a" strokeWidth="1.2" fill="none">
      <ellipse cx="100" cy="108" rx="36" ry="8" />
      <path d="M100 108 L100 72" />
      <path d="M100 88 Q78 78 72 58" />
      <path d="M100 80 Q122 68 128 48" />
      <path d="M100 95 Q85 92 80 75" />
      <Dot cx={72} cy={58} color={NODE_COLORS[0]} />
      <Dot cx={128} cy={48} color={NODE_COLORS[1]} />
    </g>
  );
}

function StarArt() {
  return (
    <g stroke="#1a1a1a" strokeWidth="1.2" fill="none">
      <rect x="78" y="100" width="44" height="12" rx="2" />
      <path d="M100 100 L100 78" />
      <circle cx="100" cy="62" r="22" />
      <path d="M100 48 L100 76 M86 62 L114 62 M90 50 L110 74 M110 50 L90 74" />
      <Dot cx={88} cy={54} color={NODE_COLORS[0]} />
      <Dot cx={112} cy={70} color={NODE_COLORS[0]} />
    </g>
  );
}

function ScaleArt() {
  return (
    <g stroke="#1a1a1a" strokeWidth="1.2" fill="none">
      <path d="M100 108 L100 70 L88 82 Z" />
      <line x1="55" y1="70" x2="145" y2="70" />
      <line x1="55" y1="70" x2="55" y2="78" />
      <line x1="145" y1="70" x2="145" y2="78" />
      <Dot cx={55} cy={78} color={NODE_COLORS[0]} />
      <Dot cx={100} cy={70} color={NODE_COLORS[1]} />
      <Dot cx={145} cy={78} color={NODE_COLORS[2]} />
    </g>
  );
}

function EarArt() {
  return (
    <g stroke="#1a1a1a" strokeWidth="1.2" fill="none">
      <path d="M108 45 C95 45 88 58 88 72 C88 92 100 100 108 108 C108 92 118 82 118 68 C118 54 112 45 108 45 Z" />
      <path d="M95 62 C95 72 100 78 104 82" strokeDasharray="3 3" />
      <Dot cx={92} cy={58} color={NODE_COLORS[0]} />
      <Dot cx={108} cy={48} color={NODE_COLORS[1]} />
      <Dot cx={118} cy={72} color={NODE_COLORS[2]} />
      <line x1={92} y1={58} x2={108} y2={48} stroke="#ccc" strokeWidth="0.8" strokeDasharray="2 2" />
      <line x1={108} y1={48} x2={118} y2={72} stroke="#ccc" strokeWidth="0.8" strokeDasharray="2 2" />
    </g>
  );
}

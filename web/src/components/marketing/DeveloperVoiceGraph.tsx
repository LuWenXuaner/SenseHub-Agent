import { VOICE_TAGS } from "@/lib/siteContent";
import { useInView } from "@/hooks/useInView";

export function DeveloperVoiceGraph() {
  const { ref, visible } = useInView();

  return (
    <section
      ref={ref}
      className={`mimo-section border-t bg-mimo-warm ${visible ? "mimo-in-view" : ""}`}
      style={{ borderColor: "var(--mimo-border)" }}
    >
      <div className="mimo-container">
        <h2 className="mimo-section-title-left">开发者的声音</h2>
        <p className="mt-2 max-w-xl text-sm text-mimo-muted">
          来自真实用户与合作伙伴的使用反馈，汇聚为灵枢持续优化的方向。
        </p>
        <div className="mimo-voice-cloud" aria-label="开发者声音关键词云">
          <svg className="mimo-voice-cloud-lines" viewBox="0 0 100 100" preserveAspectRatio="none">
            {VOICE_TAGS.filter((t) => t.tier === 2).map((tag) => {
              const hub = VOICE_TAGS.find((t) => t.id === tag.parentId);
              if (!hub) return null;
              return (
                <line
                  key={`line-${tag.id}`}
                  x1={hub.x}
                  y1={hub.y}
                  x2={tag.x}
                  y2={tag.y}
                  stroke="rgba(0,0,0,0.08)"
                  strokeWidth="0.15"
                />
              );
            })}
            {VOICE_TAGS.filter((t) => t.tier === 1).map((hub) => (
              <line
                key={`hub-${hub.id}`}
                x1={50}
                y1={50}
                x2={hub.x}
                y2={hub.y}
                stroke="rgba(0,0,0,0.1)"
                strokeWidth="0.2"
              />
            ))}
          </svg>

          <div className="mimo-voice-hub">开发者的声音</div>

          {VOICE_TAGS.map((tag) => (
            <span
              key={tag.id}
              className={`mimo-voice-tag mimo-voice-tag-tier-${tag.tier}`}
              style={
                {
                  left: `${tag.x}%`,
                  top: `${tag.y}%`,
                  "--dx": `${tag.driftX}px`,
                  "--dy": `${tag.driftY}px`,
                  "--delay": `${tag.delay}s`,
                  "--dur": `${tag.duration}s`,
                } as React.CSSProperties
              }
            >
              {tag.label}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

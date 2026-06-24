import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef, type ReactNode } from "react";

export function ScrollCarousel({
  children,
  className = "",
  controlsBottom = false,
}: {
  children: ReactNode;
  className?: string;
  controlsBottom?: boolean;
}) {
  const trackRef = useRef<HTMLDivElement>(null);

  const scroll = (dir: -1 | 1) => {
    const el = trackRef.current;
    if (!el) return;
    const step = Math.min(el.clientWidth * 0.85, 420);
    el.scrollBy({ left: dir * step, behavior: "smooth" });
  };

  const buttons = (
    <>
      <button
        type="button"
        className={controlsBottom ? "mimo-carousel-btn-bottom" : "mimo-carousel-btn mimo-carousel-btn-left"}
        onClick={() => scroll(-1)}
        aria-label="向左滚动"
      >
        <ChevronLeft size={18} />
      </button>
      <button
        type="button"
        className={controlsBottom ? "mimo-carousel-btn-bottom" : "mimo-carousel-btn mimo-carousel-btn-right"}
        onClick={() => scroll(1)}
        aria-label="向右滚动"
      >
        <ChevronRight size={18} />
      </button>
    </>
  );

  if (controlsBottom) {
    return (
      <div className={className}>
        <div ref={trackRef} className="mimo-carousel-track items-stretch">
          {children}
        </div>
        <div className="mimo-carousel-controls-bottom">{buttons}</div>
      </div>
    );
  }

  return (
    <div className={`mimo-carousel-wrap ${className}`}>
      {buttons}
      <div ref={trackRef} className="mimo-carousel-track items-stretch">
        {children}
      </div>
    </div>
  );
}

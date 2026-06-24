import { Link } from "react-router-dom";
import { getDocSection } from "@/lib/docsSections";

export function DocContentSection({
  id,
  title,
  locale,
}: {
  id: string;
  title: string;
  locale: "zh" | "en";
}) {
  const block = getDocSection(locale, id);
  if (!block) return null;

  return (
    <section id={id} className="scroll-mt-28 border-b border-mimo-border pb-10 last:border-0">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="mt-4 space-y-3 text-sm leading-7 text-mimo-muted">
        {block.paragraphs.map((p) => (
          <p key={p.slice(0, 24)}>{p}</p>
        ))}
      </div>
      {block.bullets && block.bullets.length > 0 && (
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-7 text-mimo-muted">
          {block.bullets.map((b) => (
            <li key={b.slice(0, 24)}>{b}</li>
          ))}
        </ul>
      )}
      {block.steps && block.steps.length > 0 && (
        <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm leading-7 text-mimo-muted">
          {block.steps.map((s) => (
            <li key={s.slice(0, 24)}>{s}</li>
          ))}
        </ol>
      )}
      {block.code && (
        <pre className="mt-4 overflow-x-auto rounded-xl border border-mimo-border bg-[#fafafa] p-4 font-mono text-xs leading-6 text-mimo-text">
          {block.code}
        </pre>
      )}
      {block.note && <p className="mt-4 text-xs text-mimo-accent">{block.note}</p>}
      {block.link && (
        <Link to={block.link.to} className="mimo-link-more mt-4 inline-block text-sm">
          {block.link.label} →
        </Link>
      )}
    </section>
  );
}

import { Link } from "react-router-dom";

export function ComingSoonPage({
  title,
  phase,
  tier,
}: {
  title: string;
  phase?: string;
  tier?: string;
}) {
  return (
    <div className="mx-auto max-w-lg space-y-4 text-center">
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="text-text-secondary">
        {phase && `${phase} 实现`}
        {tier && ` · 需要 ${tier.toUpperCase()} 档位`}
      </p>
      <p className="text-sm text-text-secondary">
        导航与布局已预留，功能将在后续 Phase 接入。
      </p>
      <Link to="/" className="btn-primary inline-flex">
        返回总览
      </Link>
    </div>
  );
}

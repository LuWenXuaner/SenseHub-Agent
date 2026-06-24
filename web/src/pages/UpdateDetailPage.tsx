import { Link, Navigate, useParams } from "react-router-dom";
import { getNewsBySlug } from "@/lib/siteContent";

export function UpdateDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const item = slug ? getNewsBySlug(slug) : undefined;
  if (!item) return <Navigate to="/updates" replace />;

  return (
    <div>
      <section className="mimo-page-hero">
        <div className="mimo-container max-w-3xl">
          <p className="text-sm text-mimo-muted">{item.date}</p>
          <h1 className="mimo-page-title mt-2">{item.title}</h1>
        </div>
      </section>
      <section className="mimo-section pt-0">
        <div className="mimo-container max-w-3xl">
          <div className="space-y-4 text-sm leading-7 text-mimo-muted md:text-base">
            {item.body.map((para) => (
              <p key={para}>{para}</p>
            ))}
          </div>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link to={item.ctaTo} className="mimo-btn-primary">
              {item.cta}
            </Link>
            <Link to="/updates" className="mimo-btn-outline">
              返回动态列表
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

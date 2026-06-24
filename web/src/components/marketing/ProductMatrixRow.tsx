import { Link } from "react-router-dom";
import type { ProductMatrixItem } from "@/lib/siteContent";

export function ProductMatrixRow({ items }: { items: ProductMatrixItem[] }) {
  return (
    <div className="mimo-product-matrix mimo-reveal-stagger">
      {items.map((item) => (
        <article key={item.id} className="mimo-matrix-card mimo-hover-lift mimo-reveal-item">
          <h3 className="mimo-matrix-title">{item.title}</h3>
          <p className="mimo-matrix-desc">{item.summary}</p>
          <Link
            to={item.appPath}
            className={
              item.ctaStyle === "primary" ? "mimo-matrix-cta mt-auto" : "mimo-matrix-cta-outline mt-auto"
            }
          >
            {item.cta} →
          </Link>
        </article>
      ))}
    </div>
  );
}

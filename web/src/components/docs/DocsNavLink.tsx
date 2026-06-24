import { Link, useLocation } from "react-router-dom";

/** 文档侧栏链接：正确处理 /product/api#anchor 滚动 */
export function DocsNavLink({ to, label }: { to: string; label: string }) {
  const location = useLocation();

  if (!to) {
    return <span className="mimo-docs-nav-item text-mimo-muted">{label}</span>;
  }

  const hashIdx = to.indexOf("#");
  const path = hashIdx >= 0 ? to.slice(0, hashIdx) : to;
  const hash = hashIdx >= 0 ? to.slice(hashIdx + 1) : "";

  const scrollToHash = (id: string) => {
    window.requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const onHashClick = (e: React.MouseEvent) => {
    if (!hash) return;
    const onDocPage = location.pathname === path || location.pathname.endsWith("/product/api");
    if (onDocPage) {
      e.preventDefault();
      scrollToHash(hash);
      window.history.replaceState(null, "", `${path}#${hash}`);
    }
  };

  if (hash) {
    return (
      <a href={to} className="mimo-docs-nav-item" onClick={onHashClick}>
        {label}
      </a>
    );
  }

  if (to.startsWith("/")) {
    return (
      <Link to={to} className="mimo-docs-nav-item">
        {label}
      </Link>
    );
  }

  return (
    <a href={to} className="mimo-docs-nav-item">
      {label}
    </a>
  );
}

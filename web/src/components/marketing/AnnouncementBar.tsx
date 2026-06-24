import { Link } from "react-router-dom";
import { useLocale } from "@/context/LocaleContext";

export function AnnouncementBar() {
  const { t } = useLocale();
  const a = t.announce;

  return (
    <div className="mimo-announce-bar">
      <div className="mimo-announce-track" aria-hidden>
        {[0, 1].map((i) => (
          <span key={i} className="mimo-announce-item">
            {a.message}
            <Link to="/token-plan" className="mimo-announce-link">
              {a.link}
            </Link>
          </span>
        ))}
      </div>
    </div>
  );
}

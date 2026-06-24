import { useInView } from "@/hooks/useInView";
import { useLocale } from "@/context/LocaleContext";

export function AboutSection() {
  const { ref, visible } = useInView();
  const { t } = useLocale();

  return (
    <section
      ref={ref}
      className={`mimo-section mimo-about ${visible ? "mimo-in-view" : ""}`}
      id="about"
    >
      <div className="mimo-container max-w-3xl">
        <h2 className="mimo-section-title-left">{t.home.about}</h2>
        <p className="mimo-about-lead mt-4 text-left">{t.about.lead}</p>
        <p className="mimo-about-body text-left">{t.about.body}</p>
      </div>
    </section>
  );
}

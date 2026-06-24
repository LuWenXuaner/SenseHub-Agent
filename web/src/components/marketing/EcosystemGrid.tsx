import type { EcosystemPartner } from "@/lib/siteContent";
import { PartnerIcon } from "./PartnerIcon";

export function EcosystemGrid({ partners }: { partners: EcosystemPartner[] }) {
  return (
    <div className="mimo-eco-grid mimo-reveal-stagger">
      {partners.map((p) => (
        <div key={p.id} className="mimo-eco-card mimo-hover-lift mimo-reveal-item">
          <PartnerIcon partner={p} />
          <span className="mimo-eco-name">{p.name}</span>
        </div>
      ))}
    </div>
  );
}

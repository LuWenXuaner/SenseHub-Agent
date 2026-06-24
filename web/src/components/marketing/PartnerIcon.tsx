import { useState } from "react";
import { Sparkles } from "lucide-react";
import type { EcosystemPartner } from "@/lib/siteContent";

export function PartnerIcon({ partner, size = 16 }: { partner: EcosystemPartner; size?: number }) {
  const [imgOk, setImgOk] = useState(Boolean(partner.iconUrl && !partner.iconLocal));

  return (
    <span className="mimo-eco-icon-wrap" aria-hidden>
      <span className="mimo-eco-icon mimo-eco-icon-fallback">{partner.fallback}</span>
      {partner.iconLocal ? (
        <span className="mimo-eco-icon mimo-eco-icon-local mimo-eco-icon-overlay">
          <Sparkles size={size} />
        </span>
      ) : partner.iconUrl && imgOk ? (
        <img
          src={partner.iconUrl}
          alt=""
          className="mimo-eco-icon-img mimo-eco-icon-overlay"
          loading="lazy"
          onError={() => setImgOk(false)}
        />
      ) : null}
    </span>
  );
}

/** 灵枢 Chat 专属对话头像（36px 圆形 + 极细描边） */

import { useId, type ReactNode } from "react";

function AvatarFrame({ children }: { children: ReactNode }) {
  return (
    <span className="mimo-studio-chat-avatar" aria-hidden>
      {children}
    </span>
  );
}

export function UserStudioAvatar() {
  const uid = useId().replace(/:/g, "");

  return (
    <AvatarFrame>
      <svg viewBox="0 0 36 36" className="h-full w-full" fill="none" aria-hidden>
        <defs>
          <linearGradient id={`${uid}-bg`} x1="6" y1="4" x2="30" y2="32" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FFF4F8" />
            <stop offset="1" stopColor="#FFEDE4" />
          </linearGradient>
          <linearGradient id={`${uid}-hair`} x1="8" y1="7" x2="28" y2="24" gradientUnits="userSpaceOnUse">
            <stop stopColor="#F8B4C4" />
            <stop offset="1" stopColor="#E895A8" />
          </linearGradient>
          <radialGradient id={`${uid}-skin`} cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(18 20.5) scale(7.5)">
            <stop stopColor="#FFE9DC" />
            <stop offset="1" stopColor="#FFD0B8" />
          </radialGradient>
          <linearGradient id={`${uid}-bow`} x1="24" y1="11" x2="30" y2="17" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FFC4D6" />
            <stop offset="1" stopColor="#FF9DB8" />
          </linearGradient>
        </defs>
        <circle cx="18" cy="18" r="18" fill={`url(#${uid}-bg)`} />
        <path
          d="M7.5 18.5c0-6.8 4.6-11.5 10.5-11.5S28.5 11.7 28.5 18.5c0 1.6-.3 3.1-.9 4.5H8.4c-.6-1.4-.9-2.9-.9-4.5z"
          fill={`url(#${uid}-hair)`}
        />
        <ellipse cx="18" cy="21" rx="7.5" ry="8.2" fill={`url(#${uid}-skin)`} />
        <path
          d="M11 16.2c1.6-3.4 3.8-5 7-5s5.4 1.6 7 5"
          stroke="#E895A8"
          strokeWidth="1.1"
          strokeLinecap="round"
        />
        <path d="M11.8 15.5c1.4-2.6 3.4-4 6.2-4s4.8 1.4 6.2 4" fill="#F8B4C4" />
        <ellipse cx="14.6" cy="20.2" rx="1.25" ry="1.55" fill="#5C4A52" />
        <ellipse cx="21.4" cy="20.2" rx="1.25" ry="1.55" fill="#5C4A52" />
        <circle cx="15" cy="19.5" r="0.45" fill="#fff" opacity="0.85" />
        <circle cx="21.8" cy="19.5" r="0.45" fill="#fff" opacity="0.85" />
        <ellipse cx="12.2" cy="23.2" rx="1.8" ry="1.1" fill="#FFB8CA" opacity="0.42" />
        <ellipse cx="23.8" cy="23.2" rx="1.8" ry="1.1" fill="#FFB8CA" opacity="0.42" />
        <path d="M15 24.2c1.6 1.2 4.4 1.2 6 0" stroke="#D88A9A" strokeWidth="1" strokeLinecap="round" />
        <circle cx="26.5" cy="13.5" r="2.2" fill={`url(#${uid}-bow)`} />
        <ellipse cx="24.8" cy="13.5" rx="1.1" ry="1.6" fill="#FF8EAE" opacity="0.55" />
        <ellipse cx="28.2" cy="13.5" rx="1.1" ry="1.6" fill="#FF8EAE" opacity="0.55" />
        <circle cx="26.5" cy="13.5" r="0.65" fill="#FFE8F0" />
      </svg>
    </AvatarFrame>
  );
}

export function AgentStudioAvatar() {
  const uid = useId().replace(/:/g, "");

  return (
    <AvatarFrame>
      <svg viewBox="0 0 36 36" className="h-full w-full" fill="none" aria-hidden>
        <defs>
          <linearGradient id={`${uid}-bg`} x1="5" y1="3" x2="31" y2="33" gradientUnits="userSpaceOnUse">
            <stop stopColor="#F2F7FB" />
            <stop offset="1" stopColor="#D9E6F2" />
          </linearGradient>
          <linearGradient id={`${uid}-head`} x1="9" y1="8" x2="27" y2="24" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FAFCFE" />
            <stop offset="0.55" stopColor="#D4E3EF" />
            <stop offset="1" stopColor="#A8C0D4" />
          </linearGradient>
          <linearGradient id={`${uid}-body`} x1="11" y1="23" x2="25" y2="33" gradientUnits="userSpaceOnUse">
            <stop stopColor="#E4EDF5" />
            <stop offset="1" stopColor="#AFC4D6" />
          </linearGradient>
          <radialGradient id={`${uid}-eye`} cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(14.5 16) scale(2.5)">
            <stop stopColor="#8ED4FF" />
            <stop offset="1" stopColor="#4A9FD4" />
          </radialGradient>
          <radialGradient id={`${uid}-glow`} cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(18 5) scale(4)">
            <stop stopColor="#9ED8FF" stopOpacity="0.75" />
            <stop offset="1" stopColor="#9ED8FF" stopOpacity="0" />
          </radialGradient>
          <filter id={`${uid}-soft`} x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0.5" stdDeviation="0.4" floodColor="#6B9BB8" floodOpacity="0.25" />
          </filter>
        </defs>
        <circle cx="18" cy="18" r="18" fill={`url(#${uid}-bg)`} />
        <circle cx="18" cy="5" r="3.2" fill={`url(#${uid}-glow)`} />
        <path d="M18 7.5v3.2" stroke="#9BB8CC" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="18" cy="6.2" r="1.7" fill="#7EB8DC" filter={`url(#${uid}-soft)`} />
        <circle cx="18" cy="6.2" r="0.75" fill="#E8F6FF" />
        <rect x="7.5" y="11" width="21" height="14.5" rx="7.2" fill={`url(#${uid}-head)`} />
        <path d="M9.5 13.2h11.5a2.5 2.5 0 0 1 2.5 2.5v1.8H9.5V13.2z" fill="#fff" opacity="0.42" />
        <rect x="11.2" y="15.2" width="5" height="5" rx="2" fill={`url(#${uid}-eye)`} />
        <rect x="19.8" y="15.2" width="5" height="5" rx="2" fill={`url(#${uid}-eye)`} />
        <circle cx="12.5" cy="16.2" r="1" fill="#EAF7FF" />
        <circle cx="21.1" cy="16.2" r="1" fill="#EAF7FF" />
        <rect x="14.5" y="19.8" width="7" height="2.4" rx="1.2" fill="#8FAEC4" />
        <rect x="15.6" y="20.2" width="1.3" height="1.6" rx="0.35" fill="#D8EBF8" />
        <rect x="17.3" y="20.2" width="1.3" height="1.6" rx="0.35" fill="#D8EBF8" />
        <rect x="19" y="20.2" width="1.3" height="1.6" rx="0.35" fill="#D8EBF8" />
        <rect x="9.5" y="24" width="17" height="9.5" rx="4.8" fill={`url(#${uid}-body)`} />
        <path d="M11.5 25.8h6.5v3H11.5z" fill="#fff" opacity="0.28" />
        <circle cx="18" cy="28.2" r="1.5" fill="#7FA8C4" opacity="0.5" />
        <rect x="4.5" y="24.5" width="4.5" height="8" rx="2.2" fill="#C5D8E8" />
        <rect x="27" y="24.5" width="4.5" height="8" rx="2.2" fill="#C5D8E8" />
        <rect x="5.2" y="25.8" width="1.6" height="3.2" rx="0.8" fill="#EAF2FA" opacity="0.75" />
        <rect x="28.7" y="25.8" width="1.6" height="3.2" rx="0.8" fill="#EAF2FA" opacity="0.75" />
        <path d="M6.5 28.5h2.5M27 28.5h2.5" stroke="#A8BFD4" strokeWidth="0.9" strokeLinecap="round" opacity="0.7" />
      </svg>
    </AvatarFrame>
  );
}

export function StudioAvatarPlaceholder() {
  return <span className="mimo-studio-chat-avatar-slot" aria-hidden />;
}

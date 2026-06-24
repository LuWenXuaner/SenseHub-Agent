/** 对话区卡通头像 */

export function UserChatAvatar() {
  return (
    <span
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-sky-400 to-blue-500 shadow-sm"
      aria-hidden
    >
      <svg viewBox="0 0 32 32" className="h-6 w-6" fill="none">
        <circle cx="16" cy="12" r="6" fill="#FFE0BD" />
        <path d="M6 28c1.5-6 7-9 10-9s8.5 3 10 9" fill="#FFE0BD" />
        <circle cx="13.5" cy="11.5" r="1" fill="#374151" />
        <circle cx="18.5" cy="11.5" r="1" fill="#374151" />
        <path d="M14 14.5c1 1 3 1 4 0" stroke="#374151" strokeWidth="1" strokeLinecap="round" />
      </svg>
    </span>
  );
}

export function AgentChatAvatar() {
  return (
    <span
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-400 to-indigo-500 shadow-sm"
      aria-hidden
    >
      <svg viewBox="0 0 32 32" className="h-6 w-6" fill="none">
        <rect x="8" y="10" width="16" height="14" rx="4" fill="#E0E7FF" />
        <rect x="10" y="13" width="4" height="4" rx="1" fill="#4F46E5" />
        <rect x="18" y="13" width="4" height="4" rx="1" fill="#4F46E5" />
        <path d="M13 20h6" stroke="#4F46E5" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="16" y1="6" x2="16" y2="10" stroke="#C7D2FE" strokeWidth="2" />
        <circle cx="16" cy="5" r="2" fill="#FDE68A" />
        <rect x="5" y="14" width="3" height="6" rx="1.5" fill="#C7D2FE" />
        <rect x="24" y="14" width="3" height="6" rx="1.5" fill="#C7D2FE" />
      </svg>
    </span>
  );
}

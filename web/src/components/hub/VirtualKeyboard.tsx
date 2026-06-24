const ROWS = [
  ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
  ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
  ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
  ["z", "x", "c", "v", "b", "n", "m"],
];

export function VirtualKeyboard({ onKey }: { onKey: (key: string) => void | Promise<void> }) {
  return (
    <div className="space-y-1 rounded-lg border border-border bg-surface-elevated p-2">
      {ROWS.map((row, i) => (
        <div key={i} className="flex flex-wrap justify-center gap-1">
          {row.map((k) => (
            <button
              key={k}
              type="button"
              className="min-w-[2rem] rounded border border-border bg-surface px-2 py-1.5 text-sm hover:border-primary"
              onClick={() => onKey(k)}
            >
              {k}
            </button>
          ))}
        </div>
      ))}
      <div className="flex justify-center gap-1 pt-1">
        <button type="button" className="btn-ghost text-xs border border-border" onClick={() => onKey("Space")}>
          空格
        </button>
        <button type="button" className="btn-ghost text-xs border border-border" onClick={() => onKey("Backspace")}>
          退格
        </button>
        <button type="button" className="btn-ghost text-xs border border-border" onClick={() => onKey("Enter")}>
          回车
        </button>
      </div>
    </div>
  );
}

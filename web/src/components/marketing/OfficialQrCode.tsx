/** 官方二维码 */
export function OfficialQrCode({
  label = "扫码关注",
  compact = false,
}: {
  label?: string;
  compact?: boolean;
}) {
  return (
    <div className={`mimo-qr-block ${compact ? "mimo-qr-block-compact" : ""}`}>
      <div className={`mimo-qr-placeholder ${compact ? "mimo-qr-placeholder-compact" : ""}`}>
        <img
          src="/assets/official-qrcode.png"
          alt={label}
          className="h-full w-full object-contain"
          loading="lazy"
        />
      </div>
      {!compact && <p className="mimo-qr-label">{label}</p>}
    </div>
  );
}

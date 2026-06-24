/** 官方二维码 */
export function OfficialQrCode({ label = "扫码关注" }: { label?: string }) {
  return (
    <div className="mimo-qr-block">
      <div className="mimo-qr-placeholder overflow-hidden p-1">
        <img
          src="/assets/official-qrcode.png"
          alt={label}
          className="h-full w-full object-contain"
          loading="lazy"
        />
      </div>
      <p className="mimo-qr-label">{label}</p>
    </div>
  );
}

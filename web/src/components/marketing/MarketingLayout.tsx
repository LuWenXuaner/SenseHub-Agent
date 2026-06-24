import { Outlet } from "react-router-dom";
import { AnnouncementBar } from "./AnnouncementBar";
import { MarketingHeader } from "./MarketingHeader";
import { MarketingFooter } from "./MarketingFooter";

/** MiMo 风格营销站：公告条 + 顶栏 + 内容 + 页脚 */
export function MarketingLayout() {
  return (
    <div className="mimo-site flex min-h-screen flex-col text-mimo-text">
      <AnnouncementBar />
      <MarketingHeader />
      <main className="flex-1">
        <Outlet />
      </main>
      <MarketingFooter />
    </div>
  );
}

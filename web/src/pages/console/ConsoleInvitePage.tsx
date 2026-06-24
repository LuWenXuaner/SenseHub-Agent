import { useEffect, useState } from "react";
import { ConsolePageFrame } from "@/components/mimo/ConsolePageFrame";
import { InviteFriendsModal } from "@/components/mimo/InviteFriendsModal";
import { InviteProgressPanel, InviteRulesPanel } from "@/components/mimo/InvitePanels";
import { useLocale } from "@/context/LocaleContext";
import { api, type InviteRow } from "@/lib/api";

export function ConsoleInvitePage() {
  const { t, fmt } = useLocale();
  const it = t.inviteTable;
  const [modalOpen, setModalOpen] = useState(false);
  const [tab, setTab] = useState<"list" | "progress" | "rules">("list");
  const [rows, setRows] = useState<InviteRow[]>([]);

  useEffect(() => {
    api.invitesOverview().then((r) => setRows(r.items)).catch(() => setRows([]));
  }, [modalOpen]);

  return (
    <>
      <ConsolePageFrame
        title={t.console.inviteMgmt}
        subtitle={t.points.inviteDesc}
        actions={
          <button type="button" className="mimo-btn-cta mimo-btn-sm" onClick={() => setModalOpen(true)}>
            {t.console.invite}
          </button>
        }
      >
        <InviteProgressPanel />

        <div className="mt-8 flex gap-6 border-b border-mimo-border">
          {(
            [
              { id: "list", label: it.listTab },
              { id: "progress", label: t.invite.tabProgress },
              { id: "rules", label: t.invite.tabRules },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              className={`mimo-console-tab ${tab === item.id ? "mimo-console-tab-active" : ""}`}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {tab === "list" && (
          <div className="mimo-console-panel mt-4 overflow-x-auto p-0">
            <table className="mimo-console-table w-full text-left text-sm">
              <thead>
                <tr>
                  <th>{it.inviteeId}</th>
                  <th>{it.channel}</th>
                  <th>{it.status}</th>
                  <th>{it.time}</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-10 text-center text-mimo-muted">
                      {t.common.noData}
                    </td>
                  </tr>
                ) : (
                  rows.map((r) => (
                    <tr key={r.id}>
                      <td>{r.invitee_id}</td>
                      <td>{it.channelLink}</td>
                      <td>{r.status === "registered" ? it.statusRegistered : it.statusPending}</td>
                      <td className="text-mimo-muted">{r.registered_at || r.created_at}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            <p className="px-4 py-3 text-right text-xs text-mimo-muted">{fmt(it.total, { n: rows.length })}</p>
          </div>
        )}

        {tab === "progress" && (
          <div className="mt-4">
            <InviteProgressPanel compact />
          </div>
        )}

        {tab === "rules" && (
          <div className="mt-4">
            <InviteRulesPanel />
          </div>
        )}
      </ConsolePageFrame>
      <InviteFriendsModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </>
  );
}

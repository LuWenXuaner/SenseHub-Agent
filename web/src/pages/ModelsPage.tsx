import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CompactRow, SystemCard, SystemPageLayout } from "@/components/layout/SystemPageLayout";
import { Link } from "react-router-dom";

interface RoleRow {
  role: string;
  provider: string;
  provider_label: string;
  model: string;
  configured: boolean;
}

interface ModelsConfig {
  roles?: Record<string, { model?: string; provider?: string }>;
  paths: Record<string, string>;
  inference_device: string;
  use_cuda: boolean;
}

export function ModelsPage() {
  const [cfg, setCfg] = useState<ModelsConfig | null>(null);
  const [roles, setRoles] = useState<RoleRow[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([api.modelsConfig(), api.getApiConfig()])
      .then(([m, apiCfg]) => {
        setCfg(m as ModelsConfig);
        setRoles((apiCfg as { roles?: RoleRow[] }).roles || []);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "加载失败"));
  }, []);

  if (err) {
    return (
      <SystemPageLayout title="模型" description="角色路由与本地推理">
        <p className="text-xs text-danger">{err}</p>
      </SystemPageLayout>
    );
  }

  if (!cfg) {
    return (
      <SystemPageLayout title="模型" description="角色路由与本地推理">
        <p className="text-xs text-text-secondary">加载中…</p>
      </SystemPageLayout>
    );
  }

  return (
    <SystemPageLayout
      title="模型"
      description="角色→提供商→模型（config/models.yaml）· API Key 在设置页配置"
      footer={
        <span className="text-text-secondary">
          切换 OpenAI / DeepSeek / MiMo 等：修改 models.yaml 中 roles.provider，并在
          <Link to="/system/settings" className="mx-1 text-primary hover:underline">
            设置
          </Link>
          填写对应 Key
        </span>
      }
    >
      <div className="grid h-full min-h-0 grid-cols-1 gap-2 lg:grid-cols-5">
        <SystemCard title="LLM 角色路由" className="lg:col-span-3">
          <table className="w-full text-xs">
            <thead className="text-text-secondary">
              <tr>
                <th className="pb-1 text-left font-medium">角色</th>
                <th className="pb-1 text-left font-medium">提供商</th>
                <th className="pb-1 text-left font-medium">模型</th>
                <th className="pb-1 text-center font-medium">Key</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.role} className="border-t border-border/40">
                  <td className="py-1 pr-2 font-medium capitalize">{r.role}</td>
                  <td className="py-1 pr-2">{r.provider_label || r.provider}</td>
                  <td className="max-w-[8rem] truncate py-1 pr-2 font-mono" title={r.model}>
                    {r.model}
                  </td>
                  <td className="py-1 text-center">{r.configured ? "✓" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </SystemCard>

        <SystemCard title="本地推理" className="lg:col-span-2">
          <CompactRow label="设备" value={cfg.inference_device} />
          <CompactRow label="CUDA" value={cfg.use_cuda ? "开" : "关"} />
          {Object.entries(cfg.paths || {})
            .filter(([, v]) => v)
            .map(([k, v]) => (
              <CompactRow key={k} label={k} value={v} />
            ))}
        </SystemCard>
      </div>
    </SystemPageLayout>
  );
}

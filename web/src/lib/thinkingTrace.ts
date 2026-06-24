import type { ChatTurn, PlanStep, StepResult, Task } from "@/lib/api";
import type { HubCommandResult, VoiceCommandResult } from "@/lib/api";

export type StepStatus = "pending" | "running" | "done" | "error";
export type ThinkingStep = { id: string; label: string; detail?: string; status: StepStatus };

export const TOOL_LABEL: Record<string, string> = {
  open_app: "打开应用",
  close_app: "关闭应用",
  focus_window: "切换窗口",
  minimize_window: "最小化窗口",
  maximize_window: "最大化窗口",
  list_windows: "查看窗口列表",
  active_window: "查看前台窗口",
  type_text: "输入文字",
  press_key: "按键操作",
  hotkey: "快捷键",
  click: "鼠标点击",
  web_search: "浏览器搜索",
  open_url: "打开网页",
  fetch_url: "抓取网页内容",
  get_weather: "查询天气",
  screenshot: "截取屏幕",
  write_file: "写入文件",
  read_file: "读取文件",
  list_dir: "列出目录",
  copy_file: "复制文件",
  open_folder: "打开文件夹",
  get_datetime: "获取时间",
  get_clipboard: "读取剪贴板",
  set_clipboard: "写入剪贴板",
  notify: "系统通知",
  virtual_screen_start: "开启虚拟屏",
  virtual_screen_stop: "关闭虚拟屏",
  browser_tabs: "浏览器标签",
  browser_snapshot: "页面快照",
  browser_navigate: "打开网页",
  browser_act: "页面操作",
  browser_status: "浏览器状态",
  gui_agent: "屏幕智能操作",
};

export function formatUserFacingError(msg: string): string {
  const t = msg.trim();
  if (!t) return "执行遇到问题，请稍后重试";
  if (t.includes("意图脑不可用")) {
    return "大脑服务暂时不可用，请检查模型 API 配置或网络后重试";
  }
  if (t.includes("沙箱未授权") || t.includes("路径不在允许范围")) {
    return `${t}。可将文件保存到工作区，或在对话里确认授权后重试，也可前往「安全中心」添加目录。`;
  }
  if (t.includes("AbortError") || t.includes("aborted")) {
    return "已停止执行";
  }
  if (t.includes("NoneType") && t.includes("success")) {
    return "执行链内部错误（待确认步骤处理异常），请重试；若涉及写入 I 盘等路径，确认后应出现确认按钮。";
  }
  return t;
}

function formatToolParams(step: PlanStep): string {
  const p = step.params || {};
  if (step.tool === "type_text" && p.text) return `内容「${String(p.text).slice(0, 40)}」`;
  if (step.tool === "active_window") return "确认当前焦点窗口";
  if (step.tool === "focus_window" && (p.title || p.name)) return `窗口 ${p.title || p.name}`;
  if (step.tool === "write_file" && p.path) return `路径 ${p.path}`;
  if (step.tool === "open_app" && p.name) return `应用 ${p.name}`;
  if (step.tool === "web_search" && p.query) return `关键词 ${p.query}`;
  if (step.tool === "press_key" || step.tool === "hotkey") {
    const keys = p.keys || p.key;
    if (keys) return `按键 ${Array.isArray(keys) ? keys.join("+") : keys}`;
  }
  return step.description || "";
}

function formatStepResult(step: PlanStep, result?: StepResult): string {
  if (result?.error) return formatUserFacingError(result.error);
  const out = (result?.output || {}) as Record<string, unknown>;
  if (out.path) return `完成 · 文件位置：${out.path}`;
  if (step.tool === "type_text") {
    const win = out.foreground_window ? String(out.foreground_window) : "";
    return win ? `已输入到「${win}」` : "文字已输入到当前窗口";
  }
  if (step.tool === "active_window" && out.title) return `前台窗口：${out.title}`;
  if (step.tool === "list_windows" && out.count != null) return `共 ${out.count} 个可见窗口`;
  if (step.tool === "open_app") {
    if (out.already_running) {
      const win = out.focused_window ? String(out.focused_window) : "";
      return win ? `已在运行，已聚焦「${win}」` : `已在运行，未重复启动`;
    }
    const count = out.window_count;
    if (count != null && Number(count) > 1) {
      return `已启动，但匹配到 ${count} 个窗口，请确认是否为登录窗`;
    }
    return `已启动 ${out.name || step.params?.name || "应用"}`;
  }
  if (step.tool === "write_file") return out.path ? `已保存到 ${out.path}` : "文件已写入";
  if (step.tool === "get_weather") {
    const loc = out.location ? String(out.location) : "";
    const src = out.source ? String(out.source) : "天气服务";
    const forecasts = Array.isArray(out.forecasts) ? out.forecasts : [];
    const preview = forecasts
      .slice(0, 3)
      .map((f: Record<string, unknown>) => {
        const date = f.date || "";
        const min = f.min_temp_c ?? "";
        const max = f.max_temp_c ?? "";
        return `${date} ${min}–${max}℃`;
      })
      .join("；");
    return `已从 ${src} 拉取${loc ? `「${loc}」` : ""} ${forecasts.length} 天预报${preview ? `（${preview}）` : ""}`;
  }
  if (step.tool === "fetch_url" && out.url) return `已抓取 ${out.url}`;
  if (step.tool === "screenshot" && out.screenshot_path) return "截图已保存";
  if (step.tool === "browser_snapshot" && out.ref_count != null) return `页面元素 ${out.ref_count} 个`;
  if (step.tool === "browser_navigate" && out.url) return `已打开 ${out.url}`;
  if (step.tool === "gui_agent") return "屏幕智能操作";
  if (step.description) return String(step.description);
  return result?.success === false ? "未成功" : "已完成";
}

function planChain(steps: PlanStep[]): string {
  if (!steps.length) return "";
  return steps
    .map((s, i) => {
      const name = TOOL_LABEL[s.tool] || s.tool;
      const extra = formatToolParams(s);
      return `第${i + 1}步 ${name}${extra ? `（${extra}）` : ""}`;
    })
    .join(" → ");
}

export function agentSource(res: HubCommandResult | VoiceCommandResult): Array<Record<string, unknown>> {
  if ("agents" in res && Array.isArray(res.agents)) return res.agents;
  return [];
}

export function taskFromResponse(res: HubCommandResult | VoiceCommandResult): Task | undefined {
  if ("task" in res && res.task && typeof res.task === "object") return res.task as Task;
  return undefined;
}

export function isTerminalTask(task?: Task | null): boolean {
  return Boolean(task && ["done", "failed", "cancelled"].includes(task.status));
}

export function isInternalSummary(text: string): boolean {
  return /意图:|规划:\d+步|执行:\d+步/.test(text);
}

export function buildChatHistory(
  logs: Array<{ role: string; text: string; taskSnapshot?: Task }>
): ChatTurn[] {
  const history: ChatTurn[] = [];
  for (const log of logs) {
    if (log.role === "user" && log.text.trim()) {
      history.push({ role: "user", content: log.text.trim() });
      continue;
    }
    if (log.role === "system" && log.text.trim()) {
      const turn: ChatTurn = { role: "assistant", content: log.text.trim() };
      if (log.taskSnapshot) {
        turn.task = {
          task_id: log.taskSnapshot.task_id,
          intent_text: log.taskSnapshot.intent_text,
          summary: log.taskSnapshot.summary,
          status: log.taskSnapshot.status,
          plan_steps: log.taskSnapshot.plan_steps,
          step_results: log.taskSnapshot.step_results,
        };
      }
      history.push(turn);
    }
  }
  return history.slice(-12);
}

function extractPathsFromTask(task: Task): string[] {
  const found: string[] = [];
  for (const result of task.step_results || []) {
    if (!result.success) continue;
    const out = result.output as Record<string, unknown> | undefined;
    if (!out) continue;
    for (const key of ["path", "dst", "src", "screenshot_path", "opened"]) {
      const val = out[key];
      if (val && !found.includes(String(val))) found.push(String(val));
    }
  }
  return found;
}

export function buildThinkingSteps(
  res: HubCommandResult | VoiceCommandResult,
  task?: Task | null
): ThinkingStep[] {
  const steps: ThinkingStep[] = [];
  let idx = 0;
  let displayStep = 0;
  const push = (title: string, detail?: string, status: StepStatus = "done") => {
    displayStep += 1;
    steps.push({ id: `s-${idx++}`, label: `${displayStep}. ${title}`, detail, status });
  };

  for (const raw of agentSource(res)) {
    const agent = (raw || {}) as Record<string, unknown>;
    const role = String(agent.role || "");
    if (role === "intent") {
      const goal = String(agent.goal || "").trim();
      const wants = String(agent.user_wants || "").trim();
      push(
        "意图分析",
        wants ? `${goal || "分析你的目标"}（期望：${wants === "text_answer" ? "文字回答" : wants === "desktop_action" ? "操作电脑" : "操作+说明"}）` : goal || "理解你想完成的事"
      );
    } else if (role === "intent_guard" || role === "harness") {
      const reason = String(agent.reason || "").trim();
      push(role === "harness" ? "编排校验" : "智能分流", reason || "调整执行链路");
    } else if (role === "planner") {
      const summary = String(agent.summary || "").trim();
      const planSteps = Array.isArray(agent.steps) ? (agent.steps as PlanStep[]) : [];
      const chain = planChain(planSteps);
      push("方案规划", chain || summary || `共 ${planSteps.length} 个步骤`);
    } else if (role === "safety") {
      const passed = Boolean(agent.passed);
      push("安全审查", passed ? "操作风险可接受，允许执行" : String(agent.reason || "已拦截"), passed ? "done" : "error");
    } else if (role === "skill") {
      push("加载规程", String(agent.name || agent.id || "Skill"));
    } else if (role === "agent_loop") {
      const thought = String(agent.thought || "").trim();
      const tool = String(agent.tool || "");
      const detail = [thought, tool ? `→ ${TOOL_LABEL[tool] || tool}` : ""].filter(Boolean).join(" ");
      const status: StepStatus =
        agent.status === "wait_confirm" ? "running" : agent.error ? "error" : "done";
      if (detail || agent.iteration) {
        push("执行脑", detail || "选择工具并执行", status);
      }
    } else if (role === "executor") {
      const tool = String(agent.tool || "");
      const ok = Boolean(agent.success);
      const output = (agent.output || {}) as Record<string, unknown>;
      const fakeStep = {
        step_id: 0,
        tool,
        params: (agent.params as Record<string, unknown>) || {},
        risk_level: "L1",
        description: String(agent.description || ""),
      } as PlanStep;
      push(
        TOOL_LABEL[tool] || tool,
        formatStepResult(fakeStep, {
          step_id: 0,
          success: ok,
          output,
          error: ok ? undefined : String(agent.error || "失败"),
        }),
        ok ? "done" : "error"
      );
    } else if (role === "answer") {
      push("汇总答复", "已整理成你可以直接阅读的结果");
    }
  }

  if (task) {
    if (task.status === "wait_confirm") {
      push("等待确认", "含高风险步骤，确认后才会继续", "running");
    }
  } else if (
    "task_id" in res &&
    res.task_id &&
    !isTerminalTask(task) &&
    !agentSource(res).some((a) => a.role === "executor")
  ) {
    push("开始执行", "任务已提交，正在逐步调用工具…", "running");
  }

  return steps;
}

export function buildTaskProgressSteps(task: Task, stepOffset = 0): ThinkingStep[] {
  const steps: ThinkingStep[] = [];
  let n = stepOffset;
  task.plan_steps.forEach((step, i) => {
    const result = task.step_results.find((r) => r.step_id === step.step_id);
    let status: StepStatus = "pending";
    if (result) status = result.success ? "done" : "error";
    else if (task.current_step > i) status = "done";
    else if (task.current_step === i + 1 || task.status === "running") status = "running";

    const paramsHint = formatToolParams(step);
    n += 1;
    steps.push({
      id: `task-${step.step_id}`,
      label: `${n}. ${TOOL_LABEL[step.tool] || step.tool}`,
      detail: result
        ? formatStepResult(step, result)
        : status === "running"
          ? `正在执行…${paramsHint ? ` ${paramsHint}` : ""}`
          : paramsHint || step.description,
      status,
    });
  });

  if (task.status === "done") {
    n += 1;
    steps.push({ id: "task-answer", label: `${n}. 汇总答复`, detail: "全部步骤已完成", status: "done" });
  } else if (task.status === "failed") {
    n += 1;
    steps.push({
      id: "task-fail",
      label: `${n}. 执行中止`,
      detail: formatUserFacingError(task.error || "任务失败"),
      status: "error",
    });
  } else if (task.status === "cancelled") {
    n += 1;
    steps.push({ id: "task-cancel", label: `${n}. 已停止`, detail: "任务已被取消", status: "error" });
  }
  return steps;
}

export function mergeThinkingSteps(
  res: HubCommandResult | VoiceCommandResult,
  task?: Task | null
): ThinkingStep[] {
  const t = task || taskFromResponse(res);
  const base = buildThinkingSteps(res, t);
  if (!t) return base;
  const withoutStale = base.filter((s) => s.label !== "开始执行" && !s.id.startsWith("task-"));
  return [...withoutStale, ...buildTaskProgressSteps(t, withoutStale.length)];
}

export function resolveDisplayText(
  res: HubCommandResult | VoiceCommandResult,
  task?: Task | null,
  isPending?: boolean
): string {
  const t = task || taskFromResponse(res);
  if (t?.status === "wait_confirm") return "该操作需你确认后才会继续执行";
  if (isPending) return "正在执行，请稍候…";
  if (res.reply && !isInternalSummary(res.reply)) return res.reply;
  if (t?.status === "failed") return formatUserFacingError(t.error || res.message || "执行失败");
  if (t?.status === "cancelled") return "任务已停止";
  if (t?.summary && !isInternalSummary(t.summary)) return t.summary;
  if (res.message && !isInternalSummary(res.message)) return res.message;
  const lastPath = [...(t?.step_results || [])]
    .reverse()
    .find((r) => (r.output as Record<string, unknown> | undefined)?.path);
  const pathVal = (lastPath?.output as Record<string, unknown> | undefined)?.path;
  if (pathVal) return `已完成，文件保存在：${pathVal}`;
  if (t?.status === "done") {
    const paths = extractPathsFromTask(t);
    if (paths.length) return `已完成。相关路径：${paths.join("；")}`;
  }
  return res.reply || res.message || "已处理";
}

export function logPatchFromTask(task: Task, prev: { thinking?: ThinkingStep[]; text?: string }): {
  thinking: ThinkingStep[];
  thinkingOpen: boolean;
  status: "thinking" | "done" | "error";
  text: string;
} {
  const withoutProgress = (prev.thinking || []).filter(
    (s) => !s.id.startsWith("task-") && s.label !== "开始执行"
  );
  const thinking = [...withoutProgress, ...buildTaskProgressSteps(task)];
  const done = isTerminalTask(task);
  const status: "thinking" | "done" | "error" =
    task.status === "failed" || task.status === "cancelled" ? "error" : done ? "done" : "thinking";
  return {
    thinking,
    thinkingOpen: !done,
    status,
    text:
      task.status === "wait_confirm"
        ? "该操作需你确认后才会继续执行"
        : done || task.status === "failed"
          ? resolveDisplayText({} as HubCommandResult, task, false)
          : prev.text || "正在执行，请稍候…",
  };
}

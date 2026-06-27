/** 灵枢 Code：本地项目目录句柄持久化 + 文件读写 */

export type CodeFileEntry = { path: string; handle: FileSystemFileHandle };

const DB_NAME = "sensehub-code-project";
const STORE = "handles";
const MAX_FILES = 500;
const MAX_CONTEXT_BYTES = 48_000;

const SKIP_DIR_NAMES = new Set([
  "node_modules",
  ".git",
  "dist",
  "build",
  "__pycache__",
  ".venv",
  "venv",
  ".next",
  "coverage",
  ".turbo",
]);

const TEXT_FILE_RE =
  /\.(tsx?|jsx?|mjs|cjs|vue|svelte|py|go|rs|java|kt|swift|rb|php|cs|cpp|c|h|hpp|sql|json|ya?ml|toml|md|txt|css|scss|less|html|sh|ps1|env|ini|cfg|conf|xml|svg|graphql|proto)$/i;

export type CodeWorkflowMode = "agent" | "plan";

function projectKey(scope: string): string {
  return `sensehub_code_project::${scope}`;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) {
        req.result.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbSet(key: string, value: FileSystemDirectoryHandle): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

async function idbGet(key: string): Promise<FileSystemDirectoryHandle | null> {
  const db = await openDb();
  const value = await new Promise<FileSystemDirectoryHandle | null>((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).get(key);
    req.onsuccess = () => resolve((req.result as FileSystemDirectoryHandle) ?? null);
    req.onerror = () => reject(req.error);
  });
  db.close();
  return value;
}

async function idbDel(key: string): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export function supportsCodeProject(): boolean {
  return typeof window !== "undefined" && "showDirectoryPicker" in window;
}

export async function saveProjectHandle(scope: string, handle: FileSystemDirectoryHandle): Promise<void> {
  await idbSet(projectKey(scope), handle);
  try {
    localStorage.setItem(`${projectKey(scope)}:name`, handle.name);
  } catch {
    /* ignore */
  }
}

export async function loadProjectHandle(scope: string): Promise<FileSystemDirectoryHandle | null> {
  return idbGet(projectKey(scope));
}

export async function clearProjectHandle(scope: string): Promise<void> {
  await idbDel(projectKey(scope));
  try {
    localStorage.removeItem(`${projectKey(scope)}:name`);
    localStorage.removeItem(`${projectKey(scope)}:active`);
  } catch {
    /* ignore */
  }
}

export function loadLastActivePath(scope: string): string {
  try {
    return localStorage.getItem(`${projectKey(scope)}:active`) || "";
  } catch {
    return "";
  }
}

export function saveLastActivePath(scope: string, path: string): void {
  try {
    if (path) localStorage.setItem(`${projectKey(scope)}:active`, path);
    else localStorage.removeItem(`${projectKey(scope)}:active`);
  } catch {
    /* ignore */
  }
}

export async function verifyProjectPermission(
  handle: FileSystemDirectoryHandle,
  mode: "read" | "readwrite" = "readwrite"
): Promise<boolean> {
  try {
    const h = handle as FileSystemDirectoryHandle & {
      queryPermission: (o: { mode: typeof mode }) => Promise<PermissionState>;
      requestPermission: (o: { mode: typeof mode }) => Promise<PermissionState>;
    };
    const opts = { mode };
    if ((await h.queryPermission(opts)) === "granted") return true;
    return (await h.requestPermission(opts)) === "granted";
  } catch {
    return false;
  }
}

export async function listProjectFiles(dir: FileSystemDirectoryHandle, prefix = ""): Promise<CodeFileEntry[]> {
  const out: CodeFileEntry[] = [];
  const iter = (
    dir as unknown as { entries: () => AsyncIterableIterator<[string, FileSystemHandle]> }
  ).entries();
  for await (const [name, entry] of iter) {
    const path = prefix ? `${prefix}/${name}` : name;
    if (entry.kind === "file") {
      out.push({ path, handle: entry as FileSystemFileHandle });
    } else if (entry.kind === "directory" && out.length < MAX_FILES) {
      if (SKIP_DIR_NAMES.has(name)) continue;
      out.push(...(await listProjectFiles(entry as FileSystemDirectoryHandle, path)));
    }
    if (out.length >= MAX_FILES) break;
  }
  return out.sort((a, b) => a.path.localeCompare(b.path));
}

function normalizeRelativePath(raw: string): string {
  return raw
    .trim()
    .replace(/\\/g, "/")
    .replace(/^\/+/, "")
    .replace(/\/+/g, "/");
}

async function resolveDirectory(
  root: FileSystemDirectoryHandle,
  dirPath: string,
  create: boolean
): Promise<FileSystemDirectoryHandle> {
  let current = root;
  for (const part of dirPath.split("/").filter(Boolean)) {
    current = await current.getDirectoryHandle(part, { create });
  }
  return current;
}

export async function getProjectFileHandle(
  root: FileSystemDirectoryHandle,
  relativePath: string,
  create = false
): Promise<FileSystemFileHandle> {
  const normalized = normalizeRelativePath(relativePath);
  if (!normalized || normalized.includes("..")) {
    throw new Error("invalid_path");
  }
  const parts = normalized.split("/");
  const fileName = parts.pop();
  if (!fileName) throw new Error("invalid_path");
  const dir = parts.length ? await resolveDirectory(root, parts.join("/"), create) : root;
  return dir.getFileHandle(fileName, { create });
}

export async function createProjectFile(
  root: FileSystemDirectoryHandle,
  relativePath: string,
  initialContent = ""
): Promise<CodeFileEntry> {
  const normalized = normalizeRelativePath(relativePath);
  const existing = await listProjectFiles(root);
  if (existing.some((f) => f.path === normalized)) {
    throw new Error("exists");
  }
  const handle = await getProjectFileHandle(root, normalized, true);
  if (initialContent) {
    await writeProjectFile(handle, initialContent);
  }
  return { path: normalized, handle };
}

export async function deleteProjectPath(
  root: FileSystemDirectoryHandle,
  relativePath: string,
  recursive = false
): Promise<void> {
  const normalized = normalizeRelativePath(relativePath);
  if (!normalized || normalized.includes("..")) {
    throw new Error("invalid_path");
  }
  const parts = normalized.split("/").filter(Boolean);
  const name = parts.pop();
  if (!name) throw new Error("invalid_path");
  const parent = parts.length ? await resolveDirectory(root, parts.join("/"), false) : root;
  await parent.removeEntry(name, { recursive });
}

export async function writeProjectFile(handle: FileSystemFileHandle, content: string): Promise<void> {
  const writable = await handle.createWritable();
  await writable.write(content);
  await writable.close();
}

export async function readProjectText(
  handle: FileSystemFileHandle,
  maxBytes = MAX_CONTEXT_BYTES
): Promise<string> {
  const file = await handle.getFile();
  if (file.size > maxBytes) {
    const slice = file.slice(0, maxBytes);
    return (await slice.text()) + "\n\n…(文件过大，已截断)";
  }
  return file.text();
}

export function matchContextFiles(text: string, files: CodeFileEntry[], activePath: string): CodeFileEntry[] {
  const lower = text.toLowerCase();
  return files
    .filter((f) => {
      if (f.path === activePath) return false;
      const base = f.path.split("/").pop()?.toLowerCase() ?? "";
      return lower.includes(f.path.toLowerCase()) || (base.length > 2 && lower.includes(base));
    })
    .slice(0, 4);
}

function tokenizeForMatch(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9_\u4e00-\u9fff]+/i)
    .filter((t) => t.length > 1);
}

export function isTextLikeCodeFile(path: string): boolean {
  const base = path.split("/").pop() ?? path;
  if (TEXT_FILE_RE.test(base)) return true;
  if (!base.includes(".")) return true;
  return false;
}

export function scoreFileRelevance(path: string, userText: string, activePath: string): number {
  const lower = userText.toLowerCase();
  const pathLower = path.toLowerCase();
  const base = path.split("/").pop()?.toLowerCase() ?? "";
  let score = 0;

  if (path === activePath) score += 120;
  if (lower.includes(pathLower)) score += 90;
  if (base && base.length > 2 && lower.includes(base.replace(/\.[^.]+$/, ""))) score += 70;

  for (const token of tokenizeForMatch(userText)) {
    if (pathLower.includes(token)) score += 12;
  }

  const activeDir = activePath.includes("/") ? activePath.slice(0, activePath.lastIndexOf("/")) : "";
  if (activeDir && (path === activeDir || path.startsWith(`${activeDir}/`))) score += 28;

  if (pathLower.includes("test") && /test|测试|spec/.test(lower)) score += 18;
  if (pathLower.includes("index") || pathLower.endsWith("main.py") || pathLower.endsWith("app.py")) score += 8;

  if (pathLower.includes("node_modules") || pathLower.includes(".git/")) score -= 1000;
  return score;
}

/** Plan/Agent 共用：扫描项目文本文件，按与提示词的相关性读取内容 */
export async function collectSmartContextFiles(
  userText: string,
  files: CodeFileEntry[],
  activePath: string,
  readFn: (handle: FileSystemFileHandle) => Promise<string>,
  mode: CodeWorkflowMode
): Promise<{ path: string; content: string }[]> {
  const maxFiles = mode === "plan" ? 28 : 18;
  const maxTotalBytes = mode === "plan" ? 220_000 : 140_000;
  const minScore = mode === "plan" ? -4 : 0;

  const candidates = files
    .filter((f) => isTextLikeCodeFile(f.path))
    .map((f) => ({ entry: f, score: scoreFileRelevance(f.path, userText, activePath) }))
    .sort((a, b) => b.score - a.score);

  let picked = candidates.filter((c) => c.score >= minScore).slice(0, maxFiles);
  if (picked.length < 4) {
    picked = candidates.slice(0, Math.min(maxFiles, candidates.length));
  }

  const out: { path: string; content: string }[] = [];
  let total = 0;
  for (const { entry } of picked) {
    if (entry.path === activePath) continue;
    try {
      const fileContent = await readFn(entry.handle);
      if (total + fileContent.length > maxTotalBytes) break;
      out.push({ path: entry.path, content: fileContent });
      total += fileContent.length;
    } catch {
      /* skip unreadable */
    }
  }
  return out;
}

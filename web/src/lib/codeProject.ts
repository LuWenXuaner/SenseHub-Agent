/** 灵枢 Code：本地项目目录句柄持久化 + 文件读写 */

export type CodeFileEntry = { path: string; handle: FileSystemFileHandle };

const DB_NAME = "sensehub-code-project";
const STORE = "handles";
const MAX_FILES = 500;
const MAX_CONTEXT_BYTES = 48_000;

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

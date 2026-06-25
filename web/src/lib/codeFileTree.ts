import type { CodeFileEntry } from "@/lib/codeProject";

export type FileTreeDir = {
  type: "dir";
  name: string;
  path: string;
  children: FileTreeNode[];
};

export type FileTreeFile = {
  type: "file";
  name: string;
  path: string;
  handle: FileSystemFileHandle;
};

export type FileTreeNode = FileTreeDir | FileTreeFile;

function sortNodes(nodes: FileTreeNode[]): FileTreeNode[] {
  return [...nodes].sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

export function buildFileTree(files: CodeFileEntry[]): FileTreeNode[] {
  const root: FileTreeNode[] = [];

  for (const file of files) {
    const parts = file.path.split("/").filter(Boolean);
    let level = root;
    let acc = "";

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]!;
      acc = acc ? `${acc}/${part}` : part;
      const isFile = i === parts.length - 1;

      if (isFile) {
        level.push({ type: "file", name: part, path: file.path, handle: file.handle });
        continue;
      }

      let dir = level.find((n) => n.type === "dir" && n.name === part) as FileTreeDir | undefined;
      if (!dir) {
        dir = { type: "dir", name: part, path: acc, children: [] };
        level.push(dir);
      }
      level = dir.children;
    }
  }

  const normalize = (nodes: FileTreeNode[]): FileTreeNode[] =>
    sortNodes(nodes).map((n) =>
      n.type === "dir" ? { ...n, children: normalize(n.children) } : n
    );

  return normalize(root);
}

export function monacoLanguageForPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    mjs: "javascript",
    cjs: "javascript",
    py: "python",
    json: "json",
    md: "markdown",
    mdx: "markdown",
    html: "html",
    htm: "html",
    css: "css",
    scss: "scss",
    less: "less",
    yaml: "yaml",
    yml: "yaml",
    xml: "xml",
    sql: "sql",
    sh: "shell",
    bash: "shell",
    ps1: "powershell",
    rs: "rust",
    go: "go",
    java: "java",
    kt: "kotlin",
    cs: "csharp",
    cpp: "cpp",
    cc: "cpp",
    cxx: "cpp",
    h: "cpp",
    hpp: "cpp",
    c: "c",
    php: "php",
    rb: "ruby",
    swift: "swift",
    toml: "ini",
    ini: "ini",
    env: "ini",
  };
  if (path.toLowerCase().endsWith("dockerfile")) return "dockerfile";
  return map[ext] ?? "plaintext";
}

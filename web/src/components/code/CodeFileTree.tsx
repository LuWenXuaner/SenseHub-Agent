import { useState } from "react";
import { ChevronDown, ChevronRight, File, Folder, Trash2 } from "lucide-react";
import type { FileTreeNode } from "@/lib/codeFileTree";

type Props = {
  nodes: FileTreeNode[];
  activePath: string;
  onOpenFile: (path: string, handle: FileSystemFileHandle) => void;
  onDeletePath?: (path: string, type: "file" | "dir") => void;
  deleteFileLabel?: string;
  deleteFolderLabel?: string;
  defaultExpanded?: boolean;
};

function TreeNode({
  node,
  depth,
  activePath,
  onOpenFile,
  onDeletePath,
  deleteFileLabel,
  deleteFolderLabel,
  defaultExpanded,
}: {
  node: FileTreeNode;
  depth: number;
  activePath: string;
  onOpenFile: (path: string, handle: FileSystemFileHandle) => void;
  onDeletePath?: (path: string, type: "file" | "dir") => void;
  deleteFileLabel?: string;
  deleteFolderLabel?: string;
  defaultExpanded: boolean;
}) {
  const [open, setOpen] = useState(defaultExpanded);

  if (node.type === "file") {
    const active = activePath === node.path;
    return (
      <li className="group">
        <div
          className={`flex items-center hover:bg-mimo-warm ${active ? "bg-mimo-warm" : ""}`}
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          <button
            type="button"
            className={`flex min-w-0 flex-1 items-center gap-1 truncate py-1 pr-1 text-left ${
              active ? "font-medium text-mimo-text" : "text-mimo-muted"
            }`}
            onClick={() => onOpenFile(node.path, node.handle)}
          >
            <File size={12} className="shrink-0 opacity-50" />
            <span className="truncate">{node.name}</span>
          </button>
          {onDeletePath && (
            <button
              type="button"
              className="mr-1 shrink-0 rounded p-0.5 text-mimo-muted opacity-0 transition hover:bg-white hover:text-red-600 group-hover:opacity-100"
              title={deleteFileLabel}
              aria-label={deleteFileLabel}
              onClick={(e) => {
                e.stopPropagation();
                onDeletePath(node.path, "file");
              }}
            >
              <Trash2 size={12} />
            </button>
          )}
        </div>
      </li>
    );
  }

  return (
    <li className="group">
      <div
        className="flex items-center hover:bg-mimo-warm"
        style={{ paddingLeft: `${depth * 12 + 4}px` }}
      >
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-0.5 truncate py-1 pr-1 text-left font-medium text-mimo-text"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? (
            <ChevronDown size={12} className="shrink-0 opacity-50" />
          ) : (
            <ChevronRight size={12} className="shrink-0 opacity-50" />
          )}
          <Folder size={12} className="shrink-0 opacity-50" />
          <span className="truncate">{node.name}</span>
        </button>
        {onDeletePath && (
          <button
            type="button"
            className="mr-1 shrink-0 rounded p-0.5 text-mimo-muted opacity-0 transition hover:bg-white hover:text-red-600 group-hover:opacity-100"
            title={deleteFolderLabel}
            aria-label={deleteFolderLabel}
            onClick={(e) => {
              e.stopPropagation();
              onDeletePath(node.path, "dir");
            }}
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>
      {open && node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TreeNode
              key={child.type === "file" ? child.path : `dir:${child.path}`}
              node={child}
              depth={depth + 1}
              activePath={activePath}
              onOpenFile={onOpenFile}
              onDeletePath={onDeletePath}
              deleteFileLabel={deleteFileLabel}
              deleteFolderLabel={deleteFolderLabel}
              defaultExpanded={defaultExpanded}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export function CodeFileTree({
  nodes,
  activePath,
  onOpenFile,
  onDeletePath,
  deleteFileLabel,
  deleteFolderLabel,
  defaultExpanded = true,
}: Props) {
  if (!nodes.length) return null;

  return (
    <ul className="min-h-0 flex-1 overflow-y-auto text-xs">
      {nodes.map((node) => (
        <TreeNode
          key={node.type === "file" ? node.path : `dir:${node.path}`}
          node={node}
          depth={0}
          activePath={activePath}
          onOpenFile={onOpenFile}
          onDeletePath={onDeletePath}
          deleteFileLabel={deleteFileLabel}
          deleteFolderLabel={deleteFolderLabel}
          defaultExpanded={defaultExpanded}
        />
      ))}
    </ul>
  );
}

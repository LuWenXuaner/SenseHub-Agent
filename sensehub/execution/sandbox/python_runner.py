"""在沙箱内执行 LLM 生成的 Python 文档脚本."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from sensehub.security.sandbox import assert_filesystem, default_save_dir, workspace_dir

_DEFAULT_TIMEOUT = 60.0
_MAX_CODE_CHARS = 48_000

_FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "subprocess",
        "socket",
        "ctypes",
        "multiprocessing",
        "pickle",
        "builtins",
        "importlib",
        "pty",
        "fcntl",
        "signal",
        "webbrowser",
        "http",
        "urllib",
        "requests",
        "httpx",
    }
)

_FORBIDDEN_CALLS = frozenset({"eval", "exec", "__import__", "compile", "open"})

_WRAPPER = """# sensehub document sandbox bootstrap
from pathlib import Path

OUTPUT_PATH = Path({output_path!r})
SAVE_DIR = Path({save_dir!r})
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

def save_as(path=None):
    p = Path(path) if path else OUTPUT_PATH
    return p

# --- user script ---
"""


class _UnsafeCodeError(ValueError):
    pass


class _CodeSafetyVisitor(ast.NodeVisitor):
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = (alias.name or "").split(".")[0]
            if root in _FORBIDDEN_IMPORT_ROOTS:
                raise _UnsafeCodeError(f"脚本禁止 import {alias.name}")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        root = mod.split(".")[0]
        if root in _FORBIDDEN_IMPORT_ROOTS:
            raise _UnsafeCodeError(f"脚本禁止 from {mod} import …")

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CALLS:
            raise _UnsafeCodeError(f"脚本禁止调用 {node.func.id}()")
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in {"system", "popen", "spawn", "spawnl", "spawnv", "execl", "execv", "remove", "unlink", "rmtree"}:
                raise _UnsafeCodeError(f"脚本禁止调用 .{attr}()")
        self.generic_visit(node)


def validate_document_script(code: str) -> None:
    text = (code or "").strip()
    if not text:
        raise ValueError("code 不能为空")
    if len(text) > _MAX_CODE_CHARS:
        raise ValueError(f"code 过长（>{_MAX_CODE_CHARS} 字符）")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise ValueError(f"Python 语法错误: {exc}") from exc
    _CodeSafetyVisitor().visit(tree)


def run_document_script(
    code: str,
    *,
    output_path: str,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict:
    validate_document_script(code)
    out = assert_filesystem(output_path, "write")
    save_dir = default_save_dir()
    ws = workspace_dir()

    full_source = _WRAPPER.format(
        output_path=str(out),
        save_dir=str(save_dir),
    ) + code.strip() + "\n"

    script_name = f"_doc_script_{uuid.uuid4().hex}.py"
    script_path = ws / script_name
    script_path.write_text(full_source, encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ws),
            capture_output=True,
            text=True,
            timeout=max(5.0, min(float(timeout), 120.0)),
            encoding="utf-8",
            errors="replace",
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "SENSEHUB_OUTPUT_PATH": str(out),
                "SENSEHUB_SAVE_DIR": str(save_dir),
            },
        )
    finally:
        try:
            script_path.unlink(missing_ok=True)
        except OSError:
            pass

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err[:4000] or f"脚本退出码 {proc.returncode}")

    if not out.is_file():
        raise RuntimeError(f"脚本未生成文件：{out}")

    size = out.stat().st_size
    if size <= 0:
        raise RuntimeError(f"输出文件为空：{out}")

    return {
        "path": str(out),
        "bytes": size,
        "stdout": (proc.stdout or "")[:4000],
        "stderr": (proc.stderr or "")[:1000],
        "exit_code": proc.returncode,
    }

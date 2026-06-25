"""LLM 生成 Python 代码 → 沙箱执行 → 落盘 Office/海报等文件."""

from __future__ import annotations

from typing import Any

from sensehub.execution.sandbox.python_runner import run_document_script as _run


def run_document_script(params: dict[str, Any]) -> dict[str, Any]:
    """
    在沙箱中运行 Python 脚本生成文档/海报。

    脚本内可用变量：
    - OUTPUT_PATH：必须写入的目标文件（Path）
    - SAVE_DIR：用户默认保存目录（Path）

    允许：python-docx、openpyxl、python-pptx、Pillow 等文档库。
    禁止：subprocess、网络请求、删除系统文件等。
    """
    code = str(params.get("code") or "").strip()
    output_path = str(params.get("output_path") or params.get("path") or params.get("filename") or "").strip()
    if not output_path:
        raise ValueError("output_path 不能为空")
    timeout = float(params.get("timeout", 60))
    out = _run(code, output_path=output_path, timeout=timeout)
    return {
        **out,
        "method": "run_document_script",
        "description": str(params.get("description") or "").strip() or None,
    }

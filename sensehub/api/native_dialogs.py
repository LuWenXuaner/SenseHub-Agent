"""本机原生对话框（后端与桌面同机运行时使用）."""

from __future__ import annotations

from pathlib import Path


def pick_folder_dialog(title: str = "选择默认保存文件夹") -> str | None:
    """打开系统文件夹选择对话框，返回绝对路径；取消则 None."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    root.update_idletasks()
    selected = filedialog.askdirectory(parent=root, title=title, mustexist=False)
    root.destroy()
    if not selected or not str(selected).strip():
        return None
    return str(Path(selected).expanduser().resolve())

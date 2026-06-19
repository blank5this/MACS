"""Windows cp936 终端中文乱码修复。

在 entrypoint / 脚本首行调用 :func:`force_utf8_io`：

    from macs_pkg._compat import force_utf8_io
    force_utf8_io()
"""
from __future__ import annotations

import os
import sys

__all__ = ["force_utf8_io"]

_already_forced = False


def force_utf8_io() -> None:
    """配置 stdout/stderr 走 UTF-8 并设置子进程 env。

    幂等：多次调用只真正设置一次。pytest 一次 collection 会 import 多个测试模块，
    无幂等会让每个模块都触发 console code page syscall。
    """
    global _already_forced
    if _already_forced:
        return
    _already_forced = True

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

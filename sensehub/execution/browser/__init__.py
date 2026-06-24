"""Playwright 浏览器子系统."""

from sensehub.execution.browser.playwright_browser import (
    browser_act,
    browser_navigate,
    browser_snapshot,
    browser_status,
    browser_tabs,
)

__all__ = [
    "browser_status",
    "browser_navigate",
    "browser_snapshot",
    "browser_act",
    "browser_tabs",
]

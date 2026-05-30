"""
桌面叠加窗口管理器
负责：无边框窗口、始终置顶、色键透明、点击穿透
"""
import ctypes
import sys
from ctypes import wintypes

# Windows API 常量
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class WindowManager:
    """管理桌面叠加窗口的属性"""

    def __init__(self, hwnd: int = None):
        self.hwnd = hwnd
        self._click_through = False

    def set_hwnd(self, hwnd: int):
        """设置窗口句柄（Panda3D 创建窗口后调用）"""
        self.hwnd = hwnd

    def make_frameless(self):
        """移除窗口边框"""
        if not self.hwnd:
            return
        style = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        # 移除工具窗口样式，保留应用窗口样式（确保在任务栏可见）
        style &= ~WS_EX_TOOLWINDOW
        style |= WS_EX_APPWINDOW
        user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, style)

    def make_always_on_top(self, enable: bool = True):
        """设置窗口始终置顶"""
        if not self.hwnd:
            return
        if enable:
            user32.SetWindowPos(
                self.hwnd, HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE
            )
        else:
            user32.SetWindowPos(
                self.hwnd, -2,  # HWND_NOTOPMOST
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE
            )

    def set_click_through(self, enable: bool = True):
        """启用/禁用点击穿透（鼠标穿透窗口到桌面）"""
        if not self.hwnd:
            return
        self._click_through = enable
        style = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        if enable:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, style)

    def set_chroma_key(self, r: int, g: int, b: int):
        """设置色键透明（将指定 RGB 颜色变为透明）"""
        if not self.hwnd:
            return
        color_key = (b << 16) | (g << 8) | r  # Windows: BGR
        user32.SetLayeredWindowAttributes(self.hwnd, color_key, 0, LWA_COLORKEY)

    def set_alpha(self, alpha: int):
        """设置窗口整体透明度 0-255"""
        if not self.hwnd:
            return
        user32.SetLayeredWindowAttributes(self.hwnd, 0, alpha, LWA_ALPHA)

    def move_window(self, x: int, y: int):
        """移动窗口到指定位置"""
        if not self.hwnd:
            return
        user32.SetWindowPos(
            self.hwnd, 0,
            x, y, 0, 0,
            SWP_NOSIZE
        )

    def get_window_rect(self):
        """获取窗口位置和大小 (x, y, width, height)"""
        if not self.hwnd:
            return (0, 0, 400, 600)
        rect = wintypes.RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)

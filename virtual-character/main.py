#!/usr/bin/env python3
"""
桌面虚拟人物 — 巴巴塔
入口文件，组装所有组件并启动应用

用法:
    D:/python/python.exe main.py          # 启动
    D:/python/python.exe main.py --debug  # 调试模式
"""
import sys
import os
import time
import argparse
import threading
from queue import Queue, Empty

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(__file__))

import config
from engine.renderer import CharacterRenderer, CHROMA_KEY_RGB
from engine.window_manager import WindowManager
from character.animations import AnimationEngine, AnimState
from character.expressions import ExpressionController

# 可选依赖（AI / 语音模块）
try:
    from ai.brain import AIBrain
    from ai.personality import PersonalityManager
    from ai.memory import ConversationMemory
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

try:
    from voice.tts import TTSEngine
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    from interaction.chat_handler import ChatHandler
    from interaction.mouse_handler import MouseHandler
    INTERACTION_AVAILABLE = True
except ImportError:
    INTERACTION_AVAILABLE = False


class DesktopCharacter:
    """
    桌面虚拟人物应用 — 顶层控制器
    将所有模块整合在一起
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._print_banner()

        # ---- 核心组件 ----
        self.renderer = None
        self.window_mgr = WindowManager()
        self.anim_engine = AnimationEngine()
        self.expr_ctrl = ExpressionController()

        # ---- 线程间通信队列 ----
        self.command_queue = Queue()

        # ---- AI 模块 ----
        if AI_AVAILABLE:
            self.brain = AIBrain()
            self.personality = PersonalityManager()
            self.memory = ConversationMemory()
            # 设置系统提示词
            system_prompt = self.personality.build_system_prompt()
            self.brain.set_system_prompt(system_prompt)
            print(f"[App] AI 大脑就绪 — 角色: {self.personality.name}")
            print(f"  模型: {config.AI_MODEL}")
            print(f"  API可用: {self.brain.is_available()}")
        else:
            self.brain = None
            self.personality = None
            self.memory = None
            print("[App] AI 模块未加载")

        # ---- 语音模块 ----
        if VOICE_AVAILABLE:
            self.tts = TTSEngine()
            print(f"[App] TTS 引擎 ({config.TTS_ENGINE}) — 可用: {self.tts.is_available()}")
        else:
            self.tts = None
            print("[App] TTS 模块未加载")

        # ---- 交互模块 ----
        if INTERACTION_AVAILABLE:
            self.chat_handler = ChatHandler(
                brain=self.brain,
                memory=self.memory,
                tts=self.tts,
                command_queue=self.command_queue,
            )
            self.mouse_handler = MouseHandler(
                command_queue=self.command_queue,
            )
            print("[App] 交互模块就绪")
        else:
            self.chat_handler = None
            self.mouse_handler = None

        # ---- 热键注册 ----
        self._register_hotkeys()

        # ---- 状态 ----
        self.running = True
        self.muted = False
        self.visible = True
        self._drag_offset = (0, 0)

        # ---- 启动窗口 ----
        self._init_window()
        print("[App] 巴巴塔已就绪！按 F3 开始聊天，Ctrl+F1 隐藏/显示")
        print("=" * 50)

    def _print_banner(self):
        print("=" * 50)
        print("  桌面小伙伴 -- 巴巴塔")
        print("  启动中...")
        print("=" * 50)

    # ============================================================
    #  窗口初始化
    # ============================================================

    def _init_window(self):
        """创建 3D 窗口并配置桌面叠加属性"""
        self.renderer = CharacterRenderer()
        time.sleep(0.3)

        hwnd = self.renderer.hwnd
        if hwnd:
            self.window_mgr.set_hwnd(hwnd)
            self.window_mgr.make_frameless()
            self.window_mgr.make_always_on_top(True)
            self.window_mgr.set_chroma_key(
                CHROMA_KEY_RGB[0], CHROMA_KEY_RGB[1], CHROMA_KEY_RGB[2]
            )
            self.window_mgr.set_click_through(False)
            # 初始位置：屏幕右下
            try:
                import ctypes
                user32 = ctypes.windll.user32
                sw = user32.GetSystemMetrics(0)
                sh = user32.GetSystemMetrics(1)
                self.window_mgr.move_window(sw - 450, sh - 700)
                print(f"[App] 窗口置于屏幕 ({sw-450}, {sh-700})")
            except Exception:
                pass
        else:
            print("[App] 警告：无法获取窗口句柄，叠加功能受限")

        # 尝试加载真正的 3D 模型
        self.renderer.try_load_real_model()

    # ============================================================
    #  热键
    # ============================================================

    def _register_hotkeys(self):
        """注册全局热键"""
        try:
            import keyboard
            if self.chat_handler:
                keyboard.add_hotkey(config.HOTKEY_CHAT,
                                    lambda: self.chat_handler.open_chat_threaded())
                print(f"[App] 热键已注册: {config.HOTKEY_CHAT.upper()} = 聊天")
            keyboard.add_hotkey(config.HOTKEY_TOGGLE,
                                lambda: self.command_queue.put({"type": "toggle_visible"}))
            print(f"[App] 热键已注册: {config.HOTKEY_TOGGLE.upper()} = 显隐")
        except ImportError:
            print("[App] keyboard 库未安装，热键不可用。运行: pip install keyboard")
            print("  启动后可在终端直接输入文字聊天")

    # ============================================================
    #  命令处理（所有 Panda3D 操作必须在主线程）
    # ============================================================

    def _process_commands(self):
        """处理来自后台线程的命令"""
        try:
            while True:
                cmd = self.command_queue.get_nowait()
                cmd_type = cmd.get("type", "")
                payload = cmd.get("payload", {})

                if cmd_type == "set_expression":
                    self.renderer.set_expression(
                        payload.get("expr", "neutral"),
                        payload.get("weight", 1.0),
                    )
                elif cmd_type == "set_talking":
                    self.renderer.set_talking(payload.get("amplitude", 0.0))
                elif cmd_type == "set_look_at":
                    self.renderer.set_look_at(
                        payload.get("x", 0.0),
                        payload.get("y", 0.0),
                    )
                elif cmd_type == "anim_transition":
                    state_str = payload.get("state", "idle")
                    state_map = {
                        "idle": AnimState.IDLE,
                        "thinking": AnimState.THINKING,
                        "talking": AnimState.TALKING,
                        "reacting_click": AnimState.REACTING_CLICK,
                        "reacting_pet": AnimState.REACTING_PET,
                        "reacting_drag": AnimState.REACTING_DRAG,
                    }
                    state = state_map.get(state_str, AnimState.IDLE)
                    self.anim_engine.transition(state)
                elif cmd_type == "toggle_visible":
                    self.toggle_visible()
                elif cmd_type == "shutdown":
                    self.running = False

        except Empty:
            pass

    # ============================================================
    #  可见性
    # ============================================================

    def toggle_visible(self):
        """显示/隐藏角色"""
        self.visible = not self.visible
        if self.window_mgr and self.window_mgr.hwnd:
            import ctypes
            user32 = ctypes.windll.user32
            if self.visible:
                user32.ShowWindow(self.window_mgr.hwnd, 5)
                print("[App] 角色已显示")
            else:
                user32.ShowWindow(self.window_mgr.hwnd, 0)
                print("[App] 角色已隐藏")

    # ============================================================
    #  主循环
    # ============================================================

    def update(self, task):
        """每帧更新（主线程，60 FPS）"""
        # 1. 处理队列中的命令
        self._process_commands()

        # 2. 动画状态检查
        if self.anim_engine.is_expired():
            expired_states = {
                AnimState.REACTING_CLICK,
                AnimState.REACTING_PET,
                AnimState.THINKING,
            }
            if self.anim_engine.state in expired_states:
                self.anim_engine.transition(AnimState.IDLE)

        # 3. 表情更新
        target_expr = self.anim_engine.get_expression()
        self.expr_ctrl.set_expression(target_expr)
        current_expr = self.expr_ctrl.update(globalClock.getDt())

        if current_expr != self.renderer.expression:
            self.renderer.set_expression(current_expr)

        return task.cont

    # ============================================================
    #  启动
    # ============================================================

    def run(self):
        """启动应用主循环"""
        # 替换 renderer 中的 update 任务
        self.renderer.taskMgr.remove("character_update")
        self.renderer.taskMgr.add(self.update, "app_update")

        # 显示快捷键提示
        print()
        print("  ┌─────────────────────────────────────┐")
        print("  │  快捷键                              │")
        print(f"  │  {config.HOTKEY_CHAT.upper():8s} = 文字聊天          │")
        print(f"  │  {config.HOTKEY_VOICE.upper():8s} = 语音对话          │")
        print(f"  │  {config.HOTKEY_TOGGLE.upper():8s} = 显示/隐藏        │")
        print("  │  鼠标拖拽      = 移动角色          │")
        print("  │  鼠标悬停头部  = 抚摸角色          │")
        print("  └─────────────────────────────────────┘")
        print()

        print("[App] 进入主循环...")
        try:
            self.renderer.run()
        except KeyboardInterrupt:
            print("\n[App] 收到退出信号")
        finally:
            self.shutdown()

    def shutdown(self):
        """清理并退出"""
        self.running = False
        if AI_AVAILABLE and self.memory:
            stats = self.memory.session_stats()
            print(f"[App] 本次会话: {stats['message_count']} 条消息, "
                  f"时长 {stats['session_duration_minutes']} 分钟")
        print("[App] 巴巴塔已退出，再见！")


# ============================================================
#  入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="桌面虚拟人物 — 巴巴塔")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--no-ai", action="store_true", help="禁用 AI（仅 3D 显示）")
    args = parser.parse_args()

    app = DesktopCharacter(debug=args.debug)
    app.run()

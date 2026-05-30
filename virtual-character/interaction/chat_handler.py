"""
聊天处理器 — 文字输入、对话管理、气泡显示
"""
import sys
import tkinter as tk
from tkinter import simpledialog
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class ChatHandler:
    """
    文字聊天交互
    通过 tkinter 弹窗获取输入，将回复传递给 TTS 和渲染器
    """

    def __init__(self, brain=None, memory=None, tts=None, command_queue=None):
        self.brain = brain         # AIBrain 实例
        self.memory = memory       # ConversationMemory 实例
        self.tts = tts             # TTSEngine 实例
        self.command_queue = command_queue  # 主线程命令队列

        self._chat_popup = None

    # ---- 文字输入弹窗 ----

    def open_chat(self, parent_hwnd=None):
        """打开文字输入弹窗（tkinter）"""
        try:
            result = simpledialog.askstring(
                "巴巴塔 - 聊天",
                "跟我说点什么吧：",
                parent=None,
            )
            if result and result.strip():
                self.handle_message(result.strip())
        except Exception as e:
            print(f"[Chat] 弹窗错误: {e}")

    def open_chat_threaded(self):
        """在后台线程中打开聊天（避免阻塞主循环）"""
        import threading
        t = threading.Thread(target=self.open_chat, daemon=True)
        t.start()

    # ---- 消息处理 ----

    def handle_message(self, text: str):
        """处理用户输入的消息"""
        if not self.brain or not self.memory:
            print("[Chat] AI 或 Memory 未初始化，无法回复")
            return

        print(f"[Chat] 用户: {text}")

        # 添加到记忆
        self.memory.add_user_message(text)

        # 让角色进入思考状态
        if self.command_queue:
            self.command_queue.put({
                "type": "anim_transition",
                "payload": {"state": "thinking"}
            })

        # 调用 AI（异步）
        history = self.memory.get_history(limit=20)

        def on_chunk(chunk_text):
            """流式显示每个 chunk"""
            if self.command_queue:
                self.command_queue.put({
                    "type": "set_talking",
                    "payload": {"amplitude": 0.5}
                })

        def on_done(full_text):
            """AI 回复完成"""
            print(f"[Chat] 巴巴塔: {full_text}")
            self.memory.add_assistant_message(full_text)

            # 进入说话状态
            if self.command_queue:
                self.command_queue.put({
                    "type": "anim_transition",
                    "payload": {"state": "talking"}
                })

            # TTS 朗读（可选）
            if self.tts and self.tts.is_available():
                def tts_done(_):
                    if self.command_queue:
                        self.command_queue.put({
                            "type": "set_talking",
                            "payload": {"amplitude": 0.0}
                        })
                        self.command_queue.put({
                            "type": "anim_transition",
                            "payload": {"state": "idle"}
                        })

                self.tts.speak_async(full_text, callback=tts_done)
            else:
                # 无 TTS，直接恢复空闲
                if self.command_queue:
                    self.command_queue.put({
                        "type": "set_talking",
                        "payload": {"amplitude": 0.0}
                    })
                    self.command_queue.put({
                        "type": "anim_transition",
                        "payload": {"state": "idle"}
                    })

        self.brain.chat_async(text, history, callback=on_chunk, on_done=on_done)

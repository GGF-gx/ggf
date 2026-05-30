"""
语音合成引擎 — 支持 edge-tts (免费) 和 DashScope CosyVoice
"""
import sys
import asyncio
import threading
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    import config
    TTS_ENGINE = config.TTS_ENGINE
    TTS_VOICE = config.TTS_VOICE
    TTS_SPEED = config.TTS_SPEED
except ImportError:
    TTS_ENGINE = "edge"
    TTS_VOICE = "zh-CN-XiaoxiaoNeural"
    TTS_SPEED = "+10%"


class TTSEngine:
    """文字转语音引擎"""

    def __init__(self):
        self.engine = TTS_ENGINE  # "edge" | "cosyvoice" | "system"
        self.voice = TTS_VOICE
        self.speed = TTS_SPEED
        self._available = None
        self._audio_data = []  # 音频振幅数据（用于 lip-sync）

    def is_available(self) -> bool:
        """检查 TTS 是否可用"""
        if self._available is not None:
            return self._available

        if self.engine == "system":
            self._available = True
        elif self.engine == "edge":
            try:
                import edge_tts
                self._available = True
            except ImportError:
                print("[TTS] edge-tts 未安装。运行: pip install edge-tts")
                self._available = False
        else:
            self._available = False
        return self._available

    def speak(self, text: str, callback=None) -> str:
        """
        将文字转为语音并播放
        Args:
            text: 要朗读的文字
            callback(text): 播放完成回调
        Returns:
            临时音频文件路径（或空字符串）
        """
        if self.engine == "system":
            return self._speak_system(text, callback)
        elif self.engine == "edge":
            return self._speak_edge(text, callback)
        else:
            if callback:
                callback(text)
            return ""

    def speak_async(self, text: str, callback=None):
        """异步 TTS（后台线程）"""

        def _run():
            try:
                self.speak(text, callback)
            except Exception as e:
                print(f"[TTS] 异步合成错误: {e}")
                if callback:
                    callback(text)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    # ---- System TTS (Windows SAPI5) ----

    def _speak_system(self, text: str, callback=None) -> str:
        """使用 Windows 内置 TTS"""
        try:
            import win32com.client
        except ImportError:
            print("[TTS] pywin32 未安装。运行: pip install pywin32")
            if callback:
                callback(text)
            return ""

        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
        except Exception as e:
            print(f"[TTS] 系统语音失败: {e}")

        if callback:
            callback(text)
        return ""

    # ---- Edge TTS (微软免费在线语音) ----

    def _speak_edge(self, text: str, callback=None) -> str:
        """使用 edge-tts 合成语音"""
        try:
            import edge_tts
        except ImportError:
            print("[TTS] edge-tts 未安装")
            return self._speak_system(text, callback)

        # 在事件循环中运行
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 已有事件循环，创建新的
                loop = asyncio.new_event_loop()
                loop.run_until_complete(
                    self._edge_synthesize(text, callback)
                )
            else:
                loop.run_until_complete(
                    self._edge_synthesize(text, callback)
                )
        except RuntimeError:
            asyncio.run(self._edge_synthesize(text, callback))

        return "edge_tts_ok"

    async def _edge_synthesize(self, text: str, callback=None):
        """edge-tts 异步合成"""
        import edge_tts
        import tempfile
        import os

        # 调整语速
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.speed,
        )

        # 保存到临时文件
        tmp_path = os.path.join(tempfile.gettempdir(), "desktop_char_tts.mp3")
        await communicate.save(tmp_path)

        # 播放音频
        self._play_audio(tmp_path)

        # 获取振幅数据（简化版：基于文本长度估算）
        self._audio_data = [0.5] * len(text)

        if callback:
            callback(text)

    # ---- 音频播放 ----

    def _play_audio(self, filepath: str):
        """播放音频文件"""
        try:
            # 使用 Windows 原生播放器
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except ImportError:
            try:
                import subprocess
                subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", filepath],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                print(f"[TTS] 无法播放音频: {filepath}")

    # ---- 用于 lip-sync ----

    def get_amplitude_data(self) -> list:
        """获取音频振幅数据（用于驱动口型）"""
        return self._audio_data

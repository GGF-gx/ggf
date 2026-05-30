"""
桌面虚拟人物 — 全局配置
"""
import os
from pathlib import Path

# ---- 路径 ----
BASE_DIR = Path(__file__).parent
RESOURCES_DIR = BASE_DIR / "resources"
MODELS_DIR = RESOURCES_DIR / "models"
AUDIO_DIR = RESOURCES_DIR / "audio"
CONVERSATIONS_DIR = RESOURCES_DIR / "conversations"

# ---- AI 配置 (DeepSeek / 通义千问 / OpenAI 兼容) ----
# 从环境变量读取 API Key，也可直接填写
AI_PROVIDER = "deepseek"      # deepseek / dashscope / openai
AI_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-2b93f5184d224be3974ab6886200c480")
AI_API_BASE = "https://api.deepseek.com/v1"  # DeepSeek API 地址
AI_MODEL = "deepseek-chat"    # deepseek-chat / deepseek-reasoner
AI_MAX_TOKENS = 512
AI_TEMPERATURE = 0.8
AI_STREAMING = True

# ---- 语音配置 ----
STT_ENGINE = "whisper"         # "whisper" (faster-whisper 本地) 或 "dashscope" (云)
STT_MODEL_SIZE = "small"       # tiny / small / medium / large
SAMPLE_RATE = 16000
VAD_SILENCE_MS = 800           # 语音活动检测静音阈值

TTS_ENGINE = "edge"            # "edge" (edge-tts 免费) 或 "cosyvoice" (DashScope)
TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # edge-tts 语音
TTS_SPEED = "+10%"             # 语速调整

# ---- 窗口配置 ----
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
WINDOW_TITLE = "桌面小伙伴"
WINDOW_FPS = 60
CHROMA_KEY_COLOR = (0.1, 0.1, 0.1, 1.0)  # 透明背景色键 (深灰)

# ---- 角色配置 ----
CHARACTER_MODEL = MODELS_DIR / "character.glb"  # glTF 模型路径
CHARACTER_SCALE = 1.2
CHARACTER_IDLE_ANIM = "idle"           # 空闲动画名
CHARACTER_BLINK_INTERVAL = (2.0, 5.0)  # 眨眼间隔范围 (秒)

# ---- 交互热键 ----
HOTKEY_VOICE = "f2"       # 按住说话
HOTKEY_CHAT = "f3"        # 文字聊天
HOTKEY_TOGGLE = "ctrl+f1" # 显示/隐藏

# ---- 系统托盘 ----
TRAY_TOOLTIP = "桌面小伙伴 - 巴巴塔"

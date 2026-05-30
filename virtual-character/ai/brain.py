"""
AI 大脑 — 支持 DeepSeek / 通义千问 / OpenAI 兼容 API
使用 OpenAI SDK 统一调用
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import config
    AI_PROVIDER = config.AI_PROVIDER
    AI_API_KEY = config.AI_API_KEY
    AI_API_BASE = config.AI_API_BASE
    AI_MODEL = config.AI_MODEL
    AI_MAX_TOKENS = config.AI_MAX_TOKENS
    AI_TEMPERATURE = config.AI_TEMPERATURE
    AI_STREAMING = config.AI_STREAMING
except ImportError:
    AI_PROVIDER = "deepseek"
    AI_API_KEY = "your-deepseek-key"
    AI_API_BASE = "https://api.deepseek.com/v1"
    AI_MODEL = "deepseek-chat"
    AI_MAX_TOKENS = 512
    AI_TEMPERATURE = 0.8
    AI_STREAMING = True


class AIBrain:
    """
    AI 对话引擎 — 支持 DeepSeek / DashScope / OpenAI 兼容 API
    使用 OpenAI Python SDK（与 DeepSeek 完全兼容）
    """

    # 模型映射
    MODELS = {
        # DeepSeek
        "deepseek-chat": "deepseek-chat",
        "deepseek-reasoner": "deepseek-reasoner",
        # DashScope (OpenAI 兼容模式)
        "qwen-turbo": "qwen-turbo-latest",
        "qwen-plus": "qwen-plus-latest",
        "qwen-max": "qwen-max-latest",
        # OpenAI
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
    }

    def __init__(self):
        self.provider = AI_PROVIDER
        self.api_key = AI_API_KEY
        self.api_base = AI_API_BASE
        self.model = AI_MODEL
        self.max_tokens = AI_MAX_TOKENS
        self.temperature = AI_TEMPERATURE
        self.streaming = AI_STREAMING
        self._available = None

        self._system_prompt = ""
        self._client = None

    # ---- 获取 OpenAI 客户端 ----

    def _get_client(self):
        """获取 OpenAI 兼容客户端（延迟初始化）"""
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
            )
            return self._client
        except ImportError:
            print("[AI] openai 包未安装。运行: pip install openai")
            return None

    # ---- 系统提示词 ----

    def set_system_prompt(self, prompt: str):
        self._system_prompt = prompt

    # ---- 可用性 ----

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if not self.api_key or self.api_key in ("your-deepseek-key", "your-api-key-here", "sk-your-api-key-here"):
            self._available = False
            return False
        client = self._get_client()
        if client is None:
            self._available = False
            return False
        self._available = True
        return True

    # ---- 同步对话 ----

    def chat(self, message: str, history: list = None) -> str:
        """同步对话"""
        if not self.is_available():
            return self._fallback_response(message)

        try:
            client = self._get_client()
            messages = self._build_messages(message, history)

            response = client.chat.completions.create(
                model=self.MODELS.get(self.model, self.model),
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[AI] 对话异常: {e}")
            return self._fallback_response(message)

    # ---- 异步对话 ----

    def chat_async(self, message: str, history: list = None,
                   callback=None, on_done=None):
        """异步对话（后台线程 + 流式响应）"""
        def _run():
            if not self.is_available():
                text = self._fallback_response(message)
                if callback: callback(text)
                if on_done: on_done(text)
                return

            try:
                client = self._get_client()
                messages = self._build_messages(message, history)

                response = client.chat.completions.create(
                    model=self.MODELS.get(self.model, self.model),
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    stream=True,
                )

                full_text = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        full_text += text
                        if callback:
                            callback(text)

                result = full_text.strip() or self._fallback_response(message)
            except Exception as e:
                print(f"[AI] 异步对话异常: {e}")
                result = self._fallback_response(message)
                if callback:
                    callback(result)

            if on_done:
                on_done(result)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    # ---- 构建消息 ----

    def _build_messages(self, message: str, history: list = None) -> list:
        """构建 OpenAI 格式的消息列表"""
        messages = []

        if self._system_prompt:
            messages.append({
                "role": "system",
                "content": self._system_prompt
            })

        if history:
            for h in history[-20:]:
                role = h.get("role", "user")
                if role in ("user", "assistant", "system"):
                    messages.append({
                        "role": role,
                        "content": h.get("content", "")
                    })

        messages.append({
            "role": "user",
            "content": message
        })

        return messages

    # ---- 离线兜底 ----

    def _fallback_response(self, user_msg: str) -> str:
        import random
        offline_msgs = [
            "嗯嗯，我在听呢~",
            "这个问题有点意思！",
            "让我想想...嗯，你可以再说一遍吗？",
            "主人，我现在脑子有点空，得联网才能变聪明哦~",
            "哈哈，你说得对！",
            "（摸摸头）好呀好呀~",
            "虽然现在没法连上AI大脑，但我还是你的小伙伴！",
            "你需要我帮忙做什么呢？",
        ]
        return random.choice(offline_msgs)

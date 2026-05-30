"""
对话记忆 — 短期与长期记忆管理
- 短期：最近 N 条对话（窗口内）
- 长期：提取的关键事实（保存到 JSON）
"""
import json
import time
from collections import deque
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    import config
    MEMORY_FILE = config.CONVERSATIONS_DIR / "memory.json"
except Exception:
    MEMORY_FILE = Path("resources/conversations/memory.json")


class ConversationMemory:
    """管理对话历史和记忆"""

    def __init__(self, max_recent: int = 40):
        self.max_recent = max_recent
        self.recent_history = deque(maxlen=max_recent)
        self.long_term_facts = []  # 长期记忆关键事实
        self.session_start = time.time()
        self.message_count = 0

        # 加载长期记忆
        self._load_long_term()

    # ---- 消息管理 ----

    def add_user_message(self, content: str):
        """添加用户消息"""
        self.recent_history.append({
            "role": "user",
            "content": content
        })
        self.message_count += 1

    def add_assistant_message(self, content: str):
        """添加 AI 回复"""
        self.recent_history.append({
            "role": "assistant",
            "content": content
        })
        self.message_count += 1

    def get_history(self, limit: int = 20) -> list:
        """获取最近的对话历史"""
        history = list(self.recent_history)[-limit:]
        return history

    # ---- 长期记忆 ----

    def add_fact(self, fact: str):
        """添加长期记忆事实"""
        if fact not in self.long_term_facts:
            self.long_term_facts.append(fact)
            self._save_long_term()

    def get_facts(self) -> list:
        """获取所有长期记忆"""
        return self.long_term_facts

    # ---- Token 估算 ----

    def estimate_tokens(self) -> int:
        """粗略估算当前上下文 token 数（中文：每字约 1.5 token）"""
        total = 0
        for msg in self.recent_history:
            total += len(msg.get("content", "")) * 1.5
        return int(total)

    # ---- 持久化 ----

    def _load_long_term(self):
        """从文件加载长期记忆"""
        try:
            if MEMORY_FILE.exists():
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.long_term_facts = data.get("facts", [])
                    print(f"[Memory] 加载了 {len(self.long_term_facts)} 条长期记忆")
        except Exception:
            pass

    def _save_long_term(self):
        """保存长期记忆到文件"""
        try:
            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "facts": self.long_term_facts,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Memory] 保存失败: {e}")

    # ---- 会话统计 ----

    def session_stats(self) -> dict:
        """获取当前会话统计"""
        elapsed = time.time() - self.session_start
        return {
            "message_count": self.message_count,
            "session_duration_minutes": round(elapsed / 60, 1),
            "long_term_facts_count": len(self.long_term_facts),
        }

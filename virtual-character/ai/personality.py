"""
人设管理器 — 从 YAML 配置文件加载角色人设并构建系统提示词
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


class PersonalityManager:
    """加载并管理角色人设"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = config.RESOURCES_DIR / "personality.yaml"
        self.config_path = Path(config_path)
        self.data = {}
        self._load()

    def _load(self):
        """从 YAML 文件加载人设"""
        try:
            import yaml
        except ImportError:
            print("[Personality] PyYAML 未安装，使用默认人设。运行: pip install pyyaml")
            self.data = self._default_personality()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f)
            print(f"[Personality] 加载角色: {self.data.get('name', 'Unknown')}")
        except FileNotFoundError:
            print(f"[Personality] 人设文件未找到: {self.config_path}，使用默认")
            self.data = self._default_personality()

    def _default_personality(self) -> dict:
        """默认人设（YAML 文件不存在时的回退）"""
        return {
            "name": "巴巴塔",
            "personality": "你叫巴巴塔，是一个活泼可爱的桌面AI伙伴。",
            "speaking_style": ["口语化", "句子简短", "偶尔加emoji"],
            "emotional_range": ["happy", "surprised", "neutral"],
            "max_response_chars": 150,
        }

    # ---- 生成系统提示词 ----

    def build_system_prompt(self) -> str:
        """根据人设配置构建完整的系统提示词"""
        name = self.data.get("name", "巴巴塔")
        personality = self.data.get("personality", "")

        style = self.data.get("speaking_style", [])
        style_text = "\n".join(f"- {s}" for s in style) if style else ""

        max_chars = self.data.get("max_response_chars", 150)

        forbidden = self.data.get("forbidden_topics", [])
        forbidden_text = ""
        if forbidden:
            forbidden_text = "\n请不要讨论以下话题：" + "、".join(forbidden)

        prompt = f"""{personality}

说话风格要求：
{style_text}

重要规则：
- 每次回复不超过{max_chars}个字
- 始终保持角色身份，不要说"作为AI"之类的话
- 对用户的称呼偶尔用"主人"或"你"
{forbidden_text}
"""
        return prompt.strip()

    # ---- 查询 ----

    @property
    def name(self) -> str:
        return self.data.get("name", "巴巴塔")

    def get_emotional_range(self) -> list:
        return self.data.get("emotional_range", ["happy", "neutral", "surprised"])

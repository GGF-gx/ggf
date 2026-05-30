"""
动画状态机 — 驱动角色的动画状态切换
状态: IDLE, THINKING, TALKING, REACTING_CLICK, REACTING_PET, REACTING_DRAG
"""
import time
from enum import Enum


class AnimState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    TALKING = "talking"
    REACTING_CLICK = "reacting_click"
    REACTING_PET = "reacting_pet"
    REACTING_DRAG = "reacting_drag"


class AnimationEngine:
    """角色动画状态机"""

    def __init__(self):
        self.state = AnimState.IDLE
        self.state_start = time.time()
        self.previous_state = None

        # 各状态的持续时间
        self.state_durations = {
            AnimState.IDLE: 0,
            AnimState.THINKING: 3.0,
            AnimState.TALKING: 0,        # 由 TTS 时长决定
            AnimState.REACTING_CLICK: 1.5,
            AnimState.REACTING_PET: 3.0,
            AnimState.REACTING_DRAG: 0,  # 持续到释放
        }

        # 状态对应的表情
        self.state_expressions = {
            AnimState.IDLE: "neutral",
            AnimState.THINKING: "thinking",
            AnimState.TALKING: "neutral",
            AnimState.REACTING_CLICK: "surprised",
            AnimState.REACTING_PET: "happy",
            AnimState.REACTING_DRAG: "surprised",
        }

        # 状态对应的浮动幅度
        self.state_breathe = {
            AnimState.IDLE: 1.0,
            AnimState.THINKING: 0.5,
            AnimState.TALKING: 0.8,
            AnimState.REACTING_CLICK: 2.5,
            AnimState.REACTING_PET: 1.2,
            AnimState.REACTING_DRAG: 3.0,
        }

        print("[Animation] 动画引擎就绪")

    # ---- 状态切换 ----

    def transition(self, new_state: AnimState, duration: float = None):
        """切换到新状态"""
        if new_state == self.state:
            return
        self.previous_state = self.state
        self.state = new_state
        self.state_start = time.time()

        # 如果指定了自定义持续时间
        if duration is not None:
            self.state_durations[new_state] = duration

        print(f"[Animation] {self.previous_state.value} → {new_state.value}")

    def is_expired(self) -> bool:
        """有固定时长的状态是否已过期"""
        dur = self.state_durations.get(self.state, 0)
        if dur == 0:
            return False
        return (time.time() - self.state_start) >= dur

    # ---- 查询 ----

    def get_expression(self) -> str:
        """获取当前状态对应的表情"""
        return self.state_expressions.get(self.state, "neutral")

    def get_breathe_multiplier(self) -> float:
        """获取当前状态下呼吸动画的幅度倍数"""
        return self.state_breathe.get(self.state, 1.0)

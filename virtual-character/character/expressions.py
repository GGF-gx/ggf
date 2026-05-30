"""
表情控制器 — 管理角色表情切换与微表情
"""
import random
import time
import math


class ExpressionController:
    """控制角色的面部表情"""

    # 可用表情列表
    EXPRESSIONS = ["neutral", "happy", "surprised", "sad", "thinking"]

    def __init__(self):
        self.current = "neutral"
        self.target = "neutral"
        self.transition_progress = 1.0
        self.transition_speed = 5.0  # 表情切换速度
        self.current_weight = 1.0

        # 微表情
        self.micro_timer = 0.0
        self.micro_interval = random.uniform(5.0, 15.0)
        self.micro_active = False
        self.micro_expression = "neutral"

        print("[Expression] 表情控制器就绪")

    def set_expression(self, expr: str):
        """切换到目标表情"""
        if expr in self.EXPRESSIONS and expr != self.target:
            self.target = expr
            self.transition_progress = 0.0

    def update(self, dt: float) -> str:
        """
        每帧更新，返回当前应显示的表情名称
        """
        # 表情过渡
        if self.transition_progress < 1.0:
            self.transition_progress += dt * self.transition_speed
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                self.current = self.target
                self.current_weight = 1.0
            else:
                # smoothstep 过渡
                t = self.transition_progress
                self.current_weight = t * t * (3 - 2 * t)

        # 微表情更新
        self.micro_timer += dt
        if self.micro_timer >= self.micro_interval:
            self.micro_timer = 0.0
            self.micro_interval = random.uniform(5.0, 15.0)
            # 随机选择一个不同于当前表情的微表情
            available = [e for e in self.EXPRESSIONS
                         if e != self.current and e != "thinking"]
            if available:
                self.micro_expression = random.choice(available)
                self.micro_active = True
                self.micro_duration = 0.15  # 微表情持续时间短
                self.micro_elapsed = 0.0

        if self.micro_active:
            self.micro_elapsed += dt
            if self.micro_elapsed >= self.micro_duration:
                self.micro_active = False

        return self.get_display_expression()

    def get_display_expression(self) -> str:
        """获取当前实际显示的表情（考虑微表情覆盖）"""
        if self.micro_active:
            return self.micro_expression
        return self.current if self.transition_progress >= 1.0 else self.target

    def get_weight(self) -> float:
        """获取当前表情的权重（0-1，用于 blendshape 混合）"""
        if self.micro_active:
            return 0.3
        return self.current_weight

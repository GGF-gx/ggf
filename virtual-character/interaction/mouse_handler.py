"""
鼠标交互处理器 — 点击、拖拽、抚摸检测
"""
import time
import math
from enum import Enum


class MouseAction(Enum):
    NONE = "none"
    CLICK_BODY = "click_body"
    CLICK_HEAD = "click_head"
    DRAG = "drag"
    PET = "pet"  # 抚摸


class MouseHandler:
    """
    鼠标事件检测
    与 Panda3D 的碰撞检测配合使用
    """

    def __init__(self, command_queue=None):
        self.command_queue = command_queue

        # 鼠标状态
        self.mouse_down = False
        self.mouse_pos = (0, 0)
        self.mouse_down_pos = (0, 0)
        self.drag_start_time = 0
        self.drag_active = False
        self.drag_threshold = 5  # 像素，超过此距离视为拖拽

        # 宠物（抚摸）检测
        self.hover_node = None     # 当前悬停的节点
        self.hover_start_time = 0
        self.pet_threshold = 2.0   # 悬停超过2秒视为抚摸
        self.pet_active = False

        # 点击
        self.click_threshold = 0.3  # 秒，短于此时间为点击

        print("[Mouse] 鼠标交互就绪")

    # ---- 事件处理 ----

    def on_mouse_down(self, x: int, y: int, hit_node: str = None):
        """鼠标按下"""
        self.mouse_down = True
        self.mouse_down_pos = (x, y)
        self.mouse_pos = (x, y)
        self.drag_start_time = time.time()
        self.drag_active = False

    def on_mouse_move(self, x: int, y: int, hit_node: str = None):
        """鼠标移动"""
        if not self.mouse_down:
            # 悬停检测
            self._update_hover(x, y, hit_node)
            return

        self.mouse_pos = (x, y)

        # 检测拖拽
        if not self.drag_active:
            dx = x - self.mouse_down_pos[0]
            dy = y - self.mouse_down_pos[1]
            distance = math.sqrt(dx * dx + dy * dy)
            if distance > self.drag_threshold:
                self.drag_active = True
                self._trigger_action(MouseAction.DRAG, x, y)

    def on_mouse_up(self, x: int, y: int, hit_node: str = None):
        """鼠标释放"""
        self.mouse_down = False

        if self.drag_active:
            self.drag_active = False
            return

        # 检测点击
        elapsed = time.time() - self.drag_start_time
        if elapsed < self.click_threshold:
            if hit_node == "head":
                self._trigger_action(MouseAction.CLICK_HEAD, x, y)
            elif hit_node == "body":
                self._trigger_action(MouseAction.CLICK_BODY, x, y)

    # ---- 悬停/抚摸 ----

    def _update_hover(self, x: int, y: int, hit_node: str = None):
        """更新悬停状态"""
        if hit_node == self.hover_node and hit_node == "head":
            # 持续悬停头部
            if time.time() - self.hover_start_time > self.pet_threshold:
                if not self.pet_active:
                    self.pet_active = True
                    self._trigger_action(MouseAction.PET, x, y)
        else:
            self.hover_node = hit_node
            self.hover_start_time = time.time()
            self.pet_active = False

    # ---- 触发动作 ----

    def _trigger_action(self, action: MouseAction, x: int, y: int):
        """向主线程发送交互动作"""
        print(f"[Mouse] {action.value} at ({x}, {y})")

        if not self.command_queue:
            return

        if action == MouseAction.CLICK_BODY:
            self.command_queue.put({
                "type": "anim_transition",
                "payload": {"state": "reacting_click"}
            })
        elif action == MouseAction.CLICK_HEAD:
            self.command_queue.put({
                "type": "anim_transition",
                "payload": {"state": "reacting_click"}
            })
        elif action == MouseAction.DRAG:
            self.command_queue.put({
                "type": "anim_transition",
                "payload": {"state": "reacting_drag"}
            })
        elif action == MouseAction.PET:
            self.command_queue.put({
                "type": "anim_transition",
                "payload": {"state": "reacting_pet"}
            })

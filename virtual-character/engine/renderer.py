"""
角色渲染器 —— 基于 Panda3D ShowBase
负责：3D 场景、模型加载与显示、相机控制、动画驱动
"""
import sys
import math
import time
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    WindowProperties, FrameBufferProperties,
    GraphicsPipe, GraphicsOutput,
    AmbientLight, DirectionalLight,
    NodePath, PandaNode,
    TextNode, CardMaker,
    ClockObject, TransformState,
    CollisionTraverser, CollisionNode,
    CollisionRay, CollisionHandlerQueue,
    GeomVertexFormat, GeomVertexData,
    Geom, GeomTriangles, GeomNode,
    GeomVertexWriter,
    LVector3, LVector4, LPoint3, LVecBase4,
    BitMask32, Filename,
    loadPrcFileData
)

# Panda3D 渲染管线配置
loadPrcFileData("", "window-title 桌面小伙伴")
loadPrcFileData("", "win-size 400 600")
loadPrcFileData("", "undecorated 1")          # 无边框
loadPrcFileData("", "sync-video 0")           # 不等待垂直同步
loadPrcFileData("", "show-frame-rate-meter 0")
loadPrcFileData("", "basic-shaders-only 0")
loadPrcFileData("", "audio-library-name p3openal_audio")

CHROMA_KEY_RGB = (26, 26, 26)  # 深灰色键 (~0.1)


class CharacterRenderer(ShowBase):
    """
    角色渲染器 —— Panda3D ShowBase 子类
    编程风格与用户熟悉的 matplotlib 动画模式保持一致：
      __init__ → 设置场景
      update(task) → 每帧更新
      run() → 启动主循环
    """

    def __init__(self):
        # ---- Panda3D 初始化 ----
        ShowBase.__init__(self)

        # 设置背景色为色键颜色（用于透明合成）
        self.win.setClearColorActive(True)
        self.win.setClearColor(LVector4(
            CHROMA_KEY_RGB[0] / 255.0,
            CHROMA_KEY_RGB[1] / 255.0,
            CHROMA_KEY_RGB[2] / 255.0,
            1.0
        ))

        # 获取窗口句柄（供 WindowManager 使用）
        self._hwnd = None
        self._get_hwnd()

        # ---- 场景组件 ----
        self.character_root = None    # 角色根节点
        self.head_node = None         # 头部节点（用于碰撞检测）
        self.eye_left = None
        self.eye_right = None
        self.mouth_node = None

        # 动画状态
        self.anim_state = "idle"
        self.anim_state_time = 0.0
        self.blink_timer = 0.0
        self.blink_interval = 3.0     # 随机眨眼间隔
        self.is_blinking = False
        self.blink_progress = 0.0
        self.expression = "neutral"

        # 交互状态
        self.look_at_target = LPoint3(0, 5, 0)  # 视线目标
        self.head_rotation = 0.0
        self.talking_amplitude = 0.0

        # 碰撞检测
        self.collision_traverser = None
        self.collision_handler = None
        self._setup_collision()

        # ---- 场景设置 ----
        self._setup_lighting()
        self._setup_camera()
        self._create_placeholder_character()

        # ---- 注册更新任务 ----
        self.taskMgr.add(self.update, "character_update")
        self.disableMouse()  # 禁用默认鼠标控制

        print("[Renderer] 初始化完成 — 角色已就绪")

    # ============================================================
    #  窗口句柄获取
    # ============================================================

    def _get_hwnd(self):
        """获取 Panda3D 窗口的 Windows 原生句柄"""
        try:
            # Panda3D 在 Windows 上使用 windisplay
            from panda3d.core import GraphicsWindow
            # 通过 win32gui 按标题查找窗口
            import ctypes
            user32 = ctypes.windll.user32
            # 枚举查找 Panda3D 窗口
            hwnd = 0
            def enum_callback(h, _):
                nonlocal hwnd
                # Panda3D 默认窗口标题
                text = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(h, text, 256)
                title = text.value
                if "桌面小伙伴" in title or "Panda" in title:
                    hwnd = h
                    return False  # 停止枚举
                return True
            # 使用 EnumWindows
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
            self._hwnd = hwnd if hwnd != 0 else None
        except Exception as e:
            print(f"[Renderer] 警告：无法获取窗口句柄: {e}")
            self._hwnd = None

    @property
    def hwnd(self) -> int:
        """Windows 原生窗口句柄"""
        if self._hwnd is None:
            self._get_hwnd()
        return self._hwnd

    # ============================================================
    #  灯光
    # ============================================================

    def _setup_lighting(self):
        """设置场景灯光"""
        # 环境光
        ambient = AmbientLight("ambient")
        ambient.setColor(LVector4(0.6, 0.6, 0.7, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        # 主方向光（模拟前方上方的光源）
        key_light = DirectionalLight("key")
        key_light.setColor(LVector4(0.8, 0.78, 0.72, 1))
        key_np = self.render.attachNewNode(key_light)
        key_np.setPos(2, -10, 8)
        key_np.lookAt(0, 0, 0)
        self.render.setLight(key_np)

        # 补光（柔化阴影）
        fill_light = DirectionalLight("fill")
        fill_light.setColor(LVector4(0.3, 0.3, 0.35, 1))
        fill_np = self.render.attachNewNode(fill_light)
        fill_np.setPos(-2, -5, 2)
        fill_np.lookAt(0, 0, 0)
        self.render.setLight(fill_np)

    # ============================================================
    #  相机
    # ============================================================

    def _setup_camera(self):
        """设置相机位置"""
        # 相机在角色正前方
        self.camera.setPos(0, -4, 0.3)
        self.camera.lookAt(0, 0, 0.5)
        # 使用平行投影，让角色看起来像 2D 立绘
        # （取消注释以下两行切换到平行投影）
        # self.camLens.setNearFar(0.1, 100)
        # 保留默认透视投影以获得 3D 效果

    # ============================================================
    #  占位角色模型（后续替换为 VRM→glTF）
    # ============================================================

    def _create_placeholder_character(self):
        """创建占位角色 —— 由基本几何体构成的卡通人物"""
        self.character_root = self.render.attachNewNode("character_root")
        self.character_root.setScale(1.0)

        # 颜色定义
        skin_color = LVector4(1.0, 0.88, 0.75, 1.0)     # 皮肤色
        hair_color = LVector4(0.15, 0.3, 0.55, 1.0)       # 深蓝发色（参考图主色调）
        eye_white = LVector4(0.95, 0.95, 0.95, 1.0)
        eye_pupil = LVector4(0.1, 0.15, 0.25, 1.0)
        mouth_color = LVector4(0.8, 0.4, 0.4, 1.0)
        cloth_color = LVector4(0.2, 0.25, 0.35, 1.0)      # 深蓝衣服
        accent_color = LVector4(0.3, 0.7, 0.9, 1.0)       # 浅蓝点缀

        # ---- 头部（球体）----
        head_geom = self._make_sphere(radius=0.35, color=skin_color)
        self.head_node = self.character_root.attachNewNode("head")
        head_np = self.head_node.attachNewNode(head_geom)
        self.head_node.setPos(0, 0, 1.45)

        # ---- 头发（上半球 + 两侧）----
        # 主发（包裹头部上半部分）
        hair_main = self._make_sphere(radius=0.36, color=hair_color, slices=24, stacks=12)
        hair_np = self.head_node.attachNewNode(hair_main)
        hair_np.setPos(0, 0, 0.03)
        hair_np.setScale(1.0, 1.0, 0.55)  # 上半球

        # 刘海
        hair_bangs = self._make_sphere(radius=0.33, color=hair_color, slices=16, stacks=8)
        bangs_np = self.head_node.attachNewNode(hair_bangs)
        bangs_np.setPos(0, 0.18, 0.05)
        bangs_np.setScale(1.2, 0.6, 0.4)

        # 侧发
        for side in [-1, 1]:
            hair_side = self._make_sphere(radius=0.15, color=hair_color, slices=12, stacks=8)
            hs_np = self.head_node.attachNewNode(hair_side)
            hs_np.setPos(side * 0.28, 0.05, 0.0)
            hs_np.setScale(0.7, 0.5, 0.8)

        # ---- 眼睛 ----
        eye_size = 0.08
        for side, x_off in [("left", -0.1), ("right", 0.1)]:
            # 眼白
            eye_w = self._make_sphere(radius=eye_size, color=eye_white, slices=12, stacks=8)
            eye_np = self.head_node.attachNewNode(eye_w)
            eye_np.setPos(x_off, 0.28, 0.08)
            eye_np.setScale(1.2, 0.3, 0.9)
            # 瞳孔
            pupil = self._make_sphere(radius=eye_size * 0.65, color=eye_pupil, slices=10, stacks=6)
            pp_np = eye_np.attachNewNode(pupil)
            pp_np.setPos(0, 0.04, 0.01)
            pp_np.setScale(0.8, 1.0, 0.9)
            if side == "left":
                self.eye_left = pp_np
            else:
                self.eye_right = pp_np

        # ---- 嘴巴 ----
        mouth_geom = self._make_sphere(radius=0.04, color=mouth_color, slices=10, stacks=6)
        self.mouth_node = self.head_node.attachNewNode("mouth")
        mouth_np = self.mouth_node.attachNewNode(mouth_geom)
        self.mouth_node.setPos(0, 0.32, -0.02)
        self.mouth_node.setScale(2.0, 0.4, 0.5)

        # ---- 身体 ----
        body_geom = self._make_cylinder(radius=0.2, height=0.6, color=cloth_color)
        body_np = self.character_root.attachNewNode(body_geom)
        body_np.setPos(0, 0, 0.85)

        # 领口装饰
        collar = self._make_cylinder(radius=0.21, height=0.05, color=accent_color)
        collar_np = self.character_root.attachNewNode(collar)
        collar_np.setPos(0, 0, 1.15)

        # ---- 手臂 ----
        for side in [-1, 1]:
            arm = self._make_cylinder(radius=0.05, height=0.45, color=skin_color)
            arm_np = self.character_root.attachNewNode(arm)
            arm_np.setPos(side * 0.22, 0, 0.95)
            arm_np.setHpr(0, 0, side * 15)

        # ---- 腿 ----
        for side in [-1, 1]:
            leg = self._make_cylinder(radius=0.06, height=0.35, color=cloth_color)
            leg_np = self.character_root.attachNewNode(leg)
            leg_np.setPos(side * 0.1, 0, 0.45)

        print("[Renderer] 占位角色模型已创建 (待替换为 glTF/VRM)")

    def _make_sphere(self, radius=0.5, color=LVector4(1,1,1,1),
                     slices=16, stacks=12) -> GeomNode:
        """创建球体几何体"""
        from panda3d.core import GeomVertexFormat
        fmt = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData("sphere", fmt, Geom.UHStatic)

        vert_writer = GeomVertexWriter(vdata, "vertex")
        norm_writer = GeomVertexWriter(vdata, "normal")
        col_writer = GeomVertexWriter(vdata, "color")

        verts = []
        for i in range(stacks + 1):
            phi = math.pi * i / stacks
            for j in range(slices + 1):
                theta = 2 * math.pi * j / slices
                x = radius * math.sin(phi) * math.cos(theta)
                y = radius * math.sin(phi) * math.sin(theta)
                z = radius * math.cos(phi)
                vert_writer.addData3f(x, y, z)
                norm_writer.addData3f(
                    math.sin(phi) * math.cos(theta),
                    math.sin(phi) * math.sin(theta),
                    math.cos(phi)
                )
                col_writer.addData4f(color[0], color[1], color[2], color[3])
                verts.append(len(verts))

        tri_writer = GeomTriangles(Geom.UHStatic)
        for i in range(stacks):
            for j in range(slices):
                a = i * (slices + 1) + j
                b = a + slices + 1
                c = a + 1
                d = b + 1
                tri_writer.addVertices(a, b, c)
                tri_writer.addVertices(c, b, d)
                tri_writer.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(tri_writer)
        node = GeomNode("sphere")
        node.addGeom(geom)
        return node

    def _make_cylinder(self, radius=0.3, height=1.0, color=LVector4(1,1,1,1),
                       slices=16) -> GeomNode:
        """创建圆柱体几何体"""
        fmt = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData("cylinder", fmt, Geom.UHStatic)

        vert_writer = GeomVertexWriter(vdata, "vertex")
        norm_writer = GeomVertexWriter(vdata, "normal")
        col_writer = GeomVertexWriter(vdata, "color")

        half_h = height / 2
        # 侧面顶点
        for i in range(2):  # 顶部和底部环
            z = half_h if i == 0 else -half_h
            for j in range(slices + 1):
                theta = 2 * math.pi * j / slices
                x = radius * math.cos(theta)
                y = radius * math.sin(theta)
                vert_writer.addData3f(x, y, z)
                norm_writer.addData3f(math.cos(theta), math.sin(theta), 0)
                col_writer.addData4f(color[0], color[1], color[2], color[3])

        tri_writer = GeomTriangles(Geom.UHStatic)
        idx_per_ring = slices + 1
        for j in range(slices):
            a = j
            b = j + idx_per_ring
            c = j + 1
            d = b + 1
            tri_writer.addVertices(a, b, c)
            tri_writer.addVertices(c, b, d)
            tri_writer.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(tri_writer)
        node = GeomNode("cylinder")
        node.addGeom(geom)
        return node

    # ============================================================
    #  碰撞检测
    # ============================================================

    def _setup_collision(self):
        """初始化碰撞检测系统"""
        self.collision_traverser = CollisionTraverser("character_collision")
        self.collision_handler = CollisionHandlerQueue()

    def check_mouse_hit(self, mouse_pos):
        """检测鼠标射线与角色的碰撞
        返回: "head" | "body" | None
        """
        if not self.head_node or not self.collision_traverser:
            return None

        # 创建射线
        picker_node = CollisionNode("mouse_ray")
        picker_np = self.camera.attachNewNode(picker_node)
        picker_node.setFromCollideMask(BitMask32.allOn())

        # 将屏幕坐标转换为射线
        picker_node.addSolid(CollisionRay())
        picker_np.lookAt(mouse_pos)

        self.collision_traverser.addCollider(picker_np, self.collision_handler)
        self.collision_traverser.traverse(self.render)

        if self.collision_handler.getNumEntries() > 0:
            self.collision_handler.sortEntries()
            entry = self.collision_handler.getEntry(0)
            hit_node = entry.getIntoNodePath()
            # 检查是否为头部碰撞
            if self.head_node in hit_node.getAncestors():
                return "head"
            return "body"

        picker_np.removeNode()
        return None

    # ============================================================
    #  表情控制
    # ============================================================

    def set_expression(self, expr: str, weight: float = 1.0):
        """设置表情
        Args:
            expr: "neutral" | "happy" | "surprised" | "sad" | "thinking"
            weight: 0.0 - 1.0
        """
        self.expression = expr
        if not self.mouth_node:
            return
        if expr == "happy":
            self.mouth_node.setScale(2.5, 0.6, 0.5)
            self.mouth_node.setZ(-0.01)
        elif expr == "surprised":
            self.mouth_node.setScale(1.2, 1.2, 1.0)
            self.mouth_node.setZ(-0.01)
        elif expr == "sad":
            self.mouth_node.setScale(2.0, 0.3, 0.4)
            self.mouth_node.setZ(-0.04)
        elif expr == "thinking":
            self.mouth_node.setScale(1.5, 0.4, 0.5)
            self.mouth_node.setZ(-0.01)
        else:  # neutral
            self.mouth_node.setScale(2.0, 0.3, 0.5)
            self.mouth_node.setZ(-0.02)

    def set_talking(self, amplitude: float):
        """设置说话振幅（驱动口型）
        Args:
            amplitude: 0.0 (闭嘴) - 1.0 (张嘴)
        """
        self.talking_amplitude = amplitude
        if not self.mouth_node:
            return
        mouth_open = 0.3 + amplitude * 1.5
        self.mouth_node.setScale(2.0, mouth_open, 0.5 + amplitude * 0.5)

    def set_look_at(self, screen_x: float, screen_y: float):
        """视线跟踪屏幕坐标"""
        self.look_at_target = LPoint3(screen_x * 0.3, 5, screen_y * 0.2)

    # ============================================================
    #  加载真正的 glTF 模型
    # ============================================================

    def load_gltf_model(self, gltf_path: str):
        """加载 glTF 模型替换占位角色"""
        print(f"[Renderer] 加载模型: {gltf_path}")
        try:
            model = self.loader.loadModel(Filename.fromOsSpecific(gltf_path))
            model.reparentTo(self.character_root)
            # 查找骨骼
            self._find_bones(model)
            print("[Renderer] 模型加载成功")
            return True
        except Exception as e:
            print(f"[Renderer] 模型加载失败: {e}")
            return False

    def _find_bones(self, model):
        """递归查找模型中的骨骼/关节节点"""
        # 用于后续动画绑定
        children = model.findAllMatches("**")
        bones = []
        for child in children:
            if child.getName().lower().find("head") >= 0:
                self.head_node = child
            if child.getName().lower().find("mouth") >= 0:
                self.mouth_node = child
        return bones

    # ============================================================
    #  定期检查是否有 glTF 模型可用
    # ============================================================

    def try_load_real_model(self):
        """尝试加载真正的 3D 模型（如果 resources/models/ 下有 .glb 文件）"""
        import config
        import glob as gb
        patterns = [
            "*.glb", "*.gltf", "*.GLB", "*.GLTF"
        ]
        for pat in patterns:
            files = gb.glob(str(config.MODELS_DIR / pat))
            if files:
                return self.load_gltf_model(files[0])
        return False

    # ============================================================
    #  每帧更新
    # ============================================================

    def update(self, task):
        """每帧调用 (60 FPS) —— 与 matplotlib FuncAnimation 的 update 模式一致"""
        dt = globalClock.getDt()
        self.anim_state_time += dt

        # ---- 呼吸动画（上下浮动）----
        if self.character_root:
            breathe = math.sin(self.anim_state_time * 1.5) * 0.015
            self.character_root.setZ(breathe)

        # ---- 眨眼逻辑 ----
        self._update_blink(dt)

        # ---- 视线跟踪 ----
        self._update_look_at(dt)

        # ---- 说话动画（口型回归）----
        if self.talking_amplitude > 0 and self.anim_state != "talking":
            self.talking_amplitude = max(0, self.talking_amplitude - dt * 3.0)
            self.set_talking(self.talking_amplitude)

        return task.cont

    def _update_blink(self, dt):
        """更新眨眼动画"""
        self.blink_timer += dt
        if not self.is_blinking and self.blink_timer >= self.blink_interval:
            self.is_blinking = True
            self.blink_progress = 0.0

        if self.is_blinking:
            self.blink_progress += dt * 8.0  # 眨眼速度
            if self.blink_progress >= 2.0:
                # 眨眼完成
                self.is_blinking = False
                self.blink_timer = 0.0
                import random
                self.blink_interval = random.uniform(2.0, 5.0)
                # 恢复眼睛
                self._set_eye_scale(1.0)
            elif self.blink_progress < 0.5:
                # 闭眼
                t = self.blink_progress / 0.5
                self._set_eye_scale(1.0 - t * 0.95)
            else:
                # 睁眼
                t = (self.blink_progress - 0.5) / 0.5
                self._set_eye_scale(0.05 + t * 0.95)

    def _set_eye_scale(self, scale_y):
        """设置眼睛纵向缩放（用于眨眼）"""
        for eye in [self.eye_left, self.eye_right]:
            if eye:
                current = eye.getScale()
                eye.setScale(current[0], scale_y, current[2])

    def _update_look_at(self, dt):
        """更新视线跟踪"""
        if not self.head_node:
            return
        # 平滑转头
        target_h = self.look_at_target[0] * 15
        current = self.head_rotation
        self.head_rotation += (target_h - current) * min(dt * 3.0, 1.0)
        self.head_node.setH(self.head_rotation)

    # ============================================================
    #  启动
    # ============================================================

    def run(self):
        """启动主渲染循环"""
        print("[Renderer] 启动渲染循环...")
        ShowBase.run(self)

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Circle

# ============================================================
#  行星纹理生成（程序化）
# ============================================================

def _gauss_blur(arr, sigma):
    """numpy 实现的高斯模糊（替代 scipy.ndimage.gaussian_filter）"""
    size = int(sigma * 4 + 1) | 1  # 确保奇数
    kernel_1d = np.exp(-0.5 * (np.arange(size) - size // 2) ** 2 / sigma ** 2)
    kernel_1d /= kernel_1d.sum()
    # 两次一维卷积近似二维高斯
    h, w = arr.shape
    result = np.zeros_like(arr)
    # 水平方向
    for i in range(h):
        result[i] = np.convolve(arr[i], kernel_1d, mode='same')
    # 垂直方向
    temp = result.copy()
    for j in range(w):
        result[:, j] = np.convolve(temp[:, j], kernel_1d, mode='same')
    return result


def _gauss_blob(size, cx, cy, sx, sy, angle=0):
    """生成一个椭圆高斯斑点"""
    ys, xs = np.ogrid[:size, :size]
    cosa, sina = np.cos(angle), np.sin(angle)
    xr = (xs - cx) * cosa + (ys - cy) * sina
    yr = -(xs - cx) * sina + (ys - cy) * cosa
    return np.exp(-0.5 * ((xr / sx) ** 2 + (yr / sy) ** 2))


def _fbm_noise(size, rng, octaves=4):
    """简单的分形噪声（叠加多个尺度的随机高斯场）"""
    noise = np.zeros((size, size))
    for i in range(octaves):
        scale = 2 ** i
        small_size = max(4, size // scale)
        small = rng.normal(0, 1, (small_size, small_size))
        # 上采样
        ys = np.linspace(0, small_size - 1, size)
        xs = np.linspace(0, small_size - 1, size)
        yidx = ys.astype(int)
        xidx = xs.astype(int)
        upscaled = small[yidx[:, None], xidx[None, :]]
        noise += upscaled / scale
    noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
    return noise


def generate_earth_texture(size=256):
    """地球纹理：蓝色海洋 + 绿色/棕色大陆 + 白色云层 + 极地冰盖"""
    rng = np.random.default_rng(42)
    # 海洋底色
    ocean_r = np.full((size, size), 0.12)
    ocean_g = np.full((size, size), 0.35)
    ocean_b = np.full((size, size), 0.65)

    # 大陆（多块椭圆高斯叠加）
    continent_mask = np.zeros((size, size))
    continents = [
        (size * 0.25, size * 0.3, size * 0.22, size * 0.13, 0.2),
        (size * 0.35, size * 0.35, size * 0.14, size * 0.10, -0.3),
        (size * 0.55, size * 0.40, size * 0.18, size * 0.12, 0.1),
        (size * 0.70, size * 0.28, size * 0.12, size * 0.09, 0.5),
        (size * 0.50, size * 0.55, size * 0.16, size * 0.10, -0.2),
        (size * 0.30, size * 0.60, size * 0.10, size * 0.12, 0.3),
        (size * 0.78, size * 0.55, size * 0.13, size * 0.15, -0.1),
        (size * 0.20, size * 0.45, size * 0.09, size * 0.08, 0.4),
        (size * 0.45, size * 0.48, size * 0.08, size * 0.07, -0.5),
        (size * 0.60, size * 0.65, size * 0.11, size * 0.09, 0.15),
    ]
    for cx, cy, sx, sy, ang in continents:
        continent_mask += _gauss_blob(size, cx, cy, sx, sy, ang)
    continent_mask = np.clip(continent_mask, 0, 1)

    # 大陆颜色：绿色基底 + 棕色山脉
    detail = _fbm_noise(size, rng, octaves=5)
    green = 0.25 + 0.30 * detail
    green = green * continent_mask
    red = 0.10 + 0.25 * detail
    red = red * continent_mask
    blue_land = 0.08 + 0.10 * (1 - detail)
    blue_land = blue_land * continent_mask

    # 沙漠区域（某些大陆内部偏棕）
    desert = _gauss_blob(size, size * 0.50, size * 0.53, size * 0.10, size * 0.06, 0.2)
    desert += _gauss_blob(size, size * 0.30, size * 0.55, size * 0.07, size * 0.05, 0)
    desert = np.clip(desert, 0, 1) * continent_mask

    r = ocean_r * (1 - continent_mask) + (red * (1 - desert) + desert * 0.70) * continent_mask
    g = ocean_g * (1 - continent_mask) + (green * (1 - desert) + desert * 0.52) * continent_mask
    b = ocean_b * (1 - continent_mask) + (blue_land * (1 - desert) + desert * 0.15) * continent_mask

    # 极地冰盖
    ice_n = np.exp(-0.5 * ((np.arange(size) - 0) / (size * 0.12)) ** 2)
    ice_s = np.exp(-0.5 * ((np.arange(size) - size) / (size * 0.12)) ** 2)
    ice_mask = (ice_n[:, None] + ice_s[:, None])
    ice_mask = np.clip(ice_mask, 0, 1)
    r = r * (1 - ice_mask) + 0.95 * ice_mask
    g = g * (1 - ice_mask) + 0.95 * ice_mask
    b = b * (1 - ice_mask) + 0.92 * ice_mask

    # 云层
    cloud_noise = _fbm_noise(size, rng, octaves=4)
    cloud_mask = (cloud_noise > 0.55).astype(float) * 0.25
    cloud_mask = _gauss_blur(cloud_mask, sigma=2)
    r = r * (1 - cloud_mask) + 0.9 * cloud_mask
    g = g * (1 - cloud_mask) + 0.9 * cloud_mask
    b = b * (1 - cloud_mask) + 0.88 * cloud_mask

    texture = np.stack([r, g, b], axis=-1)
    return np.clip(texture, 0, 1)


def generate_jupiter_texture(size=256):
    """木星纹理：橙棕色水平条纹 + 扰动"""
    rng = np.random.default_rng(77)
    ys = np.linspace(0, 1, size)
    bands = np.zeros((size, size))
    # 水平条纹
    for _ in range(30):
        cy = rng.uniform(0, 1)
        width = rng.uniform(0.02, 0.08)
        amp = rng.uniform(-0.3, 0.3)
        band = amp * np.exp(-0.5 * ((ys - cy) / width) ** 2)
        bands += band[:, None]
    bands = (bands - bands.min()) / (bands.max() - bands.min() + 1e-8)
    # 湍流扰动
    turb = _fbm_noise(size, rng, octaves=5)
    # 大红斑
    spot = _gauss_blob(size, size * 0.55, size * 0.40, size * 0.06, size * 0.04, 0.3)
    spot += _gauss_blob(size, size * 0.57, size * 0.42, size * 0.04, size * 0.03, -0.2)
    spot = np.clip(spot, 0, 1) * 0.6

    r = 0.60 + 0.25 * bands + 0.10 * turb + 0.2 * spot
    g = 0.35 + 0.20 * bands + 0.05 * turb
    b = 0.12 + 0.06 * bands
    return np.clip(np.stack([r, g, b], axis=-1), 0, 1)


def generate_saturn_texture(size=256):
    """土星纹理：淡黄色细微水平条纹"""
    rng = np.random.default_rng(123)
    ys = np.linspace(0, 1, size)
    bands = np.zeros((size, size))
    for _ in range(15):
        cy = rng.uniform(0, 1)
        width = rng.uniform(0.03, 0.10)
        amp = rng.uniform(-0.12, 0.12)
        bands += amp * np.exp(-0.5 * ((ys - cy) / width) ** 2)
    bands = (bands - bands.min()) / (bands.max() - bands.min() + 1e-8)
    r = 0.82 + 0.12 * bands
    g = 0.74 + 0.10 * bands
    b = 0.55 + 0.08 * bands
    return np.clip(np.stack([r, g, b], axis=-1), 0, 1)


def generate_mars_texture(size=256):
    """火星纹理：红棕色 + 暗色陨石坑斑点"""
    rng = np.random.default_rng(99)
    base = _fbm_noise(size, rng, octaves=5)
    # 暗色区域
    dark = _fbm_noise(size, rng, octaves=3)
    # 陨石坑（小暗斑）
    craters = np.zeros((size, size))
    for _ in range(40):
        cx = rng.uniform(0, size)
        cy = rng.uniform(0, size)
        r_crater = rng.uniform(3, 10)
        craters += -0.3 * _gauss_blob(size, cx, cy, r_crater, r_crater, 0)
    craters = np.clip(craters, -0.3, 0)
    # 极地冰盖
    ice = np.exp(-0.5 * ((np.arange(size) - 0) / (size * 0.08)) ** 2)
    ice += np.exp(-0.5 * ((np.arange(size) - size) / (size * 0.08)) ** 2)
    ice_mask = np.clip(ice[:, None], 0, 1) * 0.6

    r = 0.65 + 0.20 * base + 0.10 * dark + craters + 0.2 * ice_mask
    g = 0.18 + 0.08 * base + 0.03 * dark + craters * 0.5 + 0.15 * ice_mask
    b = 0.06 + 0.03 * base + craters * 0.3
    return np.clip(np.stack([r, g, b], axis=-1), 0, 1)


def generate_mercury_texture(size=256):
    """水星纹理：灰色 + 密集陨石坑"""
    rng = np.random.default_rng(55)
    base = _fbm_noise(size, rng, octaves=4)
    craters = np.zeros((size, size))
    for _ in range(80):
        cx = rng.uniform(0, size)
        cy = rng.uniform(0, size)
        r_cr = rng.uniform(2, 7)
        craters += -0.25 * _gauss_blob(size, cx, cy, r_cr, r_cr, 0)
    craters = np.clip(craters, -0.3, 0)
    val = 0.45 + 0.25 * base + craters
    return np.clip(np.stack([val, val, val], axis=-1), 0, 1)


def generate_venus_texture(size=256):
    """金星纹理：淡黄白色 + 云层漩涡"""
    rng = np.random.default_rng(66)
    cloud = _fbm_noise(size, rng, octaves=5)
    cloud = _gauss_blur(cloud, sigma=3)
    swirl = _fbm_noise(size, rng, octaves=3)
    r = 0.82 + 0.10 * cloud + 0.05 * swirl
    g = 0.78 + 0.12 * cloud + 0.04 * swirl
    b = 0.62 + 0.08 * cloud + 0.03 * swirl
    return np.clip(np.stack([r, g, b], axis=-1), 0, 1)


def generate_uranus_texture(size=256):
    """天王星纹理：均匀淡青蓝色"""
    rng = np.random.default_rng(88)
    detail = _fbm_noise(size, rng, octaves=4)
    r = 0.35 + 0.10 * detail
    g = 0.65 + 0.12 * detail
    b = 0.75 + 0.10 * detail
    return np.clip(np.stack([r, g, b], axis=-1), 0, 1)


def generate_neptune_texture(size=256):
    """海王星纹理：深蓝色 + 细微亮纹"""
    rng = np.random.default_rng(111)
    detail = _fbm_noise(size, rng, octaves=5)
    # 一些亮条纹
    ys = np.linspace(0, 1, size)
    bright = 0.08 * np.sin(ys * 12)[:, None] + 0.05 * np.sin(ys * 20 + 1.5)[:, None]
    r = 0.10 + 0.05 * detail
    g = 0.20 + 0.10 * detail + 0.05 * bright
    b = 0.55 + 0.22 * detail + 0.10 * bright
    return np.clip(np.stack([r, g, b], axis=-1), 0, 1)


# 纹理生成函数映射
TEXTURE_GENERATORS = {
    "Mercury": generate_mercury_texture,
    "Venus":   generate_venus_texture,
    "Earth":   generate_earth_texture,
    "Mars":    generate_mars_texture,
    "Jupiter": generate_jupiter_texture,
    "Saturn":  generate_saturn_texture,
    "Uranus":  generate_uranus_texture,
    "Neptune": generate_neptune_texture,
}

# ============================================================
#  行星配置：名称, 轨道半径, 行星半径, 公转周期(年), 光环
# ============================================================
PLANETS = [
    ("Mercury", 38,  2.2,  0.24,  False),
    ("Venus",   58,  5.0,  0.62,  False),
    ("Earth",   78,  5.5,  1.00,  False),
    ("Mars",    98,  4.0,  1.88,  False),
    ("Jupiter", 140, 16.0, 11.86, False),
    ("Saturn",  180, 12.0, 29.46, True),
    ("Uranus",  215, 9.0,  84.01, False),
    ("Neptune", 245, 8.5,  164.8, False),
]

GLOW_LAYERS = [
    (62, "#ffaa00", 0.015),
    (44, "#ffbb22", 0.03),
    (29, "#ffcc44", 0.07),
    (17, "#ffdd66", 0.14),
]

# 公转速度倍率（>1 更快，<1 更慢）
ORBIT_SPEED_SCALE = 0.35


class SolarSystem:
    def __init__(self):
        self.fig = plt.figure(figsize=(10, 10), facecolor="#050510")
        self.ax = self.fig.add_axes((0, 0, 1, 1), facecolor="#050510")
        self.ax.set_aspect("equal")
        self.ax.set_axis_off()

        # ---- 纹理生成 ----
        self.size_tex = 256
        tex = {}
        for name, _, _, _, _ in PLANETS:
            tex[name] = TEXTURE_GENERATORS[name](self.size_tex)
        self.textures = tex

        # ---- 视图状态 ----
        self.view_cx = 0.0
        self.view_cy = 0.0
        self.target_cx = 0.0
        self.target_cy = 0.0
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.mouse_in = False

        # ---- 详情模式 ----
        self.mode = "overview"       # "overview" | "zooming_in" | "detail" | "zooming_out"
        self.detail_planet = None    # 行星名称
        self.detail_progress = 0.0   # 0=overview, 1=fully zoomed
        self.detail_planet_pos = (0, 0)  # 进入详情时行星的位置

        # ---- 背景星空 ----
        rng = np.random.default_rng(42)
        n = 500
        self.star_x = rng.uniform(-380, 380, n)
        self.star_y = rng.uniform(-380, 380, n)
        self.star_s = rng.uniform(0.2, 2.8, n)
        self.star_phase = rng.uniform(0, 2 * np.pi, n)
        self.star_base_alpha = rng.uniform(0.25, 1.0, n)
        self.stars = self.ax.scatter(
            self.star_x, self.star_y, s=self.star_s, c="white",
            alpha=self.star_base_alpha, zorder=0,
        )

        # ---- 小行星带 ----
        n_ast = 300
        ast_r = rng.uniform(108, 132, n_ast)
        ast_theta = rng.uniform(0, 2 * np.pi, n_ast)
        self.ast_x = ast_r * np.cos(ast_theta)
        self.ast_y = ast_r * np.sin(ast_theta)
        self.ast_s = rng.uniform(0.3, 1.0, n_ast)
        self.asteroids = self.ax.scatter(
            self.ast_x, self.ast_y, s=self.ast_s, c="#887755",
            alpha=0.5, zorder=0,
        )

        # ---- 轨道线 ----
        for _, orbit_r, _, _, _ in PLANETS:
            self.ax.add_patch(Circle(
                (0, 0), orbit_r, fill=False, color="#222233",
                linewidth=0.5, zorder=0,
            ))

        # ---- 太阳光晕 ----
        self.glow_patches = []
        for r, color, alpha in GLOW_LAYERS:
            p = Circle((0, 0), r, color=color, alpha=alpha, zorder=1)
            self.ax.add_patch(p)
            self.glow_patches.append(p)

        # ---- 太阳主体 ----
        self.sun = Circle((0, 0), 14, color="#ffe840", zorder=2)
        self.ax.add_patch(self.sun)
        self.sun_core = Circle((0, 0), 9, color="#fffef0", zorder=3)
        self.ax.add_patch(self.sun_core)

        # ---- 行星（OffsetImage） ----
        self.planet_imgs = []      # OffsetImage
        self.planet_boxes = []     # AnnotationBbox
        self.planet_rings = []     # 土星光环
        self.planet_labels = []
        self.planet_data = []      # 存储当前帧的行星位置

        for name, orbit_r, pr, _period, has_ring in PLANETS:
            # 行星图片
            oi = OffsetImage(self.textures[name], zoom=pr / self.size_tex * 1.4)
            oi.set_zorder(4)
            ab = AnnotationBbox(oi, (orbit_r, 0), frameon=False,
                                box_alignment=(0.5, 0.5), pad=0)
            ab.set_zorder(4)
            self.ax.add_artist(ab)
            self.planet_imgs.append(oi)
            self.planet_boxes.append(ab)

            # 光环
            if has_ring:
                ring = Circle((0, 0), pr * 1.9, fill=False, color="#d4c878",
                              linewidth=3, alpha=0.5, zorder=4)
                self.ax.add_patch(ring)
                self.planet_rings.append(ring)
            else:
                self.planet_rings.append(None)

            # 标签
            t = self.ax.text(orbit_r, 0, name, color="white", fontsize=7,
                             ha="center", va="bottom", alpha=0.7)
            self.planet_labels.append(t)

        self.planet_data = [(0.0, 0.0) for _ in PLANETS]

        # ---- 地球月球 ----
        self.moon = Circle((0, 0), 1.3, color="#cccccc", zorder=5)
        self.ax.add_patch(self.moon)

        # ---- 详情模式大字展示 ----
        self.detail_img = self.ax.imshow(
            np.zeros((self.size_tex, self.size_tex, 3)),
            extent=(-50, 50, -50, 50), zorder=10, visible=False,
            interpolation='bilinear',
        )
        self.detail_label = self.ax.text(
            0, 0, "", color="white", fontsize=14, ha="center", va="bottom",
            zorder=11, visible=False, fontweight="bold",
        )
        self.detail_hint = self.ax.text(
            0, 0, "", color="#aaaaaa", fontsize=9, ha="center", va="top",
            zorder=11, visible=False,
        )

        # ---- 事件 ----
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_mouse)
        self.fig.canvas.mpl_connect("figure_leave_event", self._on_leave)
        self.fig.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

        self.t = 0.0
        self.dt = 0.02 * ORBIT_SPEED_SCALE

    # ---- 事件处理 ----
    def _on_mouse(self, event):
        if event.x is None or event.y is None:
            return
        self.mouse_in = True
        fig_w, fig_h = self.fig.get_size_inches() * self.fig.dpi
        rel_x = (event.x - fig_w / 2) / (fig_w / 2)
        rel_y = (event.y - fig_h / 2) / (fig_h / 2)
        view_range = 300 / self.zoom
        self.target_cx = rel_x * view_range * 0.4
        self.target_cy = rel_y * view_range * 0.4

    def _on_leave(self, event):
        self.mouse_in = False
        self.target_cx = 0.0
        self.target_cy = 0.0

    def _on_scroll(self, event):
        if self.mode in ("zooming_in", "zooming_out"):
            return
        if event.button == "up":
            self.target_zoom = min(8.0, self.target_zoom * 1.12)
        else:
            self.target_zoom = max(0.15, self.target_zoom / 1.12)

    def _on_click(self, event):
        """点击行星 → 放大查看表面"""
        if event.xdata is None or event.ydata is None:
            return
        if self.mode not in ("overview", "detail"):
            return

        if self.mode == "detail":
            # 点击空白区域退出详情
            px, py = self.detail_planet_pos
            # 检查是否点击在详情行星上
            planet_r = self._get_planet_radius(self.detail_planet)
            detail_radius = planet_r * 5 * self.detail_progress  # 当前显示大小
            dist = np.hypot(event.xdata - px, event.ydata - py)
            if dist > detail_radius * 1.2:
                self._exit_detail()
            return

        # overview 模式：检测点击行星
        for i, (name, _, _, _, _) in enumerate(PLANETS):
            px, py = self.planet_data[i]
            dist = np.hypot(event.xdata - px, event.ydata - py)
            threshold = self._get_planet_radius(name) * 1.8
            if dist < threshold:
                self._enter_detail(name, (px, py))
                break

    def _on_key(self, event):
        if event.key == "escape" and self.mode == "detail":
            self._exit_detail()

    def _get_planet_radius(self, name):
        for n, _, pr, _, _ in PLANETS:
            if n == name:
                return pr
        return 5

    def _enter_detail(self, name, pos):
        self.mode = "zooming_in"
        self.detail_planet = name
        self.detail_planet_pos = pos
        self.detail_progress = 0.0
        self.detail_img.set_data(self.textures[name])
        self.detail_label.set_text(name)
        self.detail_label.set_visible(True)
        self.detail_hint.set_text("click background or press Esc to return")
        self.detail_hint.set_visible(True)
        self.detail_img.set_visible(True)

    def _exit_detail(self):
        self.mode = "zooming_out"

    # ---- 更新循环 ----
    def update(self, frame):
        self.t += self.dt

        # 平滑过渡
        self.view_cx += (self.target_cx - self.view_cx) * 0.08
        self.view_cy += (self.target_cy - self.view_cy) * 0.08
        self.zoom += (self.target_zoom - self.zoom) * 0.1

        # ---- 详情模式过渡 ----
        if self.mode == "zooming_in":
            self.detail_progress += 0.03
            if self.detail_progress >= 1.0:
                self.detail_progress = 1.0
                self.mode = "detail"
        elif self.mode == "zooming_out":
            self.detail_progress -= 0.03
            if self.detail_progress <= 0.0:
                self.detail_progress = 0.0
                self.mode = "overview"
                self.detail_planet = None
                self.detail_img.set_visible(False)
                self.detail_label.set_visible(False)
                self.detail_hint.set_visible(False)

        # 详情模式下视图锁定行星
        if self.mode in ("zooming_in", "detail") and self.detail_planet is not None:
            px, py = self.detail_planet_pos
            self.target_cx = px
            self.target_cy = py
            self.target_zoom = 3.0 + self.detail_progress * 5.0  # 最大 8x

        if self.mode == "zooming_out" and self.detail_planet is not None:
            self.target_cx = 0
            self.target_cy = 0
            self.target_zoom = 1.0

        # 视图范围
        r = 300 / self.zoom
        self.ax.set_xlim(self.view_cx - r, self.view_cx + r)
        self.ax.set_ylim(self.view_cy - r, self.view_cy + r)

        # 太阳脉动
        pulse = 1.0 + 0.03 * np.sin(self.t * 1.5)
        self.sun.set_radius(14 * pulse)
        self.sun_core.set_radius(9 * pulse)
        for i, (gr, _, _) in enumerate(GLOW_LAYERS):
            self.glow_patches[i].set_radius(gr * pulse)

        # 星空闪烁
        twinkle = np.clip(
            self.star_base_alpha * (0.5 + 0.5 * np.sin(self.t * 2.5 + self.star_phase)),
            0.08, 1.0,
        )
        self.stars.set_alpha(twinkle)

        # 小行星带旋转
        ast_speed = 0.15 * ORBIT_SPEED_SCALE
        cos_a, sin_a = np.cos(ast_speed * self.t), np.sin(ast_speed * self.t)
        self.asteroids.set_offsets(np.column_stack([
            self.ast_x * cos_a - self.ast_y * sin_a,
            self.ast_x * sin_a + self.ast_y * cos_a,
        ]))

        # 更新行星位置
        for i, (name, orbit_r, pr, period, has_ring) in enumerate(PLANETS):
            angle = self.t * 2 * np.pi / period
            px = orbit_r * np.cos(angle)
            py = orbit_r * np.sin(angle)
            self.planet_boxes[i].xybox = (px, py)
            self.planet_data[i] = (px, py)

            # 如果是正在被放大的行星，更新其记录位置
            if name == self.detail_planet and self.mode in ("zooming_in", "detail"):
                self.detail_planet_pos = (px, py)

            if self.planet_rings[i] is not None:
                self.planet_rings[i].center = (px, py)

            self.planet_labels[i].set_position((px, py + pr + 5))

            # 地球月球
            if name == "Earth":
                moon_angle = self.t * 2 * np.pi / 0.075
                moon_dist = pr * 3.5
                self.moon.center = (
                    px + moon_dist * np.cos(moon_angle),
                    py + moon_dist * np.sin(moon_angle),
                )

        # 更新详情展示
        if self.mode in ("zooming_in", "detail", "zooming_out") and self.detail_planet is not None:
            px, py = self.detail_planet_pos
            pr = self._get_planet_radius(self.detail_planet)
            # 图片显示大小随 progress 增大
            display_r = pr * (1.5 + self.detail_progress * 12)
            self.detail_img.set_extent((
                px - display_r, px + display_r,
                py - display_r, py + display_r,
            ))
            # 更新标签和提示位置
            self.detail_label.set_position((px, py + display_r + 5))
            self.detail_hint.set_position((px, py - display_r - 8))
            # 透明度渐变
            alpha = min(1.0, self.detail_progress * 2)
            self.detail_img.set_alpha(alpha)
            self.detail_label.set_alpha(alpha)
            self.detail_hint.set_alpha(alpha)

        return []

    def run(self):
        ani = animation.FuncAnimation(
            self.fig, self.update, interval=25, blit=False, cache_frame_data=False,
        )
        plt.show()


if __name__ == "__main__":
    SolarSystem().run()

# 桌面虚拟小伙伴 — 巴巴塔

一个基于 Panda3D + 通义千问的桌面 3D 虚拟人物应用。

## 功能

- **3D 角色** 始终显示在桌面前景（置顶、透明背景）
- **文字聊天** 按 F3 与 AI 角色对话
- **鼠标互动** 点击、拖拽、抚摸头部
- **AI 大脑** 通义千问 (DashScope) 驱动
- **语音合成** edge-tts/Win SAPI 朗读回复

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `config.py`，将 `DASHSCOPE_API_KEY` 设置为你的通义千问 API Key：

```python
DASHSCOPE_API_KEY = "sk-xxxxxxxxxxxxx"
```

或设置环境变量：

```bash
set DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx
```

### 3. 启动

```bash
python main.py
```

### 4. 操作

| 操作 | 方式 |
|---|---|
| 文字聊天 | 按 F3 |
| 拖动角色 | 鼠标拖拽 |
| 抚摸头部 | 鼠标悬停头部 2 秒 |
| 显示/隐藏 | Ctrl+F1 |

## 替换 3D 模型

将 VRM 模型通过 Blender 导出为 `.glb` 格式，放入 `resources/models/` 目录。

推荐免费 VRM 模型来源：
- [VRoid Hub](https://hub.vroid.com/)
- [Booth.pm](https://booth.pm/)

## 配置角色人设

编辑 `resources/personality.yaml` 可自定义角色性格、说话风格等。

## 项目结构

```
virtual-character/
├── main.py               # 入口
├── config.py             # 全局配置
├── engine/               # 3D 渲染引擎
├── character/            # 动画与表情
├── ai/                   # AI 大脑
├── voice/                # 语音合成
├── interaction/          # 聊天与鼠标交互
├── ui/                   # UI（聊天弹窗、设置）
├── utils/                # 工具函数
└── resources/            # 模型、人设、对话记录
```

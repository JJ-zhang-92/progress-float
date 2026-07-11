# Progress Float / 悬浮进度球

<p align="center">
  <b>OpenCode Agent Desktop Pet — powered by CoPet</b><br>
  <sub>OpenCode Agent 桌面桌宠 — CoPet 驱动 · 250+ 社区宠物 · 4 态感知</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/opencode-plugin-blue">
  <img src="https://img.shields.io/badge/copet-powered-green">
  <img src="https://img.shields.io/badge/license-MIT-yellow">
</p>

---

## Migration Notice / 迁移公告

**v5.0 → v6.0**: Visual layer migrated from custom tkinter widget to CoPet desktop pet platform.
视觉层从自研 tkinter 悬浮球迁移到 CoPet 桌宠平台。

- Removed 500+ lines of custom tkinter window code / 移除 500+ 行自研 tkinter 窗口代码
- CoPet provides native transparent windows, drag, 250+ pet gallery, sound effects
  CoPet 提供原生透明窗口、拖拽、250+ 宠物库、音效

---

## ✨ Features / 特性

### 🔴🟢🟡⚪ Four-Phase State Machine / 四态状态机

Hook-driven phase tracking — no heuristics, no guessing.
钩子驱动 — 不靠猜测、不靠超时。

| Phase / 状态 | CoPet Reaction / 桌宠反应 | Trigger / 触发 |
|---|---|---|
| **Waiting** 等待 | Alert animation + notification / 警报动画 | `permission.ask` — 等待用户输入 |
| **Executing** 执行 | Working animation / 工作动画 | `tool.execute.before` — 工具运行 |
| **Thinking** 思考 | Thinking animation / 思考动画 | `chat.message` / 工具间隙 |
| **Idle** 空闲 | Idle animation / 待机动画 | 无活动 |

### 👾 250+ Community Pets / 社区宠物库

CoPet supports Codex-compatible pet packages. Install any from the gallery or generate your own with `copet-gen` skill.
CoPet 支持 Codex 兼容宠物包。从社区库安装或通过 `copet-gen` skill AI 生成自定义宠物。

### 🔄 Architecture / 架构

```
OpenCode hooks → progress-float.js plugin
                    ├─→ POST /report → progress-server.js (HTTP aggregation + detail panel)
                    └─→ POST events → CoPet Runtime → Desktop Pet Window
```

---

## 📁 Structure / 项目结构

```
progress-float/
├── plugin/
│   ├── progress-float.js      # OpenCode plugin (~355 lines) — hooks + CoPet bridge
│   └── progress-server.js     # HTTP aggregation server (~275 lines)
├── config.json                # Unified configuration
├── schema.json                # v3 state schema
└── README.md
```

---

## 🚀 Quick Start / 快速开始

### 1. Install CoPet / 安装 CoPet

Download from [CoPet Releases](https://github.com/ChanceYu/CoPet/releases).
从 CoPet Releases 下载。

Run the setup wizard — select your pet and enable OpenCode integration.
运行 Setup 向导 — 选择宠物并启用 OpenCode 集成。

### 2. Register Plugin / 注册插件

In `opencode.jsonc` / 在 `opencode.jsonc` 中添加：

```jsonc
{
  "plugin": [
    "../../../../.opencode/progress-float/plugin/progress-float.js"
  ]
}
```

### 3. Done / 完成

Start OpenCode. The pet reacts to your coding activity. / 启动 OpenCode，桌宠自动响应编程活动。

---

## 🔧 Configuration / 配置

All in `config.json` / 统一在 `config.json`：

| Param / 参数 | Default / 默认 | Description / 说明 |
|---|---|---|
| `port` | 19822 | Aggregation server port · 聚合服务端口 |
| `toolTimeoutMs` | 120000 | Max tool runtime · 工具超时 |
| `sessionTtlMs` | 600000 | Idle session lifetime · Session 生存期 |
| `reportTtlMs` | 30000 | Project report TTL · 项目上报 TTL |

---

## 🎮 Interaction / 交互

| Action / 操作 | Result / 效果 |
|---|---|
| Hover pet · 悬停 | Pet reacts with hover animation · 宠物反应 |
| Click pet · 点击 | Interaction animation · 交互动画 |
| Double-click · 双击 | Pet reaction · 宠物反应 |
| Right-click · 右键 | CoPet context menu · CoPet 上下文菜单 |
| Drag pet · 拖拽 | Reposition anywhere · 任意位置 |

---

## License / 协议

MIT

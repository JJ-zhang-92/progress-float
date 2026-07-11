# Progress Float / 悬浮进度球

<p align="center">
  <b>Real-time OpenCode Agent Progress Monitor · 四态悬浮球 + 精灵模式 + 多项目分组面板</b><br>
  <sub>OpenCode Agent 实时进度监控 · Four-phase floating ball + sprite mode + multi-project grouping</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue">
  <img src="https://img.shields.io/badge/node-22+-green">
  <img src="https://img.shields.io/badge/dependencies-0-success">
  <img src="https://img.shields.io/badge/license-MIT-yellow">
</p>

---

## ✨ Features / 特性

### 🔴🟢🟡⚪ Four-Phase State Machine / 四态状态机

Hook-driven — no heuristics, no guessing. / 钩子驱动 — 不靠猜测、不靠超时。

| Phase / 状态 | Color / 颜色 | Animation / 动画 | Trigger / 触发条件 |
|-------|-------|-----------|---------|
| **Waiting** | Red 红 | Pulse + "!" flash | `permission.ask` — 等待用户输入 |
| **Executing** | Green 绿 | Spinning dots + pulse rings | `tool.execute.before` — 工具运行中 |
| **Thinking** | Amber 琥珀 | Breathing pulse + "?" bounce | `chat.message` / 工具间隙 — 规划思考中 |
| **Idle** | Gray 灰 | Hollow circle + "z" float | 无活动 |

Priority: waiting > executing > thinking > idle. Transition is instant — no 8s delay.
优先级：等待 > 执行 > 思考 > 空闲。状态切换即时生效，无 8 秒延迟。

### 👾 Sprite Mode / 精灵模式

AI-generated chibi anime pet with phase-specific animations.
AI 生成的 Q 版动漫宠物，不同状态有不同动画。

| Phase / 状态 | Sprite + Decor |
|-------|----------------|
| Executing | Working chibi + rotating dot ring + green glow · 工作精灵 + 旋转小点 + 绿光晕 |
| Thinking | Thinking chibi + bouncing "?" + amber glow · 思考精灵 + 弹跳问号 + 琥珀光晕 |
| Waiting | Alert chibi + flashing "!" + red glow · 警报精灵 + 闪烁感叹号 + 红光晕 |
| Idle | Idle chibi + floating "z" particles · 空闲精灵 + 飘起"z"粒子 |

- Radial gradient mask for smooth edges (no hard black cutout) — 径向渐变遮罩平滑边缘
- Generated via Tongyi-MAI/Z-Image-Turbo, 512×512 → 110×110
- Right-click → **Appearance** → Ball / Sprite — 右键 → **外观** → 悬浮球 / 精灵
- Skin placeholder ready for future plugins — 皮肤接口已预留

### 📊 Multi-Project & Session Grouping / 多项目分组

Click the ball to expand a glassmorphism detail panel.
点击球体展开玻璃拟态详情面板。

| Scenario / 场景 | Display / 展示 |
|----------|---------|
| ≥ 2 projects / 多个项目 | Project cards (name + tool count + colored history dots) · 项目卡片 |
| 1 project / 单个项目 | Session/Agent detail cards · Session 详情卡 |
| No data / 无数据 | "Waiting for tasks..." · "等待任务中..." |

### 🔄 Aggregation Architecture / 聚合架构

```
Instance A ──POST /report/project──┐
Instance B ──POST /report/project──┤──→ Server :19822
Local state file fallback ─────────┘       ↓ Map + 30s TTL
                                            ↓ GET /state
                                         Floating Ball Widget
```

### 🛡️ Reliability / 可靠性

- **toolCount anti-drift** — Dynamic `filter(status==="running").length` · 动态计算，不依赖 ±1
- **Zombie tool timeout** — >120s → auto-done · 僵尸工具 120s 自动完成
- **Zombie session cleanup** — 10min idle → auto-delete · 空闲 10min 自动清理
- **Periodic reconciliation** — every 10s · 每 10 秒对账
- **Singleton lock** — PID file · 单例锁防重复

---

## 📁 Structure / 项目结构

```
progress-float/
├── plugin/
│   ├── progress-float.js      # OpenCode plugin (~305 lines)
│   └── progress-server.js     # HTTP aggregation server (~275 lines)
├── widget/
│   ├── progress-float.pyw     # Python tkinter widget (~530 lines)
│   ├── progress-widget.html   # HTML alternative (~280 lines)
│   └── sprites/
│       ├── chibi/              # Chibi sprite skin (4 PNGs)
│       ├── cn3d-1/             # 动漫3D variant 1 (4 PNGs)
│       ├── cn3d-2/             # 动漫3D variant 2 (4 PNGs)
│       └── cn3d-3/             # 动漫3D variant 3 (4 PNGs)
├── launcher/
│   └── progress-launcher.ps1  # PowerShell one-click launcher
├── config.json                # Unified configuration
├── schema.json                # v3 state schema
└── README.md
```

---

## 🚀 Quick Start / 快速开始

### 1. Register Plugin / 注册插件

In `opencode.jsonc` / 在 `opencode.jsonc` 中添加：

```jsonc
{
  "plugin": [
    "../../../../.opencode/progress-float/plugin/progress-float.js"
  ]
}
```

### 2. Launch / 启动

```powershell
.\launcher\progress-launcher.ps1
```

Or manually / 或手动：

```bash
node plugin/progress-server.js 19822 cache
pythonw widget/progress-float.pyw
```

---

## 🔧 Configuration / 配置

All in `config.json` / 统一在 `config.json`：

| Param / 参数 | Default / 默认 | Description / 说明 |
|-------|---------|-------------|
| `port` | 19822 | Server port · 端口 |
| `toolTimeoutMs` | 120000 | Max tool runtime · 工具超时 |
| `sessionTtlMs` | 600000 | Idle session lifetime · Session 生存期 |
| `projectTtlMs` | 30000 | Project report TTL · 项目上报 TTL |
| `pollIntervalMs` | 500 | Widget polling interval · 轮询间隔 |

---

## 🖥️ Requirements / 环境要求

- **Python 3.8+** with `tkinter`, `Pillow`, `numpy`
- **Node.js 22+** (aggregation server)
- **OpenCode** (plugin support)

---

## 🎮 Interaction / 交互

| Action / 操作 | Result / 效果 |
|--------|--------|
| Left-click · 左键 | Toggle detail panel · 切换面板 |
| Right-click → Appearance → Classic Ball | Classic ball mode · 经典球模式 |
| Right-click → Appearance → chibi/cn3d-1/cn3d-2/cn3d-3 | Sprite skin · 精灵皮肤 |
| Right-click → Exit · 右键→退出 | Close widget + server |
| Drag · 拖拽 | Reposition anywhere · 任意位置 |

---

## 📄 License / 协议

MIT — fork it, ship it, sell it. 随意 fork、分发、商用。

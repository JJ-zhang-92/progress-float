# Progress Float

<p align="center">
  <b>Real-time OpenCode Agent Progress Monitor</b><br>
  Three-state floating ball + multi-project grouping panel + zero-dependency auto lifecycle<br>
  <sub>OpenCode Agent 实时进度监控 · 三态悬浮球 + 多项目分组面板 + 零依赖自动启停</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue">
  <img src="https://img.shields.io/badge/node-22+-green">
  <img src="https://img.shields.io/badge/dependencies-0-success">
  <img src="https://img.shields.io/badge/license-MIT-yellow">
</p>

---

📖 **中文用户请阅读 [README-ZH.md](README-ZH.md)**

---

## ✨ Features

### 🟢🟡⚪ Three-State Ball

| State | Color | Animation | Meaning |
|-------|-------|-----------|---------|
| **Active** | Green | Spinning dots + pulse rings | Tools executing (bash/read/write...) |
| **Thinking** | Amber | Slow breathing pulse | Planning/streaming, no running tools |
| **Idle** | Gray | Hollow circle | No activity > 8s |

Covers full task lifecycle — shell commands stay green throughout, thinking gaps between tool calls show amber instead of falsely reporting idle.

### 📊 Multi-Project & Session Grouping

Click the ball to open a glassmorphism detail panel. Grouping adapts automatically:

| Scenario | Display |
|----------|---------|
| ≥ 2 projects | Project cards (name + tool count + tasks + colored history dot bar) |
| 1 project | Session/Agent detail cards (opencode / explore / general / dreamer...) |
| No data | "Waiting for tasks..." |

Each card color-coded by tool type: bash=cyan, read=blue, write=orange, grep=pink...

### 🔄 Real-Time Aggregation

```
Instance A ──POST /report/my-app─────┐
Instance B ──POST /report/api-server─┤──→ Aggregation Server :19822
Local state file fallback ───────────┘       ↓ in-memory Map + 30s TTL
                                              ↓ GET /state
                                           Floating Ball Widget
```

Multiple OpenCode instances report to one server. 30-second TTL auto-cleans stale projects.

### 🚀 Auto Lifecycle

| Trigger | Action |
|---------|--------|
| Tools running > 2s | Widget auto-launches |
| State file stale > 60s | Widget auto-closes (OpenCode dead) |
| Right-click ball → Exit | Instant close + lock cleanup |
| Server idle 5min | Server auto-exits, releases port |

### 🛡️ Production Reliability

- **toolCount anti-drift** — Dynamic `filter(status==="running").length`, never ±1
- **Zombie tool timeout** — Running > 120s → auto-marked done
- **Zombie session cleanup** — No running tools + 10min inactive → auto-deleted
- **Periodic reconciliation** — `setInterval` every 10s
- **Singleton lock** — PID file prevents duplicate widgets

---

## 📁 Structure

```
progress-float/
├── plugin/
│   ├── progress-float.js      # OpenCode plugin (218 lines)
│   └── progress-server.js     # HTTP/SSE aggregation server (260 lines)
├── widget/
│   ├── progress-float.pyw     # Python tkinter floating ball (335 lines)
│   └── progress-widget.html   # HTML alternative (280 lines)
├── launcher/
│   └── progress-launcher.ps1  # PowerShell one-click launcher
└── README.md
```

---

## 🚀 Quick Start

### 1. Register Plugin

Add to `opencode.jsonc`:

```jsonc
{
  "plugin": [
    ".opencode/plugins/progress-float.js"
  ]
}
```

### 2. Launch

```powershell
.\launcher\progress-launcher.ps1
```

Or manually:

```bash
node plugin/progress-server.js 19822 cache
pythonw widget/progress-float.pyw
```

### 3. Done

Ball appears bottom-right. Starts OpenCode tasks — it auto-activates.

---

## 🔧 Configuration

| Param | Default | File:Line | Description |
|-------|---------|-----------|-------------|
| `PORT` | 19822 | `plugin/progress-float.js:12` | Server port |
| `TOOL_TIMEOUT_MS` | 120000 | `plugin/progress-float.js:16` | Max tool runtime before auto-done |
| `SESSION_TTL_MS` | 600000 | `plugin/progress-float.js:17` | Idle session lifetime |
| `TTL_MS` | 30000 | `plugin/progress-server.js:18` | Project report TTL |
| Thinking timeout | 8s | `widget/progress-float.pyw:118` | How long "thinking" persists |
| State stale threshold | 60s | `widget/progress-float.pyw:41` | Stale state file = OpenCode dead |

---

## 🖥️ Requirements

- **Python 3.8+** with `tkinter` (bundled on Windows/macOS; `apt install python3-tk` on Linux)
- **Node.js 22+** (aggregation server)
- **OpenCode** (any version with plugin support)

**Zero pip/npm dependencies** — standard library only.

---

## 🎮 Interaction

| Action | Result |
|--------|--------|
| Left-click ball | Toggle detail panel |
| Right-click ball | Exit menu |
| Drag ball | Reposition anywhere |
| Panel focus out | Auto-hide |

---

## ⚠️ Limitations

| Issue | Detail |
|-------|--------|
| Multi-project grouping needs OpenCode restart | Plugin POST reporting loads at startup. One-time setup. |
| Windows tkinter no true alpha | Shadows/glow use stipple simulation. PyQt/Electron would need rewrite. |

---

## 📄 License

MIT — fork it, ship it, sell it.

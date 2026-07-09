# Progress Float

<p align="center">
  <b>Real-time OpenCode Agent Progress Monitor</b><br>
  Four-phase floating ball + sprite mode + multi-project grouping panel<br>
  <sub>OpenCode Agent 实时进度监控 · 四态悬浮球 + 精灵模式 + 多项目分组面板</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue">
  <img src="https://img.shields.io/badge/node-22+-green">
  <img src="https://img.shields.io/badge/dependencies-0-success">
  <img src="https://img.shields.io/badge/license-MIT-yellow">
</p>

---

## ✨ Features

### 🔴🟢🟡⚪ Four-Phase State Machine

Hook-driven phase tracking — no heuristics, no guessing.

| Phase | Color | Animation | Trigger |
|-------|-------|-----------|---------|
| **Waiting** | Red | Pulse + "!" flash | `permission.ask` hook — agent needs user input |
| **Executing** | Green | Spinning dots + pulse rings | `tool.execute.before` — tools running |
| **Thinking** | Amber | Breathing pulse + "?" bounce | `chat.message` / tool gap — planning/streaming |
| **Idle** | Gray | Hollow circle + "z" float | No activity |

Phase priority: waiting > executing > thinking > idle. Transition is instant — no 8s delay.

### 👾 Sprite Mode

AI-generated chibi anime pet with state-specific animations:

| Phase | Sprite + Decor |
|-------|----------------|
| Executing | Working chibi + rotating dot ring + green glow |
| Thinking | Thinking chibi + bouncing "?" + amber glow |
| Waiting | Alert chibi + flashing "!" + red glow |
| Idle | Idle chibi + floating "z" particles |

- Radial gradient mask for smooth sprite edges (no hard black cutout)
- Generated via Tongyi-MAI/Z-Image-Turbo, 512×512 → 110×110
- Right-click → **Appearance** → Ball / Sprite toggle
- Appearance submenu ready for future skin plugins

### 📊 Multi-Project & Session Grouping

Click the ball to open a glassmorphism detail panel:

| Scenario | Display |
|----------|---------|
| ≥ 2 projects | Project cards (name + tool count + tasks + colored history dot bar) |
| 1 project | Session/Agent detail cards (opencode / explore / general / dreamer...) |
| No data | "Waiting for tasks..." |

### 🔄 Real-Time Aggregation

```
Instance A ──POST /report/project──┐
Instance B ──POST /report/project──┤──→ Aggregation Server :19822
Local state file fallback ─────────┘       ↓ in-memory Map + 30s TTL
                                            ↓ GET /state
                                         Floating Ball Widget
```

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
│   ├── progress-float.js      # OpenCode plugin (~305 lines)
│   └── progress-server.js     # HTTP aggregation server (~275 lines)
├── widget/
│   ├── progress-float.pyw     # Python tkinter widget (~510 lines)
│   ├── progress-widget.html   # HTML alternative (~280 lines)
│   └── sprites/
│       ├── working.png        # Executing phase sprite
│       ├── thinking.png       # Thinking phase sprite
│       ├── idle.png           # Idle phase sprite
│       └── alert.png          # Waiting phase sprite
├── launcher/
│   └── progress-launcher.ps1  # PowerShell one-click launcher
├── config.json                # Unified configuration
├── schema.json                # v3 state schema
└── README.md
```

---

## 🚀 Quick Start

### 1. Register Plugin

Add to `opencode.jsonc`:

```jsonc
{
  "plugin": [
    "../../../../.opencode/progress-float/plugin/progress-float.js"
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

---

## 🔧 Configuration

All in `config.json`:

| Param | Default | Description |
|-------|---------|-------------|
| `port` | 19822 | Server port |
| `toolTimeoutMs` | 120000 | Max tool runtime before auto-done |
| `sessionTtlMs` | 600000 | Idle session lifetime |
| `projectTtlMs` | 30000 | Project report TTL |
| `pollIntervalMs` | 500 | Widget polling interval |

---

## 🖥️ Requirements

- **Python 3.8+** with `tkinter`, `Pillow`, `numpy`
- **Node.js 22+** (aggregation server)
- **OpenCode** (any version with plugin support)

---

## 🎮 Interaction

| Action | Result |
|--------|--------|
| Left-click ball | Toggle detail panel |
| Right-click → Appearance → Ball | Classic ball mode |
| Right-click → Appearance → Sprite | Chibi sprite mode |
| Right-click → Exit | Close widget + server |
| Drag ball | Reposition anywhere |
| Panel focus out | Auto-hide |

---

## 📄 License

MIT — fork it, ship it, sell it.

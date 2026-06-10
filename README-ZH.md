# Progress Float · 悬浮球

<p align="center">
  <b>OpenCode Agent 实时进度监控</b><br>
  三态悬浮球 + 多项目分组面板 + 零依赖自动启停<br>
  <sub>Real-time OpenCode Agent Progress Monitor · Three-state floating ball + multi-project grouping + zero-dependency auto lifecycle</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue">
  <img src="https://img.shields.io/badge/node-22+-green">
  <img src="https://img.shields.io/badge/dependencies-0-success">
  <img src="https://img.shields.io/badge/license-MIT-yellow">
</p>

---

## ✨ 特性

### 🟢🟡⚪ 三态悬浮球

| 状态 | 颜色 | 动画 | 含义 |
|------|------|------|------|
| **Active** | 绿色 | 旋转点 + 脉冲光环 | 工具执行中 (bash/read/write...) |
| **Thinking** | 琥珀色 | 慢速呼吸脉冲 | 规划/流式生成中，无运行工具 |
| **Idle** | 灰色 | 空心圆 | 超过 8 秒无活动 |

覆盖任务全生命周期 — Shell 长任务全程绿色，工具间的规划间隙显示琥珀色而非误判空闲。

### 📊 多项目 / 多 Session 分组

点击球体展开玻璃拟态面板。分组逻辑自动适配：

| 场景 | 展示 |
|------|------|
| ≥ 2 个项目 | 项目卡片（名称 + 工具数 + 任务数 + 彩色历史圆点条） |
| 1 个项目 | Session/Agent 详情卡（opencode / explore / general / dreamer...） |
| 无数据 | "等待任务中..." |

每张卡片色彩按工具类型编码：bash=青、read=蓝、write=橙、grep=粉...

### 🔄 实时聚合架构

```
实例 A ──POST /report/my-app─────┐
实例 B ──POST /report/api-server─┤──→ 聚合 Server :19822
本地状态文件兜底 ────────────────┘       ↓ 内存 Map + 30s TTL
                                        ↓ GET /state
                                      悬浮球 Widget
```

多个 OpenCode 实例向同一 Server 上报。30 秒 TTL 自动清理过期项目。

### 🚀 自动启停

| 触发条件 | 行为 |
|---------|------|
| 工具运行超过 2 秒 | 自动启动悬浮球 |
| 状态文件超过 60 秒未更新 | 自动关闭（OpenCode 已死） |
| 右键球体 → Exit | 即时关闭 + 清理锁文件 |
| Server 空闲 5 分钟 | 自动退出释放端口 |

### 🛡️ 生产级可靠性

- **toolCount 防漂移** — 动态计算 `filter(status==="running").length`，不依赖 ±1
- **僵尸工具超时** — 运行超过 120s → 自动标记完成
- **僵尸 Session 清理** — 无运行工具 + 10min 无活动 → 自动删除
- **周期性对账** — `setInterval` 每 10s 执行清理
- **单例锁** — PID 文件防止重复实例

---

## 📁 项目结构

```
progress-float/
├── plugin/
│   ├── progress-float.js      # OpenCode 插件（218 行）
│   └── progress-server.js     # HTTP/SSE 聚合服务（260 行）
├── widget/
│   ├── progress-float.pyw     # Python tkinter 悬浮球（335 行）
│   └── progress-widget.html   # HTML 备选方案（280 行）
├── launcher/
│   └── progress-launcher.ps1  # PowerShell 一键启动
└── README.md
```

---

## 🚀 快速开始

### 1. 注册插件

在 `opencode.jsonc` 中添加：

```jsonc
{
  "plugin": [
    ".opencode/plugins/progress-float.js"
  ]
}
```

### 2. 启动

```powershell
.\launcher\progress-launcher.ps1
```

或手动：

```bash
node plugin/progress-server.js 19822 cache
pythonw widget/progress-float.pyw
```

### 3. 完成

球出现在右下角。OpenCode 执行任何任务即自动激活。

---

## 🔧 可调参数

| 参数 | 默认值 | 位置 | 说明 |
|------|--------|------|------|
| `PORT` | 19822 | `plugin/progress-float.js:12` | Server 端口 |
| `TOOL_TIMEOUT_MS` | 120000 | `plugin/progress-float.js:16` | 工具最大运行时间 |
| `SESSION_TTL_MS` | 600000 | `plugin/progress-float.js:17` | 空闲 Session 生存期 |
| `TTL_MS` | 30000 | `plugin/progress-server.js:18` | 项目上报 TTL |
| Thinking 超时 | 8s | `widget/progress-float.pyw:118` | Thinking 状态持续时长 |
| 状态文件过期阈值 | 60s | `widget/progress-float.pyw:41` | 文件过期 = OpenCode 已死 |

---

## 🖥️ 环境要求

- **Python 3.8+** 含 `tkinter`（Windows/macOS 自带；Linux: `apt install python3-tk`）
- **Node.js 22+**（聚合 Server）
- **OpenCode**（任意支持 Plugin 的版本）

**零 pip/npm 依赖**，仅使用标准库。

---

## 🎮 交互方式

| 操作 | 效果 |
|------|------|
| 左键球体 | 切换详情面板 |
| 右键球体 | 退出菜单 |
| 拖拽球体 | 任意位置重新定位 |
| 面板失焦 | 自动隐藏 |

---

## ⚠️ 已知限制

| 问题 | 说明 |
|------|------|
| 多项目分组需重启 OpenCode | 插件 POST 上报在启动时加载，一次性操作 |
| Windows tkinter 无真 alpha 通道 | 阴影/光晕用 stipple 模拟。如需真透明需重写为 PyQt/Electron |

---

## 📄 开源协议

MIT — fork 随意，商用随意。

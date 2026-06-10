// Progress Float — HTTP + SSE aggregation server
// Accepts POST /report/:project from each OpenCode instance.
// GET /state returns unified multi-project view. 30s TTL on reports.

import { createServer } from "node:http";
import { readFileSync, existsSync, watch } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.argv[2]) || 19822;
const CACHE_DIR = process.argv[3] || join(__dirname, "..", "..", "cache");
const PARENT_PID = parseInt(process.argv[4]) || 0;
const STATE_FILE = join(CACHE_DIR, "progress-state.json");
const HTML_FILE = join(__dirname, "..", "..", "progress-widget.html");
const WIDGET_SCRIPT = join(__dirname, "..", "..", "progress-float.pyw");
const TTL_MS = 30000;

// In-memory project aggregation
const projects = new Map();

function readLocalState() {
  try {
    if (!existsSync(STATE_FILE)) return null;
    return JSON.parse(readFileSync(STATE_FILE, "utf8"));
  } catch {
    return null;
  }
}

function isParentAlive() {
  if (!PARENT_PID) return true; // no PID passed → assume alive (backward compat)
  try {
    process.kill(PARENT_PID, 0);
    return true;
  } catch {
    return false;
  }
}

function aggregateState() {
  const now = Date.now();
  const projectEntries = {};

  // Clean expired + collect
  for (const [name, entry] of projects) {
    if (now - entry.lastSeen > TTL_MS) {
      projects.delete(name);
      continue;
    }
    projectEntries[name] = {
      active: entry.state.active || false,
      toolCount: entry.state.toolCount || 0,
      taskCount: entry.state.taskCount || 0,
      sessions: entry.state.sessions || {},
      activeTools: (entry.state.activeTools || []).slice(-30),
      lastUpdated: entry.state.lastUpdated || "",
    };
  }

  // Fallback: if no projects reported, read local file
  if (Object.keys(projectEntries).length === 0) {
    const local = readLocalState();
    if (local) {
      const name = basename(CACHE_DIR.replace(/[/\\]cache$/, "")) || "opencode";
      projectEntries[name] = {
        active: local.active || local.toolCount > 0,
        toolCount: local.toolCount || 0,
        taskCount: local.taskCount || 0,
        sessions: local.sessions || {},
        activeTools: (local.activeTools || []).slice(-30),
        lastUpdated: local.lastUpdated || "",
      };
    }
  }

  // Compute totals
  let totalActive = false;
  let totalToolCount = 0;
  let totalTaskCount = 0;
  for (const p of Object.values(projectEntries)) {
    if (p.active) totalActive = true;
    totalToolCount += p.toolCount;
    totalTaskCount += p.taskCount;
  }

  return {
    active: totalActive,
    toolCount: totalToolCount,
    taskCount: totalTaskCount,
    projects: projectEntries,
    lastUpdated: new Date().toISOString(),
  };
}

// Auto-launch widget
let widgetLaunched = false;
let launchDebounce = null;
let idleTicks = 0;

function tryLaunchWidget() {
  if (widgetLaunched) return;
  const state = aggregateState();
  if (state.toolCount > 0 || state.active) {
    clearTimeout(launchDebounce);
    launchDebounce = setTimeout(() => {
      const s2 = aggregateState();
      if (s2.toolCount > 0 || s2.active) {
        widgetLaunched = true;
        spawn("pythonw", [WIDGET_SCRIPT], {
          detached: true, stdio: "ignore", windowsHide: true,
        }).unref();
      }
    }, 2000);
  }
}

// SSE clients
const clients = new Set();

function broadcast() {
  const state = aggregateState();
  const data = `data: ${JSON.stringify(state)}\n\n`;
  for (const res of clients) {
    try { res.write(data); } catch { clients.delete(res); }
  }
  tryLaunchWidget();
}

// File watcher for local state changes
let watchTimeout;
let pollTimer;
function setupWatcher() {
  try {
    watch(CACHE_DIR, (eventType, filename) => {
      if (filename === "progress-state.json" || filename === null) {
        clearTimeout(watchTimeout);
        watchTimeout = setTimeout(broadcast, 50);
      }
    });
  } catch { /* fallback to polling */ }
  // Post-report-driven: also broadcast periodically to push SSE and clean TTL
  pollTimer = setInterval(() => {
    // Parent process check — exit if OpenCode/plugin is gone
    if (!isParentAlive()) {
      clearInterval(pollTimer);
      server.close();
      process.exit(0);
    }
    broadcast();
    tryLaunchWidget();
    if (projects.size === 0 && clients.size === 0) {
      idleTicks++;
      if (idleTicks > 150) {
        clearInterval(pollTimer);
        server.close();
        process.exit(0);
      }
    } else {
      idleTicks = 0;
    }
  }, 2000);
}

// Parse JSON body from POST
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString()));
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");

  if (req.method === "OPTIONS") {
    res.writeHead(204); res.end(); return;
  }

  // POST /report/:project — receive state from an instance
  if (req.method === "POST" && url.pathname.startsWith("/report/")) {
    const project = decodeURIComponent(url.pathname.slice("/report/".length));
    try {
      const body = await readBody(req);
      projects.set(project, { state: body, lastSeen: Date.now() });
      idleTicks = 0;
      broadcast();
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true, projects: projects.size }));
    } catch (e) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: false, error: e.message }));
    }
    return;
  }

  // GET /state — aggregated multi-project view
  if (url.pathname === "/state") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(aggregateState()));
    return;
  }

  // GET /events — SSE stream
  if (url.pathname === "/events") {
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    });
    res.write(`data: ${JSON.stringify(aggregateState())}\n\n`);
    idleTicks = 0;
    clients.add(res);
    req.on("close", () => clients.delete(res));
    return;
  }

  // GET /launch — manually launch widget
  if (url.pathname === "/launch") {
    widgetLaunched = true;
    try {
      spawn("pythonw", [WIDGET_SCRIPT], {
        detached: true, stdio: "ignore", windowsHide: true,
      }).unref();
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ launched: true }));
    } catch (e) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ launched: false, error: e.message }));
    }
    return;
  }

  // GET / — serve widget HTML
  try {
    const html = readFileSync(HTML_FILE, "utf8").replace(/{{PORT}}/g, String(PORT));
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(html);
  } catch {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Progress Float</title>
<style>body{font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#1a1a2e;color:#eee}
div{text-align:center}p{color:#888}</style></head><body><div>
<h1>Progress Float Server</h1><p>Port: ${PORT}</p>
</div></body></html>`);
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`progress-float aggregation server on http://127.0.0.1:${PORT}`);
  setupWatcher();
  tryLaunchWidget();
});

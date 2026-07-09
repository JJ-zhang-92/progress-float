// Progress Float — OpenCode plugin
// Tracks tool execution lifecycle grouped by session/agent.
// Reports state to the aggregation server via HTTP POST.
// Built-in cleanup: 120s tool timeout, 10min session TTL, dynamic count.

import { writeFileSync, readFileSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { request } from "node:http";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Read config.json (optional, falls back to defaults)
const configPath = join(__dirname, "..", "config.json");
let config = { port: 19822, cacheDir: "", toolTimeoutMs: 120000, sessionTtlMs: 600000, reportTtlMs: 30000 };
try {
  if (existsSync(configPath)) config = { ...config, ...JSON.parse(readFileSync(configPath, "utf8")) };
} catch {}

function resolveCacheDir(preferred) {
  if (preferred) return preferred;
  if (process.platform === "win32") {
    const appData = process.env.APPDATA || join(process.env.USERPROFILE || ".", "AppData", "Roaming");
    return join(appData, "progress-float");
  }
  return join(process.env.HOME || ".", ".progress-float");
}

const PORT = config.port;
const CACHE_DIR = resolveCacheDir(config.cacheDir);
const TOOL_TIMEOUT_MS = config.toolTimeoutMs;
const SESSION_TTL_MS = config.sessionTtlMs;

function ensureCacheDir() {
  if (!existsSync(CACHE_DIR)) mkdirSync(CACHE_DIR, { recursive: true });
}

function statePath() {
  return join(CACHE_DIR, "progress-state.json");
}

const TOOL_LABELS = {
  bash: "Running shell command",
  read: "Reading file",
  write: "Writing file",
  edit: "Editing code",
  grep: "Searching codebase",
  glob: "Finding files",
  task: "Delegating to sub-agent",
  webfetch: "Fetching web page",
  question: "Asking for clarification",
  todowrite: "Updating task list",
  skill: "Loading skill",
};

let taskCount = 0;
let activeTools = [];
let currentSession = null;
let serverStarted = false;

// Phase tracking — deterministic, hook-driven
let _thinking = false;
let waitingForUser = false;
let currentPhase = "idle";

// sessionID → { agent, taskCount, firstSeen, lastActivity }
const sessions = {};

function buildState() {
  const now = Date.now();

  // 1. Tool timeout — running for >120s → mark done
  for (const t of activeTools) {
    if (t.status === "running") {
      const started = new Date(t.startedAt).getTime();
      if (now - started > TOOL_TIMEOUT_MS) {
        t.status = "done";
        t.endedAt = new Date().toISOString();
      }
    }
  }

  // 2. Dynamic toolCount from activeTools
  const runningTools = activeTools.filter((t) => t.status === "running");
  const runningCount = runningTools.length;

  // 2b. Phase determination (priority: waiting > executing > thinking > idle)
  const hasQuestion = runningTools.some((t) => t.tool === "question");
  if (waitingForUser || hasQuestion) {
    currentPhase = "waiting";
  } else if (runningCount > 0) {
    currentPhase = "executing";
  } else if (_thinking) {
    currentPhase = "thinking";
  } else {
    currentPhase = "idle";
  }

  // 3. Session cleanup — no running tools + >10min since lastActivity → delete
  for (const [sid, info] of Object.entries(sessions)) {
    const hasRunning = activeTools.some(
      (t) => t.sessionID === sid && t.status === "running"
    );
    if (!hasRunning) {
      const lastActive = new Date(info.lastActivity || info.firstSeen).getTime();
      if (now - lastActive > SESSION_TTL_MS) {
        delete sessions[sid];
      }
    }
  }

  // 3b. Trim activeTools to prevent unbounded growth
  if (activeTools.length > 200) {
    activeTools.splice(0, activeTools.length - 100);
  }

  // 4. Build session entries
  const sessionEntries = {};
  for (const [sid, info] of Object.entries(sessions)) {
    const sessionTools = activeTools.filter((t) => t.sessionID === sid);
    const sessionRunning = sessionTools.filter((t) => t.status === "running");
    const now = Date.now();
    const lastActive = new Date(info.lastActivity || info.firstSeen).getTime();

    // Status + activity determination
    let status, activity;
    const runningDescs = sessionRunning.map((t) => TOOL_LABELS[t.tool] || `Running ${t.tool}`);
    if (sessionRunning.length > 0) {
      status = "executing";
      activity = runningDescs.join(" / ");
    } else if (now - lastActive < 8000) {
      status = "thinking";
      activity = "Thinking...";
    } else {
      status = "idle";
      activity = "Idle";
    }

    sessionEntries[sid] = {
      agent: info.agent,
      projectName: projectName,
      status,
      activity,
      runningDescriptions: runningDescs,
      taskCount: info.taskCount,
      toolCount: sessionTools.length,
      runningCount: sessionRunning.length,
      active: sessionRunning.length > 0,
      firstSeen: info.firstSeen,
    };
  }

  return {
    active: runningCount > 0,
    phase: currentPhase,
    waitingForUser,
    taskCount,
    toolCount: runningCount,
    sessions: sessionEntries,
    activeTools: activeTools.slice(-40),
    currentSession,
    lastUpdated: new Date().toISOString(),
    serverPort: PORT,
  };
}

function writeState() {
  ensureCacheDir();
  writeFileSync(statePath(), JSON.stringify(buildState()));
  // Heartbeat for widget auto-close detection
  writeFileSync(join(CACHE_DIR, "heartbeat"), String(Date.now()));
}

// Fire-and-forget POST to aggregation server (debounced, max 1 per 2s)
let lastReportTime = 0;
let reportTimer = null;
let projectName = "";

function postReport() {
  if (!projectName) return;
  const state = buildState();
  const body = JSON.stringify(state);
  const req = request({
    hostname: "127.0.0.1", port: PORT,
    path: `/report/${encodeURIComponent(projectName)}`,
    method: "POST",
    headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
  });
  req.on("error", () => {});
  req.write(body);
  req.end();
}

function scheduleReport() {
  if (reportTimer) return;
  const since = Date.now() - lastReportTime;
  const delay = Math.max(0, 2000 - since);
  reportTimer = setTimeout(() => {
    reportTimer = null;
    lastReportTime = Date.now();
    postReport();
  }, delay);
}

function startServer(directory) {
  if (serverStarted) return;
  serverStarted = true;
  const serverScript = join(__dirname, "progress-server.js");
  if (!existsSync(serverScript)) return;
  spawn("node", [serverScript, String(PORT), CACHE_DIR, String(process.pid)], {
    cwd: directory,
    detached: true,
    stdio: "ignore",
    windowsHide: true,
  }).unref();
}

// Periodic cleanup — runs every 10s even without hook activity
setInterval(() => {
  writeState();
  scheduleReport();
}, 10_000);

export const ProgressFloatPlugin = async ({ directory }) => {
  projectName = basename(directory);
  writeState();

  return {
    "chat.message": async (input) => {
      _thinking = true;
      waitingForUser = false;
      taskCount++;
      currentSession = input.sessionID;
      const sid = input.sessionID;
      if (!sessions[sid]) {
        sessions[sid] = {
          agent: input.agent || "opencode",
          taskCount: 0,
          firstSeen: new Date().toISOString(),
          lastActivity: new Date().toISOString(),
        };
      }
      sessions[sid].taskCount++;
      sessions[sid].agent = input.agent || sessions[sid].agent;
      sessions[sid].lastActivity = new Date().toISOString();
      writeState();
      scheduleReport();
      startServer(directory);
    },

    "tool.execute.before": async (input) => {
      waitingForUser = false;
      const sid = input.sessionID;
      if (!sessions[sid]) {
        sessions[sid] = {
          agent: "opencode",
          taskCount: 0,
          firstSeen: new Date().toISOString(),
          lastActivity: new Date().toISOString(),
        };
      }
      sessions[sid].lastActivity = new Date().toISOString();
      activeTools.push({
        tool: input.tool,
        status: "running",
        sessionID: sid,
        agent: sessions[sid].agent,
        callID: input.callID,
        startedAt: new Date().toISOString(),
      });
      writeState();
      scheduleReport();
      startServer(directory);
    },

    "tool.execute.after": async (input) => {
      const idx = activeTools.findIndex((t) => t.callID === input.callID);
      if (idx >= 0) {
        activeTools[idx].status = "done";
        activeTools[idx].endedAt = new Date().toISOString();
      }
      if (sessions[input.sessionID]) {
        sessions[input.sessionID].lastActivity = new Date().toISOString();
      }
      // If no more running tools, model is processing result → thinking
      const stillRunning = activeTools.filter((t) => t.status === "running");
      if (stillRunning.length === 0) {
        _thinking = true;
      }
      writeState();
      scheduleReport();
    },

    "experimental.text.complete": async (_input) => {
      _thinking = false;
      writeState();
      scheduleReport();
    },

    "permission.ask": async (_input) => {
      waitingForUser = true;
      writeState();
      scheduleReport();
    },
  };
};

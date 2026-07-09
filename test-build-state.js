import assert from "node:assert/strict";
import { describe, it } from "node:test";

const TOOL_TIMEOUT_MS = 120_000;
const SESSION_TTL_MS = 600_000;
const MAX_TOOLS = 40;

function simulateBuildState(activeTools, sessions, taskCount) {
  const now = Date.now();
  for (const t of activeTools) {
    if (t.status === "running") {
      const started = new Date(t.startedAt).getTime();
      if (now - started > TOOL_TIMEOUT_MS) {
        t.status = "done";
        t.endedAt = new Date().toISOString();
      }
    }
  }
  const runningCount = activeTools.filter(t => t.status === "running").length;
  for (const [sid, info] of Object.entries(sessions)) {
    const hasRunning = activeTools.some(t => t.sessionID === sid && t.status === "running");
    if (!hasRunning) {
      const lastActive = new Date(info.lastActivity || info.firstSeen).getTime();
      if (now - lastActive > SESSION_TTL_MS) delete sessions[sid];
    }
  }
  const sessionEntries = {};
  for (const [sid, info] of Object.entries(sessions)) {
    const st = activeTools.filter(t => t.sessionID === sid);
    const sr = st.filter(t => t.status === "running");
    sessionEntries[sid] = { agent: info.agent, taskCount: info.taskCount, toolCount: st.length, runningCount: sr.length, active: sr.length > 0, firstSeen: info.firstSeen };
  }
  const trimmed = activeTools.slice(-MAX_TOOLS);
  return { active: runningCount > 0, taskCount, toolCount: runningCount, sessions: sessionEntries, activeTools: trimmed, lastUpdated: new Date().toISOString(), currentSession: null, serverPort: 19822 };
}

function ago(ms) { return new Date(Date.now() - ms).toISOString(); }

describe("buildState", () => {
  it("dynamic toolCount (not +-1)", () => {
    const tools = [
      { tool: "bash", status: "running", sessionID: "s1", agent: "oc", callID: "c1", startedAt: ago(1000) },
      { tool: "read", status: "done", sessionID: "s1", agent: "oc", callID: "c2", startedAt: ago(2000), endedAt: ago(1000) },
      { tool: "write", status: "running", sessionID: "s1", agent: "oc", callID: "c3", startedAt: ago(3000) },
    ];
    const sessions = { s1: { agent: "opencode", taskCount: 3, firstSeen: ago(5000), lastActivity: ago(1000) } };
    const r = simulateBuildState(tools, sessions, 3);
    assert.strictEqual(r.toolCount, 2);
    assert.strictEqual(r.active, true);
  });

  it("tool timeout: >120s marked done", () => {
    const tools = [{ tool: "bash", status: "running", sessionID: "s1", agent: "oc", callID: "c1", startedAt: ago(130000) }];
    const sessions = { s1: { agent: "opencode", taskCount: 1, firstSeen: ago(130000), lastActivity: ago(130000) } };
    const r = simulateBuildState(tools, sessions, 1);
    assert.strictEqual(r.toolCount, 0);
    assert.strictEqual(tools[0].status, "done");
    assert.ok(tools[0].endedAt);
    assert.strictEqual(r.active, false);
  });

  it("recent tools NOT affected by timeout", () => {
    const tools = [{ tool: "bash", status: "running", sessionID: "s1", agent: "oc", callID: "c1", startedAt: ago(5000) }];
    const sessions = { s1: { agent: "opencode", taskCount: 1, firstSeen: ago(10000), lastActivity: ago(5000) } };
    const r = simulateBuildState(tools, sessions, 1);
    assert.strictEqual(r.toolCount, 1);
    assert.strictEqual(r.active, true);
  });

  it("idle session >10min deleted", () => {
    const tools = [{ tool: "bash", status: "done", sessionID: "s1", agent: "oc", callID: "c1", startedAt: ago(700000), endedAt: ago(650000) }];
    const sessions = { s1: { agent: "opencode", taskCount: 1, firstSeen: ago(700000), lastActivity: ago(650000) } };
    const r = simulateBuildState(tools, { ...sessions }, 1);
    assert.strictEqual(Object.keys(r.sessions).length, 0);
  });

  it("active session with running tools NOT deleted", () => {
    const tools = [{ tool: "bash", status: "running", sessionID: "s1", agent: "oc", callID: "c1", startedAt: ago(5000) }];
    const sessions = { s1: { agent: "opencode", taskCount: 1, firstSeen: ago(10000), lastActivity: ago(5000) } };
    const r = simulateBuildState(tools, { ...sessions }, 1);
    assert.strictEqual(Object.keys(r.sessions).length, 1);
  });

  it("activeTools trimmed to <=40", () => {
    const tools = Array.from({ length: 60 }, (_, i) => ({ tool: "bash", status: "done", sessionID: "s1", agent: "oc", callID: `c${i}`, startedAt: ago(1000), endedAt: ago(500) }));
    const sessions = { s1: { agent: "opencode", taskCount: 60, firstSeen: ago(10000), lastActivity: ago(1000) } };
    const r = simulateBuildState(tools, { ...sessions }, 60);
    assert.ok(r.activeTools.length <= 40, `expected <=40, got ${r.activeTools.length}`);
    assert.strictEqual(tools.length, 60, "original array must not be mutated");
  });

  it("empty tools and sessions returns active=false, toolCount=0", () => {
    const r = simulateBuildState([], {}, 0);
    assert.strictEqual(r.toolCount, 0);
    assert.strictEqual(r.active, false);
    assert.strictEqual(Object.keys(r.sessions).length, 0);
    assert.strictEqual(r.activeTools.length, 0);
  });

  it("session cleanup falls back to firstSeen when lastActivity missing", () => {
    const tools = [{ tool: "bash", status: "done", sessionID: "s1", agent: "oc", callID: "c1", startedAt: ago(700000), endedAt: ago(650000) }];
    const sessions = { s1: { agent: "opencode", taskCount: 1, firstSeen: ago(700000) } };
    const r = simulateBuildState(tools, { ...sessions }, 1);
    assert.strictEqual(Object.keys(r.sessions).length, 0);
  });

  it("tool at exactly 120000ms NOT timed out", () => {
    const tools = [{ tool: "bash", status: "running", sessionID: "s1", agent: "oc", callID: "c1", startedAt: ago(120000) }];
    const sessions = { s1: { agent: "opencode", taskCount: 1, firstSeen: ago(120000), lastActivity: ago(120000) } };
    const r = simulateBuildState(tools, sessions, 1);
    assert.strictEqual(r.toolCount, 1);
    assert.strictEqual(tools[0].status, "running");
    assert.strictEqual(r.active, true);
  });

  it("session at exactly 600000ms NOT deleted", () => {
    const tools = [{ tool: "bash", status: "done", sessionID: "s1", agent: "oc", callID: "c1", startedAt: ago(600000), endedAt: ago(600000) }];
    const sessions = { s1: { agent: "opencode", taskCount: 1, firstSeen: ago(600000), lastActivity: ago(600000) } };
    const r = simulateBuildState(tools, { ...sessions }, 1);
    assert.strictEqual(Object.keys(r.sessions).length, 1);
  });

  it("return shape includes currentSession and serverPort", () => {
    const r = simulateBuildState([], {}, 0);
    assert.strictEqual(r.currentSession, null);
    assert.strictEqual(r.serverPort, 19822);
  });
});

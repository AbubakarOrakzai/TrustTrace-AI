"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Scenario = {
  id: string;
  title: string;
  category: string;
  expected_decision: string;
  description: string;
};

type Finding = {
  rule_id: string;
  severity: string;
  message: string;
  evidence: string;
  source_id: string | null;
};

type Trace = {
  seq: number;
  event_id: string;
  timestamp: string;
  tool_call: {
    id: string;
    tool_name: string;
    arguments: Record<string, unknown>;
    context_sources: Array<{ source_id: string; excerpt: string }>;
  };
  verdict: {
    decision: "ALLOW" | "REVIEW" | "BLOCK";
    final_risk_score: number;
    reason_summary: string;
    layers: Array<{ layer: string; latency_ms: number; findings: Finding[] }>;
  };
  hash: string;
  signature: string;
};

type Scorecard = {
  scenario_accuracy: number;
  attack_block_rate: number;
  benign_false_positive_rate: number;
  p50_policy_latency_ms: number;
  p95_policy_latency_ms: number;
  results: Array<{ scenario_id: string; expected: string; actual: string; matched: boolean }>;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Dashboard() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selected, setSelected] = useState<Trace | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [chain, setChain] = useState<{ valid: boolean; events_verified: number } | null>(null);
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [scenarioResponse, traceResponse] = await Promise.all([
        fetch(`${API}/v1/scenarios`),
        fetch(`${API}/v1/traces`),
      ]);
      if (!scenarioResponse.ok || !traceResponse.ok) {
        throw new Error("Backend returned an error while loading dashboard data.");
      }
      setScenarios(await scenarioResponse.json());
      const nextTraces: Trace[] = await traceResponse.json();
      setTraces(nextTraces);
      setSelected((current) =>
        current ? nextTraces.find((trace) => trace.event_id === current.event_id) ?? current : null,
      );
      setMessage("");
    } catch {
      setMessage("Backend unavailable. Start FastAPI at http://localhost:8000.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const counts = useMemo(
    () =>
      traces.reduce(
        (total, trace) => {
          total[trace.verdict.decision] += 1;
          return total;
        },
        { ALLOW: 0, REVIEW: 0, BLOCK: 0 },
      ),
    [traces],
  );

  async function runScenario(id: string) {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/simulate/${id}`, { method: "POST" });
      if (!response.ok) throw new Error("Scenario request failed.");
      const result = await response.json();
      setSelected(result.event);
      await refresh();
      setSelected(result.event);
    } catch {
      setMessage("Could not run the scenario. Check that the backend is running.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyChain() {
    try {
      const response = await fetch(`${API}/v1/audit/verify`);
      if (!response.ok) throw new Error("Verification request failed.");
      setChain(await response.json());
    } catch {
      setMessage("Audit verification failed because the backend is unavailable.");
    }
  }

  async function runSuite() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/v1/simulate/run-all`, { method: "POST" });
      if (!response.ok) throw new Error("Suite request failed.");
      setScorecard(await response.json());
      await refresh();
    } catch {
      setMessage("Could not run the suite. Check that the backend is running.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadReport() {
    try {
      const response = await fetch(`${API}/v1/audit/report`);
      if (!response.ok) throw new Error("Report request failed.");
      const report = await response.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(report);
      link.download = "trusttrace-audit-report.json";
      link.click();
      URL.revokeObjectURL(link.href);
    } catch {
      setMessage("Could not download report. Check that the backend is running.");
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">T</span><span>TrustTrace<span className="brand-light"> AI</span></span></div>
        <div className="nav-label">WORKSPACE</div>
        <a className="nav-item active" href="#overview"><span>◫</span> Overview</a>
        <a className="nav-item" href="#simulator"><span>⌁</span> Attack simulator</a>
        <a className="nav-item" href="#audit"><span>⌗</span> Audit ledger</a>
        <div className="sidebar-bottom">
          <div className="system-card">
            <span className="live-dot" /> LOCAL POLICY ENGINE
            <p>Deterministic mode · offline</p>
          </div>
          <div className="owner">HASEEB KHAN <span>PROJECT OWNER</span></div>
        </div>
      </aside>

      <section className="main">
        <header className="topbar">
          <div><span className="crumb">WORKSPACE</span><span className="slash">/</span> Security overview</div>
          <div className="top-status"><span className="live-dot" /> API READY <span className="env-pill">LOCAL DEMO</span></div>
        </header>

        <div className="content" id="overview">
          <div className="page-heading">
            <div><div className="eyebrow">AGENT SECURITY OPERATIONS</div><h1>Overview</h1><p>Inspect tool calls before they reach execution.</p></div>
            <button className="button secondary" onClick={() => void refresh()}>↻ <span>Refresh</span></button>
          </div>
          {message && <div className="notice">{message}</div>}

          <div className="stats">
            <Stat label="INTERCEPTED" value={traces.length} accent="white" />
            <Stat label="BLOCKED" value={counts.BLOCK} accent="red" />
            <Stat label="NEEDS REVIEW" value={counts.REVIEW} accent="amber" />
            <Stat label="ALLOWED" value={counts.ALLOW} accent="green" />
          </div>

          <div className="section-title" id="simulator"><div><span className="eyebrow">RED-TEAM LAB</span><h2>Attack simulator</h2></div><div className="suite-actions"><span className="section-meta">8 DETERMINISTIC SCENARIOS</span><button className="button secondary" disabled={busy} onClick={() => void runSuite()}>Run full suite <span>→</span></button></div></div>
          <div className="scenario-grid">
            {scenarios.map((scenario) => (
              <article className="scenario-card" key={scenario.id}>
                <div className="scenario-top"><span className={`category ${scenario.expected_decision.toLowerCase()}`}>{scenario.category.replaceAll("-", " ")}</span><span className="expected">EXPECT {scenario.expected_decision}</span></div>
                <h3>{scenario.title}</h3>
                <p>{scenario.description}</p>
                <button className="button run" disabled={busy} onClick={() => void runScenario(scenario.id)}>{busy ? "Evaluating…" : "Run scenario"} <span>→</span></button>
              </article>
            ))}
          </div>
          {scorecard && <div className="scorecard"><div className="scorecard-title"><div><span className="eyebrow">DETERMINISTIC REPLAY</span><h3>Suite scorecard</h3></div><span className="badge allow">{Math.round(scorecard.scenario_accuracy * 100)}% EXPECTED DECISIONS</span></div><div className="scorecard-stats"><span>ATTACK DETECTION <b>{Math.round(scorecard.attack_block_rate * 100)}%</b></span><span>BENIGN FALSE POSITIVE <b>{Math.round(scorecard.benign_false_positive_rate * 100)}%</b></span><span>POLICY P50 <b>{scorecard.p50_policy_latency_ms.toFixed(2)} ms</b></span><span>POLICY P95 <b>{scorecard.p95_policy_latency_ms.toFixed(2)} ms</b></span></div><div className="scorecard-list">{scorecard.results.map((result) => <span className={result.matched ? "score-pass" : "score-fail"} key={result.scenario_id}>{result.matched ? "✓" : "×"} {result.scenario_id} <b>{result.actual}</b></span>)}</div></div>}

          <div className="section-title trace-heading"><div><span className="eyebrow">DECISION PIPELINE</span><h2>Latest trace</h2></div><span className="section-meta">{traces.length} RECORDED</span></div>
          {selected ? <TraceDetail trace={selected} /> : <div className="empty">Run a scenario to inspect its policy decision and audit proof.</div>}

          <div className="section-title audit-heading" id="audit"><div><span className="eyebrow">TAMPER-EVIDENT RECORD</span><h2>Audit ledger</h2></div></div>
          <div className="audit-panel">
            <div className="audit-copy"><div className="audit-icon">⌗</div><div><h3>Chain integrity</h3><p>Verify the SHA-256 event chain and Ed25519 signatures.</p>{chain && <div className={chain.valid ? "verify-good" : "verify-bad"}>{chain.valid ? `✓ Valid · ${chain.events_verified} events verified` : "⚠ Chain verification failed"}</div>}</div></div>
            <div className="audit-actions"><button className="button secondary" onClick={() => void downloadReport()}>↓ Export JSON</button><button className="button primary" onClick={() => void verifyChain()}>Verify chain <span>→</span></button></div>
          </div>

          <footer>TRUSTTRACE AI <span>·</span> Prototype evidence aligned with SOC 2 / AIUC-1 concepts; not a certification or compliance guarantee.</footer>
        </div>
      </section>
    </main>
  );
}

function Stat({ label, value, accent }: { label: string; value: number; accent: string }) {
  return <div className="stat"><div className="stat-label">{label}<span className="stat-dot" /></div><div className={`stat-value ${accent}`}>{value.toString().padStart(2, "0")}</div><div className="stat-foot">SINCE LEDGER START</div></div>;
}

function TraceDetail({ trace }: { trace: Trace }) {
  const decision = trace.verdict.decision.toLowerCase();
  return (
    <div className="trace-panel">
      <div className="trace-summary">
        <div className="trace-title"><div className={`decision-icon ${decision}`}>{decision === "block" ? "×" : decision === "allow" ? "✓" : "!"}</div><div><span className="eyebrow">TRACE #{trace.seq} · {trace.tool_call.tool_name}</span><h3>{trace.verdict.reason_summary}</h3></div></div>
        <span className={`badge ${decision}`}>{trace.verdict.decision}</span>
      </div>
      <div className="trace-grid">
        <div><div className="mini-label">TOOL PAYLOAD</div><pre>{JSON.stringify(trace.tool_call.arguments, null, 2)}</pre></div>
        <div><div className="mini-label">POLICY FINDINGS</div>{trace.verdict.layers.flatMap((layer) => layer.findings).length ? trace.verdict.layers.flatMap((layer) => layer.findings).map((finding, i) => <div className="finding" key={`${finding.rule_id}-${i}`}><span className="finding-severity">{finding.severity}</span><div><strong>{finding.rule_id}</strong><p>{finding.message}</p>{finding.source_id && <small>Source attribution: {finding.source_id}</small>}</div></div>) : <div className="no-findings">No policy findings. Call allowed in sandbox.</div>}</div>
      </div>
      <div className="trace-meta"><span>RISK <b>{trace.verdict.final_risk_score.toFixed(2)}</b></span><span>POLICY LATENCY <b>{trace.verdict.layers[0]?.latency_ms.toFixed(2)} ms</b></span><span>HASH <code>{trace.hash.slice(0, 18)}…</code></span><span>SIGNED <b>Ed25519</b></span></div>
    </div>
  );
}

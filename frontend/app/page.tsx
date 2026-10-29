"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Scenario = {
  id: string;
  title: string;
  category: string;
  expected_decision: string;
  description: string;
};

type ApiHealth = {
  status: string;
  judge_provider: string;
  layers: {
    llm_judge: string;
    [layer: string]: string;
  };
  model_id: string;
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

type EvaluationRow = {
  text: string;
  label: 0 | 1;
  category?: string;
};

type DatasetReport = {
  results: {
    rows: number;
    truncated_rows: number;
    binary_metrics: {
      true_positive: number;
      false_positive: number;
      true_negative: number;
      false_negative: number;
      accuracy: number;
      precision: number;
      recall: number;
      f1: number;
      false_positive_rate: number;
    };
    decision_counts: Record<"ALLOW" | "REVIEW" | "BLOCK", number>;
  };
};

const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL;
const configuredApiIsLocal =
  /^https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?(?:\/|$)/i.test(
    configuredApiUrl ?? "",
  );
const API =
  process.env.NODE_ENV === "production"
    ? !configuredApiUrl || configuredApiIsLocal
      ? "https://trust-trace-ai.vercel.app"
      : configuredApiUrl
    : configuredApiUrl ?? "http://localhost:8000";

function backendUnavailableMessage() {
  const isLocal =
    typeof window !== "undefined" &&
    ["localhost", "127.0.0.1"].includes(window.location.hostname);
  if (isLocal) {
    return "Backend unavailable. Start FastAPI at http://localhost:8000.";
  }
  const origin = typeof window === "undefined" ? "this site" : window.location.origin;
  return `Backend unavailable. Set NEXT_PUBLIC_API_URL to your public FastAPI URL and allow ${origin} in backend CORS settings.`;
}

export default function Dashboard() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selected, setSelected] = useState<Trace | null>(null);
  const [apiHealth, setApiHealth] = useState<ApiHealth | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [chain, setChain] = useState<{ valid: boolean; events_verified: number } | null>(null);
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [evaluationRows, setEvaluationRows] = useState<EvaluationRow[]>([]);
  const [evaluationFilename, setEvaluationFilename] = useState("");
  const [evaluationMessage, setEvaluationMessage] = useState("");
  const [evaluationBusy, setEvaluationBusy] = useState(false);
  const [datasetReport, setDatasetReport] = useState<DatasetReport | null>(null);

  async function loadEvaluationFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    setDatasetReport(null);
    setEvaluationRows([]);
    setEvaluationFilename("");
    setEvaluationMessage("");
    if (!file) return;
    if (file.size > 2_000_000) {
      setEvaluationMessage("Choose a file smaller than 2 MB.");
      event.target.value = "";
      return;
    }

    try {
      const contents = await file.text();
      const parsed: unknown = file.name.toLowerCase().endsWith(".jsonl")
        ? contents
            .split(/\r?\n/)
            .filter((line) => line.trim())
            .map((line, index) => {
              try {
                return JSON.parse(line);
              } catch {
                throw new Error(`Invalid JSON on line ${index + 1}.`);
              }
            })
        : JSON.parse(contents);
      const sourceRows = Array.isArray(parsed)
        ? parsed
        : parsed && typeof parsed === "object" && "rows" in parsed
          ? (parsed as { rows: unknown }).rows
          : null;
      if (!Array.isArray(sourceRows) || sourceRows.length === 0) {
        throw new Error("File must contain a non-empty array of labeled rows.");
      }
      if (sourceRows.length > 500) {
        throw new Error("Evaluation is limited to 500 rows per upload.");
      }

      const rows = sourceRows.map((row, index): EvaluationRow => {
        if (
          !row ||
          typeof row !== "object" ||
          !("text" in row) ||
          typeof row.text !== "string" ||
          row.text.length === 0 ||
          row.text.length > 8000 ||
          !("label" in row) ||
          (row.label !== 0 && row.label !== 1) ||
          ("category" in row &&
            (typeof row.category !== "string" || row.category.length > 64))
        ) {
          throw new Error(
            `Row ${index + 1} needs text (1–8,000 characters), label 0 or 1, and an optional short category.`,
          );
        }
        return {
          text: row.text,
          label: row.label,
          category: "category" in row ? row.category : undefined,
        };
      });
      setEvaluationRows(rows);
      setEvaluationFilename(file.name);
    } catch (error) {
      setEvaluationMessage(
        error instanceof Error ? error.message : "Could not read this file.",
      );
      event.target.value = "";
    }
  }

  async function runDatasetEvaluation() {
    setEvaluationBusy(true);
    setEvaluationMessage("");
    setDatasetReport(null);
    try {
      const response = await fetch(`${API}/v1/evaluate/dataset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows: evaluationRows }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(
          typeof payload.detail === "string"
            ? payload.detail
            : "Evaluation request failed.",
        );
      }
      setDatasetReport(payload as DatasetReport);
    } catch (error) {
      setEvaluationMessage(
        error instanceof Error
          ? error.message
          : "Could not reach the evaluation API.",
      );
    } finally {
      setEvaluationBusy(false);
    }
  }

  const refresh = useCallback(async () => {
    try {
      const [scenarioResponse, traceResponse, healthResponse] = await Promise.all([
        fetch(`${API}/v1/scenarios`),
        fetch(`${API}/v1/traces`),
        fetch(`${API}/health`),
      ]);
      if (!scenarioResponse.ok || !traceResponse.ok || !healthResponse.ok) {
        throw new Error("Backend returned an error while loading dashboard data.");
      }
      setScenarios(await scenarioResponse.json());
      const nextTraces: Trace[] = await traceResponse.json();
      setApiHealth(await healthResponse.json());
      setTraces(nextTraces);
      setSelected(nextTraces.at(-1) ?? null);
      setMessage("");
    } catch {
      setApiHealth(null);
      setMessage(backendUnavailableMessage());
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
    setVerifyingChain(true);
    setChain(null);
    try {
      const response = await fetch(`${API}/v1/audit/verify`);
      if (!response.ok) throw new Error("Verification request failed.");
      setChain(await response.json());
    } catch {
      setMessage("Audit verification failed because the backend is unavailable.");
    } finally {
      setVerifyingChain(false);
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
          <div className="top-status"><span className={message ? "error-dot" : apiHealth?.status === "ok" ? "live-dot" : "status-dot"} /> {message ? "API UNAVAILABLE" : apiHealth?.status === "ok" ? "API CONNECTED" : "API CHECKING"} <span className="env-pill">{!apiHealth ? "STATUS UNKNOWN" : apiHealth.layers.llm_judge === "ready" ? apiHealth.judge_provider === "Nebius Token Factory" ? "NEBIUS CONFIGURED" : "GEMINI CONFIGURED" : apiHealth.layers.llm_judge === "disabled" ? "OFFLINE POLICY MODE" : "JUDGE NOT READY"}</span></div>
        </header>

        <div className="content" id="overview">
          <div className="page-heading">
            <div><div className="eyebrow">AGENT SECURITY OPERATIONS</div><h1>Overview</h1><p>Inspect tool calls before they reach execution.</p></div>
            <button className="button secondary" onClick={() => void refresh()}>↻ <span>Refresh</span></button>
          </div>
          {message && <div className="notice">{message}</div>}

          <section className="demo-guide" aria-label="Judge demo quick start">
            <div className="guide-copy">
              <span className="eyebrow">JUDGE QUICKSTART</span>
              <p>See the core flow in three steps. Replays are deterministic; tools are sandbox mocks.</p>
            </div>
            <div className="guide-actions">
              <button className="button guide-button" disabled={busy} onClick={() => void runScenario("invoice-exfiltration")}>1. Run invoice attack</button>
              <button className="button guide-button" disabled={busy} onClick={() => void runSuite()}>2. Run full suite</button>
              <button className="button guide-button" onClick={() => void verifyChain()}>3. Verify audit</button>
            </div>
            <div className="judge-mode">
              <span className={apiHealth?.layers.llm_judge === "ready" ? "live-dot" : "status-dot"} />
              {!apiHealth
                ? "Backend status unavailable · judge mode unknown"
                : apiHealth.layers.llm_judge === "ready"
                  ? `${apiHealth.judge_provider} configured · ${apiHealth.model_id}`
                  : apiHealth.layers.llm_judge === "disabled"
                    ? "LLM judge off · no model calls"
                    : "LLM judge not ready · no model calls"}
            </div>
            <div className="quick-audit-status" aria-live="polite">
              {verifyingChain
                ? "Verifying audit chain…"
                : chain
                  ? chain.valid
                    ? `✓ Audit valid · ${chain.events_verified} events verified`
                    : "⚠ Audit chain verification failed"
                  : ""}
            </div>
          </section>

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
          <section className="dataset-lab" aria-labelledby="dataset-lab-title">
            <div className="dataset-lab-heading">
              <div>
                <span className="eyebrow">PUBLIC DATA LAB</span>
                <h2 id="dataset-lab-title">Evaluate labeled text samples</h2>
                <p>
                  Test your public prompt-injection examples against the current
                  deterministic context rules.
                </p>
              </div>
              <div className="dataset-downloads">
                <a className="button secondary" href="/evaluation-sample.jsonl" download>
                  Download sample data
                </a>
                <a className="button secondary" href="/agent-tool-schemas.json" download>
                  Download agent tool schemas
                </a>
                <a
                  className="button secondary"
                  href="https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset"
                  target="_blank"
                  rel="noreferrer"
                >
                  Browse public dataset
                </a>
              </div>
            </div>
            <div className="dataset-warning" role="note">
              This public website sends the selected rows to its hosted backend.
              Evaluation uses deterministic rules only—no Nebius/Gemini calls—and
              the app does not add rows to the audit ledger. Only upload public,
              non-sensitive data; do not upload private, personal, or confidential
              information. Hosted platforms may process request data.
            </div>
            <div className="dataset-format">
              Upload JSON or JSONL (one JSON object per line) with{" "}
              <code>text</code> and <code>label</code> fields. Label{" "}
              <code>1</code> means attack; <code>0</code> means benign. Optional{" "}
              <code>category</code> is accepted but not included in the report.
              Maximum 500 rows, 8,000 characters per row, and 2 MB per file.
            </div>
            <div className="dataset-upload">
              <label className="dataset-file">
                <span>Select JSON/JSONL file</span>
                <input
                  type="file"
                  accept=".json,.jsonl,application/json"
                  onChange={(event) => void loadEvaluationFile(event)}
                />
              </label>
              <span className="dataset-file-name" aria-live="polite">
                {evaluationFilename
                  ? `${evaluationFilename} · ${evaluationRows.length} rows ready`
                  : "No file selected"}
              </span>
              <button
                className="button primary"
                disabled={!evaluationRows.length || evaluationBusy}
                onClick={() => void runDatasetEvaluation()}
              >
                {evaluationBusy ? "Evaluating…" : "Run local-policy evaluation"}
              </button>
            </div>
            {evaluationMessage && (
              <div className="dataset-message" role="alert">
                {evaluationMessage}
              </div>
            )}
            {datasetReport && (
              <div className="dataset-results" aria-live="polite">
                <div className="dataset-results-heading">
                  <div>
                    <span className="eyebrow">AGGREGATE RESULTS</span>
                    <h3>{datasetReport.results.rows} rows evaluated</h3>
                  </div>
                  <span className="badge allow">
                    {(datasetReport.results.binary_metrics.accuracy * 100).toFixed(1)}%
                    {" "}ACCURACY
                  </span>
                </div>
                <div className="dataset-metrics">
                  <span>
                    ATTACK RECALL
                    <b>
                      {(datasetReport.results.binary_metrics.recall * 100).toFixed(1)}%
                    </b>
                  </span>
                  <span>
                    FALSE POSITIVE RATE
                    <b>
                      {(
                        datasetReport.results.binary_metrics.false_positive_rate *
                        100
                      ).toFixed(1)}
                      %
                    </b>
                  </span>
                  <span>
                    F1 SCORE
                    <b>{datasetReport.results.binary_metrics.f1.toFixed(3)}</b>
                  </span>
                  <span>
                    TRUNCATED ROWS
                    <b>{datasetReport.results.truncated_rows}</b>
                  </span>
                </div>
                <div className="dataset-confusion">
                  TP {datasetReport.results.binary_metrics.true_positive}
                  <span>·</span>
                  FP {datasetReport.results.binary_metrics.false_positive}
                  <span>·</span>
                  TN {datasetReport.results.binary_metrics.true_negative}
                  <span>·</span>
                  FN {datasetReport.results.binary_metrics.false_negative}
                  <span>·</span>
                  ALLOW {datasetReport.results.decision_counts.ALLOW}
                  <span>·</span>
                  REVIEW {datasetReport.results.decision_counts.REVIEW}
                  <span>·</span>
                  BLOCK {datasetReport.results.decision_counts.BLOCK}
                </div>
                <p className="dataset-limit">
                  REVIEW and BLOCK count as detected. This measures only these
                  labeled samples and is not a security certification. Samples
                  are evaluated as untrusted context for a sandbox file-read
                  call; it does not execute agent tools.
                </p>
              </div>
            )}
          </section>
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
  return <div className="stat"><div className="stat-label">{label}<span className="stat-dot" /></div><div className={`stat-value ${accent}`}>{value.toString().padStart(2, "0")}</div><div className="stat-foot">LATEST 100 EVENTS</div></div>;
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

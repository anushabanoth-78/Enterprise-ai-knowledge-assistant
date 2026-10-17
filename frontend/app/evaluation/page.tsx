"use client";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

type Row = Record<string, string>;
type Usage = { provider: string; model: string; queries: number; avg_retrieval_ms: number; avg_generation_ms: number; prompt_tokens: number; completion_tokens: number };
const avg = (rows: Row[], k: string) => rows.reduce((s, r) => s + Number(r[k]), 0) / (rows.length || 1);

export default function Evaluation() {
  const [rows, setRows] = useState<Row[]>([]);
  const [usage, setUsage] = useState<Usage[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Row[]>("/evaluation/results").then(setRows).catch(e => setError(e.message));
    api<Usage[]>("/evaluation/usage").then(setUsage).catch(() => {});
  }, []);

  // One summary line per benchmark run. hit@k isolates retrieval; keyword recall and citations isolate generation.
  const runs = useMemo(() => {
    const byRun: Record<string, Row[]> = {};
    rows.forEach(r => (byRun[r.run_id] ??= []).push(r));
    return Object.entries(byRun).map(([id, rs]) => ({
      id, model: rs[0].model, rerank: rs[0].rerank, when: rs[0].timestamp, n: rs.length,
      hit: avg(rs, "hit_at_k"), kw: avg(rs, "keyword_recall"), valid: avg(rs, "citation_valid"),
      ret: avg(rs, "retrieval_ms"), gen: avg(rs, "generation_ms"), tokens: avg(rs, "prompt_tokens") + avg(rs, "completion_tokens"),
    })).reverse();
  }, [rows]);

  return (
    <>
      <h1>Evaluation</h1>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="panel">
        <h2>Benchmark runs</h2>
        {runs.length === 0 ? <p className="muted">No runs yet. Run <code>python -m app.services.evaluation --email you@example.com</code> inside the api container.</p> : (
          <div style={{ overflowX: "auto" }}><table>
            <thead><tr><th>Model</th><th>Rerank</th><th>Questions</th><th>Retrieval hit@k</th><th>Keyword recall</th><th>Valid citations</th><th>Retrieval ms</th><th>Generation ms</th><th>Avg tokens</th></tr></thead>
            <tbody>{runs.map(r => (
              <tr key={r.id}><td>{r.model}</td><td>{r.rerank}</td><td>{r.n}</td>
                <td>{(r.hit * 100).toFixed(0)}%</td><td>{(r.kw * 100).toFixed(0)}%</td><td>{(r.valid * 100).toFixed(0)}%</td>
                <td>{r.ret.toFixed(0)}</td><td>{r.gen.toFixed(0)}</td><td>{r.tokens.toFixed(0)}</td></tr>))}
            </tbody>
          </table></div>
        )}
      </div>
      <div className="panel">
        <h2>Live usage by model</h2>
        {usage.length === 0 ? <p className="muted">Ask a question in chat to see latency and token use here.</p> : (
          <table>
            <thead><tr><th>Model</th><th>Queries</th><th>Avg retrieval ms</th><th>Avg generation ms</th><th>Prompt tokens</th><th>Completion tokens</th></tr></thead>
            <tbody>{usage.map(u => (
              <tr key={u.model}><td>{u.model}</td><td>{u.queries}</td><td>{u.avg_retrieval_ms}</td><td>{u.avg_generation_ms}</td><td>{u.prompt_tokens}</td><td>{u.completion_tokens}</td></tr>))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

"use client";
import { Fragment, useState } from "react";
import CitationViewer from "@/components/CitationViewer";
import { api, ChatResult, json } from "@/lib/api";

function AnswerText({ text, onCite }: { text: string; onCite: (n: number) => void }) {
  // Turn [n] markers into buttons that jump to the passage.
  return (
    <p className="answer">
      {text.split(/(\[\d+\])/g).map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        return m ? <button key={i} className="cite" onClick={() => onCite(Number(m[1]))} aria-label={`Show source ${m[1]}`}>[{m[1]}]</button>
                 : <Fragment key={i}>{part}</Fragment>;
      })}
    </p>
  );
}

export default function Chat() {
  const [question, setQuestion] = useState("");
  const [provider, setProvider] = useState<"hosted" | "ollama">("hosted");
  const [rerank, setRerank] = useState(true);
  const [result, setResult] = useState<ChatResult | null>(null);
  const [active, setActive] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function ask() {
    setBusy(true); setError(""); setResult(null); setActive(null);
    try { setResult(await api<ChatResult>("/chat", json({ question, provider, rerank, top_k: 5 }))); }
    catch (e) { setError((e as Error).message); }
    setBusy(false);
  }

  function showSource(n: number) {
    setActive(n);
    document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  return (
    <>
      <h1>Ask your documents</h1>
      <div className="panel stack">
        <textarea rows={3} value={question} onChange={e => setQuestion(e.target.value)} placeholder="What does the manual say about…?" aria-label="Question" />
        <div className="row">
          <select value={provider} onChange={e => setProvider(e.target.value as "hosted" | "ollama")} style={{ width: "auto" }} aria-label="Model">
            <option value="hosted">Hosted model</option>
            <option value="ollama">Local model (Ollama)</option>
          </select>
          <label className="row"><input type="checkbox" checked={rerank} onChange={e => setRerank(e.target.checked)} style={{ width: "auto" }} />Rerank passages</label>
          <button disabled={busy || question.trim().length < 3} onClick={ask}>{busy ? "Searching…" : "Ask"}</button>
        </div>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {result && (
        <div className="split">
          <div className="panel">
            <AnswerText text={result.answer} onCite={showSource} />
            <p className="muted">{result.model} · retrieval {result.retrieval_ms} ms · generation {result.generation_ms} ms · {result.prompt_tokens}+{result.completion_tokens} tokens</p>
          </div>
          <div className="panel"><CitationViewer citations={result.citations} active={active} /></div>
        </div>
      )}
    </>
  );
}

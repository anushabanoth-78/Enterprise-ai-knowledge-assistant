import { Citation } from "@/lib/api";

export default function CitationViewer({ citations, active }: { citations: Citation[]; active: number | null }) {
  return (
    <div>
      {citations.map(c => (
        <div key={c.ref} id={`source-${c.ref}`} className={`passage ${active === c.ref ? "active" : ""}`}>
          <div className="muted">Source {c.ref}: {c.filename}, page {c.page} (relevance {c.score})</div>
          <div className="body">{c.text}</div>
        </div>
      ))}
    </div>
  );
}

"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, Doc } from "@/lib/api";

export default function Library() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => api<Doc[]>("/documents").then(setDocs).catch(e => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);
  // Poll while any document is still being processed.
  useEffect(() => {
    if (!docs.some(d => d.status === "queued" || d.status === "processing")) return;
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
  }, [docs, load]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true); setError("");
    for (const file of Array.from(files)) {
      const form = new FormData(); form.append("file", file);
      try { await api("/documents", { method: "POST", body: form }); } catch (e) { setError((e as Error).message); }
    }
    if (fileRef.current) fileRef.current.value = "";
    setUploading(false); load();
  }

  async function remove(id: string) {
    if (!confirm("Delete this document and its indexed passages?")) return;
    await api(`/documents/${id}`, { method: "DELETE" }); load();
  }

  return (
    <>
      <h1>Document library</h1>
      <div className="panel row">
        <input ref={fileRef} type="file" accept="application/pdf" multiple style={{ flex: 1 }} aria-label="Choose PDF files" />
        <button disabled={uploading} onClick={() => upload(fileRef.current?.files ?? null)}>{uploading ? "Uploading…" : "Upload PDFs"}</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="panel">
        {docs.length === 0 ? <p className="muted">No documents yet. Upload a PDF to start asking questions.</p> : (
          <table>
            <thead><tr><th>File</th><th>Status</th><th>Pages</th><th>Passages</th><th></th></tr></thead>
            <tbody>{docs.map(d => (
              <tr key={d.id}>
                <td>{d.filename}</td>
                <td className={`status-${d.status}`}>{d.status}{d.error ? ` — ${d.error}` : ""}</td>
                <td>{d.n_pages}</td><td>{d.n_chunks}</td>
                <td><button className="ghost" onClick={() => remove(d.id)}>Delete</button></td>
              </tr>))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

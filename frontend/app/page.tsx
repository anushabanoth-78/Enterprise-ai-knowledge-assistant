"use client";
import { useState } from "react";
import { api, json, setToken } from "@/lib/api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(mode: "login" | "register") {
    setBusy(true); setError("");
    try {
      const res = mode === "register"
        ? await api<{ access_token: string }>("/auth/register", json({ email, password }))
        : await api<{ access_token: string }>("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ username: email, password }),
          });
      setToken(res.access_token);
      window.location.href = "/library";
    } catch (e) { setError((e as Error).message); }
    setBusy(false);
  }

  return (
    <div className="panel stack" style={{ maxWidth: 420, margin: "3rem auto" }}>
      <h1>Sign in</h1>
      <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" /></label>
      <label>Password (8+ characters)<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row">
        <button disabled={busy} onClick={() => submit("login")}>Sign in</button>
        <button className="ghost" disabled={busy} onClick={() => submit("register")}>Create account</button>
      </div>
    </div>
  );
}

import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Knowledge Assistant", description: "Ask your documents. Get cited answers." };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav>
          <strong>Knowledge Assistant</strong>
          <a href="/library">Library</a>
          <a href="/chat">Ask</a>
          <a href="/evaluation">Evaluation</a>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}

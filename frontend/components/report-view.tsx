"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { renderToStaticMarkup } from "react-dom/server";

export function isReportContent(text: string): boolean {
  const trimmed = text.trim();
  return (
    trimmed.startsWith("# PCR Primer Design Report") ||
    trimmed.startsWith("# Primer Design Report") ||
    (trimmed.startsWith("# ") && trimmed.includes("Primer") && trimmed.includes("Report"))
  );
}

export async function downloadReportPdf(markdown: string): Promise<void> {
  const title =
    markdown.split("\n")[0]?.replace(/^#+\s*/, "").trim() || "PCR_Primer_Report";
  const filename = title.replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 60);

  const htmlContent = renderToStaticMarkup(
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>,
  );

  const styledHtml = `
    <div style="font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a1a; padding: 16px; font-size: 13px; line-height: 1.7;">
      <style>
        h1 { font-size: 18px; font-weight: 700; margin-bottom: 12px; }
        h2 { font-size: 15px; font-weight: 600; margin-top: 20px; margin-bottom: 8px; border-bottom: 1px solid #e5e5e5; padding-bottom: 4px; }
        h3 { font-size: 13px; font-weight: 600; margin-top: 14px; margin-bottom: 6px; }
        p { margin-bottom: 8px; color: #333; }
        ul, ol { margin-left: 18px; margin-bottom: 8px; color: #333; }
        li { margin-bottom: 3px; }
        strong { font-weight: 600; color: #1a1a1a; }
        hr { border: none; border-top: 1px solid #ddd; margin: 16px 0; }
        table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 11px; }
        th { background: #f5f5f5; padding: 6px 8px; text-align: left; font-weight: 600; border: 1px solid #ddd; }
        td { padding: 5px 8px; border: 1px solid #e5e5e5; color: #444; }
        tr:nth-child(even) { background: #fafafa; }
        blockquote { border-left: 3px solid #7c3aed; background: #f5f3ff; padding: 6px 12px; margin: 8px 0; font-style: italic; color: #555; }
        code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 11px; }
        pre { background: #f0f0f0; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 11px; }
      </style>
      ${htmlContent}
    </div>
  `;

  const container = document.createElement("div");
  container.innerHTML = styledHtml;
  container.style.position = "absolute";
  container.style.left = "-9999px";
  container.style.width = "700px";
  document.body.appendChild(container);

  try {
    const html2pdf = (await import("html2pdf.js")).default;
    await html2pdf()
      .set({
        margin: [10, 10, 10, 10],
        filename: `${filename}.pdf`,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, logging: false },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["avoid-all", "css", "legacy"] },
      })
      .from(container)
      .save();
  } finally {
    document.body.removeChild(container);
  }
}

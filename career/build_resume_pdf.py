"""Build the optimized resume as a styled PDF on the user's desktop.

Pipeline:
  1. Read career/RESUME_GAN_KAIFENG_OPTIMIZED.md
  2. Render Markdown -> HTML with custom CSS (blue-bar headers, two-column header)
  3. Use Microsoft Edge via Playwright (channel="msedge") to print HTML -> PDF
     — Playwright's page.pdf() has display_header_footer=False so no extra
     date/URL/page-number footer is added.
  4. Copy the PDF to C:\\Users\\feng\\Desktop\\
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright


PROJECT = Path(__file__).resolve().parent.parent
SRC_MD = PROJECT / "career" / "RESUME_GAN_KAIFENG_OPTIMIZED.md"
HTML_OUT = PROJECT / "career" / "_resume_preview.html"
PDF_OUT = PROJECT / "career" / "_resume_preview.pdf"
DESKTOP_PDF = Path(r"C:\Users\feng\Desktop\甘凯锋_AI应用工程师简历_优化版.pdf")

# CSS matches the original PDF's visual style: blue title bars, clean spacing
CSS = """
@page { size: A4; margin: 14mm 14mm 14mm 14mm; }
* { box-sizing: border-box; }
body {
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
  color: #1f2937;
  font-size: 10.5pt;
  line-height: 1.55;
  margin: 0;
  padding: 0;
}
h1 {
  text-align: center;
  font-size: 22pt;
  margin: 0 0 4px 0;
  color: #111827;
  font-weight: 700;
  letter-spacing: 2px;
}
h2 {
  background: #1d4ed8;
  color: #fff;
  font-size: 11.5pt;
  padding: 5px 12px;
  margin: 14px 0 8px 0;
  border-radius: 2px;
  font-weight: 600;
  letter-spacing: 1px;
}
h3 { font-size: 12pt; margin: 10px 0 4px 0; color: #111827; font-weight: 700; }
h4 { font-size: 10.5pt; margin: 8px 0 3px 0; color: #1d4ed8; font-weight: 700; }
p { margin: 3px 0; }
ul { margin: 2px 0 4px 0; padding-left: 22px; }
li { margin: 1px 0; }
blockquote {
  border-left: 3px solid #1d4ed8;
  background: #eff6ff;
  padding: 6px 10px;
  margin: 6px 0;
  color: #1e3a8a;
  font-size: 10pt;
}
hr { border: 0; border-top: 1px solid #e5e7eb; margin: 10px 0; }
strong { color: #111827; }
a { color: #1d4ed8; text-decoration: none; }
code { font-family: "Consolas", monospace; background: #f3f4f6; padding: 0 3px; border-radius: 2px; font-size: 9.5pt; }
table { border-collapse: collapse; width: 100%; margin: 4px 0; }
th, td { border: 1px solid #e5e7eb; padding: 3px 6px; text-align: left; font-size: 10pt; }
th { background: #eff6ff; }
"""


def md_to_html(md_text: str) -> str:
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
    )
    return (
        f"<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{html_body}</body></html>"
    )


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    with sync_playwright() as pw:
        # channel="msedge" reuses the system Microsoft Edge, no Chromium download
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.goto(f"file:///{html_path.as_posix()}", wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            print_background=True,
            display_header_footer=False,
        )
        browser.close()


def main() -> None:
    if not SRC_MD.exists():
        raise SystemExit(f"Source Markdown not found: {SRC_MD}")

    md = SRC_MD.read_text(encoding="utf-8")
    html = md_to_html(md)
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"[1/3] HTML written: {HTML_OUT}")

    html_to_pdf(HTML_OUT, PDF_OUT)
    print(f"[2/3] PDF rendered: {PDF_OUT} ({PDF_OUT.stat().st_size} bytes)")

    shutil.copyfile(PDF_OUT, DESKTOP_PDF)
    print(f"[3/3] Copied to desktop: {DESKTOP_PDF}")


if __name__ == "__main__":
    main()

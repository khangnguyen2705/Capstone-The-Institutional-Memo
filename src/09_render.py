"""(a) Render INVESTMENT_MEMO.md to a polished PDF (Chrome headless) and Word
(.docx via htmldocx), with the exhibit charts embedded.

Run from project root:  python3 src/09_render.py
"""
from __future__ import annotations
import os, base64, subprocess
import markdown

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(HERE, "INVESTMENT_MEMO.md")
HTML = os.path.join(HERE, "INVESTMENT_MEMO.html")
PDF = os.path.join(HERE, "INVESTMENT_MEMO.pdf")
DOCX = os.path.join(HERE, "INVESTMENT_MEMO.docx")
FIG = os.path.join(HERE, "figures")

EXHIBITS = [
    ("capacity_frontier_v2.png", "Exhibit 1 — v2 capacity frontier (Kalman book, full-period liquidity): net Sharpe vs. gross deployed notional."),
    ("capacity_frontier_full.png", "Exhibit 2 — v1 capacity frontier, forward liquidity (2022–2026)."),
    ("capacity_frontier.png", "Exhibit 3 — v1 capacity frontier, stressed 2022 liquidity (conservative anchor)."),
    ("impact_curve.png", "Exhibit 4 — Net dollar P&L vs. deployed capital: the edge rolls over as impact compounds."),
    ("drawdown.png", "Exhibit 5 — v1 OOS growth of $1 and drawdown."),
    ("walkforward_oos.png", "Exhibit 6 — Out-of-sample walk-forward: blend vs. sleeves vs. static 60/40."),
]

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.45;
       color: #1a1a1a; max-width: 100%; }
h1 { font-size: 19pt; border-bottom: 3px solid #1f3a5f; padding-bottom: 6px; color: #1f3a5f; }
h2 { font-size: 13.5pt; color: #1f3a5f; border-bottom: 1px solid #ccc; padding-bottom: 3px;
     margin-top: 20px; }
h3 { font-size: 11.5pt; color: #333; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.3pt; }
th, td { border: 1px solid #bbb; padding: 4px 7px; text-align: left; }
th { background: #1f3a5f; color: #fff; }
tr:nth-child(even) { background: #f3f6fa; }
blockquote { background: #eef3f9; border-left: 4px solid #1f3a5f; margin: 12px 0;
             padding: 8px 14px; font-style: normal; }
code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
strong { color: #14243a; }
img { max-width: 100%; height: auto; margin: 6px 0; border: 1px solid #ddd; }
.exhibit { page-break-inside: avoid; margin: 14px 0; }
.cap { font-size: 9pt; color: #555; font-style: italic; margin-top: 2px; }
hr { border: none; border-top: 1px solid #ccc; margin: 16px 0; }
"""


def b64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def main():
    body = markdown.markdown(open(MD).read(),
                             extensions=["tables", "fenced_code", "sane_lists"])
    # exhibits (base64 so the file is self-contained / Chrome-portable)
    ex_html = ['<hr><h2>Exhibits</h2>']
    ex_docx = ['<hr><h2>Exhibits</h2>']
    for fn, cap in EXHIBITS:
        p = os.path.join(FIG, fn)
        if os.path.exists(p):
            ex_html.append(f'<div class="exhibit"><img src="{b64(p)}"/>'
                           f'<div class="cap">{cap}</div></div>')
            ex_docx.append(f'<p><img src="figures/{fn}"/></p>'
                           f'<p><i>{cap}</i></p>')
    full_html = (f"<!doctype html><html><head><meta charset='utf-8'>"
                 f"<style>{CSS}</style></head><body>{body}{''.join(ex_html)}"
                 f"</body></html>")
    open(HTML, "w").write(full_html)
    print(f"[html] {HTML}")

    # ---- PDF via Chrome headless ----
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome):
        subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={PDF}", f"file://{HTML}"],
                       check=True, capture_output=True)
        print(f"[pdf]  {PDF}  ({os.path.getsize(PDF)//1024} KB)")
    else:
        print("[pdf]  Chrome not found — skipped")

    # ---- DOCX via htmldocx ----
    try:
        from docx import Document
        from htmldocx import HtmlToDocx
        doc = Document()
        HtmlToDocx().add_html_to_document(body + "".join(ex_docx), doc)
        doc.save(DOCX)
        print(f"[docx] {DOCX}  ({os.path.getsize(DOCX)//1024} KB)")
    except Exception as e:
        print(f"[docx] failed: {e}")


if __name__ == "__main__":
    main()

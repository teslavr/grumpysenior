"""The Books: a single self-contained HTML page, generated from the event log.

No CDN, no build step, no JavaScript framework -- it is one file you can drop into
`docs/` and let GitHub Pages serve. Charts are inline SVG.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from .metrics import Metrics

CSS = """
:root {
  --bg:#faf8f5; --panel:#fff; --ink:#1a1614; --muted:#6b625c; --line:#e6ded5;
  --accent:#8c1c13; --good:#2d6a4f; --warn:#b5651d;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#141210; --panel:#1d1a17; --ink:#f0eae4; --muted:#a49a92; --line:#332d28;
    --accent:#d9534f; --good:#74c69d; --warn:#e0a458;
  }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.6 ui-serif,Georgia,'Times New Roman',serif; }
.wrap { max-width:1000px; margin:0 auto; padding:48px 24px 80px; }
h1 { font-size:2.4rem; margin:0 0 4px; letter-spacing:-.02em; }
.sub { color:var(--muted); font-style:italic; margin:0 0 40px; }
h2 { font-size:1.05rem; text-transform:uppercase; letter-spacing:.12em;
  color:var(--muted); margin:48px 0 16px; font-family:ui-sans-serif,system-ui,sans-serif; }
.grid { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:20px; }
.n { font-size:2.3rem; font-weight:600; letter-spacing:-.03em; line-height:1.1; }
.k { font-size:.8rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted);
  font-family:ui-sans-serif,system-ui,sans-serif; margin-top:6px; }
.q { font-size:.88rem; color:var(--muted); margin-top:10px; font-style:italic; }
.accent { color:var(--accent); } .good { color:var(--good); } .warn { color:var(--warn); }
table { width:100%; border-collapse:collapse; font-family:ui-sans-serif,system-ui,sans-serif;
  font-size:.9rem; }
th,td { text-align:left; padding:10px 12px; border-bottom:1px solid var(--line); }
th { font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
.scroll { overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:var(--panel); }
.bar { height:8px; background:var(--line); border-radius:4px; overflow:hidden; min-width:60px; }
.bar > i { display:block; height:100%; background:var(--accent); }
footer { margin-top:64px; padding-top:20px; border-top:1px solid var(--line);
  color:var(--muted); font-size:.85rem; }
.empty { background:var(--panel); border:1px dashed var(--line); border-radius:10px;
  padding:40px; text-align:center; color:var(--muted); }
"""

_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Books — GrumpySenior.dev</title>
<style>{css}</style></head>
<body><div class="wrap">
<h1>The Books</h1>
<p class="sub">Every sit-down the Commission has held. Numbers only — no code, no paths,
no findings. Generated {generated}.</p>
{body}
<footer>
GrumpySenior.dev · records are anonymous by construction: an install id, which models
sat, what they agreed on, what it cost. Nothing about the code itself is ever written
down, which is why this page can be public.
</footer>
</div></body></html>"""


def _card(value, label, question, cls="") -> str:
    return (
        f'<div class="card"><div class="n {cls}">{value}</div>'
        f'<div class="k">{html.escape(label)}</div>'
        f'<div class="q">{html.escape(question)}</div></div>'
    )


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def render(m: Metrics) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if not m.runs:
        body = ('<div class="empty">No sit-downs on record yet. Run '
                '<code>grumpy review &lt;file&gt;</code> and come back.</div>')
        return _TEMPLATE.format(css=CSS, generated=generated, body=body)

    parts = []

    parts.append("<h2>Does the Commission actually agree?</h2><div class='grid'>")
    parts.append(_card(_pct(m.corroboration_rate), "corroborated",
                       "Two or more Families found it. If this collapses, the confidence "
                       "number is fiction and the product has no floor.", "accent"))
    parts.append(_card(_pct(m.unanimity_rate), "unanimous",
                       "Every seated Family found it independently."))
    parts.append(_card(_pct(m.contested_rate), "the Don dissented",
                       "Kept anyway by the no-veto rule. If these turn out consistently "
                       "wrong, the rule is noise and should go.", "warn"))
    parts.append(_card(m.struck_by_don, "struck by the Don",
                       "Lone findings he rejected. He is allowed to — for exactly one voice."))
    parts.append("</div>")

    parts.append("<h2>Do the fixes hold up?</h2><div class='grid'>")
    parts.append(_card(_pct(m.fix_offer_rate), "sit-downs with an offer",
                       "A concrete corrected file, not just complaints."))
    parts.append(_card(_pct(m.fix_verified_rate), "offers that verified",
                       "Parsed, and passed the configured check. Broken fixes are never "
                       "shown — this is the anti-hallucination gate.", "good"))
    parts.append(_card(m.total_issues, "issues published", "Across every sit-down."))
    parts.append(_card(f"{m.median_seconds}s", "median sit-down", "Wall clock, full Commission."))
    parts.append("</div>")

    parts.append("<h2>Does anyone come back?</h2><div class='grid'>")
    parts.append(_card(m.users, "installs", "Distinct anonymous install ids."))
    parts.append(_card(m.runs, "sit-downs", "Total reviews run."))
    parts.append(_card(m.runs_per_user, "per install", "Novelty use looks like 1.0 and stays there."))
    parts.append(_card(_pct(m.repeat_user_rate), "came back",
                       "Installs with more than one review. The clearest kill signal.", "accent"))
    parts.append("</div>")

    if m.per_family:
        parts.append("<h2>Which Families earn their seat?</h2><div class='scroll'><table>")
        parts.append("<tr><th>Family</th><th class='num'>sat</th><th class='num'>findings</th>"
                     "<th class='num'>per sitting</th><th class='num'>failed</th><th>failure rate</th></tr>")
        peak = max((d["findings_per_sitting"] for d in m.per_family.values()), default=1) or 1
        for model, d in sorted(m.per_family.items(),
                               key=lambda kv: kv[1]["findings_per_sitting"], reverse=True):
            width = round(100 * d["findings_per_sitting"] / peak)
            parts.append(
                f"<tr><td><code>{html.escape(model)}</code></td>"
                f"<td class='num'>{d['sat']}</td><td class='num'>{d['findings']}</td>"
                f"<td class='num'>{d['findings_per_sitting']}</td>"
                f"<td class='num'>{d['failures']}</td>"
                f"<td><div class='bar'><i style='width:{width}%'></i></div>"
                f"<small>{_pct(d['failure_rate'])}</small></td></tr>"
            )
        parts.append("</table></div>")

    if m.failures:
        parts.append("<h2>Why Families drop out</h2><div class='scroll'><table>")
        parts.append("<tr><th>reason</th><th class='num'>count</th></tr>")
        for reason, count in m.failures.most_common():
            parts.append(f"<tr><td>{html.escape(reason)}</td><td class='num'>{count}</td></tr>")
        parts.append("</table></div>")

    if m.surfaces:
        parts.append("<h2>How it gets called</h2><div class='scroll'><table>")
        parts.append("<tr><th>surface</th><th class='num'>sit-downs</th></tr>")
        for surface, count in m.surfaces.most_common():
            parts.append(f"<tr><td>{html.escape(surface)}</td><td class='num'>{count}</td></tr>")
        parts.append("</table></div>")

    return _TEMPLATE.format(css=CSS, generated=generated, body="\n".join(parts))

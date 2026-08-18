"""grumpy — the Commission sits on your code. Your own Don presides.

    grumpy review orders.py
    grumpy review orders.py --lines 40-90
    cat snippet.py | grumpy review -
    grumpy review --staged
    grumpy review orders.py --format json     # for agents and CI
    grumpy mcp                                # serve over MCP (any agent)

Exit codes: 0 = clean, 1 = findings at or above --fail-on, 2 = could not run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config, default_committee, vendor_of
from .engine import Result, review_source
from .sources import Source, from_file, from_git, from_stdin

SEVERITY_ORDER = {"none": -1, "low": 0, "medium": 1, "high": 2}


def build_config(args) -> Config:
    cfg = Config.load(getattr(args, "config", None))
    if getattr(args, "master", None):
        cfg.master = args.master
        cfg.committee = default_committee(cfg.master)
    if getattr(args, "committee", None):
        cfg.committee = args.committee
    return cfg


def collect_sources(args) -> list[Source]:
    if args.staged or args.diff:
        return from_git(staged=args.staged)
    if args.path == "-":
        return [from_stdin(args.filename)]
    if args.path:
        return [from_file(args.path, args.lines)]
    raise ValueError("give a path, `-` for stdin, or --staged / --diff")


def emit(results: list[Result], fmt: str, out: str | None) -> None:
    if fmt == "json":
        payload = json.dumps([r.as_dict() for r in results], indent=2)
    else:
        payload = "\n\n---\n\n".join(r.as_markdown() for r in results)
    if out:
        Path(out).write_text(payload)
        print(f"written to {out}", file=sys.stderr)
    else:
        print(payload)


def cmd_review(args) -> int:
    cfg = build_config(args)
    try:
        sources = collect_sources(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"grumpy: {exc}", file=sys.stderr)
        return 2

    if not sources:
        print("grumpy: nothing to review", file=sys.stderr)
        return 0

    if not args.quiet:
        print(
            f"the Don:        {cfg.master} ({vendor_of(cfg.master)})\n"
            f"the Commission: {', '.join(cfg.committee)}",
            file=sys.stderr,
        )

    results: list[Result] = []
    for source in sources:
        if not args.quiet:
            print(f"\nreviewing {source.label}", file=sys.stderr)
        try:
            result = review_source(cfg, source.label, source.code, surface="cli")
        except RuntimeError as exc:
            print(f"grumpy: {exc}", file=sys.stderr)
            return 2
        if not args.quiet:
            for model, error in result.committee_errors.items():
                print(f"  · {model}: FAILED — {error}", file=sys.stderr)
            print(
                f"  · {len(result.issues)} issue(s), worst={result.worst_severity}"
                + (f", {result.suppressed} struck by the Don" if result.suppressed else ""),
                file=sys.stderr,
            )
            if result.verdict:
                print(f"  · fix: {result.verdict.label} — {result.verdict.detail}", file=sys.stderr)
        results.append(result)

    if not args.quiet:
        print(file=sys.stderr)
    emit(results, args.format, args.out)

    floor = SEVERITY_ORDER.get(args.fail_on, 99)
    worst = max((SEVERITY_ORDER.get(r.worst_severity, -1) for r in results), default=-1)
    return 1 if worst >= floor else 0


def cmd_stats(args) -> int:
    """The Books, in the terminal."""
    from .metrics import compute
    from .telemetry import EVENTS, load

    m = compute(load(Path(args.log) if args.log else None))
    if not m.runs:
        print(f"No sit-downs on record ({EVENTS}). Run a review first.")
        return 0
    pct = lambda x: f"{round(x * 100)}%"
    print(f"sit-downs {m.runs} · installs {m.users} · {m.runs_per_user} per install · "
          f"{pct(m.repeat_user_rate)} came back")
    print(f"issues {m.total_issues} · corroborated {pct(m.corroboration_rate)} · "
          f"unanimous {pct(m.unanimity_rate)} · contested {pct(m.contested_rate)} · "
          f"struck {m.struck_by_don}")
    print(f"fixes offered {pct(m.fix_offer_rate)} · verified {pct(m.fix_verified_rate)} · "
          f"median {m.median_seconds}s")
    if m.per_family:
        print("\nFamily                                        sat  finds  /sit  fail")
        for model, d in sorted(m.per_family.items(),
                               key=lambda kv: kv[1]["findings_per_sitting"], reverse=True):
            print(f"  {model:<42} {d['sat']:>4} {d['findings']:>6} "
                  f"{d['findings_per_sitting']:>5} {d['failures']:>5}")
    if m.failures:
        print("\ndrop-outs: " + ", ".join(f"{k}={v}" for k, v in m.failures.most_common()))
    return 0


def cmd_dashboard(args) -> int:
    """Generate The Books as one self-contained page, for GitHub Pages."""
    from .dashboard import render
    from .metrics import compute
    from .telemetry import load

    page = render(compute(load(Path(args.log) if args.log else None)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"written to {out} ({len(page):,} bytes)")
    return 0


def cmd_models(args) -> int:
    from .providers import list_available_models

    cfg = build_config(args)
    rows = list_available_models(cfg.region)
    if not rows:
        print(f"No models visible in {cfg.region}. Enable model access in the Bedrock console.")
        return 2
    width = max(len(r["id"]) for r in rows)
    for row in sorted(rows, key=lambda r: (r["kind"], r["id"])):
        print(f"{row['id']:<{width}}  {row['kind']:<18}  {row['name']}")
    return 0


def cmd_mcp(args) -> int:
    from .mcp_server import serve

    serve(build_config(args))
    return 0


def cmd_review_pr(args) -> int:
    from .github import GitHubError, changed_files, from_environment, upsert_comment

    cfg = build_config(args)
    try:
        pr = from_environment()
        files = changed_files(pr)
    except GitHubError as exc:
        print(f"grumpy: {exc}", file=sys.stderr)
        return 2

    if not files:
        print("grumpy: no reviewable files in this PR", file=sys.stderr)
        return 0

    reviewed, skipped = files[: args.max_files], files[args.max_files :]
    sections: list[str] = []
    worst = -1

    for name in reviewed:
        path = Path(name)
        if not path.is_file():
            print(f"  · {name}: not checked out, skipped", file=sys.stderr)
            continue
        try:
            result = review_source(cfg, name, path.read_text(), surface="github-action")
        except RuntimeError as exc:
            print(f"  · {name}: {exc}", file=sys.stderr)
            continue
        worst = max(worst, SEVERITY_ORDER.get(result.worst_severity, -1))
        if result.clean and not result.verdict:
            continue
        sections.append(
            f"<details open><summary><code>{name}</code></summary>\n\n"
            f"{result.as_markdown()}\n</details>"
        )

    if not sections:
        print("grumpy: nothing worth commenting on", file=sys.stderr)
        return 0

    body = "\n\n".join(sections)
    if skipped:
        # A cap must never read as full coverage.
        body += (
            f"\n\n<sub>Reviewed {len(reviewed)} of {len(files)} changed files. "
            "Not looked at: " + ", ".join(f"`{s}`" for s in skipped) + ".</sub>\n"
        )

    print(f"posted: {upsert_comment(pr, body)}", file=sys.stderr)
    return 1 if worst >= SEVERITY_ORDER.get(args.fail_on, 99) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grumpy", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="path to .grumpy.yml")
    parser.add_argument("--master", help="the model you write code with")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="review a file, a snippet, or your working tree")
    review.add_argument("path", nargs="?", help="file path, or `-` to read stdin")
    review.add_argument("--lines", help="review only these lines, e.g. 40-90")
    review.add_argument("--filename", help="name for stdin input, so we know the language")
    review.add_argument("--staged", action="store_true", help="review files staged for commit")
    review.add_argument("--diff", action="store_true", help="review your uncommitted changes")
    review.add_argument("--committee", nargs="*", help="override the committee")
    review.add_argument("--format", choices=["md", "json"], default="md")
    review.add_argument("--fail-on", choices=["low", "medium", "high", "never"], default="never",
                        help="exit 1 when an issue at this severity is found")
    review.add_argument("--out", help="write to a file instead of stdout")
    review.add_argument("-q", "--quiet", action="store_true", help="no progress on stderr")
    review.set_defaults(func=cmd_review)

    stats = sub.add_parser("stats", help="the Books: usage metrics from the local event log")
    stats.add_argument("--log", help="path to events.jsonl (default ~/.grumpy/events.jsonl)")
    stats.set_defaults(func=cmd_stats)

    dash = sub.add_parser("dashboard", help="render the Books as a self-contained HTML page")
    dash.add_argument("--out", default="docs/index.html")
    dash.add_argument("--log", help="path to events.jsonl")
    dash.set_defaults(func=cmd_dashboard)

    models = sub.add_parser("models", help="list Bedrock models this account can call")
    models.set_defaults(func=cmd_models)

    mcp = sub.add_parser("mcp", help="run as an MCP server on stdio (Claude Code, Cursor, Codex)")
    mcp.set_defaults(func=cmd_mcp)

    pr = sub.add_parser("review-pr", help="review the current pull request (GitHub Action)")
    pr.add_argument("--max-files", type=int, default=5)
    pr.add_argument("--fail-on", choices=["low", "medium", "high", "never"], default="never")
    pr.set_defaults(func=cmd_review_pr)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

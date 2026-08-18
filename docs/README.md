# The Books

`index.html` is the analytics page, served by GitHub Pages. It is generated — do not
edit it by hand:

```bash
grumpy dashboard --log docs/events.jsonl --out docs/index.html
```

`events.jsonl` is the event log. **One line per sit-down, and it contains no content**:
an anonymous install id, which models sat, how many findings were corroborated, whether
the fix verified, and how long it took. No source code, no file paths, no repository
names, no finding text — a tool that promises your code stays in your account does not
get an exception for its own analytics.

That constraint is what makes this page publishable at all. It was designed into the
schema before the first chart existed, rather than bolted on after someone asked.

Local telemetry is off with `GRUMPY_NO_TELEMETRY=1`, and lives in `~/.grumpy/`.

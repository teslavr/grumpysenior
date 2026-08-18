# What I cut for time

## The timebox, honestly

The four-hour version of this is the two documents plus a script that calls three
models on a hardcoded diff and prints the result. That existed, and it worked.

I kept going past it, and I'd rather say so than pretend the scope fit. The reason is
specific: once the Commission was sitting, the thing I wanted was not a demo of it —
it was to have it. So it became a CLI I can point at any file, an MCP server my own
coding agent calls, and a PR bot. If that reads as failing to respect a timebox, fair.
I'd make the same call again, and the working tool is the argument.

## What I deliberately did not build

**Diff-awareness.** It reviews whole files or explicit line ranges, not hunks. On a
large PR it reads the file rather than only what changed — more tokens, and occasional
findings about code the author never touched. The right fix is to send the hunk plus
enclosing scope. Half a day, and the first thing I'd do next.

**Inline suggested changes on GitHub.** The bot posts one comment with a diff, not
per-line `suggestion` blocks with the one-click accept. That anchoring — mapping a
finding to the exact position in the diff so the button applies cleanly — is the
fiddliest part of the GitHub integration and buys nothing architecturally. It is
mechanical work, and I would rather have spent the hours on the consensus logic.

**Real test-running as verification.** A proposed fix is checked for syntax, and a
verification command can be configured, but nothing runs the repository's own test
suite in a sandbox. That is the honest version of "verified" and it needs isolation I
didn't want to hand-roll under time pressure.

**Learning from outcomes.** Nothing records which proposed fixes were merged. That
signal is the north-star metric in the strategy doc *and* the obvious training loop for
per-repo tuning — which Families to trust, which severities to suppress. It is the
highest-value thing not here, and it needs persistence, which the brief said I could skip.

**Cost and latency routing.** Every sit-down seats the full Commission. It should run one
cheap model on a trivial diff and the full panel only on risky ones. Easy, but it is a
tuning problem and tuning without usage data is guessing.

**Languages other than Python.** The Commission reviews anything; only Python fixes get
mechanically verified. Everything else ships labelled `unverified`, which is honest but
weaker.

**A UI.** There is a terminal and a PR comment. The brief said not to over-index on
pixel-perfect CSS, and I took that as permission rather than an instruction.

## What I cut and then put back

**Tolerant JSON parsing.** The first live run dropped a Family because Llama
returned malformed JSON — it had been asked to embed a whole source file inside a JSON
string, and did not escape the newlines. I patched the parser, and the patch made it
worse: two members failed on the next run.

The real fix was to stop asking for that at all. Findings come back as small JSON
values; the corrected code comes after a delimiter, as plain text, with nothing to
escape. Consensus went from 2/3 to 3/3 and the run got twice as fast.

I am including this because the failure is the interesting part. A cross-model product
lives or dies on its weakest Family, and "make the strong model work"
is not the same problem as "make every vendor work."

## Where I spent the time instead

On the one decision the product stands on: **the Don consolidates but cannot
silently overrule the Commission.** Getting that boundary right — and building the
consensus floor that enforces it rather than trusting a prompt — was worth more than
any of the above.

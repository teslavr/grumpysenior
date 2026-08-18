# Opera — "AI Product Builder" Case Study · GrumpySenior.dev

Sergei Lavrinenko's take-home for the Opera AI Product Builder role.

## Deliverables

| # | Brief asked for | Here |
|---|---|---|
| 1 | Product & Strategy, max 2 pages | [`01-strategy.md`](01-strategy.md) |
| 2 | System architecture, one diagram or concise doc | [`02-architecture.md`](02-architecture.md) |
| 3 | Mock or prototype — Option B, with a **live** LLM loop | [`grumpysenior/`](grumpysenior/) — a working tool, not a script |
| — | "What I cut for time" note | [`03-what-i-cut.md`](03-what-i-cut.md) |

## The product in one line

The Commission sits on your code: five Families, five different models, five different
vendors. Your own Don presides over the sit-down — and is not allowed to overrule them.

## Status

Live and verified against real AWS Bedrock. The Commission: Meta Llama 3.3 70B, Mistral
Pixtral Large, DeepSeek R1. The Don: Claude Opus 4.6. Both planted defects
in `grumpysenior/samples/orders.py` found by all three Families independently; the proposed
fix parses. ~23 seconds per file.

## The Books

Usage analytics, generated from an event log that contains **counts only — never code,
paths, or findings**: [`docs/`](docs/), published to GitHub Pages. `grumpy stats` prints
the same numbers in a terminal. This is what makes the kill criteria in the strategy doc
computable rather than aspirational.

## Internal (not for submission)

- [`DECISIONS.md`](DECISIONS.md) — the why behind each choice, prep for the live defence
- [`CONTEXT.md`](CONTEXT.md) — background so a fresh session can pick this up cold

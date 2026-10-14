# Tool-stream completion corpus

Parseable tool arguments can appear before a tool call has finished. This small offline corpus lets local-AI integrators inspect that distinction in OpenAI-style streaming chat completions (SSE `data:` events carrying `choices[].delta.tool_calls`, closed by `finish_reason: "tool_calls"` and `[DONE]`) and replay their own acceptance tests. It never executes a tool.

In these twelve authored synthetic cases, waiting for a completed `tool_calls` finish matched every expected accept/refuse outcome. A simple whole-buffer baseline matched it exactly. That negative result gives no correctness reason to prefer the incremental parser over the baseline on this corpus.

Version 1.0.0 · 2026-09-30 · Apache-2.0 · CyberNative AI LLC

## Replay

From this directory, use CPython 3.12 through [uv](https://docs.astral.sh/uv/):

```bash
uv run --no-project --python 3.12 python -m unittest discover -s . -p 'test_*.py' -v
uv run --no-project --python 3.12 python measure.py replay
```

Only the Python standard library is required. There is no dependency install or model download for the measurement. `uv` may acquire Python if 3.12 is not already installed; the measurement itself needs no network. `replay/` is the only generated output directory. For this fixed corpus, allow one CPU, 256 MiB RAM, 90 seconds and 64 MiB of output; abort if those limits are exceeded or the process fails. These are declared run bounds, not controls enforced by `measure.py`. The original measurement ran inside an offline, non-root CPU container; its launcher is not part of this package. No GPU, model calls or tool execution are involved.

The two files should match the frozen representative evidence byte for byte:

```bash
uv run --no-project --python 3.12 python - <<'PYCODE'
from pathlib import Path
import hashlib
for name in ("raw.ndjson", "result.json"):
    actual = Path("replay", name).read_bytes()
    expected = Path("evidence", name).read_bytes()
    assert actual == expected, name
    print(name, hashlib.sha256(actual).hexdigest())
PYCODE
```

For one stream, extract the first authored fixture and replay one byte at a time:

```bash
uv run --no-project --python 3.12 python - <<'PYCODE'
import json
from pathlib import Path
fixture = json.loads(Path("fixture.json").read_text(encoding="utf-8"))[0]
Path("replay/example.sse").write_bytes(fixture["stream"].encode("utf-8"))
print(fixture["id"], fixture["expected"])
PYCODE
uv run --no-project --python 3.12 python streamcheck.py replay/example.sse --chunk-bytes 1
```

`calls` means proposed diagnostic data. It is not permission to execute: schema checks, authorization and side-effect controls belong to the integrating application. Review any capture for secrets and personal data before using it; the included fixtures are synthetic.

## What was tested

Question and acceptance criteria were frozen before the measured run. The question was whether accepting on a completed tool-call finish avoids incorrect proposals compared with accepting immediately when arguments parse, and whether incremental framing has a correctness advantage over whole-buffer framing.

The scorer uses all 12 fixtures, each as one whole chunk, one-byte chunks and every possible two-part byte split. This produces 5,174 transport variants, four arms and 20,696 raw records per trial. Variants are not independent tasks or model generations. Seed 0 is an identifier; there was no random sampling.

The arms are name-first/eager, JSON-ready, terminal-gated incremental framing, and whole-buffer framing with the same terminal acceptance function. The whole-buffer framing code is separate; the acceptance function is shared. Correctness means exact equality to the fixture's authored expected proposed calls, including an empty list for refusals. The raw field `unsafe` means a nonempty incorrect proposal; it is not a measured security exploit or actual tool execution.

All refusal controls are retained: length termination, disconnect, DONE without a completed finish, non-tool stop, unterminated finish event and incomplete arguments. The text-only no-call control is also retained. Positive controls cover split arguments/name, parallel calls, comments, BOM, Unicode and line-ending/multi-data framing. Inspect `fixture.json` for the precise dialect and expectations.

## Frozen result

These numbers are generated from `evidence/result.json`:

- Terminal-gated and whole-buffer-terminal each matched 5,174/5,174 variants; no misses or incorrect proposals. Their full diagnostic outputs agreed.
- JSON-ready made 2,083 incorrect proposals across five refusal controls. Incomplete arguments is the sixth refusal control and does not contribute to that total.
- Name-first/eager made 4,984 incorrect proposals and missed 2,620 expected-call variants; those counts can overlap.
- Each terminal arm recorded 281 `JSONDecodeError` outcomes in the incomplete-arguments control. They returned no calls and were scored as correct refusals. Errors are visible in raw data, not omitted observations.

The producing run had two exact repeats with identical raw and result bytes. `evidence/` contains one representative pair. A different AI contributor also checked complete coverage, hashes and two fresh repeats using the same organization, harness and environment. Labels: **Executed** and **Artifact checked (agent QA)**. This is not independent scientific reproduction.

Initial execution produced no measurements because source permissions prevented the non-root executor from reading the files. The executor UID and a date-format validation issue were corrected before measurement; fixtures, parsers, metrics and acceptance criteria did not change. No unfavorable measurements were removed. The successful measurement used CPython 3.12.13 in an offline CPU container. See `PROVENANCE.json` for image digest, declared bounds, contributions and source/evidence hashes.

## Limits and use

This is twelve authored cases in one dialect: single-choice OpenAI-style chat-completion deltas. It tests neither real-model efficacy nor native model grammar, HTTP connection reuse, production safety, demand, speed or superiority over a maintained SSE library. The matching whole-buffer baseline defeats an incremental-parser differentiation claim on this test. The package is a regression corpus and diagnostic example, not a maintained production parser.

Framing was informed by [WHATWG HTML §9.2.5–9.2.6](https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream), checked 2026-09-30. The code strictly refuses invalid UTF-8, unlike browser replacement decoding. It implements only the tested data-event framing, not full SSE/EventSource conformance, reconnects or HTTP transport.

The useful next test is whether these refusal fixtures catch a specific missing acceptance check in an integrator's actual client. Synthetic replay alone does not establish that. Use the corpus as tests; do not substitute its parser for application authorization.

## Publisher, authorship and corrections

Prepared by CyberNative AI LLC, an AI-run company, using AI agents; the company is the accountable publisher and maintainer, and AI contributors are not formal authors. Artifact QA used a different AI contributor within the same organization and shared the producing harness and environment. These are material limitations, not independent-team evidence.

Corrections: **hello@cybernative.ai**. As of 2026-09-30, we commit to publish dated corrections with affected versions and preserve superseded evidence. Send a specific failing fixture or missing acceptance scenario rather than sensitive captures. All included code and synthetic data are under Apache-2.0; see `LICENSE` and `NOTICE`.

Correction, 2026-10-14 (affects version 1.0.0 as first published): this section and `qa.assistance` in `PROVENANCE.json` described the work as assisted by AI, which implies a human author. AI agents prepared it. Fixtures, code, evidence, results and limitations are unchanged; the superseded wording remains in this repository's history.

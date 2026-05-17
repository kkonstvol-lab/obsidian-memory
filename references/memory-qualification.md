# Memory Qualification — Evidence Before Architecture

This reference explains how to qualify retrieval and context patterns before adopting them in an Obsidian Memory system.

The rule is simple:

> No measured failure mode, no new memory layer.

OpenViking-style memory ideas can be useful as reference architecture, but they should not become dependencies or default runtime layers just because they are interesting.

---

## Goal

Qualify memory patterns by proving they improve real retrieval work without weakening safety.

The v1 sequence:

```text
control baseline -> golden set -> baseline contest -> gap report -> minimal read-only trial -> shadow result
```

This keeps the system from drifting into architecture for architecture's sake.

---

## Source Of Truth

The source of truth remains:

- `wiki/**`
- `12-shared/**`
- `12-{agent}/**`
- `raw-sources/converted/**`
- `raw-sources/provenance/**`
- Git history

Qualification artifacts are derived and disposable.

They may include:

- golden query files;
- baseline reports;
- gap reports;
- shadow-session reports;
- trial result files;
- evidence candidate lists.

They must not become canonical memory by themselves.

---

## Out Of Scope For V1

Do not include these in a first qualification release:

- mandatory vector search;
- external memory service dependency;
- automatic memory extraction;
- transcript archive;
- direct canonical writes;
- default dynamic context injection;
- raw binary retrieval;
- private folder indexing across agents.

V1 is a read-only proof system.

---

## Gate 0: Control Baseline

Before testing a new retrieval pattern, prove the current control plane is stable.

Recommended checks:

```bash
python3 assets/operator/release_status.py --repo . --intent public-obsidian-memory
python3 assets/operator/release_surface_check.py --profile public-skill --standalone .
python3 assets/operator/retrieval_eval.py report
python3 assets/operator/bridge_health.py --vault /path/to/vault --status
```

For a private vault with its own operator script, run the local equivalent.

Acceptance:

- commands complete without blockers;
- the current baseline is recorded;
- no canonical writes are performed;
- unresolved warnings are named, not hidden.

Blocker:

- if the control plane is unstable, do not trial new memory patterns.

---

## Gate 1: Golden Set

Create a real query set before changing architecture.

Suggested size:

- 35 tuning queries;
- 15 blind holdout queries.

Required categories:

- identity or self memory;
- project memory;
- correction or lesson recall;
- source/provenance recall;
- graph relationship recall;
- recent runtime context;
- ambiguous queries;
- negative no-result queries;
- private-scope probes;
- raw-binary probes;
- secret/transcript leakage probes.

Golden item schema:

```json
{
  "query": "What should answer this?",
  "expected_uri": "wiki/summaries/example.md",
  "expected_no_result": false,
  "acceptable_alternates": [],
  "forbidden_targets": [],
  "required_evidence": [],
  "difficulty": "medium",
  "review_notes": ""
}
```

Use exactly one of `expected_uri` or `expected_no_result`.

Rules:

- Do not inspect holdout results until final review.
- Do not change expected targets after seeing a result unless the audit note explains why.
- Negative/private cases are mandatory, not optional.
- The goal is trusted evidence, not a flattering score.

---

## Gate 2: Baseline Contest

Compare current retrieval before adding anything.

Contestants may include:

- plain lexical search;
- current wiki index navigation;
- existing graph/hybrid retrieval;
- approved local query paths;
- manual evidence lookup timing.

Metrics:

- `recall@5`;
- `MRR`;
- `precision@3`;
- `no_result_accuracy`;
- `operator_accept_rate`;
- `time_to_trusted_evidence`;
- `false_confidence_rate`;
- `forbidden_hit_rate`;
- `leakage_rate`.

Hard safety thresholds:

- forbidden hits must be zero;
- leakage must be zero;
- private/transcript leaks must be zero;
- private-agent folder hits must be zero unless explicitly in scope;
- raw binary hits must be zero.

Decision:

- If the baseline passes, do not add a new memory layer.
- If it fails, write a gap report.

---

## Gate 3: Gap Report

Every trial must map to an observed failure mode.

Examples:

- unstable paths or links -> internal URI/id layer;
- poor coarse filtering -> deterministic L0/L1 context index;
- weak multi-hop recall -> hierarchical retrieval;
- unclear evidence -> evidence-first query packet;
- repeated review friction -> ledger-lite;
- semantic misses after lexical/graph attempts -> semantic pilot.

Rules:

- One failure mode, one minimal trial.
- No neighboring backlog feature "while we are here".
- Safety failures do not justify a richer retrieval layer; they require a smaller, safer design.

---

## Gate 4: Minimal Read-Only Trial

Allowed v1 trials:

1. **Internal URI/id layer**
   - Use only if the gap report proves addressing instability.
   - Keep ids internal until holdout proves stability.

2. **Deterministic L0/L1 context index**
   - Use only if the baseline struggles with coarse candidates.
   - No LLM summaries in v1.

3. **Evidence-first context query**
   - Use only after the index or baseline evidence shows measurable need.
   - No automatic injection.
   - No canonical writes.
   - No LLM rerank unless separately qualified.

Success thresholds:

- `recall@5 >= 85%`;
- `MRR >= 0.65`;
- `precision@3 >= 0.75`;
- `no_result_accuracy >= 90%`;
- `operator_accept_rate >= 75%`;
- `false_confidence_rate <= 10%`;
- `time_to_trusted_evidence <= 15s`;
- all safety metrics zero.

Anti-Goodhart rules:

- Higher recall without precision and clear evidence is not success.
- A negative query returning a confident result is critical failure.
- A private/raw/secret hit is immediate failure.
- Evidence must be understandable to an operator in about 15 seconds.

---

## Shadow Result

After a passing trial, run shadow sessions before persistent use.

Shadow session rules:

- Use real tasks, not only golden queries.
- Keep dynamic context disabled by default.
- Record the query, candidates, evidence quality, operator decision, and safety flags.
- Do not auto-write canonical Markdown.
- Do not publish shadow reports from private vaults.

Recommended decision labels:

- `shadow-pass`: useful and safety-clean;
- `operator-review`: useful but ambiguous, noisy, or incomplete;
- `kill`: unsafe, leaky, overconfident, or not worth maintenance.

---

## Kill Rules

Kill or freeze the trial when:

- any private/raw/secret leak appears;
- holdout fails after one correction cycle;
- the baseline is equal or better at lower maintenance cost;
- the layer cannot be disabled without affecting canonical Markdown;
- maintenance cost exceeds the agreed budget two review cycles in a row;
- false confidence or noisy candidates keep recurring.

---

## Public Documentation Rule

When documenting qualification in a public skill:

- publish the workflow and safety thresholds;
- use synthetic examples;
- classify claims as shipped tool, recommended contract, or internal lesson;
- avoid machine-specific paths;
- avoid private report ids, proposal ids, and raw session text;
- describe OpenViking-style ideas as optional reference patterns only.

If the repository does not ship an implementation, say the workflow is a contract, not a bundled engine.

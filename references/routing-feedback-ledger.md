# Routing Feedback Ledger

Routing Feedback Ledger is an optional operator pattern for reviewing agent
skill selection without pretending that agent self-report is proof.

Use it when work feels noticeably better or worse and you need to separate
possible causes:

- skill routing;
- runtime or application behavior;
- approval friction;
- memory/context quality;
- ordinary task difficulty.

This reference documents a portable pattern. The public skill does not ship an
automatic routing recorder, hook capture layer, or private ledger state.

---

## Core Principle

Do not write "the skill helped" as a fact unless evidence supports it.

Write:

- what happened;
- which skills were explicit vs auto-selected;
- what evidence exists;
- how confident the causal interpretation is;
- what action candidate, if any, follows.

If evidence is only agent self-assessment, causal confidence stays low.

---

## When To Record

Create a draft only after significant work. Good triggers:

- an auto-selected skill materially changed the task path;
- a skill seemed unnecessary, missed, conflicting, or too heavy;
- runtime or approval behavior was surprising;
- a branch longer than roughly 15 minutes ended noticeably better or worse than
  usual;
- the user explicitly asked to capture the observation.

Do not record short routine tasks, obvious routing, repeated conclusions, or
low-confidence notes with no next action.

---

## Suggested Fields

Required fields:

```yaml
schema_version: routing-ledger.v1
event_id: stable id
created_at_utc: timestamp
thread_ref: local thread or short reference
task_title: short title
task_type: implementation | planning | memory | skill-work | debugging | research | other
skills_explicit: []
skills_auto: []
routing_case_type: correct_helpful | unnecessary_skill | missed_skill | overheavy_workflow | skill_conflict | ceremony_without_quality | runtime_not_skill | unknown
outcome: completed | partial | blocked | abandoned
routing_effect: improved | neutral | harmed | unknown
evidence_level: user_feedback | outcome_proof | self_assessment | unknown
causal_confidence: low | medium | high
likely_improvement_source: skills | runtime | memory | approvals | mixed | unknown
next_action: none | skill_trigger_patch | memory_rule | runtime_check | eval_candidate | no_action
```

Optional fields:

```yaml
approvals_friction: none | low | medium | high | blocked | unknown
runtime_surface: codex_desktop | codex_cli | claude_code | cursor | unknown
approval_mode_observed: auto_review | manual | restricted | unknown
runtime_change_suspected: true | false | unknown
ceremony_level: low | medium | high | unknown
evidence_refs: []
notes: short private-safe note
review_tags: []
```

---

## Evidence Rules

- `self_assessment` cannot support high causal confidence.
- Without `user_feedback` or `outcome_proof`, default to
  `causal_confidence: low`.
- If runtime or approvals may explain the improvement, avoid
  `likely_improvement_source: skills`; use `runtime`, `approvals`, `mixed`, or
  `unknown`.
- Keep `routing_effect: unknown` when the result improved but the cause is not
  clear.

---

## Privacy Boundary

Do not store:

- raw shell commands;
- raw tool output;
- env names or values;
- tokens or secret-bearing URLs;
- private excerpts;
- long logs;
- copied user or assistant messages;
- real private routing ledgers in a public skill repository.

Use synthetic examples in public docs and tests.

---

## Weekly Review

Review recent entries, usually the last seven days, and group findings by:

- useful auto-selected skills;
- unnecessary skill triggers;
- missed skills;
- over-heavy workflows;
- ceremony without quality;
- runtime-not-skill cases;
- unknown causality.

The review should end with action candidates:

- `skill_trigger_patch` — adjust a skill trigger in a separate task;
- `memory_rule` — capture a durable operating rule after approval;
- `runtime_check` — inspect application, CLI, or approval behavior;
- `eval_candidate` — save a case for a future trigger eval corpus;
- `no_action` — keep the observation but change nothing.

Do not create a second lifecycle board. Durable changes still go through the
existing decision-review, memory decision, skill patch, or eval planning flow.

---

## Payoff And Stop-Loss

After 10-20 real entries, decide:

- `keep` — the ledger produced actionable routing improvements;
- `simplify` — the pattern is useful but too heavy;
- `pause` — the ledger created ceremony without decisions;
- `promote_to_eval` — at least three strong cases should become eval corpus
  candidates.

Useful signal:

- a stable helpful skill is identified;
- a false-positive trigger is found;
- a missed skill is found;
- runtime or approval effects are separated from skill effects;
- weekly review leads to a concrete skill, memory, or runtime follow-up.

Bureaucracy signal:

- most entries are obvious;
- most entries are low-confidence with no action;
- the agent proposes ledger drafts too often;
- weekly review does not change decisions.

---

## Public Implementation Boundary

If you later ship a portable script for this pattern:

- keep it synthetic-fixture tested;
- default to read-only draft and review;
- require explicit approval for append;
- store real entries under local/private `12-{agent}/routing-ledger/`;
- never bundle private ledger state in the public skill.

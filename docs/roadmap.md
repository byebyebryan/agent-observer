# Agent Observer direction

The current product is reusable Codex read-only observation for dashboards,
diagnostics and agent utilities. Native managers own conversation control.
[Fleet Plus](https://dev.byebyebryan.com/fleet-plus/) carries the shared showcase;
this repository owns native semantics, public interfaces and acceptance evidence.

## Current baseline

The [a9 release](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a9)
supports full API 4/snapshot 6/Service 4 and working-set reads. Collector and
working-set roles have a reviewed Mesh a25 pair; other roles and consumers
retain independent selections. [Operations](operations.md) links exact receipts.

Observer writes, Claude observation and standalone active-only hosting are
retired. Working-set includes active membership and recent context. Earlier
plans for restoring those retired paths are superseded.

## Priorities and acceptance

| Area | Useful next step | Acceptance boundary |
| --- | --- | --- |
| Read utilities | Build concrete clients using public cached/full/working-set facades | Client behavior, lease expiry and partial/unavailable output |
| Native coverage | Investigate a reproducible identity or membership discrepancy | Independent native comparison on the affected host/home |
| Efficiency | Measure the owning collector/read path against an exact baseline | Matched CPU, memory and unchanged freshness/coverage |
| Consumer integration | Adopt an accepted producer interface where useful | Consumer-specific package, UI/device and recovery proof |

These are priorities, not scheduled implementation or deployment approvals.
Carbon's working-set membership was partial in the dated public-delivery receipt;
that remains an unresolved limit, not a complete-fleet claim or a fresh diagnosis.

## Deferred work and reopen conditions

- Delta synchronization remains dark after failed CPU/capacity gates. Reopen only
  with a concrete measured requirement and a reviewed bounded qualification plan.
- Optional complete-view feed and transport adoption need an actual consumer,
  independent compatibility evidence and explicit role selection.
- New native providers need capability/contract/native review. Reserved wire
  vocabulary is insufficient.
- Native event replay or guaranteed completion notifications need a separate
  producer contract and independent evidence; sampled state watches do not supply it.

The [historical roadmap](history/design/roadmap-before-20261024.md) preserves
earlier execution tracks and failures. Completed or superseded steps are not an
active backlog. Add dated findings to history/evidence and revise this page only
when the product direction or acceptance boundary changes.

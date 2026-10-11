# Codex-only operational cleanup

Date: 2026-10-11. The authorized [execution plan](../../operational-cleanup-plan.md)
preserves API 2/read 4/Service 2/Mesh SDK 1 and all selected runtime artifacts.
This report keeps source, installed/native, operating cost and publication
acceptance distinct. O0/O1 are accepted; O2–O5 remain pending below.

## Independent installed baseline

Source starts at `2fcacd1`; both normal collectors/readers select a18. Core wheel
SHA-256 is `06544d27ae62f590ee8e1b56f93d32026dffc2d0b13ac3c2c4df3b1e2dedba1e`,
with immutable producer source `fa3cd58e30d4175eeeb328081b013aea40b1625f`. Archive
hashes and installed operational gates pass on both hosts. The a16/Mesh a10
bridge, historical writer and downstream entrypoints retain separate selections.

The independent reference imports no Observer implementation and brackets each
installed direct/cached read with native daemon metadata. It takes no provider
actions. [Snap](snap-baseline.json) and [Starship](starship-baseline.json) contain
bounded identity, state, comparison counts and hash/incarnation bookends; raw
titles, directories and conversation content are excluded.

| Host | Native/public raw rows | Running rows | Default visible | Filtered children | Result |
| --- | --- | --- | --- | --- | --- |
| Snap | 91 | 3 users | 53 | 38 | Identity, runtime, phase, activity, age/order and filtering pass |
| Starship | 384 | 4 users + 2 children | 130 | 254 | Same checks pass; 2 known native creation clocks are volatile |

The Starship children `01a12999-db1f-70c1-921d-ae7d850fb638` and
`01a12999-e868-7802-aeb7-0f2492d21095` have unsaved native creation timestamps
that move between samples. Direct reads expose a sampling race; cached reads
differ by seven seconds in this baseline. This is not a fixed one-second bound.
Both are hidden by default and have unavailable conversation activity. No runtime,
phase, identity or conversation-age discrepancy is observed. The 46 older
Starship unknown kinds remain the accepted historical classification limitation.

Both normal services are current. Native daemon and bridge incarnations are
captured before the pass. Other agents' desktop/dotfiles work is concurrent;
those changes are not attributed to this pass or staged for publication.

## Guidance and source gate

The notification guide now uses the installed a18 interpreter and current
Codex-only commands. Historical Claude-inclusive cost and pilot documents are
labeled with their original scope. The mandatory source gate passes all 353
tests without skips in the selected Mesh-reader environment and checks all 133
Markdown files. The workflow's scoped Ruff lint also passes. An additional
format-only probe reports existing style drift in its two tooling files;
formatting is not a workflow gate and no unrelated reformatting is introduced.

## Operating costs

The ten-minute ordinary-host no-added-reader baseline is accepted. Separate
collector sampling attributes root and helper costs; delivery sampling agrees
within the window boundary difference and finds both resident bridges idle.

| Host | Collector root CPU | Helpers CPU | Total CPU | Mean / sampled peak PSS | End processes / FDs |
| --- | --- | --- | --- | --- | --- |
| Snap | 0.293% | 0.445% | 0.738% | 25.91 / 35.88 MiB | 2 / 12 |
| Starship | 0.928% | 0.963% | 1.892% | 31.41 / 42.39 MiB | 2 / 12 |

[Snap collector](snap-collector-baseline.json),
[Starship collector](starship-collector-baseline.json),
[Snap delivery](snap-delivery-baseline.json) and
[Starship delivery](starship-delivery-baseline.json) retain aggregate costs and
bounded CPU windows. No sustained collector hotspot is exposed by this baseline.
It observes ordinary active hosts, not an idle benchmark or a causal before/after
measurement of Claude removal.

Pending O2: paired five-minute subscriber windows from each host. Added readers
are sequential by origin. CPU means a
percentage of one core; root, helpers, resident bridge and owned readers are
separate. RSS/PSS/FD/process peaks are one-second sampled observations. Shared
native daemon cost and remote SSH-server/stdio-bridge trees are excluded from
the reader-tree attribution. No strict memory budget is introduced.

## Final installed/native and publication gates

O3–O5 remain pending: final native/current fleet checks, hosted main/tag CI,
publication of the exact accepted a18 wheel/manifest and fresh downloaded-byte
verification on both hosts. A local test pass or pushed commit is not a hosted
CI/release receipt. Later operator/documentation commits do not change a18's
producer-source or wheel binding. Download verification changes no selection.

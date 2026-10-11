# Codex-only operational cleanup

Date: 2026-10-11. The authorized [execution plan](../../operational-cleanup-plan.md)
preserves API 2/read 4/Service 2/Mesh SDK 1 and all selected runtime artifacts.
This report keeps source, installed/native, operating cost and publication
acceptance distinct. O0–O3 are accepted; O4/O5 publication gates remain pending.

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

All six paired five-minute windows completed, with one origin adding readers at
a time and the peer measured concurrently. These are raw validated watches,
including the originating reader's SSH child. Human rendering and future
GUI/device clients require their own resource measurements.

| Origin / window | Origin collector CPU | Resident bridge CPU | Reader CPU | Reader mean PSS |
| --- | --- | --- | --- | --- |
| [Snap local one](snap-local-one-snap.json) | 0.828% | 0.822% | 3.156% | 21.87 MiB |
| [Snap fleet one](snap-fleet-one-snap.json) | 0.848% | 0.861% | 10.142% | 30.47 MiB |
| [Snap fleet two](snap-fleet-two-snap.json) | 0.894% | 1.701% | 10.696% + 10.646% | 30.01 + 29.92 MiB |
| [Starship local one](starship-local-one-starship.json) | 2.099% | 3.402% | 4.533% | 26.36 MiB |
| [Starship fleet one](starship-fleet-one-starship.json) | 2.178% | 3.528% | 7.657% | 29.97 MiB |
| [Starship fleet two](starship-fleet-two-starship.json) | 2.713% | 6.942% | 7.719% + 7.799% | 29.48 + 29.20 MiB |

Peer receipts are retained alongside each origin receipt. Across all windows,
collector averages stay at or below 1.104% Snap and 2.713% Starship. Reader and
bridge costs scale approximately linearly; this is not a cheap-watch claim.
The highest sampled reader PSS is 43.25 MiB. Stable process/FD counts and restored
post-window sockets show no accumulating reader resources in this bounded pass;
they do not establish long-duration leak freedom.

CPU means a
percentage of one core; root, helpers, resident bridge and owned readers are
separate. RSS/PSS/FD/process peaks are one-second sampled observations. Shared
native daemon cost and remote SSH-server/stdio-bridge trees are excluded from
the reader-tree attribution. No strict memory budget is introduced.

## Reader profile attribution and follow-up

[Snap's process-CPU profile](snap-reader-profile.json) ran for 46 seconds,
including startup. Observer native frame/snapshot validation ran 102 times;
`validate_shape` accounted for 1.45 million recursive calls. Mesh's generic
`tree` walk ran about 4 million recursive calls, alongside JSON Schema admission
and encoding. This is a mixed Observer/Mesh validation cost, not only transport
or collection. Instrumented timing is not the normal CPU budget above.

Starship's [first process-CPU profile](starship-reader-profile.json) exited early
after 12 seconds under heavy instrumentation; its unavailable error reason is
not inferred. The [lighter wall-clock retry](starship-reader-profile-wall.json)
completed 45 seconds and stopped the owned reader normally with SIGINT. It shows
95 native snapshot validations, 1.50 million shape calls and 4.11 million generic
tree calls. Wall-clock totals include socket waiting and are not CPU shares.
Both completed profiles stopped their owned readers; ordinary services remained
selected. The six normal watch windows had no corresponding early exits.

The next performance checkpoint should be joint work: Observer owns pure native
validation and callback cost; Mesh owns generic walks/schema/proof/lease admission.
Measure repeated admission before choosing bounded reuse or faster validation.
Preserve mutable-input rejection, exact content binding, current-time expiry,
proof checks and disconnect revocation. An optimized runtime needs a successor
immutable artifact and independent native/selection gates; accepted a18 bytes
are not rebuilt here. Clients can share one validated read view among displays,
while retaining their own timers, presentation and authority revocation.

## Final installed/native and publication gates

Final [Snap](snap-after.json) and [Starship](starship-after.json) direct/cached
daemon comparisons repeat the 91/384 rows and 3/6 running counts. Exact identity,
runtime, phase, conversation activity/age, ordering and filtering pass with only
the two already identified Starship creation-clock cases. Both installed
operational gates pass. Protected provider/workspace/unit hashes, service and
daemon incarnations, native processes, bridge and selected links match baseline.
Snap's mutable `.claude.json` changed; no writer is attributed. Concurrent
desktop work committed dotfiles `6e30240`; this pass does not stage or publish
those unrelated changes.

Independent [Snap Mesh/native](snap-mesh-native-after.json) and
[Starship Mesh/native](starship-mesh-native-after.json) comparisons confirm the
same identity/runtime/activity results; the Starship creation clocks remain
sampling races. Actual two-host [Snap](snap-fleet-after.json) and
[Starship](starship-fleet-after.json) fleet pull/push return 475 Codex-only rows
and progress from pending/partial to complete. These fleet conformance receipts
are not themselves an independent native oracle. All owned read streams close.

The final source gate passes 353 tests without skips, 133 Markdown checks and
the workflow's scoped Ruff lint. Dotfiles remote `6e30240` already contains the
accepted `5fea4d1` selection; it needs no additional push from this pass.

Hosted main/tag CI, publication of the exact accepted a18 wheel/manifest and
fresh downloaded-byte verification remain pending. A local test pass or pushed
commit is not a hosted CI/release receipt. Later operator/documentation commits
do not change a18's producer-source or wheel binding. Download verification
changes no selection.

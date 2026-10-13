# Native timing: Mesh and operational acceptance

2026-10-13. C4–C6 follow the independently accepted
[local/native timing checkpoint](../2026-10-12-native-timing/REPORT.md).
Codex is the only native provider. This receipt does not accept a dashboard,
Agent Plus, attachment/actions, native notification enrichment or WSS deployment.

## Exact roles and boundaries

Observer `0.6.0a2`, source `f4882257f907fc2bd3c5f0254eddbe55fcf43618`, is installed
at `~/.local/share/agent-observer/0.6.0a2-b22d2b5795a9b3dd-mesh-a16-timing` on both
hosts. The [manifest](../../../artifacts/observer-0.6.0a2.json) binds wheel SHA-256
`b22d2b5795a9b3dddabeba1e6f0ce61070eaa15b5888d1875524214281c86d0d`, API 3,
snapshot/watch 5 and Service 3. It is installed and selected, not published as
a GitHub release by this pass.

Mesh `0.1.0a16`, source `c4ec7ca14e1f9f8ff40ba4cb9501e4850de39d44`, has
[its own manifest](mesh-0.1.0a16.json), wheel SHA-256
`a1a9fcae5c11d574f9690248e93d4e349b84e3e3787dd5aefcd1b7b670cd0e08`, and explicit
Agent profile `agent-observer.mesh-candidate.v2`. SDK 1, Read 1 and Delivery 1
remain unchanged. Profile v1 remains frozen for older Agent owners and Tmux.
Core/local service remain Mesh-free. Mesh owns delivery/proofs; Observer owns
native acquisition and the cached Agent source/profile/lazy factory.

The [byte comparison](a1-a2-byte-parity.json) verifies the a1 native-accepted
Observer package files against the a2 wheel, excluding only version declaration
and the separately accepted Mesh CLI/profile changes. The controlled a1 native
timing cases therefore cover identical core/service/read timing bytes in a2.
Installed a2 native comparisons and managed proofs remain separately recorded.

## C4: installed and two-host networking proof

[Snap](snap-owner.json) and [Starship](starship-owner.json) pass seven selected
profile cases and ten owned network cases through the exact installed packages.
The cases cover warm-up, partial/stale rosters, forged nonce/digest/receipt/clock,
gap/restart/catalog replacement, publisher resync, original receipts, wrong
binding/hello, healthy siblings during deadline failure, cancellation and cleanup.
These are controlled/synthetic cases, not native provider lifecycle claims.

Both [Snap](snap-publisher.json) and [Starship](starship-publisher.json) pass
cached IPC and an owned localhost fixed SSH carrier invoking the actual installed
Agent launcher. Public subscribe assessment passes. Closed readers leave no
native channels, active connections or cleanup failures, and import no native
collector, action client or Tmux adapter.

The [private two-host gate](private-fleet.json) then uses the rendered shared
launcher on real Snap/Starship SSH without changing normal selections. Agent v2
produces 481 rows and Tmux v1 produces two; both cached snapshot/push paths have
ready hosts, remote proofs, original lease expiry, disconnect revocation and
zero cleanup failures. The two lazy domain factories remain independently
selected. [Harness](private-fleet-check.py) and [owned host setup](private-fleet-host.py)
are retained for audit; private configurations/listeners/processes are retired.

Following normal role selection, [Snap](snap-selected-fleet.json) and
[Starship](starship-selected-fleet.json) pass complete fleet snapshot/watch through
the ordinary SSH catalog and normal named launcher, with remote proofs and
owned connection cleanup. The generic Mesh Agent CLI/default descriptor remains
v1; new Agent clients explicitly inject the v2 Observer profile. A final
[normal mixed-profile proof](mixed-profile-tmux.json) rejects the retained v1
Agent reader against the selected v2 endpoint, then reads/watches three ordinary
Tmux rows across both hosts through the normal shared launcher, with remote
proof, expiry/disconnect revocation and cleanup. The Agent failure does not
invalidate the Tmux domain.

## C5: paired rollout, rollback and resources

[Snap](snap-paired-selection.json) and [Starship](starship-paired-selection.json)
prove baseline Service 2/read-v1-profile, candidate Service 3/Agent v2, coordinated
rollback to the old tuple, and final reselection. Every stage authenticates the
selected collector/publisher processes, accepts cached read/subscribe, and
records a new service incarnation. Before mutation, captured targets and owned
unit entries must match; unrelated drift fails closed. Partial failures restore
only captured or candidate-owned bytes. The [paired harness](paired-selection.py)
does not use Mesh-only rollback against a mismatched collector protocol.

The historical writer, Tmux owner PID/start identity and selection, Codex config,
and available Claude settings retain their captured values. Only Observer and
its resident Agent publisher units are restarted; no provider action, daemon/TUI
restart, history deletion, Tmux unit change or downstream migration occurs.
Snap keeps 30/120-second runtime/history cadence; Starship keeps 20/60 seconds,
with native refresh hints. The shared launcher loads Mesh a16 from the accepted
Agent prefix while preserving Tmux's selected a7 native facade and v1 factory.

Two operational preflight defects were corrected: an unrelated desktop-template
dependency in the global ignore file escaped into Observer's scoped projection;
the candidate archive lacked the canonical `manifest.json` filename expected by
the operations helper. The projection now includes only scoped inputs, with a
regression test; the archive alias contains the exact manifest bytes. The first
candidate verification failure restored the prior paired tuple on both hosts.
Neither correction changes the installed observation wheel.

Five-minute owned-service windows use the same reader/resource procedure and
each host's normal cadences, with 100 cached reads, three push readers and one
connected non-reading client. Baseline Service 2 uses only a protocol-header
adaptation in the [measurement harness](baseline-service-resource.py), never a
runtime observation converter.

| Host | a18 baseline CPU / peak RSS | a2 owned candidate CPU / peak RSS |
| --- | --- | --- |
| Snap | 1.10% / 68.6 MB | 2.22% / 70.0 MB |
| Starship | 3.11% / 76.5 MB | 4.32% / 83.1 MB |

CPU is one-core equivalent, including service and owned/reaped children. RSS is
aggregate resident memory, not unique PSS. [Baseline Snap](snap-baseline-service.json),
[baseline Starship](starship-baseline-service.json), [candidate Snap](snap-owned-service.json)
and [candidate Starship](starship-owned-service.json) retain detailed counters,
original component receipts and reader results. Windows run at different times
against changing ordinary work; the table is descriptive, not causal attribution
of overhead or a fleet-watcher cost claim. The earlier native checkpoint records
same-view timing byte growth separately.

The final five-minute normal-unit windows also pass: [Snap](snap-selected-service.json)
uses 1.42% one-core CPU and 70.7 MB peak aggregate RSS; [Starship](starship-selected-service.json)
uses 4.82% and 84.3 MB. Each has three independent push readers with zero gaps or
errors, plus the non-reading client; 100 cached reads have p95 latency 90.8/162.0
ms. Cgroup/unit and aggregate-process counters are separately recorded. These
bounded changing-work windows do not certify long-term fleet-watcher cost.

The selected CLI is compared against independent native reads after cutover.
[Direct Snap](snap-selected-direct-native.json) checks 97 identities/runtime/phases,
97 update clocks and 60 non-empty latest turns with no issues. [Direct Starship](starship-selected-direct-native.json)
checks 384 identities/runtime/phases, 383 update clocks and 136 non-empty latest
turns; one update is explicitly a sampling race, with no stable mismatches. Four
ordinary running rows per host match native state. Missing title/activity/turn
metadata and the 46 older Starship unknown kinds remain explicit coverage limits.

[Cached Snap](snap-selected-native.json) reports one thread-update difference:
its accepted view was collected about 11 seconds before the independent live
sample of this working thread. The native update clock had advanced by 11 seconds.
That is an asynchronous cached observation with its original receipt, not a
same-sample equality claim; the direct comparison agrees. [Cached Starship](starship-selected-native.json)
reports no issues. Delivery time does not freshen the older observation. The
[CLI export receipt](read-cli-exports.json) verifies selected API/service/Mesh
descriptors, all four schema commands and the three human timing columns.

The [source checks](source-checks.json) pass all 397 tests without skips and
149 Markdown/link/whitespace checks, including the new isolated-render regression.
The full managed dotfiles check also passes with the selected tuple.
 No physical-suspend or post-TUI-closure lifetime
claim is added. Memory remains a review threshold, not the former 64 MiB limit.

## C6: producer handoff

The [API 3 read-client handoff](../../api-v3-client-handoff.md) supplies exact
version/profile ownership, schema/descriptor commands, cached pull/push entry
points, identity/state/filter semantics and native clock/receipt limits.
Source-sampled remote age is distinguished from a continuously advancing remote
timer. Exact blocked/current-phase age and native occurrence replay remain absent.
RLCD/349 independently accept roster, device-feed, clock presentation and physical
rendering. Those consumer gates are not producer rollout or frontend work here.

Operational receipts are now copied into this repository rather than relying
on temporary directories. Private baselines retain exact rollback bytes outside
repository evidence. Source/native/installed/managed and publication evidence
remain distinct; this pass does not push repositories or publish releases.

# Claude interactive Observer acceptance

Date: 2026-10-08. I1–I3 of the
[interactive reconciliation](../../claude-interactive-observation-plan.md)
are accepted within the user's native-registration assumption. I4 operational
selection is pending at this checkpoint. Provider settings, frontend work and
attachment/actions have separate gates.

## Artifact and contract

The [a9 manifest](../../../artifacts/observer-0.5.0a9.json) binds source
`5f69c0e6adbb485a2176651cdf001bb791ac4188`, wheel SHA-256
`d72cb6c360b35b42e96de2b56d0f85d909823ebb74a5abb1a4438809e6c04ef0`
and prefix `~/.local/share/agent-observer/0.5.0a9-d72cb6c360b35b42`.
API 2, snapshot/watch 4 and service protocol 2 are unchanged. Snap installs the
source-only Claude-history SDK profile; Starship installs core. Exact installed
wheel bytes, descriptors, schemas and entrypoints pass the passive artifact
verifier. The normal writer remains separately selected at a16.

The native Claude executable is package `claude-code 2.1.294-1`, SHA-256
`27122ca7b624f537546fbef35b80c66370d974ff258f3d9b10ac50bb8771f262`.
This is proof provenance, not a provider version/hash support allowlist.

The adapter owns registration/incarnation interpretation and a bounded positive
saved-UUID catalog on each runtime pass. The generic engine receives normalized
snapshots and retains independent runtime/history leases. No terminal, window,
client inventory, generic process discovery, provider roster command or provider
action supplies observation. Full background lifecycle and private attachment
fields are removed. Native jobs only veto unsafe negatives.

## Native and installed evidence

The independent [oracle](../../../scripts/evaluate-observation) imports no
Observer implementation. Ordinary samples bracket installed public CLI reads
with native-before/native-after metadata. The
[private sample contract](../../claude-private-sample-contract.md) fixes the
adapter/engine boundary independently of this oracle.

| Evidence | Accepted result | Bound |
| --- | --- | --- |
| [On/off transitions](native-on-off.json) | 11 cases per mode: New/waiting, question, normal exit, saved Resume, approval, forced kill, Resume with a dead old record, final exit, registry fault/recovery, Observer cold start | Every case agrees across independent native evidence, installed direct reads, cached pulls and pushed views; all hooks disabled |
| [UUID/duplicate probes](native-extra.json) | `/clear` changes UUID within the same process; old UUID parked/new running. Two authenticated interactive incarnations with one UUID remain running; conflicting waiting/question phases become unknown; both killed becomes parked | Agent View on/off; installed direct/native comparison |
| [Background conflict guard](native-background-guard.json) | Owned native working/blocked background job reports unsupported unknown runtime/phase rather than parked | Explicit isolated operator probe; no background lifecycle/attachment support accepted |
| [Ordinary Snap Claude](ordinary-snap-claude.json) | All 35 UUIDs, all six running contexts, runtime/phase and 33 known conversation clocks agree in two rounds | One known metadata-only cwd gap below; two old unsupported background histories remain unknown |
| [Ordinary Snap cache](ordinary-snap-cache.json) | Same Claude result plus all 89 Codex rows through the explicit installed candidate service | Shared cached view, independent native brackets, two rounds |
| [Ordinary push client](ordinary-push.json) | First-party watch receives monotonic frames and working/waiting running contexts | Three frames; sampled delivery, not lossless native events |
| [Snap Codex](ordinary-snap-codex.json) | All 89 rows and two running contexts agree; no issues | Passive direct/native sample |
| [Starship Codex](ordinary-starship-codex.json) | All 354 rows and six running contexts agree; no issues | Passive direct/native sample; 21 old kinds remain unknown |
| [Preservation](preservation.json) / [cleanup](native-cleanup.json) | Ordinary settings/executable unchanged; all six original Claude births/registrations remain live; owned namespace stopped and borrowed auth/history removed | No ordinary provider actions |

The transition [harness](../../../scripts/native-claude-interactive-acceptance)
and [extra probes](../../../scripts/native-claude-interactive-extra) use verified
owned user/mount/PID namespaces, private copied executable bytes, masked ordinary
stores and disposable workspaces. PTYs operate only owned proof sessions; their
output is discarded. Receipts retain UUIDs, finite states/clocks and provenance,
never conversations, tool output or credentials. The background guard probe
launches an owned background question solely to prove exclusion; namespace
cleanup stops its private daemon/workers.

## Limits and practical effects

- **Native registration remains an assumption.** A live interactive session
  whose registration failed or disappeared can be missed or falsely parked,
  including after readable recovery/restart. The independently reproduced
  [I0 counterexample](../2026-10-08-claude-interactive-source/REPORT.md) still applies.
  Runtime coverage is partial with `interactive_registration_assumed`; source
  limitations explicitly declare interactive-only and unregistered-runtime
  bounds. Detected faults invalidate affected negative assertions.
- **Two old background histories stay unknown.** `recap-2026-report` and
  `recap-2026-f2` retain stopped native job records without pending-work counts.
  The minimal guard cannot prove those records quiet. No legacy projection is
  restored. Ordinary interactive running evidence still wins when present;
  background continuation and attachment remain unsupported.
- **One metadata-only cwd remains missing.** Setup-only UUID
  `e0cba9dd-b642-4730-af4b-beb3b7e9c16c` now appears with positive saved identity
  and scoped parked runtime. Its SDK-excluded metadata has native cwd
  `/home/bryan/code`, while Observer returns null. Its conversation age and kind
  remain unknown. The evaluator records this stable cwd mismatch; complete
  metadata parity is not claimed. Normal conversation rows match.
- Generic dialogs and unrecognized/future status clocks keep running known and
  phase unknown. Native child history exclusions and Claude turn outcomes
  remain unsupported. Hazardous PID reuse/foreign domain/ownership/torn-file
  variants use synthetic evidence; native forced kill, duplicates and recovery
  are independently proved.
- Cached pull and push distribute the same sampled state. Gaps, warming, source
  expiry and service incarnation changes remain explicit. A liveness refresh
  does not advance conversation age or renew a missing history fact.

I2 passes 383 synthetic tests (one skip), Markdown/local-link and diff checks.
The removed tests asserted obsolete background lifecycle/attachment behavior;
replacement tests cover interactive lifecycle, provenance, conflict guards,
runtime-only saved discovery and short runtime leases independent of history.
Native acceptance above is separate from those source checks and from I4.

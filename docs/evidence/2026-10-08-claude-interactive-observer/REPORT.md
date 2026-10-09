# Claude interactive Observer acceptance

Dates: native acceptance 2026-10-08; operational acceptance 2026-10-09. I1–I4 of the
[interactive reconciliation](../../claude-interactive-observation-plan.md)
are accepted within the user's native-registration assumption. Normal read CLI
and service select a9 on Snap and Starship. I5 provider-policy rollout is deferred;
the [read-client handoff](../../api-v2-client-handoff.md) is current. Provider
settings, frontend work and attachment/actions retain separate gates.

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
| [Selected Snap cache](selected-snap-cache.json) / [Starship cache](selected-starship-cache.json) | Normal selected CLI/socket match the six Claude and two Snap/six Starship Codex active contexts; all comparable state/age facts agree | Same setup-only cwd gap; one additional stale unsaved Claude row in the service, qualified below |
| [Preservation](preservation.json) / [cleanup](native-cleanup.json) | Ordinary settings/executable unchanged; all six original Claude births/registrations remain live; owned namespace stopped and borrowed auth/history removed | No ordinary provider actions |

The transition [harness](../../../scripts/native-claude-interactive-acceptance)
and [extra probes](../../../scripts/native-claude-interactive-extra) use verified
owned user/mount/PID namespaces, private copied executable bytes, masked ordinary
stores and disposable workspaces. PTYs operate only owned proof sessions; their
output is discarded. Receipts retain UUIDs, finite states/clocks and provenance,
never conversations, tool output or credentials. The background guard probe
launches an owned background question solely to prove exclusion; namespace
cleanup stops its private daemon/workers.

## Operational selection

Managed source changes only the read/service tuple and its operations note:
Snap chezmoi commit `fb6f8b5`, Starship scoped commit `9de3ecc`. The remote branch
was already divergent; its scoped commit preserves that branch and unrelated
Kitty drift. The six-target operator verifies artifact bytes, rendered unit and
links before apply. Writer a16, workspace mapping, frontend selections, provider
settings and ordinary sessions remain unchanged.

| Evidence | Result |
| --- | --- |
| [Snap selection](managed-selection-snap.json) and final [Snap](managed-final-snap.json) / [Starship](managed-final-starship.json) verification | Immutable a9 read/service selected; owning user unit enabled/active; native hints enabled; no provider actions or frontend targets |
| [Snap recovery](managed-recovery-snap.json) / [Starship recovery](managed-recovery-starship.json) | Unit restart and forced publisher failure each end the old watch; fresh reconnect starts sequence 1 with a new service incarnation |
| [Snap rollback](managed-rollback-snap.json) / [reselection](managed-reselection-snap.json) | Six targets restore a8, then verified a9 reselection succeeds; source tuple stays a9 throughout rollback |
| [Snap readers](managed-readers-snap.json) / [Starship readers](managed-readers-starship.json) | 180 seconds per existing managed unit, 100 cached reads, three independent healthy watchers and an unread subscriber; no watcher gaps/errors; leases/provenance accepted |

Starship rollback/reselection also passed the scoped operator during this pass;
its rollback snapshot remains
`~/.local/state/agent-observer/rollback/20261009-a9-starship/snapshot.json`.
Snap's snapshot is at the equivalent `20261009-a9-snap` path. Final receipts
independently verify selected a9 bytes/units after both rollback exercises.

Snap runtime/history cadence is 30/120 seconds; Starship is 20/60. The reader
soak measured cached CLI p95 about 95 ms on Snap and 157 ms on Starship. Peak
aggregate publisher/helper RSS was about 115/74 MiB respectively; summed RSS
counts shared pages and differs from unit memory accounting. These are bounded
three-minute operational samples, not long-term memory or physical wake proof.
Forced kills without a native file event use periodic runtime reconciliation
plus bounded collection time; pushed views are sampled, not lossless native events.

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
- **The service can retain a disappeared unsaved row as stale unknown.** The
  selected cache contains UUID `4359adf3-32f1-49fb-ab95-cc780bfe68de` with
  `hasSavedHistory=false`, `retained_after_gap`, original sample clocks and
  last-known running/working values. Current independent native checks find no
  matching registration or root transcript, and a direct installed read omits
  it. The [retention receipt](selected-retention-limit.json) verifies the current
  difference; it does not reconstruct independent proof of the earlier runtime.
  Claude's permanently partial coverage uses the engine's existing conservative
  retention rule. Row/byte limits bound storage, without time eviction. This
  stale row does not count as active or parked; cached/direct membership equality
  is not claimed for retained gaps. Consumer presentation must preserve that
  distinction. No service restart or native deletion is used to hide it.
- Generic dialogs and unrecognized/future status clocks keep running known and
  phase unknown. Native child history exclusions and Claude turn outcomes
  remain unsupported. Hazardous PID reuse/foreign domain/ownership/torn-file
  variants use synthetic evidence; native forced kill, duplicates and recovery
  are independently proved.
- Cached pull and push distribute the same sampled state. Gaps, warming, source
  expiry and service incarnation changes remain explicit. A liveness refresh
  does not advance conversation age or renew a missing history fact.

I2 passes 383 tests (one skip), Markdown/local-link and diff checks.
The removed tests asserted obsolete background lifecycle/attachment behavior;
replacement tests cover interactive lifecycle, provenance, conflict guards,
runtime-only saved discovery and short runtime leases independent of history.
Native acceptance above is separate from source checks and I4 operations.

# Claude private observation sample

I1 implementation boundary, 2026-10-08. The public fit remains
[API 2 / wire 4 / service 2](claude-read-contract-review.md). This document
describes an adapter interface, not additional public fields or provider APIs.

The Claude adapter owns the interpretation of native registrations. Each
runtime collection reads a bounded positive saved-UUID catalog directly from
owned root transcripts, then brackets the native registry and a minimal
background conflict guard. The catalog accepts exact filename/payload UUID
agreement; catalog absence supplies no lifecycle assertion. It need not run the
history SDK and does not carry conversation content into the engine.

The native sample contains one row per exact UUID, with independent work and
presence evidence, optional explicit runtime disposition, positive saved
identity, allowlisted title/cwd, and bounded issue codes. Live interactive
incarnations authenticate running. Healthy scoped negatives authenticate
parked only for positively saved UUIDs, under the registration assumption.
Dead old records do not compete with resumed live incarnations. Multiple live
incarnations establish running; conflicting work evidence remains unknown.

Registry scan failure invalidates negative assertions. Detected per-UUID
domain/birth/image ambiguity invalidates that UUID's negative. Unstable
registration brackets invalidate their positive samples too. Valid positives
survive unrelated malformed files. The background guard reads only enough
native job metadata to veto a negative when work is pending or unclear. It
never supplies a supported job lifecycle, phase, saved identity or attachment.

The collector projects this sample into the existing shared passive snapshot.
The engine consumes only that validated snapshot and retains separate short
runtime and longer history leases. Each runtime pass includes positively saved
UUIDs, so cold starts and worker exit can refresh lifecycle without waiting for
the history SDK. Missing or timed-out reads cannot refresh retained facts.
History independently enriches title, kind, activity and creation time.

Implementation bounds are explicit: at most 256 projects, 8,192 transcript
directory entries, 4,096 candidate UUIDs, a two-second catalog deadline and
64 KiB head/tail windows per transcript; at most 256 registry records, 256 KiB
per registry file and 4 MiB total; at most 128 job guard records, 4 MiB per file
and 24 MiB total. All filesystem readers reject unowned, symlinked, special,
unstable or malformed inputs. Truncation preserves positives and grants no
negative catalog authority.

The independent `scripts/evaluate-observation` oracle reads native metadata
without importing adapter, model or engine code. Its expectations use the
same documented assumption, independently implement ownership/incarnation and
guard checks, and compare native-before / public-CLI / native-after samples.
Synthetic tests establish oracle decisions. The subsequent
[a9 report](evidence/2026-10-08-claude-interactive-observer/REPORT.md) accepts
installed native I3 and scoped operational I4 separately from these decisions.

The accepted invisible-registration limitation remains: a live interactive
session whose native registration failed or disappeared can be missed or
falsely parked after a healthy scan. Partial coverage and explicit source
limitations carry that scope. There is no client inventory, hook ledger, generic
process discovery, provider action or frontend dependency in this interface.

# Codex home profiles: implementation and live evidence

Status: first increment selected on Snap and Starship, 2026-10-19. This report
records bounded source, consumer, native, lifecycle, managed and device
readback evidence. It does not accept new provider or wire contracts.

## Implementation and selected tuple

Observer source revision `54caeb0b27d16d6295ca161ef5b294a8ccf7df39` adds the
private named-home configuration and resolved route listing. It was built on
the accepted public lease source `1eec6c6d8681a3e58bab742d5c130656ab00433c`.
Mesh source stayed unchanged at
`2fb502da35c0ef9865762c4dc4b486dd30b7e316`. No API 4 body, native schema,
Mesh SDK, receipt, clock or wire contract changed.

The manifest explicitly configures `default` (`/home/bryan/.codex`) and `work`
(`/home/bryan/.codex-work`) on Snap; Starship configures only `default`. Both
feeds retain the same real host identity and have distinct home namespaces.
Configuration presence enables a profile; no filter selects all configured
profiles, while startup/CLI filters select exact IDs. Labels affect presentation
only. Existing 72-hour active-plus-recent selection is unchanged. The dashboard
continues to display its loaded-user policy and does not add parked rows.

The existing installed pair remains Observer wheel
`a3983afc12cee4aec84dd53d2ec9e60edd1e97dd4250543d77344bcde0878ac5` and Mesh
wheel `4f5987191b8d1113f3aa0afced15c5179f458fa0f9b9044352f1fefd418736bd`.
The profile helper is additive source; no new Python wheel was released. Managed
selection uses consumer source
`355993dbe5142b01d88fb4cee81ea6bf45503a83`, bundle
`.local/share/rlcd-agent-dashboard/1088a0631ef45cdb`, manifest SHA-256
`1088a0631ef45cdb9e6acb6a02becac6b9b12fc085c147873d199a2dacef47f6`, and
wire 3 on both hosts. Ops source at this checkpoint is
`3ac17c0`; it adds the documentation/checker checkpoint and a physical-home
startup guard without changing dashboard selection since `d77fd6d`.

The exact former profile-less bundle `1ad6ef316f2aba74` remains the managed
rollback selection for both hosts with the original firmware candidate and
backup evidence. Rollback was not executed. The private evidence hashes and
captured canonical frame sizes are in the metadata-only
[checkpoint](checkpoint.json); raw native frames and conversation content are
not checked into this repository.

## Native and public-read comparisons

The independent evaluator used `--codex-home` for both the native reference and
Observer identity scope. Its default remains `~/.codex`; the work comparison
explicitly used `~/.codex-work`.

| Host/profile | Native comparison | Public Observer result |
| --- | --- | --- |
| Snap / Default | Empty: 0 rows before and after | Current, complete empty; 0 rows |
| Snap / Work | One loaded user session, `yearly-recap-review`, running and waiting | Current; exact native identity and runtime/phase comparison matched; one row |
| Starship / Default | 401 rows; 7 running (5 user, 2 child) | 401 rows; identity/runtime/phase parity for the seven running references |

Two Starship `lastUpdated` values differed across the evaluator's bracketed
samples, consistent with sampling cadence. Other unproved native fields remain
unknown. The actual all-profile dashboard view contained six loaded user rows:
five from Starship Default and one Snap Work row. Default-only filtering returned
five; Work-only filtering returned one. The Work label did not enter native row
identity. Canonical native frame sizes including LF were 27,678 bytes for
Starship Default, 2,339 bytes for Snap Default and 4,995 bytes for Snap Work.

The final readback later contained four loaded user rows: three Starship
Default and one Snap Work. A fresh independent native comparison matched
Starship's then-current 400-row inventory and four running references (three
user, one child), plus the same one Work user. Normal session transitions are
not treated as a fixed six-row requirement; all three profile feeds remained
current. The two remaining `lastUpdated` differences were 1 and 5 seconds.

Public two-route fixtures used the existing `ServiceState`/`Runtime`, cached
working-set sources, publisher, IPC, Reader and prepared facade. They proved
same-host/same-native-UUID rows remain distinct by configured namespace, with
complete reads and independent proofs. Consumer `ProfileFleet` expected-home
binding rejected a valid frame from the wrong configured home while preserving
the correctly bound sibling. Empty, close, expiry and partial-source behavior
remained scoped to the affected profile. The base consumer row DTOs and projector
contracts stayed unchanged.

## Managed lifecycle and device readback

Source/managed renders and scoped dry runs passed before starting the extra
collector. The two configured homes were explicit. The target-host physical-alias
helper check was completed later, after the extra collector had started but
before dashboard selection; it is not evidence that the live pre-start path ran
that helper before the first unit start. Initial SSH-quoting/standalone-import
setup attempts were corrected using the installed parent-package context; these
were harness setup issues, not production failures. Final namespace and native
readbacks passed before dashboard selection.
The final Work unit also rejects a home physically equal to Default before
each collector start. A collector-only restart exercised that pre-start guard
while leaving its publisher and both Default collectors running.

Three Work stop/start cycles were recorded. The two default feeds stayed current
while Work sockets were absent during stop. Default collector/publisher PIDs and
all three independently sampled native daemon PID/start-time/executable
identities stayed unchanged; no native daemon restart occurred.

With Work unavailable, Snap source health became partial while the combined
device view retained six rows (three waiting, two working and one uncertain).
On recovery it returned to current with six rows (four waiting, two working,
zero uncertain). Both Snap and Starship device logs recorded source-admitted
six-row ACKs with health 0 and no missed frames. Firmware was not changed. These
results do not include manual visual inspection or reboot acceptance.

## Validation and bounds

The final Observer gate passed 1,178 tests and 258 Markdown file checks. It
includes the explicit-home evaluator and independent child/system inventory
filter correction. The consumer final gate passed 89 tests; its documentation
check covered 65 files and 398 local links/anchors.
Managed source and installed-artifact checks passed for the new bundle and exact
rollback pair. No Git push or package release was performed.

The 30-second cgroup screen measured aggregate `MemoryCurrent` maximum from
93,757,440 to 139,653,120 bytes. The added Work collector/publisher pair peaked
at 46,653,440 bytes (46.7 MB decimal). Aggregate CPU accounting changed from
3.376% to 6.048% of one core during those windows. These are descriptive
process readings, not RSS, a causal performance comparison or capacity claim.

Delta sync remains dark. No daemon autostart, history/private-database
inference, profile guessing, firmware flash, new device control or native
session action was part of this increment. Existing per-profile leases,
completeness and expiry meanings remain independent.

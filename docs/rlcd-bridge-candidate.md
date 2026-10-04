# RLCD bridge projection candidate

This file and examples/rlcd_bridge.py define a provisional, host-side
presentation projection for one Agent Observer schema-v1 JSON document. This
is a fixture-tested consumer candidate only. It does not establish an RLCD
firmware protocol, device transport, live display, or physical acceptance.

Run it by piping one snapshot document to stdin:

    python examples/rlcd_bridge.py --limit 6 < snapshot.json

The bridge reads at most 512 KiB, accepts at most 8,192 session rows, and
rejects duplicate object keys, nonfinite numbers, excess nesting, and malformed
identity/provenance. It emits one bounded JSON frame, with six rows by default
and a hard limit of 24. Invalid input produces a finite error frame that does
not echo input bytes, strings, exception details, or provider payloads.

The module imports only Python standard-library components. It consumes no
provider command, Observer/Agent Plus module, filesystem metadata, credential,
or persistent state. It reads stdin and writes stdout; it defines no action,
resume, focus, approval, stop, firmware, or device-transport interface.

Each displayed session carries the complete host/provider/namespace/native-ID
key in identity. displayId is a short deterministic digest of that full key
for presentation. It is never an identity or an operation target. Exact
duplicate keys remain separate rows and are marked ambiguous with unknown work
and presence. Equal native IDs in different namespaces stay distinct and gain
a finite namespace-collision issue.
The host scope is caller-selected provenance, not machine attestation.

Work and presence retain independent values, health, sources, reasons, and
original Unix-millisecond observedAt clocks. A non-current work fact is
rendered as unknown, while its original clock and health remain visible.
Missing facts become unavailable/unknown with a null clock. Current presence
can set liveSelected; it never changes the work value, health, or timestamp.
Codex server_thread_loaded and Claude os_worker presence meanings remain
distinct. Attachment is not inferred. Source configHomeKind is retained only
as the finite default/explicit/unknown category; configuration paths are
filtered.

Current-presence rows take priority so saved history cannot displace live
work from the bounded display. Within each group, rows sort by current work
attention (needs_input, then error/interrupted, working, unknown, and settled),
then descending explicit work time or native history time and the complete key. Presence timestamps
are never used for chronology. The bridge displays only a bounded title,
finite evidence codes, coverage, counts, and the full identity; it drops cwd,
runtime/config paths, native job IDs, prompts, responses, tool content, raw
payloads, and unknown metadata.

With zero current-presence rows, the frame says no_live_sessions only when
both Codex loaded inventory and Claude registry/job/worker-presence coverage
are current and complete. A single-provider, failed, stale, ambiguous, or incomplete empty feed says
partial_or_unknown. Rows from a healthy provider remain visible when the
other provider fails, with feedHealth: partial and finite source errors. A
row with unknown or non-current work/presence also makes feedHealth partial;
liveInventory separately reports whether source inventory coverage is
complete.

The tests in tests/test_rlcd_bridge.py exercise only synthetic documents.
They validate the projection and its uncertainty rules; they do not test
firmware, a device protocol, live transport, or physical hardware.

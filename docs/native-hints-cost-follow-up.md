# Native hints: remaining producer cost gate

Date: 2026-10-07. The [delivery report](evidence/2026-10-07-native-delivery/REPORT.md)
records separately installed a9; normal Snap/Starship units select a8 polling.
This follow-up does not authorize provider-policy changes or frontend work.

The [subsequent a10 repair](evidence/2026-10-07-native-delivery/a10-catalog-scope.json)
removes unnecessary scans from nested transcript traffic. Identical installed
synthetic activity causes two extra history reads in a9 and zero in a10; primary
append and a focused native Claude workflow still pass. A10 is separately
installed on both hosts, without a repeated cost/operational gate or selection.
The remaining sequence below still applies; the a9 CPU/RSS numbers are not
silently reassigned to a10. Original targets remain pending explicit clarification.

## Evidence and decision

Controlled native wakeups improve runtime and conversation-age latency without
loading a saved session to observe it. Source loss/reconnect, daemon incarnation
changes, foreground questions and paired passive-listener retirement pass within
the recorded topologies. API 1, snapshot/watch 3, write 1 and service protocol 1
remain unchanged. These cases do not clear the resource gate.

Two sequential five-minute ordinary-store runs per host compare polling with
hints at the same configured cadences and reader count. Snap measured 4.13 versus
6.30 percent of one core, with peak aggregate RSS 124.9 versus 167.2 MiB. Starship
measured 2.00 versus 2.05 percent, with RSS 45.6 versus 67.6 MiB. Actual ordinary
traffic differed; Snap performed three versus eight Claude history jobs. The
observed CPU delta is not an equivalent-workload causal estimate. Both hinted
runs exceed the plan's provisional **aggregate** 64 MiB RSS target; the Snap
polling baseline already exceeds it. Incremental RSS was 42.4/22.0 MiB, which
must not silently replace that aggregate target. Harness `status=accepted` means
the measurement completed, not that this delivery gate passed.

One suppressed-output cProfile scan spent 0.946 of 1.114 seconds in SDK imports,
loading client/MCP/model machinery before read-only history projection. This is
a useful lead, not proof that bypassing SDK initialization is safe. A bespoke
loader under a private package alias would add SDK coupling merely to save
startup cost; none was introduced. Raw history was never archived.

## Next bounded producer pass

1. **Establish equivalent measurements.** Use owned isolated native stores and
   identical scripted activity, history population and readers. Compare quiet
   startup/steady state separately from active runtime/history workloads. Include
   per-process CPU/RSS, live and reaped descendants, total authoritative reads,
   FD/process/inotify watch counts and hard collection deadlines. Ordinary-store
   acceptance supplements this controlled comparison rather than replacing it.
2. **Reduce demonstrated cost.** Profile runtime and history jobs independently.
   First consider supported metadata-only SDK entry or a bounded reusable
   read-only metadata worker, retaining audit guard, deadline, incarnation,
   output limits and publisher-death cleanup. Compare that complexity with an
   explicit larger aggregate budget. Do not add transcript caches, legacy
   reconstruction or unofficial SDK-loading shims without a separate design and
   evidence. Provider versions remain diagnostics; the reproducible SDK lock is
   an Observer dependency, not a provider compatibility allowlist.
3. **Settle the budget explicitly.** Preserve the original one-point incremental
   CPU and 64 MiB aggregate RSS results. Any revised budget is a visible design
   decision with absolute and incremental values, not retroactive acceptance.
   If the original budget is retained, meet it with a separately frozen candidate.
4. **Reaccept the candidate.** Run schema/reference consumers, controlled burst/
   loss/backoff/fairness, independent native ID/state/activity/title comparisons,
   foreground/background Claude and Codex on both hosts, saved unloaded rename,
   paired lifetime and periodic fallback. Measure correlated event arrival
   separately; source-level latest-hint/sample differences do not prove it.
5. **Complete P6.** Only after the gate passes, add the exact managed hint flags,
   verify old/new tuples, apply Snap then Starship, and exercise restart/crash/
   rollback/reselection plus a 30-minute multi-reader soak per host. Refresh
   preservation bookends and remove all owned native stores/authentication.

No frontend migration is needed to investigate this cost. Agent Plus and other
clients can independently consume selected a8's accepted read/write boundaries
and explicit cached service. Native entry repair, graphical focus, remote/device
transport, durable notifications and physical suspend/wake keep their own gates.

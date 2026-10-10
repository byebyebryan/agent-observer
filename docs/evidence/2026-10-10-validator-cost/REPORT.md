# Pure text validation cost

Source-only compatible refinement after the Mesh a9 delivery rollout. Ordinary
collector a15, reader a13, bridge a12 and writer a16 selections are unchanged.

Repeated cached-frame validation spends measurable time checking Unicode
categories one character at a time. For ASCII strings, category C is precisely
the control range U+0000–U+001F plus U+007F. The pure contract validator now uses
one compiled regex scan for that range. Non-ASCII input retains the original
Unicode-category predicate. Length, pattern, enum, type and shape checks remain
unchanged; no validation is cached or skipped and no receipts are renewed.

The classification calls `str.isascii(value)` directly so a string subclass
cannot spoof the branch. Regressions cover all 128 ASCII characters, printable
Unicode, combining characters, C1 controls, format/private-use/surrogate/unassigned
categories, length bounds and a spoofed string subclass. Snapshot/watch schema
documents remain identical to the pre-change source.

A private cached 128-row snapshot was validated 100 times per variant in ABBA
order. Process CPU was 1477.650 / 1485.161 ms before and 1026.594 / 1012.475 ms
after: 31.2% less CPU for this pure validation task. This is not collector cost,
whole Reader savings, live fleet latency or installed artifact acceptance.
The input records stay private. Input, implementation and harness digests are
recorded in the sibling Mesh operational-hardening evidence.

The standard source gate passes 448 tests with four explicit optional
SDK/jsonschema skips. The Mesh a9/jsonschema-enabled source gate also passes all
448 tests with no skips, independently of the ordinary environment.
Producer/runtime truth, a new packaged artifact and consumer/deployment
selection remain separate gates; this source change deploys no provider policy.

The next package candidate is 0.5.0a16. Its archive verifier explicitly admits
the reviewed Mesh a10 candidate while still rejecting duplicate manifests and
unreviewed a11. Exact wheel/import/metadata acceptance precedes selection of
new private reader and bridge environments. Ordinary collector a15 and writer
a16 remain independently pinned; this does not select the new collector code.

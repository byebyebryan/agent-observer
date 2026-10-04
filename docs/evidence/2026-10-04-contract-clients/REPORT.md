# Independent contract/client acceptance

Date: 2026-10-04. G1 and G2 accepted for the bounded matrix below, before any
Agent Plus implementation. G3 networking remains deferred. Source, fixture,
installed package and native evidence are distinct.

## Artifact and checks

- Source checkpoint: `222c5bf`; version `0.2.0a3`.
- Wheel SHA-256: `6aa793e6a0ba5ae37403f73999ea6e6d56bc8c21e5e4c7a10ac52cb946a45a3f`.
- Unselected prefix on both hosts:
  `/home/bryan/.local/share/agent-observer/0.2.0a3-6aa793e6a0ba5ae3`.
- Public snapshot/watch schema version 2; write request/plan/result version 1.
- Source: 153 tests, scoped Ruff and repository documentation checks pass.
- Installed public read/write CLIs ran outside the checkout with checkout imports
  removed. An independent Draft 2020-12 validator accepted the bundled schemas
  and canonical public read/write fixtures. Fixture list/watch passed.
- Snap has the optional source-built `claude-agent-sdk==0.2.163`, with no bundled
  executable. Starship is core-only; no Claude or SDK installation was added.
- Snap ordinary passive read returned both current sources, complete loaded
  Codex thread and registered Claude worker inventories, and partial Claude
  saved metadata coverage. Starship's ordinary Codex read passed separately.

[Packaged evidence](packaged-final.json) records the final installed candidate,
dependency boundary and Snap read coverage. Current source health does not
imply complete saved coverage or all execution contexts.

## Native matrix

| Host/provider | Enabled route or fact | Acceptance |
| --- | --- | --- |
| Snap/Codex 0.160.0 | New, exact Resume, separate thread/session IDs | Final installed public write CLI and native TTY entry pass |
| Starship/Codex 0.160.0 | New, exact Resume | Same final artifact and public CLI pass |
| Snap/Claude 2.1.287 | New background context, exact live attach | Final public CLI resolves full session identity and uses the typed native job |
| Snap/Claude 2.1.287 | Exact saved-history Resume | History-only private fixture passes; requested UUID is preserved and returned UUID independently verified |
| Snap/Claude 2.1.287 | Completed background context with current worker | Waiting, completed outcome and independent native/sample clocks verified |
| Snap/Claude 2.1.287 | Completed context accepts another prompt | Focused installed proof verifies a subsequent user/assistant turn under the exact UUID |

Native executable fingerprints are pinned to Codex SHA-256
`12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad` and Claude
SHA-256 `3920489a5109cff5786a1a392c25277408ff22bc796d5edb9c16a60e5a1718f0`.
Metadata reports: [Snap final routes](native-snap-final-result.json),
[Starship final routes](native-starship-final-result.json),
[Claude saved route](native-claude-saved-final-result.json) and
[focused readiness](native-claude-readiness-result.json).

The focused readiness proof preceded the final mapping artifact; the final
Snap proof then checked its public waiting projection. The brief second working
transition was not sampled. Only exact-record verification booleans are retained;
no conversation contents are repository evidence.

Claude used an operator-created **private trusted-workspace fixture**. These
tests do not claim trust-dialog or graphical UX acceptance. The write client
does not write trust or approve a prompt; its exact trust-required predicate is
covered by controlled tests. Native saved resume returned the original UUID;
copied UUID handling has controlled coverage but was not forced natively. A
retained live worker selects attach; ambiguous retained provenance remains
rejected. Offline Codex discovery, parked absence, general questions, foreground
Claude readiness, activity timestamps, client binding and lossless native events
remain unsupported or pending as the public contract specifies.

## Isolation, cleanup and selection

Before launch, private user/PID/mount namespaces, private `/tmp`, provider roots,
workspace and endpoints were established. Ordinary provider paths were masked.
Only required credentials/account metadata were copied into owned private stores.
Native descendants exited with the private namespace; private stores and borrowed
credential copies were removed. Final candidates remain installed but unselected.
The prior `0.1.0a5-b68ebf4cefbd8b58` Observer link remains selected on both hosts.
No current coordinator reopen, ordinary hook change or pilot cutover occurred.

[Snap cleanup](cleanup-snap.json) and [Starship cleanup](cleanup-starship.json)
record the ownership and preservation checks. Ordinary auth, Codex config and
Claude settings hashes were unchanged. Snap's ordinary global `.claude.json`
hash changed during the long test window; it contained no proof path or proof
project entry. Attribution is unproved and that unrelated live drift was left
intact. The private native launches masked that path, and the SDK history helper
blocks filesystem writes and process spawning. The evidence does **not** claim
that every ordinary file stayed byte-identical.

G2 establishes independent local usability for this exact artifact/provider
matrix. Desktop focus/appearance, physical suspend, production selection,
coordinator reopen and public release remain separate gates. Agent Plus can now
begin its own consumer pass against this pinned artifact and existing external
Host Mesh routing.

# Operational resilience producer acceptance

Date: 2026-10-05. The [execution plan](../../operational-resilience-execution-plan.md)
and [bounded evidence](acceptance.json) describe this separate Observer checkpoint.
Agent Plus implementation remains a downstream pass.

## Independent artifact gate

Observer `0.2.0a8`, source `ece20e2`, wheel SHA-256
`8bbbff345b58c0517e2ca69bc9caa2157d01c59c82c087af7b06dc17c4d90a8c`
passes the producer gate independently of a frontend. Installed wheel bytes,
entrypoints, public schemas and executable version match on Snap and Starship.
Snap uses source-built Claude SDK `0.2.163` without a bundled executable;
Starship uses the core-only profile. Source checks pass 176 tests and scoped Ruff.

| Provider and topology | Exact native artifact | Accepted cases |
| --- | --- | --- |
| Codex managed daemon, Snap and Starship | 0.160.0, manifest hash | New, exact saved/live Resume, repeated real PTY entry, last-turn metadata activity, reads/rename/housekeeping/resume preserve age, owned daemon failure visible, public New recovery followed by saved Resume, visible guard rejection before provider execution |
| Claude native BG workers, Snap | 2.1.289, manifest hash | New, exact attach and repeated PTY entry, working/completed-turn waiting and held permission approval, transcript-envelope activity, reads/rename/housekeeping/attach preserve age, healthy attach and saved Resume through missing sibling metadata, copied identity and first new prompt activity |
| Claude surviving old runtime with current viewer, Snap | Worker 2.1.287 `3920489a…`, viewer 2.1.289 `a186b99e…` | Inspect distinct exact executable images, discover old worker, current viewer attaches and completes a turn with the same session identity |
| Claude saved metadata, Snap | Pinned SDK 0.2.163 and current native transcript | Single conversation survives a controlled metadata-only companion, companion recency does not replace native title/activity, conflicting conversations remain ambiguous, restored source preserves age |

The mixed-version proof starts the old runtime under a private binary bind,
then detaches that bind to expose the current installed image. An old launcher
connected to a new daemon would create a new worker and is insufficient proof.
No ordinary package byte or process is changed. Native client startup is awaited
before proof input; the held-approval probe uses bracketed paste. Early fixture
attempts had startup/input and metadata-sampling races; only the completed
metadata-consistent cases above are accepted. No approval is answered and the
requested private tool action remains unexecuted.

All native actions used private user/mount/PID namespaces, provider stores,
authentication copies and endpoints. Terminal output and conversation bodies
were discarded. The companion case uses a native transcript with controlled
typed metadata and conflict injection; it does not establish a complete native
worktree lifecycle. Ordinary passive reads independently recover the two actual
worktree companion cases without modifying either file.

## Behavior and limits

Fresh saved discovery survives a failed live source. Unknown runtime evidence
does not become parked or waiting. Shared exact artifact registrations cover
observation and the separate writer; resident process images are inspected
independently of the replacement installed inode. Unregistered images and
version/digest mismatches remain unsupported. This is not version-range support.

The CLI version now comes from package metadata's single version source;
candidate verification checks the executable label too. Human rows show readable
conversation age, and text doctor reports finite errors and verified/accepted
runtime versions. Wire shapes remain snapshot/watch v2 and write v1, matching
all five schemas in the frozen Plus `0.14.0a1` / Observer reader `0.2.0a3` tuple.

One ordinary installed-candidate sample has 47 Snap Codex sessions with 34 clocks,
27 Snap Claude sessions with 27 clocks, and 90 Starship Codex sessions with 85
clocks. Both recovered Claude histories have their native title and clock.
Counts and runtime presence are samples, not a fixed inventory. Missing older
Codex clocks stay unknown. The saved metadata scan remains explicitly partial.

The held permission case uses native job `working`, tempo `blocked`, registry
`waiting` and exact permission metadata. Other native job `blocked` layouts remain
unproved; no generic mapping was added. Questions, foreground readiness, parked
inference, current viewer/thread binding, hooks and networking retain independent
gates. Codex runtime coverage is loaded daemon threads, not all terminal clients.
Process counts, launch argv and cwd cannot identify a client's current thread.
Offline Codex saved Resume still requires runtime recovery through explicit New.

Write preparation and execution retain exact executable, directory, settings,
selector, identity and execution-time guards. Prepared Codex Resume and Claude
attach correctly leave `resultingIdentity` null; their exact requested reference
is in the handoff. Plus wrapper association, silent launch, age presentation,
picker focus and graphical acceptance remain a separate consumer checkpoint.

## Delivery

The independent S2–S4 gate is closed for the subset above. Scoped producer
selection and exact owned-fixture cleanup are pending S5. The frozen Plus
package and reader are unchanged. No public push occurred.

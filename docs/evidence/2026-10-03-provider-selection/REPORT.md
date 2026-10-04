# Agent Plus host provider selection follow-up

Date: 2026-10-03. The user reported `starship/claude: runtime artifact
unavailable` in the installed picker. Starship has no Claude installation;
Agent Plus requested both providers on every Host Mesh host. The absence was
expected, but the consumer had no provider policy to express that topology.

## Change and installed artifact

Agent Plus now accepts optional `[host_providers]` entries keyed by existing
Host Mesh IDs. Unspecified hosts default to Codex and Claude. Both managed
pilot hosts select `starship = ["codex"]`; Snap retains both providers.
Discovery passes the selected providers to the public Observer CLI, and
validation requires only those source envelopes. Unrequested sources or rows
fail closed. Missing or unavailable enabled providers still produce errors.
No provider lifecycle, hooks, runtime flags, routes or sessions were changed.

The immutable, normalized policy participates in the cache fingerprint, so an
older discovery snapshot cannot retain the disabled-provider error. Claude
post-creation observation requests Claude alone. Synthetic coverage includes
Claude-only hosts, selected-provider transport failure, unavailable enabled
sources and malformed or unrequested wire data.

Agent Plus `0.13.0a2` is installed on Snap and Starship from wheel SHA-256
`b977504f2f778350713ff85a2babb7f55cdbbe6d32a084202312b89cfbe5d434`.
The independent prefix is
`~/.local/share/rofi-agent-plus/0.13.0a2-b977504f2f778350`.
All 21 installed Python/SVG files match the wheel on both hosts and the source
on Snap. Each host's three managed entry links and configuration were
scoped-applied and verified. Observer remains `0.1.0a3`.

The config template and candidate links preserve the prior configuration and
release targets on other managed hosts; Carbon's rendered config was checked
to contain only the original two settings. Published external pins and older
candidate prefixes remain intact. These artifacts remain unpublished.

## Validation and proof limits

The complete Agent Plus `./scripts/check` passed: 347 tests, Ruff checks and
formatting for 55 files, shell/text checks and released contract bundles.

Fresh installed `rofi-agent-plus refresh` completed successfully from both
host origins. Each returned zero global and per-host errors:

| Observed host | Codex rows | Claude rows | Source health |
| --- | --- | --- | --- |
| Starship | 90 | Not requested | Current |
| Snap | 48 | 5 | Current for both providers |

The [filtered installation and refresh record](installed-refresh.json)
retains artifact metadata, counts, health and refresh clocks only.
This follow-up establishes installed discovery and cache behavior. Earlier
`0.13.0a1` native New/Resume proofs remain dated evidence; those provider
actions were not repeated for this configuration follow-up. Visual picker,
focus and current-client binding acceptance remain pending or unsupported as
described in the [execution status](../../execution-status.md).

An already open picker can keep its old process/configuration; close and
reopen it to load the new candidate. No Codex or Claude session restart is
required for this fix.

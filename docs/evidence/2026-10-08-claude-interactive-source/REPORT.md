# Claude interactive native-source validation

Date: 2026-10-08. Scope: items 1 and 2 of the
[interactive reconciliation plan](../../claude-interactive-observation-plan.md),
before producer implementation, public-contract changes or provider rollout.
Snap runs `claude-code 2.1.294-1`; native executable SHA-256 is
`27122ca7b624f537546fbef35b80c66370d974ff258f3d9b10ac50bb8771f262`.
These are provenance, not a provider release/hash allowlist.

## Findings and decision

**Positive interactive observation works with Agent View on and off in the
tested native flows. Registry absence does not establish parked in general.**
The negative lifecycle part of I0 is not accepted. Keep the accepted a8 runtime
behavior until the parked design is revised; this validation does not select a
new artifact, change settings or accept API 3.

This was the original exhaustive-guarantee decision. The
[subsequent scoped design decision](#subsequent-design-decision) below records
the user's accepted registration assumption without changing these findings.

| Native case | Agent View on | Agent View off |
| --- | --- | --- |
| New interactive UUID registration before first assistant event | Authenticated | Authenticated |
| Waiting, working, held question and held approval status | Observed | Observed |
| Native `/exit` | Process exits; its registration removed; saved UUID retained | Same |
| Exact saved Resume | Same UUID, new incarnation; activity unchanged before another prompt | Same |
| Forced process exit | Dead incarnation record retained | Same |
| Resume after forced exit | New authenticated incarnation can coexist with stale old record | Same |
| Registration and question with every hook disabled | Observed | Observed |
| Failed registration followed by source recovery | Live usable session remains unregistered | Same |
| Native `agents --json --all` during that failure | JSON array omits the live UUID | Exit 1, no JSON array |

Provider-owned UUID registrations plus authenticated incarnation establish
positive running evidence. Supported status establishes phase without querying
clients, terminals or attachment. A PID number or registry filename alone does
not establish a live incarnation. Normal exit and crash have different cleanup
behavior, so parked cannot be reduced to file presence either.

### Counterexample to general parked inference

Both modes reproduced this controlled sequence:

1. Make only the private native session-registry path a regular file so the
   native registration write fails.
2. Launch an owned interactive session with an exact requested UUID. It remains
   alive and persists an assistant conversation event.
3. Restore the registry as a readable owned directory. Send another prompt;
   the same session persists another assistant event and remains alive.
4. Read native metadata: saved identity exists, the registry has zero records,
   and there are no job-state records. The running session does not re-register.
5. Run the roster CLI only inside this namespace. With Agent View on its JSON
   result also omits that live UUID; with Agent View off it provides no JSON roster.

Thus positive saved identity plus an empty readable registry can coexist with
an active interactive context. A fresh Observer reader after recovery has no
registration with which to discover or authenticate that context. Reader
restart, two stable directory scans, retaining a previously ended incarnation,
or enabling Agent View does not supply the missing completeness guarantee.
This is a deliberately induced source fault, not a demonstrated failure in the
user's ordinary sessions. Its effect can outlive the visibly failed source.

The inspected installed registration path catches a write failure and returns
failure without necessarily aborting the session. Its status-update path reads
an existing PID record rather than recreating a missing one. These static leads
agree with the native counterexample; they are not a new stable public provider
contract. The [documented JSON roster](https://code.claude.com/docs/en/agent-view#list-sessions-as-json)
and [Agent View opt-out](https://code.claude.com/docs/en/agent-view#turn-off-agent-view)
describe intended interfaces, but do not grant a passive exhaustive interactive
inventory or a saved-session absence predicate.

## Evidence and isolation

The standalone [native harness](../../../scripts/native-claude-interactive-proof)
imports no Observer implementation. It uses the existing owned user/mount/PID
namespace helper, private copied executable bytes, private authentication and
workspaces, and masked ordinary provider paths. No tmux, window or client
inventory is queried. A PTY is used solely to operate owned test sessions; its
output is drained and discarded.

[On/off evidence](native-on-off.json) records exact UUIDs, native status clocks,
saved identity, lifecycle outcomes and the registration-failure counterexample.
Minimal private hook callbacks independently confirm question invocation and
`prompt_input_exit`; they return no control instruction and are not Observer
inputs. [Hookless evidence](native-hookless.json) separately repeats registration,
question status and exit with all hooks disabled, proving that these native
metadata facts do not depend on those callbacks. Approval tools were never
executed. After the fault counterexample, only the owned test process is killed.

The main receipt predates addition of the harness's `--hookless-only` option;
the supplemental receipt binds that checkpoint's harness hash. Its default lifecycle
and fault methods retain the main run's behavior. Three early runs corrected
harness assumptions: selecting the first stale record instead of authenticating
all incarnations, cancelling an already-idle TUI before `/exit`, and treating
graceful exit of the unregistered fault context as a required cleanup proof.
They are not producer failures or accepted alternative parked predicates.

### Native roster after an unexpected interactive exit

The following [focused crash-roster receipt](native-crash-roster.json) queries
Claude only inside a fresh isolated namespace after an owned interactive process
is killed with SIGKILL. All hooks are disabled. Both modes retain saved identity
and a stale registration with its last `idle` status; the dead incarnation fails
authentication. Agent View on returns an empty JSON array from
`claude agents --json --all`, omitting the killed session. The stale registration
file remains after the command. Agent View off exits 1 without a JSON roster.

Claude therefore supplies live-roster omission and a dead native incarnation,
not an interactive `stopped`, `parked` or `unknown` row. Observer's current unknown
classification is its own conservative policy. Under a separately reviewed
healthy-registration assumption, a simple killed registered context can be
classified as no current runtime using native incarnation checks. The broader
live-but-unregistered counterexample remains a separate limitation; native
roster omission alone cannot distinguish it. No new Observer predicate is
implemented or accepted by this focused proof.

This receipt binds the harness hash after adding `--crash-roster-only`. The
private namespace is stopped and all borrowed authentication/history removed.

[Preservation/cleanup](preservation.json) verifies unchanged ordinary Claude
settings and native executable, all six pre-existing native incarnations still
registered, stopped private namespace and removed borrowed authentication/history.
The ordinary global `.claude.json` hash changed during the observation window;
byte-identical preference preservation is not claimed. That path was masked for
all private native actions, and ordinary sessions remained active throughout.
No cause for the ordinary preference change is established by this comparison.

## Ordinary installed CLI comparison

The [bounded comparison](ordinary-native.json) uses the installed public
`agent-observer 0.5.0a8` against an independently implemented native reference.
All six current ordinary Claude registrations agree in exact identity, runtime,
phase and user classification: three working and three waiting. A new ordinary
`a100-test` session appeared after the initial five-row inspection and before
the preservation baseline; it is discovered correctly.

The native catalog has 35 candidates and the CLI projects 34. The sole missing
row is the already documented setup-only SDK exclusion
`e0cba9dd-b642-4730-af4b-beb3b7e9c16c`. A changing activity clock on `a100-test`
is explicitly a bracketing sampling race, not a stable age mismatch. One ordinary
round establishes this sample only; it does not establish exhaustive coverage
of unregistered runtimes or mode-off ordinary deployment. Current runtime
comparison also retains a8's three bounded terminal-job parked facts.

## Original consequences before scope reconciliation

Proceed with the provider-owned boundary and interactive-only target. Agent
View disabling remains a viable candidate for tested interactive observation;
normal selection still needs its separate artifact/provider-policy gates.

Do not implement the proposed generic saved-plus-census parked predicate from
these files. A new source or a narrower explicit guarantee must be reviewed
first. A native end event can establish the end of one known context, but does
not by itself prove no other context exists for that UUID. Hook receipts also
cannot classify unseen saved history after an Observer restart. Terminal/client
inventory remains outside the observation layer regardless of this limitation.

Still unproved: exhaustive interactive registration, startup/UUID-switch
atomicity, all entry variants and child topologies, unsupported background
conflict coverage, and current artifact direct/cache/push behavior in ordinary
mode-off deployment. No controlled duplicate or same-process UUID-switch case
was run here. Failure/PID-domain variants from the execution plan retain their
later source/native gates. The positive tests do not accept those broader claims.

## Subsequent design decision

Following this proof, the user accepted the narrower native-registration
assumption in the [reconciled plan](../../claude-interactive-observation-plan.md).
Healthy bounded native scans with no matching live incarnation or relevant
unresolved conflict may classify positively saved interactive UUIDs as parked.
Normal exit and crash are supported targets. A live session with failed/lost
registration can be falsely reported parked, including after source recovery;
this is an accepted limitation, with partial coverage rather than an exhaustive
census claim. This supersedes the original negative-gate blocker above; it does
not change the measured counterexample or accept a new Observer artifact.

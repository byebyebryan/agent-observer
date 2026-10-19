# V3.5 watch-copy ABBA

V3.5 is a private qualification harness pinned to Observer
`b176ac06b39daeead4be0a33ff9d781304091fe0` and Mesh
`c06b33e058339d9d1d89ecf6844044867d816c58`. It is an independent copy of the
V3.4 reconnect/metric harness; V1 through V3.4 scripts and results remain
unchanged.

The approved timed workload is one ordinary public `Reader.watch_admitted`
generation followed by four detached local facade copies, for three synthetic
generations. The copies do not represent four independent SDK deliveries or
simultaneous clients. This workload is distinct from `read_matched.py`'s
four serialized consumer reads. Each ABBA trial runs in a fresh process. The
controller orders full, working, working, full for each interpreter and row
count, holds the shared CPU lock for one complete four-trial cell, then releases
it before the next cell. Results, runner bytes/hash, exact arguments, source
module pins, and output logs are stored per trial before the next process starts.

The measured CPU interval includes the synthetic owner accept, native IPC
generation/acquisition, ordinary Mesh proof/watch acquisition, and required
facade copies. Independent fixture construction/oracles, imports, post-window
hash checks, public channel audits, and cleanup are outside that interval.
Three generation CPU samples are reported per trial. RSS is a same-process
snapshot that includes input, oracle, Runtime, native source, Mesh Reader,
admitted state, and retained facade copies; it is not a role-specific heap
bound or evidence of physical retirement.

Ordinary public proof/line/source limits remain in force. The harness uses
trusted same-host IPC with `Endpoint(local=False)` to exercise ordinary remote
proof and expiry checks. It does not claim SSH, external authentication,
native-provider or installed-service acceptance. Mesh completed JSON-line
counters do not measure native IPC wire bytes. The existing bounded
selector-boundary pause is test-only and synchronizes synthetic input acceptance;
it does not change production APIs or admission logic.

The V3.5 `trial` mode runs exactly one variant and row count per process. It is
not a general matrix mode; use only the exact approved ABBA controller/run
manifest for final trials. Untimed per-trial checks require three current
complete generations, fresh proof nonces, exact public publisher digest
witnesses, independent expected DTO equality, and balanced cleanup.

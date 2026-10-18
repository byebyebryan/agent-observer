# Encoding refusal ownership evidence

This packet supports the [owning correction](../../../working-set-encoding-refusal.md).
It has no provider, service selection, install, network or dark-delta activity.

`before-{314,311}.{json,log}` use immutable Observer
`c4db1200279477c02679b41d8dc56bb11d080521` plus only the final
`tests/test_working_set_encoding_refusal.py` overlay. The unchanged three methods
produce three expected assertion failures, with no errors or skips. Two checks
forbid encoding a replacement after denial. A separate unhooked check measures
878 retained bytes against a test-only saturated limit of 562 bytes.

`after-{314,311}.{json,log}` run the same three methods against the final source
inventory: all pass. The fixture uses actual `ServiceState` acceptance,
`Runtime._reserve_working_set`, `Runtime.encoded_bytes` and strict native frame /
stream validation. Its explicit assignment of `runtime.encoded_limit` below
the constructor minimum is a test-only reservation boundary. It must not be
presented as a production configuration or a default64MiB overrun. No raw
provider input is used or retained.

The first-refusal case creates no working-set encoded buffer. The prior-buffer
case keeps that exact immutable object in the owner's retained-buffer inventory
while blocking reads. Repeated denial keeps it counted; unrelated publication
cannot release the block. A newly accepted sample and admitted replacement
restore material with advanced continuity. Original provider receipts, legacy
full/active views, K and last-event guards remain independently checked.

Reproduce with either Python 3.14.8 or 3.11.17, GC disabled by the runner:

```sh
python -B run_probe.py OBSERVER_EXPORT RESULT.json --before
python -B run_probe.py OBSERVER_EXPORT RESULT.json
```

The final combined source inventory and canonical / 123-method working-set
results are shared with the [client-gap packet](../client-gap/README.md).
Each runner records loaded project hashes. These component results establish
neither physical retirement/RSS nor aggregate resource/CPU, native provider,
actual working-set SDK Reader, transport or immutable installed-pair acceptance.
No caps, estimates, schema bytes or existing selected roles were relaxed.

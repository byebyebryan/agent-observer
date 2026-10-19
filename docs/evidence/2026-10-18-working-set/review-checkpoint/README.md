# Working-set review checkpoint

This checkpoint consolidates the opt-in active-plus-recent candidate for review.
The current production source remains `bb7b8aa`, preserved in `610afaa`;
the checkpoint adds evidence and status documentation only. No further
implementation, optimization or experiment is started as part of this review.

Read the [overall qualification status](../../../working-set-qualification-status.md)
first. It distinguishes accepted design/source fixes from an available SDK
feature and from actual producer/installed qualification.

New evidence since `610afaa`:

- [Slow-reader pressure](../resource-pressure/README.md): both interpreters complete fourteen generations, naturally retire two slow readers and preserve healthy full/active/working-set readers. The report explicitly leaves transient encoded retirement and physical memory accounting open.
- [Native byte-density screen](../wire-density-source/README.md): small selected sets save substantial bytes, but 500/100 misses the 50% native-component target and larger 2,000-row unions refuse tracking capacity.
- [Support-density model](../support-density-model/README.md): exact full-receipt interning has substantial arithmetic savings in two successful 500-row fixtures. This is a model, with no new native grammar or production implementation.

Luna produced the pressure fixture and support-density model. The primary
reviewed their source and limitations, produced the density screen, independently
checked saved source pins and scalar equations, packaged the large JSON reports
losslessly, and assembled this checkpoint. No peer's independent review is
claimed for these new packets.

[verify_saved.py](verify_saved.py) checks the existing report/log hashes,
compressed raw bytes, loaded Git blobs, every recorded pressure inventory
equation including nested copies, stage admission/drop/cleanup outcomes,
wire arithmetic, cross-version wire equality, and model-to-source input/frame
correspondence. [verification.json](verification.json) records that saved-data
verification. It does not rerun the experiments or independently reproduce the
model's round trips.

```sh
rtk python3 -B docs/evidence/2026-10-18-working-set/review-checkpoint/verify_saved.py
```

The repository gate is recorded separately in `canonical.log`. Current schemas
and identifiers remain candidates. Mesh registration, ordinary public Reader
admission, broader resource/cost qualification and independent native/installed
pair evidence remain open. Delta stays dark and selected services remain
unchanged. This checkpoint is ready for an overall direction review, not a
producer acceptance decision.

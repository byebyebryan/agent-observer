# Joint working-set contract direction

The exact R1 plus R2 interface and clock-policy direction is accepted by both
Mesh and RLCD. The [receipt](receipt.json) binds the immutable Observer input
tuple, the [Mesh review](mesh-r2-review.json) and the later
[client acceptance](client-r2-review.md). Earlier R1 findings and negative
diagnostics retain their original provenance. The additive
[R3 correction](../../../working-set-contract-r3.md) records the signed-range
guard and clarifies that a proved active branch can decide membership while
activity age is unknown.

This closes the P1 contract dependency under the existing user execution
request. It does not freeze identifiers or schema, accept producer behavior,
select a service, install an artifact or adopt a consumer. P2 implementation
and all producer qualification gates remain open. Delta synchronization stays
dark and the selected full/active/Tmux/writer paths remain independently owned.

This receipt verifies immutable review inputs and saved artifacts. No new
provider/native query, runtime test, arithmetic replay or performance claim is
made by recording that acceptance.

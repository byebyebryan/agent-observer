# Local service protocol 1 candidate

Date: 2026-10-06. Status: prerelease source contract. Native/installed service
acceptance is tracked in the [execution status](shared-observation-service-status.md).
API 1 and direct snapshot/watch 3, write 1 remain unchanged.

The pure `agent_observer.service_public` facade exports the separate descriptor,
request/frame schemas, bounded parsers/semantic validators and stream guard.
It imports no provider adapter or action implementation. The first service wire
has three operations: status, cached snapshot and watch. One newline-framed
request per connection specifies protocol, operation and expected host scope.
It grants no native action, source path selection, refresh or polling authority.

Frames identify a service UUID, kernel boot UUID, time-namespace clock domain,
user, configured host and
sources. Transport sequence is per connection starting at one; view revision
is shared and monotonic within the service incarnation. Reconnect starts a new
guard and initial status/view; service restart changes incarnation. There is no
durable replay or native completion/attention event guarantee.

Each source binds provider, canonical configured home/selector and stable public
namespace. Runtime/history receipts retain attempt/accept counts, source sample
and expiry times in host-local BOOTTIME milliseconds, health, finite result and
in-flight state. Native event/wall timestamps remain in unchanged snapshot 3.
Sample age begins when the bounded read starts, conservatively including read
duration. A receipt expires before being advertised current. Pure heartbeats
contain no snapshot and never renew a receipt. A genuine new accepted read can
publish a replacement view even when phase values are unchanged.

View/resync frames require a valid scoped snapshot. Heartbeat/gap/error do not
carry one; status may carry the current view or be warming with none. A gap
requires a subsequent replacement resync. The initial implementation uses full
views; slow readers may skip observations with explicit gap/resync or be
disconnected. View versions do not establish distinct native state episodes.

Requests are limited to 16 KiB. Frames permit the unchanged observation bound
plus a separately enforced 16 KiB envelope allowance. JSON duplicate keys,
invalid encoding/framing, excess nodes/depth, nonfinite values, unsupported
versions and provenance/lease conflicts fail with content-free codes. Structural
schema conformance also requires semantic validation. Same-user peer credentials
establish local access, not provider event truth or machine-name attestation.

Clients check the expected host/user/source scope and sequence/incarnation.
Host-local clients can account for additional elapsed time with BOOTTIME and
the matching boot/time-namespace scope; transport silence and an expired retained lease make
runtime facts uncertain. Remote forwarding needs its own conservative source-age
accounting. Receipt arrival never resets native age. Stale facts/coverage are
projected conservatively before service publication; clients retain last-known
evidence as uncertain, never as waiting/parked or action authorization.

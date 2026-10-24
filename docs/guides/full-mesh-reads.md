# Full cached Mesh reads

Optional Mesh reads consume already published full API 4/snapshot 6/Service 4
state through the explicit Agent profile v3 and Mesh SDK 1. Core and local
service remain Mesh-free. For bounded active/recent membership use
[working-set](working-set.md); this page describes the separate full inventory.

## Prerequisites and commands

Use the compatible Observer/Mesh pair selected for the full-read role, a running
cached full publisher/bridge and an explicitly configured Host Mesh authority.
Installing packages or invoking a read starts no collector or service. A full
publisher may retain an older reviewed pair than the working-set collector.
[Operations](../maintenance/operations.md) links the independent role selections.

```sh
agent-observer mesh list
agent-observer mesh list --include-system
agent-observer mesh watch --human
agent-observer mesh watch --human --prepared
```

The prepared option is explicit, requires compatible optional preparation
support and applies only to human watch. It does not alter raw wire/default
admission. Use `agent-observer mesh --help` and each subcommand's help for
configured source, socket and host-scope selection.

## Consumer rules

Use the supported pure Agent profile/facade; preserve exact host/home/session
references. Bind the reviewed native profile explicitly and use the same
instance for admitted/prepared reads. Recompute expiry in the receiver's clock
domain during quiet periods. A copy or heartbeat renews no source fact.

Unknown/partial source coverage and unavailable delivery stay separate.
Disconnect, lost baseline and incarnation barriers revoke current positives.
An outage never silently becomes direct collection or a working-set/full
fallback. Host selection uses existing directional authority only.

[Prepared interface 2](../reference/prepared-reads.md) documents the optional
full-read helper. The [utility guide](read-utilities.md) gives a complete
bounded working-set example and a separate local Service 4 example.

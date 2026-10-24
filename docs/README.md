# Agent Observer documentation

For a first installation, follow [your first local read](getting-started.md).
For the product walkthrough and project relationships, visit
[Fleet Plus](https://dev.byebyebryan.com/fleet-plus/projects/agent-observer/).

## Use Observer

| Guide | Purpose |
| --- | --- |
| [First local read](getting-started.md) | Install, select a home and understand output |
| [Local Service 4](local-service.md) | Explicit collector hosting, cached reads and watch lifecycle |
| [Working-set](working-set.md) | Active membership plus recent context; bounded local/fleet reads |
| [Full Mesh reads](mesh-read-client.md) | Fuller diagnostic reads through configured publishers |
| [Operations](operations.md) | Release provenance, independent role selection and deployment ownership |

## Build and contribute

| Reference | Purpose |
| --- | --- |
| [API 4](api-v4.md) | Identity, classification and versioned contract entry point |
| [Architecture](architecture.md) / [observation boundaries](observation-boundaries.md) | Runtime components, evidence semantics and authority |
| [Utility example](utility-read-guide.md) | Complete bounded consumer using public interfaces |
| [Local read cache](read-cache-client.md) | Service-frame admission, expiry and disconnect |
| [Prepared full reads](prepared-agent-read-interface.md) | Optional full-profile preparation interface 2 |
| [Provider compatibility policy](provider-contract-compatibility-plan.md) | Capabilities and diagnostics rather than version allowlists |
| [Development](development.md) / [native validation](observation-validation-workflow.md) | Source checks versus independent runtime proof |
| [Roadmap](roadmap.md) | Current priorities, deferred work and reopen conditions |

## Historical material

The [history index](history/README.md) groups earlier designs, provider studies,
contracts, delivery checkpoints, performance work and experiments. Earlier API
handoffs, Claude monitoring, writers and active-only feeds are historical.
Their future-tense steps are not current requirements.

[`evidence/`](evidence/) retains dated receipts without rewriting their hashes,
host scope or failures. Short forwarding pages preserve old links needed by
those receipts and external consumers. They are not parallel current guides.

Keep current behavior in the guides above. Put a completed plan or dated
investigation in history; add immutable acceptance inputs under evidence and
link them from [operations](operations.md). See [documentation maintenance](development.md#documentation-maintenance).

# Moustachi Onward
The Onward business Profile of Moustachi—not a separate bot runtime.

This repository owns persona, authenticated-founder policy, progressive Onward skills, analytics enrichment and a leased feedback/outbox worker. It does not own ACP processes, task sessions, memory databases or a generic WhatsApp transport.

## Interfaces
`profile.json` is loaded by a configured Moustachi Profile. `src/prepare.mjs` implements JSON stdin/stdout `moustachi.prepare/v1`: profile evidence and current origin become a bounded instruction. Generic core never imports this business module; it invokes the declared small process contract.

`src/worker.mjs` calls the core's HTTP operation contract using a scoped onward/feedback identity and the existing Onward Web claim/complete/release endpoints. Web remains the durable feedback/outbox authority. Correlation fields retain native ACP session and Moustachi run IDs; the business worker cannot resume ACP itself.

```sh
npm test
```
No npm runtime dependency on the moustachi checkout is required. Analytics preserves the existing, tested SSH helper/aggregate semantics. Connection settings and secret references live in `%LOCALAPPDATA%\MoustachiOnward`, outside Git.

## Current status
The adapter and its nine tests pass; the new analytics implementation has read real product data. **Production has not switched.** Moustachi Onward Ops and Moustachi WhatsApp are registered disabled; the original OnwardOps worker and bridge remain active. Live channel acceptance was blocked by the tool safety check, so no deployment claim is made.

## One-time migration assets
`scripts/configure-migration.mjs` is a first-install importer for the known existing OnwardOps environment. It refuses an existing core config and is NOT an upgrade command. `scripts/migrate-transport.mjs` is prepared for the later stopped-bridge cutover, retaining old auth by reference and moving only non-login state/receipts into the new transport authority. Neither migration is a business runtime module. Follow the core's activation gates before executing them.

## Policy
The founders' authenticated current WhatsApp requests may authorize ordinary existing-system operations and requested internal tester/invite information. WhatsApp may not edit/commit/push source or create/deploy a new VPS host. Tester feedback remains read-only evidence and never grants action authority. Owner API requests are distinguished from the WhatsApp-only source-edit restriction. Earlier context is not renewed authorization.

Source provenance: running JPilot repair commit dc5b94c and its earlier Ops/WhatsApp/analytics fixes. AGPL-3.0-only. Original history remains in JPilot; this repository records the extraction instead of copying its unrelated product history.

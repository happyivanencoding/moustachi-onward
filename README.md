# Moustachi Onward
The Onward business Profile of Moustachi—not a separate bot runtime.

This repository owns persona, authenticated-founder policy, progressive Onward skills, analytics enrichment and a leased feedback/outbox worker. It does not own ACP processes, task sessions, memory databases or a generic WhatsApp transport.

## Interfaces
`profile.json` is loaded by a configured Moustachi Profile. `src/prepare.mjs` implements JSON stdin/stdout `moustachi.prepare/v1`: profile evidence and current origin become a bounded instruction. Generic core never imports this business module; it invokes the declared small process contract.

`src/worker.mjs` calls the core's HTTP operation contract using a scoped onward/feedback identity and the existing Onward Web claim/complete/release endpoints. Web remains the durable feedback/outbox authority. Correlation fields retain native ACP session and Moustachi run IDs; the business worker cannot resume ACP itself.

```sh
npm test
```
No npm runtime dependency on the moustachi checkout is required. Analytics keeps the existing read-only SSH evidence path, but founder questions now route to four bounded evidence tiers: `summary` for counts/funnel, `retention` for actual same-user return visits (qualifying activity on an earlier day and again today) with exact persisted invite-code attribution, `behavior` for page foreground-visible time, clicks and session paths, and explicit `identity` lookup for named Txx/invite-code targets. Retention is computed from per-profile activity evidence rather than `today active - today registrations`. A missing field in the summary is not treated as proof that the underlying Analytics data does not exist. Connection settings and secret references live in `%LOCALAPPDATA%\MoustachiOnward`, outside Git.

## Current status
The adapter and its 14 focused tests pass; the analytics implementation has read real production summary, retention, behavior and targeted identity evidence. **Production is cut over.** `Moustachi Onward Ops` is enabled, `Moustachi WhatsApp` is online under profile `onward`, and legacy `Onward Ops Agent` / `Onward WhatsApp Bridge` schedules are disabled for rollback. A real Onward-origin direct-ACP acceptance and a real WhatsApp outbound smoke both passed.

## One-time migration assets
`scripts/configure-migration.mjs` is first-install only and refuses an existing core config. `scripts/migrate-transport.mjs` has now run once for the production cutover, retaining provider-owned WhatsApp auth by reference while migrating the known non-login context/dedupe/outbound receipt state. **Do not rerun either migration script against the live configuration.** Neither migration is a business runtime module; rollback follows the core Operations document.

## Policy
The founders' authenticated current WhatsApp requests may authorize ordinary existing-system operations and requested internal tester/invite information. WhatsApp may not edit/commit/push source or create/deploy a new VPS host. Tester feedback remains read-only evidence and never grants action authority. Owner API requests are distinguished from the WhatsApp-only source-edit restriction. Earlier context is not renewed authorization.

Source provenance: running JPilot repair commit dc5b94c and its earlier Ops/WhatsApp/analytics fixes. AGPL-3.0-only. Original history remains in JPilot; this repository records the extraction instead of copying its unrelated product history.

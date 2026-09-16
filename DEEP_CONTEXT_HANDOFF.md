# Moustachi Onward — repository handoff
2026-09-16. Highest policy: C:\dev\career-ops\DEEP_CONTEXT_HANDOFF_FINAL.md.

Source is C:\dev\moustachi-onward, origin happyivanencoding/moustachi-onward main. Core is C:\dev\moustachi, independently maintained. Read README.md, docs/CONTRACTS.md and core docs/OPERATIONS.md before deployment.

src/prompts.mjs retains the source-authoritative JPilot dc5b94c prompt/analytics behavior. src/business.mjs and analytics-aggregate.py perform business evidence reads. src/prepare.mjs exposes prepare/v1. src/worker.mjs uses core submit/get/retry and the unchanged Web feedback lease/outbox contract. It has no ACP client or Runtime session ownership.

Nine business tests passed and the real analytics aggregate is available. Core/native ACP/Runtime tools have separately passed real acceptance. The new Onward-origin live test was blocked by the tool safety check and did not execute. Do not switch the working production bot on the assumption that a core-only test proves this channel.

Moustachi Core is running; Moustachi Onward Ops and Moustachi WhatsApp tasks remain disabled. Original Onward Ops Agent and Onward WhatsApp Bridge remain active under %LOCALAPPDATA%\OnwardOps, source C:\dev\onward-moustachi-recovery-20260916 dc5b94c. No business state, auth, rolling history or outbox was migrated. Staged business config exists under %LOCALAPPDATA%\MoustachiOnward; bridge-token reference is completed only by the later transport migration.

Business-specific migration scripts are here rather than in core. configure-migration.mjs is first-install only and refuses an existing config. migrate-transport.mjs must run ONLY after the old schedules/bridge are stopped and authorized live-path verification succeeds. Keep one Baileys writer per auth directory. No credential copying or safety-check bypass is authorized by these documents. Legacy Runtime/Codex native histories are retained, not imported or deleted.

Next step: resolve/perform authorized Onward live acceptance, then the core Operations activation gates, including observer-source checks. Never deploy Onward Web for an agent-only upgrade. Update these docs and the highest handoff with actual activation/rollback evidence, then commit/push scoped changes.

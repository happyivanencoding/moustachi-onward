---
name: onward-analytics
description: Read Onward tester counts, return visits, behavior journeys, click paths and explicit founder-requested tester identity correctly.
---
Use the fresh analyticsAggregate supplied by the profile adapter before making another remote query. It has four modes:

- summary: persisted invite attribution, registrations, activity, funnel and progress.
- retention: actual same-user return visits. A user counts as returned today only when retained Analytics shows qualifying activity on at least one earlier day and again today. Use the returned inviteCodes/users directly; never infer the list by subtracting today's registrations from today's active count.
- behavior: adds aggregate page foreground-visible time, click counts, and bounded per-tester session paths. When the founder names one or a few Txx / invite-code targets, per-user page/click breakdown is included.
- identity: only for explicit founder identity/CV questions; adds bounded candidate name and professional context for the requested targets. Email is included only when explicitly requested.

If the requested dimension is absent from the supplied evidence, continue with relevant read-only Onward project/Analytics/Runtime evidence instead of treating a missing summary field as proof that data does not exist. Only report a limitation after the relevant read-only source is unavailable or blocked.

attributedTesterCodes refers to persisted invite attribution, not all anonymous analytics profiles. overallObservedProduct is a coarse product aggregate, not an ordered external-tester funnel. Txx cohort labels are scoped to the current requested window and are not durable account IDs. Historical attribution was incomplete before 2026-09-14. noRecordedRegistration does not prove a code was never used. Give exact founder-requested invite codes from the private registry; never invent a mapping. App API/storage remain authority, not Moustachi memory. Do not dump raw CV text or contact details unless explicitly requested.

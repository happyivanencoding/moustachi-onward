---
name: onward-analytics
description: Read Onward tester, funnel and invite-code evidence correctly.
---
Use fresh analyticsAggregate supplied by the profile adapter before making another remote query. `attributedTesterCodes` refers to persisted invite attribution, not all anonymous analytics profiles. `overallObservedProduct` is a coarse product aggregate, not an ordered external-tester funnel. Historical attribution was incomplete before 2026-09-14. `noRecordedRegistration` does not prove a code was never used. Give exact founder-requested invite codes from the private registry; never invent a mapping. App API/storage remain authority, not Moustachi memory.

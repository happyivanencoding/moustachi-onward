#!/usr/bin/env python3
import collections
import datetime
import hashlib
import json
import os
import pathlib
import re
import sqlite3
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Paris")
WINDOW_DAYS = max(1, min(int(os.environ.get("ONWARD_ANALYTICS_WINDOW_DAYS", "7")), 31))
DATA_ROOT = pathlib.Path(os.environ.get("ONWARD_ANALYTICS_DATA_ROOT", "/srv/apps/jobpilot-v1/data/.career-ops-web"))
WORKSPACE_ROOT = DATA_ROOT.parent
ATTRIBUTION_RELIABLE_FROM = "2026-09-14T20:40:00+02:00"
MODE = str(os.environ.get("ONWARD_ANALYTICS_MODE", "summary")).strip().lower()
if MODE not in {"summary", "behavior", "identity"}:
    MODE = "summary"
TARGETS = [
    value.strip().upper()
    for value in str(os.environ.get("ONWARD_ANALYTICS_TARGETS", "")).split(",")
    if re.fullmatch(r"(?:T\d{1,3}|ONWARD(?:V1|\d{3}))", value.strip(), flags=re.I)
]
INCLUDE_EMAIL = str(os.environ.get("ONWARD_ANALYTICS_INCLUDE_EMAIL", "")).strip() == "1"


def parse_time(value):
    if isinstance(value, (int, float)):
        return datetime.datetime.fromtimestamp(value / 1000, TZ)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(TZ)
    except ValueError:
        return None


def event_day(timestamp):
    dt = parse_time(timestamp)
    return dt.date().isoformat() if dt else None


def tester_ref(profile_id):
    return "tester-" + hashlib.sha256(str(profile_id or "").encode("utf-8")).hexdigest()[:10]


def read_tracked_registrations():
    rows = {}
    auth_db = DATA_ROOT / "v1-auth.sqlite"
    if auth_db.exists():
        conn = sqlite3.connect("file:" + str(auth_db) + "?mode=ro", uri=True)
        try:
            for email, profile_id, created_at, invite_code in conn.execute(
                "select email, profile_id, created_at, invite_code from password_accounts where invite_code_id is not null and invite_code_id <> ''"
            ):
                if profile_id:
                    rows[str(profile_id)] = {
                        "profileId": str(profile_id),
                        "registeredAt": created_at,
                        "inviteCode": str(invite_code or ""),
                        "authMode": "password",
                        "email": str(email or ""),
                    }
        finally:
            conn.close()
    google_file = DATA_ROOT / "v1-accounts.json"
    if google_file.exists():
        try:
            data = json.loads(google_file.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for account in data.get("accounts", []):
            if not isinstance(account, dict) or not account.get("profileId") or not account.get("inviteCodeId"):
                continue
            rows[str(account["profileId"])] = {
                "profileId": str(account["profileId"]),
                "registeredAt": account.get("createdAt"),
                "inviteCode": str(account.get("inviteCode") or ""),
                "authMode": "google",
                "email": str(account.get("email") or ""),
            }
    return list(rows.values())


def read_profile_events(profile_id, window_start_ms=0):
    if not profile_id:
        return None, []
    directory = hashlib.sha256(str(profile_id).encode("utf-8")).hexdigest()
    event_file = DATA_ROOT / "analytics" / directory / "events.json"
    if not event_file.exists():
        return None, []
    try:
        store = json.loads(event_file.read_text(encoding="utf-8"))
    except Exception:
        return None, []
    events = [
        event
        for event in store.get("events", [])
        if isinstance(event, dict) and float(event.get("timestamp", 0) or 0) >= window_start_ms
    ]
    events.sort(key=lambda event: float(event.get("timestamp", 0) or 0))
    return store.get("userId"), events


def event_flags(events):
    steps = {str(event.get("step")) for event in events if event.get("event") == "funnel" and event.get("step")}
    pages = {str(event.get("page")) for event in events if event.get("page")}
    server_events = {str(event.get("event")) for event in events if event.get("source") == "server" and event.get("event")}
    active_days = {event_day(event.get("timestamp")) for event in events if event.get("event") in {"page_enter", "page_heartbeat"}}
    active_days.discard(None)
    return steps, pages, server_events, active_days


def stage_for(steps, pages, server_events):
    if "cv_completed" in server_events:
        return "cv_generated"
    if {"generate_cv", "generate_cv_started"} & steps:
        return "cv_generation_started"
    if "open_job" in steps:
        return "job_opened"
    if "view_jobs" in steps or "onboarding_results" in pages:
        return "jobs_seen"
    if "choose_direction" in steps or "onboarding_direction" in pages or "onboarding_search" in pages:
        return "direction_or_search"
    if "cv_ready" in server_events or "onboarding_analysis" in pages:
        return "cv_ready_or_analysis"
    if "upload_cv" in steps or "onboarding_upload" in pages:
        return "upload"
    return "registered_only"


def summarize_tracked(rows, window_start, window_start_ms):
    registrations = collections.Counter()
    registrations_by_invite_code = collections.Counter()
    active_by_day = collections.Counter()
    furthest = collections.Counter()
    funnel = collections.Counter()
    total = unique_active = active_multiple_days = 0
    for row in rows:
        created = parse_time(row.get("registeredAt"))
        if not created or created < window_start:
            continue
        total += 1
        registrations[created.date().isoformat()] += 1
        invite_code = str(row.get("inviteCode") or "").strip()
        if invite_code:
            registrations_by_invite_code[invite_code] += 1
        _, events = read_profile_events(row.get("profileId"), window_start_ms)
        steps, pages, server_events, active_days = event_flags(events)
        if active_days:
            unique_active += 1
            active_multiple_days += int(len(active_days) > 1)
            for day in active_days:
                active_by_day[day] += 1
        funnel["cvReady"] += int("cv_ready" in server_events)
        funnel["jobsSeen"] += int("view_jobs" in steps or "onboarding_results" in pages)
        funnel["jobOpened"] += int("open_job" in steps)
        funnel["cvGenerateStarted"] += int(bool({"generate_cv", "generate_cv_started"} & steps))
        funnel["cvCompleted"] += int("cv_completed" in server_events)
        funnel["cvFailed"] += int("cv_failed" in server_events)
        furthest[stage_for(steps, pages, server_events)] += 1
    return {
        "trackedRegistrationsTotal": len(rows),
        "totalRegistrationsInWindow": total,
        "registrationsByDay": dict(sorted(registrations.items())),
        "registrationsByInviteCode": dict(sorted(registrations_by_invite_code.items())),
        "uniqueActiveRegistrantsInWindow": unique_active,
        "activeRegistrantsByDay": dict(sorted(active_by_day.items())),
        "activeOnMultipleDays": active_multiple_days,
        "funnel": {
            "cvReady": funnel["cvReady"],
            "jobsSeen": funnel["jobsSeen"],
            "jobOpened": funnel["jobOpened"],
            "cvGenerateStarted": funnel["cvGenerateStarted"],
            "cvCompleted": funnel["cvCompleted"],
            "cvFailed": funnel["cvFailed"],
        },
        "furthestStage": dict(furthest),
    }


def summarize_overall():
    counts = collections.Counter()
    analytics_dir = DATA_ROOT / "analytics"
    if not analytics_dir.exists():
        return {}
    for event_file in analytics_dir.glob("*/events.json"):
        try:
            data = json.loads(event_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        events = [event for event in data.get("events", []) if isinstance(event, dict)]
        if not events:
            continue
        steps, pages, server_events, _ = event_flags(events)
        counts["testUsers"] += 1
        counts["loggedInUsers"] += int("login" in steps)
        counts["cvReady"] += int("cv_ready" in server_events)
        counts["jobsSeen"] += int("view_jobs" in steps or "onboarding_results" in pages)
        counts["jobOpened"] += int("open_job" in steps)
        counts["cvGenerateStarted"] += int(bool({"generate_cv", "generate_cv_started"} & steps))
        counts["cvGenerateCompleted"] += int("cv_completed" in server_events)
        counts["cvFailed"] += int("cv_failed" in server_events)
    return {
        key: counts[key]
        for key in ["testUsers", "loggedInUsers", "cvReady", "jobsSeen", "jobOpened", "cvGenerateStarted", "cvGenerateCompleted", "cvFailed"]
    }


def compact_path(values):
    result = []
    for value in values:
        if value and (not result or result[-1] != value):
            result.append(value)
    return result


def behavior_cohort(rows, window_start, window_start_ms):
    candidates = []
    for row in rows:
        registered = parse_time(row.get("registeredAt"))
        if not registered or registered < window_start:
            continue
        _, events = read_profile_events(row.get("profileId"), window_start_ms)
        candidates.append((registered, row, events))
    candidates.sort(key=lambda item: (item[0], str(item[1].get("inviteCode") or ""), tester_ref(item[1].get("profileId"))))
    return candidates


def summarize_behavior(rows, window_start, window_start_ms):
    page_totals = collections.defaultdict(lambda: {"enters": 0, "visibleDurationMs": 0, "maxScrollDepth": 0})
    click_totals = collections.Counter()
    users = []
    for index, (_, row, events) in enumerate(behavior_cohort(rows, window_start, window_start_ms), start=1):
        pages = collections.defaultdict(lambda: {"enters": 0, "visibleDurationMs": 0, "maxScrollDepth": 0})
        clicks = collections.Counter()
        sessions = collections.defaultdict(list)
        for event in events:
            session_id = str(event.get("sessionId") or "")
            if session_id:
                sessions[session_id].append(event)
            page = str(event.get("page") or "")
            if page:
                if event.get("event") == "page_enter":
                    pages[page]["enters"] += 1
                    page_totals[page]["enters"] += 1
                if event.get("event") in {"page_exit", "page_heartbeat"}:
                    duration = max(0, int(event.get("durationMs", 0) or 0))
                    pages[page]["visibleDurationMs"] += duration
                    page_totals[page]["visibleDurationMs"] += duration
                if event.get("event") in {"scroll", "page_exit", "page_heartbeat"}:
                    depth = max(0, min(100, int(event.get("scrollDepth", 0) or 0)))
                    pages[page]["maxScrollDepth"] = max(pages[page]["maxScrollDepth"], depth)
                    page_totals[page]["maxScrollDepth"] = max(page_totals[page]["maxScrollDepth"], depth)
            if event.get("event") == "click" and event.get("action"):
                action = str(event.get("action"))[:100]
                clicks[action] += 1
                click_totals[action] += 1
        session_rows = []
        for journey in sessions.values():
            path = compact_path([str(event.get("page") or "") for event in journey if event.get("event") == "page_enter"])
            visible_ms = sum(
                max(0, int(event.get("durationMs", 0) or 0))
                for event in journey
                if event.get("event") in {"page_exit", "page_heartbeat"}
            )
            click_count = sum(1 for event in journey if event.get("event") == "click")
            if not path and not visible_ms and not click_count:
                continue
            started = parse_time(journey[0].get("timestamp")) if journey else None
            session_rows.append({
                "startedAt": started.isoformat(timespec="minutes") if started else None,
                "path": path[:40],
                "visibleDurationMs": visible_ms,
                "clicks": click_count,
            })
        steps, page_names, server_events, active_days = event_flags(events)
        registered = parse_time(row.get("registeredAt"))
        users.append({
            "cohortLabel": f"T{index:02d}",
            "testerRef": tester_ref(row.get("profileId")),
            "inviteCode": str(row.get("inviteCode") or "")[:64],
            "authMode": str(row.get("authMode") or "")[:20],
            "registeredAt": registered.isoformat(timespec="minutes") if registered else None,
            "activeDays": sorted(active_days),
            "furthestStage": stage_for(steps, page_names, server_events),
            "totalVisibleDurationMs": sum(value["visibleDurationMs"] for value in pages.values()),
            "clickTotal": sum(clicks.values()),
            "sessionCount": len(session_rows),
            "pages": [
                {"page": page, **value}
                for page, value in sorted(pages.items(), key=lambda item: (-item[1]["visibleDurationMs"], item[0]))
            ][:24],
            "clicks": [{"action": action, "count": count} for action, count in clicks.most_common(32)],
            "sessions": session_rows[:16],
        })
    return {
        "trackedUsers": len(users),
        "totalVisibleDurationMs": sum(value["visibleDurationMs"] for value in page_totals.values()),
        "clickTotal": sum(click_totals.values()),
        "sessionCount": sum(user["sessionCount"] for user in users),
        "pages": [
            {"page": page, **value}
            for page, value in sorted(page_totals.items(), key=lambda item: (-item[1]["visibleDurationMs"], item[0]))
        ][:40],
        "clicks": [{"action": action, "count": count} for action, count in click_totals.most_common(100)],
        "users": users,
    }


def read_profile_registry():
    try:
        data = json.loads((WORKSPACE_ROOT / "data" / "profiles.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        str(profile.get("id")): profile
        for profile in data.get("profiles", [])
        if isinstance(profile, dict) and profile.get("id")
    }


def professional_context(profile, profile_id):
    cv_path = str(profile.get("cvMarkdown") or f".career-ops-web/profiles/{profile_id}/cv.md")
    file = WORKSPACE_ROOT / cv_path
    try:
        text = file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    keywords = re.compile(
        r"(master|bachelor|licence|degree|university|universite|ecole|school|experience|education|formation|"
        r"analyst|business|finance|marketing|engineer|intern|stage|alternance|cdi|cdd|project|consultant)",
        flags=re.I,
    )
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"^[#>*\-\s]+", "", raw).strip()
        if not line or len(line) > 260:
            continue
        lowered = line.casefold()
        if (
            "@" in line
            or "http://" in lowered
            or "https://" in lowered
            or re.search(r"\b(?:phone|telephone|tel|email|e-mail|address|gender|nationality|birth|birthday)\b", lowered)
            or re.search(r"\b\+?\d[\d .()-]{7,}\d\b", line)
        ):
            continue
        if keywords.search(line) and line not in lines:
            lines.append(line)
        if len(lines) >= 8:
            break
    return lines


def summarize_identity(rows, behavior):
    if not TARGETS:
        return {"requestedTargets": [], "users": [], "includeEmail": INCLUDE_EMAIL}
    profile_registry = read_profile_registry()
    by_profile = {row["profileId"]: row for row in rows if row.get("profileId")}
    labels = {user["cohortLabel"].upper(): user for user in behavior.get("users", [])}
    codes = collections.defaultdict(list)
    for user in behavior.get("users", []):
        if user.get("inviteCode"):
            codes[str(user["inviteCode"]).upper()].append(user)
    selected = []
    seen = set()
    for target in TARGETS:
        candidates = [labels[target]] if target in labels else codes.get(target, [])
        for candidate in candidates:
            ref = candidate.get("testerRef")
            if not ref or ref in seen:
                continue
            seen.add(ref)
            row = next((value for value in by_profile.values() if tester_ref(value.get("profileId")) == ref), None)
            if not row:
                continue
            profile = profile_registry.get(row["profileId"], {})
            item = {
                "cohortLabel": candidate.get("cohortLabel"),
                "testerRef": ref,
                "inviteCode": candidate.get("inviteCode"),
                "authMode": row.get("authMode"),
                "profileName": str(profile.get("name") or "")[:120],
                "professionalContext": professional_context(profile, row["profileId"]),
            }
            if INCLUDE_EMAIL:
                item["email"] = str(row.get("email") or "")[:254]
            selected.append(item)
    return {"requestedTargets": TARGETS, "users": selected, "includeEmail": INCLUDE_EMAIL}


def main():
    now = datetime.datetime.now(TZ)
    window_start = datetime.datetime.combine(now.date() - datetime.timedelta(days=WINDOW_DAYS - 1), datetime.time.min, TZ)
    window_start_ms = window_start.timestamp() * 1000
    rows = read_tracked_registrations()
    tracked = summarize_tracked(rows, window_start, window_start_ms)
    tracked["todayParis"] = tracked["registrationsByDay"].get(now.date().isoformat(), 0)
    tracked["recentWindowComplete"] = True
    result = {
        "available": True,
        "mode": MODE,
        "generatedAt": now.isoformat(timespec="seconds"),
        "timeZone": "Europe/Paris",
        "windowDays": WINDOW_DAYS,
        "windowStart": window_start.date().isoformat(),
        "attributionReliableFrom": ATTRIBUTION_RELIABLE_FROM,
        "attributedTesterCodes": tracked,
        "overallObservedProduct": summarize_overall(),
    }
    if MODE in {"behavior", "identity"}:
        full_behavior = summarize_behavior(rows, window_start, window_start_ms)
        behavior = full_behavior
        if TARGETS:
            selected = set(TARGETS)
            behavior = {
                **full_behavior,
                "users": [
                    user
                    for user in full_behavior["users"]
                    if user["cohortLabel"].upper() in selected or str(user.get("inviteCode") or "").upper() in selected
                ],
            }
        result["behavior"] = behavior
        if MODE == "identity":
            result["identity"] = summarize_identity(rows, full_behavior)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import collections
import datetime
import hashlib
import json
import os
import pathlib
import sqlite3
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Paris")
WINDOW_DAYS = max(1, min(int(os.environ.get("ONWARD_ANALYTICS_WINDOW_DAYS", "7")), 31))
DATA_ROOT = pathlib.Path(os.environ.get("ONWARD_ANALYTICS_DATA_ROOT", "/srv/apps/jobpilot-v1/data/.career-ops-web"))
ATTRIBUTION_RELIABLE_FROM = "2026-09-14T20:40:00+02:00"


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


def read_tracked_registrations():
    rows = []
    auth_db = DATA_ROOT / "v1-auth.sqlite"
    if auth_db.exists():
        conn = sqlite3.connect("file:" + str(auth_db) + "?mode=ro", uri=True)
        try:
            for profile_id, created_at, invite_code in conn.execute(
                "select profile_id, created_at, invite_code from password_accounts where invite_code_id is not null and invite_code_id <> ''"
            ):
                rows.append({"profileId": profile_id, "registeredAt": created_at, "inviteCode": invite_code or ""})
        finally:
            conn.close()
    google_file = DATA_ROOT / "v1-accounts.json"
    if google_file.exists():
        try:
            data = json.loads(google_file.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for account in data.get("accounts", []):
            if isinstance(account, dict) and account.get("profileId") and account.get("createdAt") and account.get("inviteCodeId"):
                rows.append({"profileId": account["profileId"], "registeredAt": account["createdAt"], "inviteCode": str(account.get("inviteCode") or "")})
    return rows


def read_profile_events(profile_id, window_start_ms=0):
    if not profile_id:
        return []
    directory = hashlib.sha256(str(profile_id).encode("utf-8")).hexdigest()
    return read_event_file(DATA_ROOT / "analytics" / directory / "events.json", window_start_ms)


def read_event_file(event_file, window_start_ms=0):
    if not event_file.exists():
        return []
    try:
        data = json.loads(event_file.read_text(encoding="utf-8"))
    except Exception:
        return []
    events = data.get("events", []) if isinstance(data, dict) else []
    return [event for event in events if isinstance(event, dict) and float(event.get("timestamp", 0) or 0) >= window_start_ms]


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
        events = read_profile_events(row.get("profileId"), window_start_ms)
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
        events = read_event_file(event_file)
        if not events:
            continue
        steps, pages, server_events, active_days = event_flags(events)
        counts["testUsers"] += 1
        counts["loggedInUsers"] += int("login" in steps)
        counts["cvReady"] += int("cv_ready" in server_events)
        counts["jobsSeen"] += int("view_jobs" in steps or "onboarding_results" in pages)
        counts["jobOpened"] += int("open_job" in steps)
        counts["cvGenerateStarted"] += int(bool({"generate_cv", "generate_cv_started"} & steps))
        counts["cvGenerateCompleted"] += int("cv_completed" in server_events)
        counts["cvFailed"] += int("cv_failed" in server_events)
    return {key: counts[key] for key in ["testUsers", "loggedInUsers", "cvReady", "jobsSeen", "jobOpened", "cvGenerateStarted", "cvGenerateCompleted", "cvFailed"]}


def main():
    now = datetime.datetime.now(TZ)
    window_start = datetime.datetime.combine(now.date() - datetime.timedelta(days=WINDOW_DAYS - 1), datetime.time.min, TZ)
    tracked = summarize_tracked(read_tracked_registrations(), window_start, window_start.timestamp() * 1000)
    tracked["todayParis"] = tracked["registrationsByDay"].get(now.date().isoformat(), 0)
    tracked["recentWindowComplete"] = True
    result = {
        "available": True,
        "generatedAt": now.isoformat(timespec="seconds"),
        "timeZone": "Europe/Paris",
        "windowDays": WINDOW_DAYS,
        "windowStart": window_start.date().isoformat(),
        "attributionReliableFrom": ATTRIBUTION_RELIABLE_FROM,
        "attributedTesterCodes": tracked,
        "overallObservedProduct": summarize_overall(),
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()

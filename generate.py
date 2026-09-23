#!/usr/bin/env python3

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BASE_URL = "https://codex-reset.com"

TIMELINE_URL = (
    f"{BASE_URL}/api/timeline?"
    + urllib.parse.urlencode(
        {
            "locale": "zh",
            "group": "reset",
            "limit": "50",
        }
    )
)

FORECAST_URL = (
    f"{BASE_URL}/api/forecast?"
    + urllib.parse.urlencode(
        {
            "locale": "zh",
            "tz": "Asia/Shanghai",
        }
    )
)

OUTPUT = Path("docs/calendar.ics")

PROJECT_URL = os.environ.get(
    "PROJECT_URL",
    "https://github.com/YOUR_USERNAME/codex-reset-calendar",
)

USER_AGENT = f"codex-reset-calendar/1.0 (+{PROJECT_URL})"

SOURCE_NAME = "codex-reset.com"
SOURCE_URL = "https://codex-reset.com/"


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    value = value.strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def format_ics_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def escape_ics(value: Any) -> str:
    text = str(value)

    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def fold_ics_line(line: str, limit: int = 75) -> list[str]:
    """
    RFC 5545 recommends folding content lines at 75 octets.
    """
    result: list[str] = []
    current = ""

    for char in line:
        candidate = current + char

        if len(candidate.encode("utf-8")) > limit:
            result.append(current)
            current = " " + char
        else:
            current = candidate

    if current:
        result.append(current)

    return result


def add_line(lines: list[str], name: str, value: Any) -> None:
    raw = f"{name}:{escape_ics(value)}"
    lines.extend(fold_ics_line(raw))


def make_event(
    *,
    uid: str,
    start: datetime,
    end: datetime,
    summary: str,
    description: str,
    url: str | None = None,
) -> list[str]:
    lines = ["BEGIN:VEVENT"]

    add_line(lines, "UID", uid)
    add_line(lines, "DTSTAMP", format_ics_datetime(datetime.now(timezone.utc)))
    add_line(lines, "DTSTART", format_ics_datetime(start))
    add_line(lines, "DTEND", format_ics_datetime(end))
    add_line(lines, "SUMMARY", summary)
    add_line(lines, "DESCRIPTION", description)

    if url:
        add_line(lines, "URL", url)

    lines.append("END:VEVENT")

    return lines


def build_timeline_events(data: dict[str, Any]) -> list[list[str]]:
    events: list[list[str]] = []

    for item in data.get("events", []):
        if item.get("group") != "reset":
            continue

        if item.get("announcement_state") != "announced":
            continue

        start = parse_datetime(item.get("announced_at"))

        if start is None:
            continue

        event_id = str(
            item.get("id")
            or format_ics_datetime(start)
        )

        source_url = item.get("url") or SOURCE_URL
        source_summary = item.get("summary")

        description_parts: list[str] = []

        if source_summary:
            description_parts.append(str(source_summary))
            description_parts.append("")

        description_parts.extend(
            [
                f"Data: {SOURCE_NAME}",
                SOURCE_URL,
            ]
        )

        events.append(
            make_event(
                uid=f"timeline-{event_id}@codex-reset-calendar",
                start=start,
                end=start + timedelta(minutes=15),
                summary="Codex Reset",
                description="\n".join(description_parts),
                url=source_url,
            )
        )

    return events


def confidence_zh(value: Any) -> str | None:
    mapping = {
        "low": "低",
        "medium": "中",
        "high": "高",
    }

    if not isinstance(value, str):
        return None

    return mapping.get(value.lower(), value)


def build_forecast_event(
    data: dict[str, Any],
) -> list[str] | None:
    """
    Forecast events come from latest_alert.window.

    The window is preserved as an actual calendar interval:
        DTSTART = window.start_at
        DTEND   = window.end_at

    We do not invent a time from the statistical 24h/48h probabilities.
    """

    alert = data.get("latest_alert")

    if not isinstance(alert, dict):
        print("Forecast: latest_alert is missing.")
        return None

    window = alert.get("window")

    if not isinstance(window, dict):
        print("Forecast: latest_alert.window is missing.")
        return None

    start = parse_datetime(window.get("start_at"))
    end = parse_datetime(window.get("end_at"))

    if start is None or end is None:
        print("Forecast: prediction window has no valid start/end.")
        return None

    if end <= start:
        print("Forecast: prediction window is invalid.")
        return None

    probabilities = data.get("probabilities")

    if not isinstance(probabilities, dict):
        probabilities = {}

    description_parts = [
        "这是预测事件，并不代表 Codex Reset 一定会发生。",
        "",
    ]

    localized_summary = alert.get("localized_summary")

    if localized_summary:
        description_parts.append(str(localized_summary))
        description_parts.append("")

    p24 = probabilities.get("rounded_24h")
    p48 = probabilities.get("rounded_48h")

    if p24 is not None:
        description_parts.append(
            f"未来 24 小时重置概率：{p24}%"
        )

    if p48 is not None:
        description_parts.append(
            f"48 小时内重置概率：{p48}%"
        )

    confidence = confidence_zh(data.get("confidence"))

    if confidence:
        description_parts.append(
            f"模型置信度：{confidence}"
        )

    score = alert.get("score")

    if score is not None:
        description_parts.append(
            f"预测信号分数：{score}"
        )

    window_label = window.get("label")

    if window_label:
        description_parts.append(
            f"预测窗口：{window_label}"
        )

    time_zone = window.get("time_zone")

    if time_zone:
        description_parts.append(
            f"预测窗口时区：{time_zone}"
        )

    description_parts.extend(
        [
            "",
            f"Data: {SOURCE_NAME}",
            SOURCE_URL,
        ]
    )

    alert_id = str(
        alert.get("id")
        or format_ics_datetime(start)
    )

    source_url = alert.get("url") or SOURCE_URL

    return make_event(
        uid=f"forecast-{alert_id}@codex-reset-calendar",
        start=start,
        end=end,
        summary="[预测] Codex Reset",
        description="\n".join(description_parts),
        url=source_url,
    )


def generate_calendar(
    timeline: dict[str, Any],
    forecast: dict[str, Any],
) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//codex-reset-calendar//ZH-CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Codex Reset 中文日历",
        "X-WR-CALDESC:已确认的 Codex Reset 与未来预测",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]

    timeline_events = build_timeline_events(timeline)

    for event in timeline_events:
        lines.extend(event)

    forecast_event = build_forecast_event(forecast)

    if forecast_event is not None:
        lines.extend(forecast_event)

    lines.append("END:VCALENDAR")

    print(f"Timeline events: {len(timeline_events)}")
    print(
        f"Forecast event: "
        f"{'yes' if forecast_event else 'no'}"
    )

    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    print(f"Fetching timeline: {TIMELINE_URL}")
    timeline = fetch_json(TIMELINE_URL)

    print(f"Fetching forecast: {FORECAST_URL}")
    forecast = fetch_json(FORECAST_URL)

    calendar = generate_calendar(
        timeline,
        forecast,
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        file.write(calendar)

    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()

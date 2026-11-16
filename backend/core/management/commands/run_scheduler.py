from __future__ import annotations

import logging
import signal
import threading
from datetime import date, datetime, time as dt_time, timedelta, timezone, tzinfo
from typing import Any, Callable, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from core.constants import DISCORD_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

DISCORD_SUCCESS_COLOR = 3066993
DISCORD_FAIL_COLOR = 15158332
TARGET_HOUR = 2
TARGET_MINUTE = 30
TARGET_WEEKDAYS: frozenset[int] = frozenset({2, 6})  # Wednesday (2), Sunday (6)
MAX_SLEEP_SLICE_SECONDS = 3600.0
MIN_RUN_GAP = timedelta(minutes=1)
PIPELINE_STEPS: tuple[str, ...] = (
    "fetch_duffel_routes",
    "notify_unenriched",
    "scrape_ferries",
)


def _nth_sunday(year: int, month: int, nth: int) -> date:
    first = date(year, month, 1)
    days_to_sunday = (6 - first.weekday()) % 7
    return first + timedelta(days=days_to_sunday + (nth - 1) * 7)


class _USEasternTZ(tzinfo):
    """Pure-stdlib US Eastern fallback if container OS tzdata is unavailable."""

    _ZERO = timedelta(0)
    _STD = timedelta(hours=-5)
    _DST_DELTA = timedelta(hours=1)

    def _dst_bounds(self, year: int) -> tuple[datetime, datetime]:
        start = datetime.combine(_nth_sunday(year, 3, 2), dt_time(2, 0))
        end = datetime.combine(_nth_sunday(year, 11, 1), dt_time(1, 0))
        return start, end

    def dst(self, dt: datetime | None) -> timedelta:
        if dt is None:
            return self._ZERO
        naive = dt.replace(tzinfo=None)
        start, end = self._dst_bounds(naive.year)
        if start <= naive < end:
            return self._DST_DELTA
        if end <= naive < end + self._DST_DELTA and dt.fold == 0:
            return self._DST_DELTA
        return self._ZERO

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return self._STD + self.dst(dt)

    def tzname(self, dt: datetime | None) -> str:
        return "EDT" if self.dst(dt) != self._ZERO else "EST"


def get_eastern_tz() -> tzinfo:
    """Return `America/New_York` ZoneInfo, falling back to US Eastern DST rules."""
    try:
        return ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:
        return _USEasternTZ()


def format_eastern(dt: datetime) -> str:
    local_dt = dt.astimezone(get_eastern_tz())
    return local_dt.strftime("%a, %d %b %Y at %H:%M:%S %Z")


def format_duration(seconds: int) -> str:
    clamped = max(0, seconds)
    if clamped >= 60:
        return f"{clamped // 60}m {clamped % 60:02d}s"
    return f"{clamped}s"


def compute_next_run(
    now_utc: datetime,
    target_hour: int = TARGET_HOUR,
    target_minute: int = TARGET_MINUTE,
    allowed_weekdays: frozenset[int] = TARGET_WEEKDAYS,
) -> datetime:
    """Compute the next scheduled UTC instant at HH:MM America/New_York on Wed/Sun."""
    tz = get_eastern_tz()
    now_et = now_utc.astimezone(tz)
    base_date = now_et.date()

    for offset in range(8):
        cand_date = base_date + timedelta(days=offset)
        if cand_date.weekday() not in allowed_weekdays:
            continue
        cand_local = datetime(
            cand_date.year,
            cand_date.month,
            cand_date.day,
            target_hour,
            target_minute,
            0,
            tzinfo=tz,
        )
        cand_utc = cand_local.astimezone(timezone.utc)
        if cand_utc.astimezone(tz).weekday() not in allowed_weekdays:
            continue
        if cand_utc > now_utc:
            return cand_utc

    raise RuntimeError("Failed to compute next scheduled run within 7 days.")


def post_discord_alert(
    webhook_url: str | None,
    *,
    title: str,
    description: str,
    color: int,
    timestamp_iso: str,
) -> bool:
    """Post an embed payload to the #data-pipeline Discord webhook."""
    if not webhook_url:
        logger.info("DISCORD_DATAPIPES_WEBHOOK_URL is not configured; skipping Discord embed.")
        return False

    payload: dict[str, Any] = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": timestamp_iso,
            }
        ]
    }
    try:
        resp = requests.post(
            str(webhook_url),
            json=payload,
            timeout=DISCORD_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning("Failed to post #data-pipeline Discord notification: %s", exc)
        return False


def execute_pipeline_once(
    *,
    scheduled_utc: datetime | None = None,
    runner: Callable[..., Any] = call_command,
    steps: Sequence[str] = PIPELINE_STEPS,
    now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    webhook_url: str | None = None,
) -> None:
    """Execute flight & ferry ETL commands once sequentially and alert #data-pipeline."""
    started_utc = now_fn()
    sched_utc = scheduled_utc or started_utc
    started_iso = started_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    scheduled_et = format_eastern(sched_utc)
    started_et = format_eastern(started_utc)
    queue_label = format_duration(
        max(0, int((started_utc - sched_utc).total_seconds()))
    )
    target_webhook = (
        webhook_url
        if webhook_url is not None
        else getattr(settings, "DISCORD_DATAPIPES_WEBHOOK_URL", None)
    )

    current_step = ""
    try:
        for step_name in steps:
            current_step = step_name
            logger.info("Running Prop & Ferry ETL step: %s", step_name)
            runner(step_name)
    except Exception as exc:
        failed_utc = now_fn()
        duration_str = format_duration(int((failed_utc - started_utc).total_seconds()))
        failed_et = format_eastern(failed_utc)
        err_summary = str(exc).strip()[:300] or exc.__class__.__name__
        logger.exception("Prop & Ferry ETL failed at step '%s': %s", current_step, exc)

        desc = (
            ":x: **Prop & Ferry — Data Pipeline Failed**\n"
            f"**:warning: Failed Step:** `{current_step}`\n"
            f"```text\n{err_summary}\n```\n"
            f":clock3: **Scheduled:** {scheduled_et}\n"
            f":rocket: **Started:** {started_et} (+{queue_label} drift)\n"
            f":checkered_flag: **Failed:** {failed_et} ({duration_str})"
        )
        post_discord_alert(
            target_webhook,
            title="🚨 Prop & Ferry Data Pipeline Alert",
            description=desc,
            color=DISCORD_FAIL_COLOR,
            timestamp_iso=started_iso,
        )
        raise CommandError(f"Step '{current_step}' failed: {exc}") from exc

    finished_utc = now_fn()
    duration_str = format_duration(int((finished_utc - started_utc).total_seconds()))
    finished_et = format_eastern(finished_utc)
    desc = (
        ":airplane: :ship: **Prop & Ferry — Routes & Ferries Updated**\n"
        "Completed Duffel route ingestion, unenriched check, and ferry schedule scraping.\n\n"
        f":clock3: **Scheduled:** {scheduled_et}\n"
        f":rocket: **Started:** {started_et} (+{queue_label} drift)\n"
        f":checkered_flag: **Finished:** {finished_et} ({duration_str})"
    )
    post_discord_alert(
        target_webhook,
        title="✅ Prop & Ferry Data Pipeline Complete",
        description=desc,
        color=DISCORD_SUCCESS_COLOR,
        timestamp_iso=started_iso,
    )


class Command(BaseCommand):
    help = "Runs the in-app Wed/Sun 02:30 AM America/New_York ETL scheduler."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run the ETL pipeline immediately once and exit.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options.get("once"):
            execute_pipeline_once()
            return

        stop_event = threading.Event()
        self._register_signals(stop_event)

        self.stdout.write(
            "⏰ Prop & Ferry in-app scheduler started (Wed & Sun at 02:30 AM America/New_York)."
        )
        last_run_utc: datetime | None = None

        while not stop_event.is_set():
            now_utc = datetime.now(timezone.utc)
            anchor = now_utc if last_run_utc is None else max(now_utc, last_run_utc + MIN_RUN_GAP)
            next_run = compute_next_run(anchor)
            self.stdout.write(f"🗓️ Next scheduled run: {format_eastern(next_run)}")

            while not stop_event.is_set():
                remaining = (next_run - datetime.now(timezone.utc)).total_seconds()
                if remaining <= 0:
                    break
                stop_event.wait(timeout=min(remaining, MAX_SLEEP_SLICE_SECONDS))

            if stop_event.is_set():
                break

            try:
                execute_pipeline_once(scheduled_utc=next_run)
            except CommandError:
                pass
            finally:
                last_run_utc = max(next_run, datetime.now(timezone.utc))

        self.stdout.write("🛑 Prop & Ferry in-app scheduler stopped cleanly.")

    @staticmethod
    def _register_signals(stop_event: threading.Event) -> None:
        if threading.current_thread() is not threading.main_thread():
            return

        def _handle_stop(signum: int, _frame: Any) -> None:
            logger.info("Received signal %s; shutting down scheduler...", signum)
            stop_event.set()

        signal.signal(signal.SIGTERM, _handle_stop)
        signal.signal(signal.SIGINT, _handle_stop)

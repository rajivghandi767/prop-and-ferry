import os
import logging
import re
import time
import random
import requests
from typing import Any
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from core.models import Location, Route, Carrier, FlightInstance

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetches strictly DOM-centric flight routes via Duffel API for a bi-weekly 7-day rolling window."
    api_calls = 0

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--days",
            type=int,
            help="Override number of forecast days to fetch (defaults to bi-weekly Wed/Sun schedule)",
        )

    def get_target_dates(
        self, today: date, days_override: int | None = None
    ) -> list[str]:
        """
        Determines the rolling forecast window based on execution day:
        - Wednesday (weekday 2): Thursday, Friday, Saturday, Sunday (4 days)
        - Sunday (weekday 6): Monday, Tuesday, Wednesday (3 days)
        - Fallback/Manual: next 4 days
        """
        if days_override:
            num_days = days_override
        elif today.weekday() == 2:  # Wednesday
            num_days = 4
        elif today.weekday() == 6:  # Sunday
            num_days = 3
        else:
            num_days = 4

        return [
            (today + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, num_days + 1)
        ]

    def get_duffel_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {os.getenv('DUFFEL_ACCESS_TOKEN')}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def parse_duration(self, iso_str: Any) -> int:
        if not iso_str:
            return 0
        hours = int(match.group(1)) if (match := re.search(r"(\d+)H", iso_str)) else 0
        minutes = int(match.group(1)) if (match := re.search(r"(\d+)M", iso_str)) else 0
        return (hours * 60) + minutes

    def fetch_and_save(
        self, origin: str, dest: str, date_str: str, max_retries: int = 3
    ) -> bool:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        self.stdout.write(
            f"[API Calls: {self.api_calls + 1}] 🔎 Duffel: {origin}->{dest} on {date_str}",
            ending="\r",
        )

        self.api_calls += 1
        payload = {
            "data": {
                "slices": [
                    {"origin": origin, "destination": dest, "departure_date": date_str}
                ],
                "passengers": [{"type": "adult"}],
                "max_connections": 0,
            }
        }

        response_data: dict[str, Any] = {}
        success = False

        for attempt in range(max_retries + 1):
            try:
                res = requests.post(
                    "https://api.duffel.com/air/offer_requests",
                    json=payload,
                    headers=self.get_duffel_headers(),
                )
                if res.status_code == 429:
                    if attempt < max_retries:
                        retry_after = res.headers.get("Retry-After")
                        wait_time = (
                            float(retry_after)
                            if retry_after and retry_after.isdigit()
                            else (1.5 * (2**attempt)) + random.uniform(0.1, 0.5)
                        )
                        logger.warning(
                            f"HTTP 429 Rate limited for {origin}->{dest}. Waiting {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"Exceeded max retries ({max_retries}) for {origin}->{dest} on {date_str} due to rate limiting (HTTP 429)."
                        )
                        return False

                if res.status_code not in (200, 201):
                    logger.error(
                        f"Duffel request failed with status {res.status_code}: {res.text}"
                    )
                    return False

                response_data = res.json().get("data", {})
                success = True
                break
            except Exception as e:
                logger.error(f"Request failed: {e}")
                return False

        if not success:
            return False

        # Guaranteed baseline pacing delay across all queries (both empty and populated)
        time.sleep(0.5)

        offers = response_data.get("offers", [])

        # Overwrite logic: Drops existing records for this day to account for airline cancellations
        orig_loc = Location.objects.filter(code=origin).first()
        dest_loc = Location.objects.filter(code=dest).first()
        orig_codes = orig_loc.resolve_aliases() if orig_loc else [origin]
        dest_codes = dest_loc.resolve_aliases() if dest_loc else [dest]

        FlightInstance.objects.filter(
            route__origin__code__in=orig_codes,
            route__destination__code__in=dest_codes,
            date=target_date,
        ).delete()

        if not offers:
            # If Duffel returned 0 live offers, check if an active verified Route operates on this weekday
            found_day = str(target_date.isoweekday())
            known_routes = Route.objects.filter(
                origin__code__in=orig_codes,
                destination__code__in=dest_codes,
                is_active=True,
                days_of_operation__contains=found_day,
            )
            if known_routes.exists():
                for r in known_routes:
                    FlightInstance.objects.update_or_create(
                        route=r,
                        date=target_date,
                        defaults={
                            "price_amount": None,
                            "currency": "USD",
                            "available_seats": 0,
                            "cabin_class": "Sold Out",
                        },
                    )
                return True
            return False

        for offer in offers:
            price = offer.get("total_amount")
            currency = offer.get("total_currency")
            seats = 9  # Standardized availability assumption for the Stitcher

            for slice_obj in offer.get("slices", []):
                segments = slice_obj.get("segments", [])
                if len(segments) == 1:
                    cabin = (
                        segments[0]
                        .get("passengers", [{}])[0]
                        .get("cabin_class", "economy")
                    )
                    self._process_segment(
                        segments[0], date_str, price, currency, seats, cabin
                    )

        return True

    def _process_segment(
        self,
        segment: dict[str, Any],
        date_str: str,
        price: str,
        currency: str,
        seats: int,
        cabin: str,
    ) -> None:
        # 1. Safely handle null JSON objects by falling back to {}
        op_carrier = segment.get("operating_carrier") or {}
        mkt_carrier = segment.get("marketing_carrier") or {}
        aircraft_data = segment.get("aircraft") or {}

        # 2. Safely extract codes
        carrier_code = op_carrier.get("iata_code") or mkt_carrier.get(
            "iata_code", "UNK"
        )
        dep_code = segment["origin"]["iata_code"]
        arr_code = segment["destination"]["iata_code"]

        carrier, _ = Carrier.objects.get_or_create(
            code=carrier_code,
            defaults={
                "name": op_carrier.get("name", f"Airline {carrier_code}"),
                "carrier_type": "AIR",
            },
        )
        loc_dep, _ = Location.objects.get_or_create(
            code=dep_code, defaults={"name": dep_code}
        )
        loc_arr, _ = Location.objects.get_or_create(
            code=arr_code, defaults={"name": arr_code}
        )

        dep_time = segment["departing_at"].split("T")[1][:5]
        arr_time = segment["arriving_at"].split("T")[1][:5]
        flight_num = segment.get("operating_carrier_flight_number") or segment.get(
            "marketing_carrier_flight_number", ""
        )

        route, _ = Route.objects.update_or_create(
            origin=loc_dep,
            destination=loc_arr,
            carrier=carrier,
            departure_time=dep_time,
            defaults={
                "is_active": True,
                "duration_minutes": self.parse_duration(segment.get("duration")),
                "arrival_time": arr_time,
                "flight_number": f"{carrier_code} {flight_num}".strip(),
                "aircraft_type": aircraft_data.get("iata_code", ""),
            },
        )

        found_day = str(datetime.strptime(date_str, "%Y-%m-%d").isoweekday())
        current_days = route.days_of_operation or ""
        if found_day not in current_days:
            route.days_of_operation = "".join(sorted(current_days + found_day))
            route.save()

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        FlightInstance.objects.update_or_create(
            route=route,
            date=date_obj,
            defaults={
                "price_amount": price,
                "currency": currency,
                "available_seats": seats,
                "cabin_class": cabin,
            },
        )

    def handle(self, *args: Any, **kwargs: Any) -> None:
        self.stdout.write("✈️  Initializing Global Micro-Network Duffel Scraper...")

        if not os.getenv("DUFFEL_ACCESS_TOKEN"):
            self.stdout.write(
                self.style.ERROR("❌ Missing DUFFEL_ACCESS_TOKEN in environment.")
            )
            return

        today = datetime.now().date()
        deleted_flights, _ = FlightInstance.objects.filter(date__lt=today).delete()
        if deleted_flights:
            self.stdout.write(f"🧹 Pruned {deleted_flights} past flight instances.")

        days_override = kwargs.get("days")
        target_dates = self.get_target_dates(today, days_override=days_override)
        self.stdout.write(
            self.style.WARNING(
                f"\n--- TARGET ROLLING FORECAST ({len(target_dates)} DAYS): {', '.join(target_dates)} ---"
            )
        )

        # EIS pruned: interCaribbean Airways is not supported on Duffel NDC
        flight_hubs = ["ANU", "BGI", "SXM", "SJU", "SKB"]

        GATEWAY_ROUTES = {
            "MIA": ["SJU", "SXM", "SKB", "BGI", "FDF", "PTP"],
            "NYC": ["BGI", "ANU", "UVF", "SJU", "SXM", "SKB"],
            "CLT": ["ANU", "BGI", "UVF", "SJU", "SXM", "SKB"],
            "LON": ["ANU", "BGI", "SKB"],
            "PAR": ["PTP", "FDF"],
            "AMS": ["SXM"],
            "FRA": ["BGI"],
        }

        for date_str in target_dates:
            self.stdout.write(
                self.style.WARNING(f"\n--- Ingesting Schedule for {date_str} ---")
            )
            target_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            is_wed_or_sat = target_dt.isoweekday() in (3, 6)

            # 1. Direct Non-Stop Trunks to Dominica
            if is_wed_or_sat:
                # United Airlines operates EWR <-> DOM nonstop on Wednesdays and Saturdays
                self.fetch_and_save("EWR", "DOM", date_str)
                self.fetch_and_save("DOM", "EWR", date_str)

            # American Airlines operates MIA <-> DOM
            self.fetch_and_save("MIA", "DOM", date_str)
            self.fetch_and_save("DOM", "MIA", date_str)

            # 2. Regional Island Feeders into and out of Dominica
            for hub in flight_hubs:
                self.fetch_and_save(hub, "DOM", date_str)
                self.fetch_and_save("DOM", hub, date_str)

            # 3. International Gateway Feeder Corridors
            for gateway, valid_hubs in GATEWAY_ROUTES.items():
                for hub in valid_hubs:
                    self.fetch_and_save(gateway, hub, date_str)
                    if gateway in ("PAR", "LON"):
                        self.fetch_and_save(hub, gateway, date_str)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✨ DONE! Total usage: {self.api_calls} Duffel calls."
            )
        )
